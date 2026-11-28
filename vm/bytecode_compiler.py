"""
bytecode_compiler.py

Purpose:
Translates IR functions into VM bytecode. Handles instruction translation,
opcode mapping, fused operation insertion, instruction splitting, and
AES-256-CTR per-block encryption/decryption of bytecode.

Architectural Role:
Compilation layer between the IR generation pipeline and the VM
execution engine. Takes IrFunction objects and produces bytearray
bytecode ready for encryption and execution.

Security Relevance:
- Per-block AES-256-CTR encryption (block_size=64 bytes) with keys
  derived per block via SHA-256. Ensures that identical instruction
  sequences at different block offsets produce different ciphertext.
- secure_zero() helper attempts to zero sensitive buffers, though
  Python's immutable bytes still leak contents in memory dumps.
- The _Rng class uses a forward-only SHA-256 chain: each call to
  next() overwrites state with SHA-256(previous_state). This provides
  forward secrecy for register allocation (past register assignments
  cannot be reconstructed after the RNG advances).

Threat model: Bytecode extraction, static analysis, ciphertext-only
attacks on encrypted bytecode.

Key design rationale for CTR mode:
- No padding (avoids padding oracle attacks).
- Parallelizable.
- Random IV per block (from SHA-256 of block key).

Wrong keys and tampered containers are rejected by HMAC before decryption.
"""

from __future__ import annotations
import hashlib
import hmac
import os
import struct

from .vm_isa import VMInstruction, VMOpcode, VMOperand, _phase2_enabled
from irgen.compile import IrValue


def secure_zero(data):
    """
    Attempt to zero the contents of a mutable buffer.

    Works for bytearray and list. bytes objects are immutable and
    cannot be zeroed — caller should use bytearray for sensitive data.

    Security note: Python's garbage collector may leave copies of
    the data elsewhere in memory. This is a best-effort mitigation.
    """
    if isinstance(data, bytearray):
        for i in range(len(data)):
            data[i] = 0
    elif isinstance(data, list):
        for i in range(len(data)):
            data[i] = 0


def _import_ir():
    from irgen.compile import IrFunction, IrInstruction, IrValue, IrType
    return IrFunction, IrInstruction, IrValue, IrType


class BytecodeAuthenticationError(ValueError):
    """Raised when an encrypted bytecode container cannot be authenticated."""


_ENCRYPT_MAGIC = b"NVM1"
_ENCRYPT_VERSION = 1
_ENCRYPT_HEADER = struct.Struct(">4sBI")  # magic, version, block size
_ENCRYPT_NONCE_SIZE = 8
_ENCRYPT_TAG_SIZE = hashlib.sha256().digest_size
_ENCRYPT_OVERHEAD = _ENCRYPT_HEADER.size + _ENCRYPT_NONCE_SIZE + _ENCRYPT_TAG_SIZE
_MAX_BLOCK_SIZE = 1 << 20


def _validate_encryption_inputs(key: bytes, block_size: int) -> None:
    if len(key) != 32:
        raise ValueError("bytecode encryption key must be exactly 32 bytes")
    if not isinstance(block_size, int) or not 1 <= block_size <= _MAX_BLOCK_SIZE:
        raise ValueError(f"block_size must be between 1 and {_MAX_BLOCK_SIZE}")


def compile_to_bytecode(
    ir_function,
    opcode_map: dict[str, int] | None = None,
    seed: bytes | None = None,
) -> bytearray:
    """
    Compile an IR function to VM bytecode.

    Iterates over IR blocks and instructions, translating each to one
    or more VMInstructions, then applies fused operations and instruction
    splitting.

    Args:
        ir_function: An IrFunction object from irgen.compile.
        opcode_map: Optional dict mapping opcode names to logical opcodes.
        seed: Build seed for register allocation RNG.

    Security note: Register allocation uses a deterministic RNG seeded
    from the build seed. Register-to-value mappings are consistent
    across compilations with the same seed but unpredictable without it.
    """
    IrFunction, IrInstruction, IrValue, IrType = _import_ir()

    if opcode_map is None:
        opcode_map = {name: idx for idx, name in VMOpcode.LOGICAL_NAMES.items()}

    if seed is None:
        seed = os.urandom(16)

    rng = _Rng(seed)
    ctx: dict = {}
    _validate_register_allocation(ir_function)

    # Pass 1: translate instructions and record each block's BYTE offset.
    # The VM's PC is a byte offset into the bytecode, so jump targets must be
    # real offsets -- the old code emitted md5(label)[:4] as the target, which
    # lands far past the end of the bytecode and halts the VM immediately.
    block_lists = []
    block_offsets: dict = {}
    offset = 0
    for block in ir_function.blocks:
        block_offsets[block.label] = offset
        insts = []
        for inst in block.instructions:
            vm_insts = _translate_instruction(inst, opcode_map, rng, base=offset, ctx=ctx)
            for vm_inst in vm_insts:
                offset += len(vm_inst.encode(opcode_map))
            insts.extend(vm_insts)
        if block.terminator:
            # Measure the terminator's length here (targets resolve to 0 in
            # this pass; ABS_ADDR is a fixed 4 bytes, so the length is final
            # and pass 2 re-translates with the real offsets).
            for vm_inst in _translate_terminator(block.terminator, opcode_map, rng,
                                                 label_offsets={}):
                offset += len(vm_inst.encode(opcode_map))
        block_lists.append((block, insts))
    total = offset
    # "exit" and unknown labels land one past the end: PC >= len(bytecode)
    # halts the VM.
    block_offsets["exit"] = total

    # Pass 2: encode instructions (patching CALL label placeholders to real
    # block offsets / end-of-bytecode), then terminators with resolved offsets.
    bytecode = bytearray()
    for block, insts in block_lists:
        for vm_inst in insts:
            ops = []
            for op in vm_inst.operands:
                if isinstance(op, tuple) and op[0] == VMOperand.ABS_ADDR and op[1] == -1:
                    # placeholder for an unresolved call target
                    ops.append((VMOperand.ABS_ADDR, total))
                else:
                    ops.append(op)
            if ops != list(vm_inst.operands):
                vm_inst = VMInstruction(vm_inst.opcode, ops)
            bytecode.extend(vm_inst.encode(opcode_map))
        if block.terminator:
            for vm_inst in _translate_terminator(block.terminator, opcode_map, rng,
                                                 label_offsets=block_offsets):
                bytecode.extend(vm_inst.encode(opcode_map))

    bytecode = _apply_fused_operations(bytecode, opcode_map, rng)
    bytecode = _apply_instruction_splitting(bytecode, opcode_map, rng)

    return bytecode


def _get_ir_types():
    from irgen.compile import IrValue as _IrValue, IrType as _IrType
    return _IrValue, _IrType


_INTEGER_BITS = {"i1": 1, "i8": 8, "i16": 16, "i32": 32, "i64": 64}


def _ir_width(ir_type) -> int:
    """Return the VM bit width for an IR integer/pointer type."""
    kind = getattr(ir_type, "kind", None)
    if kind in _INTEGER_BITS:
        return _INTEGER_BITS[kind]
    if kind == "ptr":
        return 64
    raise NotImplementedError(f"unsupported IR type '{kind}' for VM integer compilation")


def _next_rng_value(rng) -> int:
    if hasattr(rng, "next"):
        return rng.next()
    return rng.randint(0, 0xFFFFFFFF)


def _fresh_reg(rng, forbidden: set[int]) -> int:
    for _ in range(64):
        reg = _next_rng_value(rng) % 12 + 1
        if reg not in forbidden:
            return reg
    raise RuntimeError("could not allocate a temporary VM register")


def _load_constant(reg: int, value: int, width: int, rng, out: list) -> None:
    """Materialize a width-truncated integer using existing 16-bit MOVs.

    Build high-to-low so each lower chunk is shifted into its actual bit
    position before OR-ing. Scratch registers are saved/restored on the value
    stack, preserving unrelated live values.
    """
    mask = (1 << width) - 1
    value = int(value) & mask
    high_shift = ((width - 1) // 16) * 16
    high_chunk = (value >> high_shift) & 0xFFFF
    out.append(VMInstruction(VMOpcode.MOV, [
        (VMOperand.REG, reg), (VMOperand.IMM8, high_chunk & 0xFF),
        (VMOperand.IMM8, (high_chunk >> 8) & 0xFF),
    ]))
    if width <= 16:
        return

    shift_reg = _fresh_reg(rng, {reg})
    out.append(VMInstruction(VMOpcode.PUSH, [(VMOperand.REG, shift_reg)]))
    out.append(VMInstruction(VMOpcode.MOV, [
        (VMOperand.REG, shift_reg), (VMOperand.IMM8, 16), (VMOperand.IMM8, 0),
    ]))
    for shift in range(high_shift - 16, -1, -16):
        out.append(VMInstruction(VMOpcode.SHL, [
            (VMOperand.REG, reg), (VMOperand.REG, shift_reg),
        ]))
        chunk = (value >> shift) & 0xFFFF
        if chunk:
            temp = _fresh_reg(rng, {reg, shift_reg})
            out.append(VMInstruction(VMOpcode.PUSH, [(VMOperand.REG, temp)]))
            out.append(VMInstruction(VMOpcode.MOV, [
                (VMOperand.REG, temp), (VMOperand.IMM8, chunk & 0xFF),
                (VMOperand.IMM8, (chunk >> 8) & 0xFF),
            ]))
            out.append(VMInstruction(VMOpcode.OR, [
                (VMOperand.REG, reg), (VMOperand.REG, temp),
            ]))
            out.append(VMInstruction(VMOpcode.POP, [(VMOperand.REG, temp)]))
    out.append(VMInstruction(VMOpcode.POP, [(VMOperand.REG, shift_reg)]))


def _mask_reg(reg: int, width: int, rng, out: list) -> None:
    """Truncate ``reg`` to the IR result width after an arithmetic op."""
    if width >= 64:
        return
    temp = _fresh_reg(rng, {reg})
    out.append(VMInstruction(VMOpcode.PUSH, [(VMOperand.REG, temp)]))
    _load_constant(temp, (1 << width) - 1, width, rng, out)
    out.append(VMInstruction(VMOpcode.AND, [
        (VMOperand.REG, reg), (VMOperand.REG, temp),
    ]))
    out.append(VMInstruction(VMOpcode.POP, [(VMOperand.REG, temp)]))



def _scratch_regs(rng, forbidden: set[int], count: int) -> list[int]:
    """Allocate distinct scratch registers, all saved/restored by callers."""
    regs = []
    blocked = set(forbidden)
    for _ in range(count):
        reg = _fresh_reg(rng, blocked)
        regs.append(reg)
        blocked.add(reg)
    return regs


def _emit_reg_copy(src: int, dst: int) -> list[VMInstruction]:
    return [VMInstruction(VMOpcode.PUSH, [(VMOperand.REG, src)]),
            VMInstruction(VMOpcode.POP, [(VMOperand.REG, dst)])]


def _width_bytes(width: int) -> int:
    return max(1, (width + 7) // 8)


def _emit_store_memory(src: int, addr: int, width: int, rng) -> list[VMInstruction]:
    """Store a fixed-width integer little-endian through byte memory."""
    nbytes = _width_bytes(width)
    s_addr, s_val, s_tmp = _scratch_regs(rng, {src, addr}, 3)
    out = [VMInstruction(VMOpcode.PUSH, [(VMOperand.REG, s_addr)]),
           VMInstruction(VMOpcode.PUSH, [(VMOperand.REG, s_val)]),
           VMInstruction(VMOpcode.PUSH, [(VMOperand.REG, s_tmp)])]
    out.extend(_emit_reg_copy(addr, s_addr))
    for index in range(nbytes):
        out.extend(_emit_reg_copy(src, s_val))
        if index:
            out.append(VMInstruction(VMOpcode.MOV, [
                (VMOperand.REG, s_tmp), (VMOperand.IMM8, (8 * index) & 0xFF),
                (VMOperand.IMM8, (8 * index) >> 8)]))
            out.append(VMInstruction(VMOpcode.SHR, [
                (VMOperand.REG, s_val), (VMOperand.REG, s_tmp)]))
        out.append(VMInstruction(VMOpcode.STORE, [
            (VMOperand.REG, s_val), (VMOperand.REG, s_addr)]))
        if index + 1 < nbytes:
            out.append(VMInstruction(VMOpcode.MOV, [
                (VMOperand.REG, s_tmp), (VMOperand.IMM8, 1), (VMOperand.IMM8, 0)]))
            out.append(VMInstruction(VMOpcode.ADD, [
                (VMOperand.REG, s_addr), (VMOperand.REG, s_tmp)]))
    out.extend([VMInstruction(VMOpcode.POP, [(VMOperand.REG, s_tmp)]),
                VMInstruction(VMOpcode.POP, [(VMOperand.REG, s_val)]),
                VMInstruction(VMOpcode.POP, [(VMOperand.REG, s_addr)])])
    return out


def _emit_load_memory(dst: int, addr: int, width: int, rng) -> list[VMInstruction]:
    """Load a fixed-width little-endian integer through byte memory."""
    nbytes = _width_bytes(width)
    s_addr, s_val, s_tmp = _scratch_regs(rng, {dst, addr}, 3)
    out = [VMInstruction(VMOpcode.PUSH, [(VMOperand.REG, s_addr)]),
           VMInstruction(VMOpcode.PUSH, [(VMOperand.REG, s_val)]),
           VMInstruction(VMOpcode.PUSH, [(VMOperand.REG, s_tmp)])]
    out.extend(_emit_reg_copy(addr, s_addr))
    out.append(VMInstruction(VMOpcode.MOV, [
        (VMOperand.REG, dst), (VMOperand.IMM8, 0), (VMOperand.IMM8, 0)]))
    for index in range(nbytes):
        out.append(VMInstruction(VMOpcode.LOAD, [
            (VMOperand.REG, s_val), (VMOperand.REG, s_addr)]))
        if index:
            out.append(VMInstruction(VMOpcode.MOV, [
                (VMOperand.REG, s_tmp), (VMOperand.IMM8, (8 * index) & 0xFF),
                (VMOperand.IMM8, (8 * index) >> 8)]))
            out.append(VMInstruction(VMOpcode.SHL, [
                (VMOperand.REG, s_val), (VMOperand.REG, s_tmp)]))
        out.append(VMInstruction(VMOpcode.OR, [
            (VMOperand.REG, dst), (VMOperand.REG, s_val)]))
        if index + 1 < nbytes:
            out.append(VMInstruction(VMOpcode.MOV, [
                (VMOperand.REG, s_tmp), (VMOperand.IMM8, 1), (VMOperand.IMM8, 0)]))
            out.append(VMInstruction(VMOpcode.ADD, [
                (VMOperand.REG, s_addr), (VMOperand.REG, s_tmp)]))
    out.extend([VMInstruction(VMOpcode.POP, [(VMOperand.REG, s_tmp)]),
                VMInstruction(VMOpcode.POP, [(VMOperand.REG, s_val)]),
                VMInstruction(VMOpcode.POP, [(VMOperand.REG, s_addr)])])
    return out

def _translate_instruction(ir_inst, opcode_map, rng, base: int = 0, ctx: dict | None = None) -> list[VMInstruction]:
    """
    Translate a single IR instruction to one or more VM instructions.

    Handles supported arithmetic, memory, control flow, alloca, ret and
    comparisons.  Calls, phi nodes, GEPs and unknown ops fail closed because
    this compiler has no calling convention, predecessor selection or typed
    pointer arithmetic for them.

    Security note: The IR-to-VM opcode mapping is hard-coded in the
    ir_to_vm dict. An attacker who knows this mapping can reverse
    the translation. The ephemeral ISA pipeline (ephemeral_isa.py)
    adds a second obfuscation layer on top of this.
    """
    IrValue, IrType = _get_ir_types()
    opcode = ir_inst.opcode
    operands = ir_inst.operands

    ir_to_vm = {
        "add": VMOpcode.ADD,
        "sub": VMOpcode.SUB,
        "mul": VMOpcode.MUL,
        "div": VMOpcode.DIV,
        "mod": VMOpcode.MOD,
        "and": VMOpcode.AND,
        "or": VMOpcode.OR,
        "xor": VMOpcode.XOR,
        "shl": VMOpcode.SHL,
        "shr": VMOpcode.SHR,
        "nop": VMOpcode.NOP,
    }

    if opcode == "nop":
        return [VMInstruction(VMOpcode.NOP)]

    if opcode in ir_to_vm:
        vm_op = ir_to_vm[opcode]
        # VM arithmetic is in-place: ADD dst, src means dst = dst + src.
        # Copy the first operand into the result register first (PUSH/POP,
        # the ISA has no reg-reg MOV), then apply the second operand.
        pre: list[VMInstruction] = []
        rr = _value_to_reg(ir_inst.result, rng)
        ra = _materialize(operands[0], rng, pre) if operands else 0
        rb = _materialize(operands[1], rng, pre) if len(operands) > 1 else 0
        sequence = pre + [
            VMInstruction(VMOpcode.PUSH, [(VMOperand.REG, ra)]),
            VMInstruction(VMOpcode.POP, [(VMOperand.REG, rr)]),
            VMInstruction(vm_op, [(VMOperand.REG, rr), (VMOperand.REG, rb)]),
        ]
        if opcode != "nop":
            _mask_reg(rr, _ir_width(ir_inst.result_type), rng, sequence)
        return sequence

    if opcode == "load":
        # VM LOAD reads (dst, addr_reg): the IR instruction has the address
        # as operand and the result as ir_inst.result. Emitting only one
        # register desynchronised the whole stream.
        pre: list[VMInstruction] = []
        addr = _materialize(operands[0], rng, pre) if operands else 0
        dst = _value_to_reg(ir_inst.result, rng)
        return pre + _emit_load_memory(dst, addr, _ir_width(ir_inst.result_type), rng)

    if opcode == "store":
        # VM STORE reads (src, addr_reg).
        pre: list[VMInstruction] = []
        src = _materialize(operands[0], rng, pre) if len(operands) > 0 else 0
        addr = _materialize(operands[1], rng, pre) if len(operands) > 1 else 0
        return pre + _emit_store_memory(src, addr, _ir_width(ir_inst.result_type), rng)

    if opcode == "alloca":
        # Allocate a distinct memory slot for the pointer: MOV the slot
        # address (16-bit immediate) into the result register. The old LEA
        # emission was a no-op placeholder, so every alloca collided at 0.
        slot = ctx.setdefault("alloca", 0)
        ctx["alloca"] = slot + _width_bytes(_ir_width(ir_inst.result_type))
        if ctx["alloca"] > 65536:
            raise NotImplementedError("VM alloca memory exceeds the 64KB address space")
        return [VMInstruction(VMOpcode.MOV, [
            (VMOperand.REG, _value_to_reg(ir_inst.result, rng)),
            (VMOperand.IMM8, slot & 0xFF), (VMOperand.IMM8, (slot >> 8) & 0xFF)])]

    if opcode == "call":
        raise NotImplementedError(
            "VM compilation does not support call: no calling convention for "
            "arguments, return values, or stack frames")

    if opcode == "ret":
        # RET pops the return address; it carries no operand bytes.
        return [VMInstruction(VMOpcode.RET)]

    if opcode in ("zext", "bitcast"):
        # Python lowers boolean expressions to i1 followed by zext i1->i32.
        # Both operations are register-width copies in this VM; emitting a
        # NOP here left every comparison result at its initial zero value.
        pre: list[VMInstruction] = []
        src = _materialize(operands[0], rng, pre) if operands else 0
        dst = _value_to_reg(ir_inst.result, rng)
        return pre + [
            VMInstruction(VMOpcode.PUSH, [(VMOperand.REG, src)]),
            VMInstruction(VMOpcode.POP, [(VMOperand.REG, dst)]),
        ]

    if opcode == "phi":
        raise NotImplementedError(
            "VM compilation does not support phi: predecessor-aware value selection is unavailable")

    if opcode == "gep":
        raise NotImplementedError(
            "VM compilation does not support gep: typed pointer arithmetic is unavailable")

    if opcode in ("eq", "ne", "lt", "le", "gt", "ge"):
        # Direct typed comparison avoids SUB flag overflow (for example
        # INT32_MAX - INT32_MIN) and works for both i32 and i64 bit patterns.
        pre: list[VMInstruction] = []
        ra = _materialize(operands[0], rng, pre) if operands else 0
        rb = _materialize(operands[1], rng, pre) if len(operands) > 1 else 0
        rr = _value_to_reg(ir_inst.result, rng)
        predicate = {"eq": 0, "ne": 1, "lt": 2,
                     "le": 3, "gt": 4, "ge": 5}[opcode]
        return pre + [VMInstruction(VMOpcode.CMP, [
            (VMOperand.REG, rr), (VMOperand.REG, ra),
            (VMOperand.REG, rb), (VMOperand.IMM8, predicate),
        ])]

    raise NotImplementedError(f"unsupported IR opcode '{opcode}' for VM compilation")


def _translate_terminator(term_inst, opcode_map, rng,
                          label_offsets: dict | None = None) -> list[VMInstruction]:
    """
    Translate a block terminator IR instruction to VM instruction(s).

    Handles jmp, br (conditional branch -> FUSED_CMP_JMP), ret, and
    unreachable. Jump targets are BYTE OFFSETS resolved by the caller's
    two-pass layout (the VM's PC is a byte offset; hashing labels into
    32-bit values made every branch land past the end of the bytecode).
    """
    opcode = term_inst.opcode
    operands = term_inst.operands
    label_offsets = label_offsets or {}

    def resolve(target) -> int:
        if isinstance(target, str):
            return label_offsets.get(target, label_offsets.get("exit", 0))
        return int(target)

    if opcode == "jmp":
        target = operands[0] if operands else "exit"
        return [VMInstruction(VMOpcode.JMP, [(VMOperand.ABS_ADDR, resolve(target))])]

    if opcode == "br":
        cond = operands[0] if operands else None
        true_label = operands[1] if len(operands) > 1 else "exit"
        false_label = operands[2] if len(operands) > 2 else "exit"
        true_val = resolve(true_label)
        false_val = resolve(false_label)
        cond_reg = _value_to_reg(cond, rng) if hasattr(cond, 'id') else 0
        vm_ops = [(VMOperand.REG, cond_reg)]
        vm_ops.append((VMOperand.ABS_ADDR, true_val))
        vm_ops.append((VMOperand.ABS_ADDR, false_val))
        return [VMInstruction(VMOpcode.FUSED_CMP_JMP, vm_ops)]

    if opcode == "ret":
        # Materialize the return value into register 1 (the return
        # register): constants via MOV imm, values via the memory slot at
        # address 0 (reg 0 holds 0). The old code dropped the value entirely.
        if len(operands) > 1 and operands[1] is not None:
            v = operands[1]
            if isinstance(v, int):
                pre: list[VMInstruction] = []
                width = _ir_width(operands[0]) if operands else 64
                _load_constant(1, v, width, rng, pre)
                return pre + [VMInstruction(VMOpcode.RET)]
            if hasattr(v, 'id'):
                pre: list[VMInstruction] = []
                r = _materialize(v, rng, pre)
                # Copy through the value stack, not byte-addressed memory:
                # STORE/LOAD truncates to 8 bits and corrupted every computed
                # return value above 255.
                return pre + [VMInstruction(VMOpcode.PUSH, [(VMOperand.REG, r)]),
                              VMInstruction(VMOpcode.POP, [(VMOperand.REG, 1)]),
                              VMInstruction(VMOpcode.RET)]
        return [VMInstruction(VMOpcode.RET)]

    if opcode == "unreachable":
        return [VMInstruction(VMOpcode.NOP)]

    raise NotImplementedError(f"unsupported IR terminator '{opcode}' for VM compilation")


def _materialize(op, rng, out: list) -> int:
    """Return a register holding ``op``, emitting a MOV for constants.

    The interpreter reads register indices for arithmetic operands, so a
    constant has to be loaded into a register first.
    """
    if isinstance(op, IrValue):
        # Constants are IrValues with integer-literal names (see
        # irgen.compile.IrValue); they still need a MOV into their register.
        try:
            val = int(op.name)
        except (ValueError, AttributeError, TypeError):
            return _value_to_reg(op, rng)
        reg = _value_to_reg(op, rng)
        _load_constant(reg, val, _ir_width(op.type), rng, out)
        return reg
    reg = _value_to_reg(op, rng) if hasattr(op, 'id') else rng.randint(1, 12)
    if isinstance(op, str):
        # A salted builtin hash() changes between processes; the VM
        # bytecode must be reproducible and the C/Python interpreters
        # must agree on the value.
        val = int.from_bytes(
            hashlib.blake2b(op.encode(), digest_size=2).digest(), "little")
    else:
        val = int(op) & 0xFFFF if hasattr(op, '__int__') else 0
    _load_constant(reg, val, 64, rng, out)
    return reg


def _iter_ir_values(ir_function):
    """Yield every SSA value referenced or defined by a function."""
    for block in ir_function.blocks:
        for inst in block.instructions:
            if inst.result is not None:
                yield inst.result
            for op in inst.operands:
                if isinstance(op, IrValue):
                    yield op
                elif isinstance(op, tuple) and op and isinstance(op[0], IrValue):
                    yield op[0]
        if block.terminator:
            for op in block.terminator.operands:
                if isinstance(op, IrValue):
                    yield op


def _validate_register_allocation(ir_function) -> None:
    """Fail closed when the legacy modulo mapping would merge SSA values.

    The VM has no spill machinery.  ``id % 12`` register selection is safe
    only when no two distinct values in this function collide; silently
    allowing a collision overwrites a live value with an unrelated one.
    """
    owners: dict[int, IrValue] = {}
    for value in _iter_ir_values(ir_function):
        reg = _value_to_reg(value, None)
        old = owners.get(reg)
        if old is not None and old.id != value.id:
            raise NotImplementedError(
                "VM register allocation collision: values "
                f"{old.name} and {value.name} both map to r{reg}; "
                "spilling/liveness allocation is required")
        owners[reg] = value


def _value_to_reg(value, rng) -> int:
    """
    Map an IR value to a VM register.

    If the value has an 'id' attribute, the register is derived from
    id % 12 + 1 (registers 1-12, avoiding the reserved FLAGS=13, PC=14
    and SP=15). Otherwise, a fresh register is allocated from the RNG.

    Security note: Register allocation is deterministic for the same
    seed. Each compilation with the same seed produces the same
    register assignments.
    """
    if hasattr(value, 'id'):
        return (value.id % 12) + 1
    return rng.next() % 12 + 1


def _label_to_int(label: str) -> int:
    """Convert a label string to a 32-bit integer via MD5 hash."""
    h = hashlib.md5(label.encode()).digest()
    return struct.unpack('<I', h[:4])[0]


def _apply_fused_operations(bytecode: bytearray, opcode_map, rng) -> bytearray:
    """
    Apply fused operation transforms to bytecode (placeholder).

    Requires Advanced Protection to be enabled. Currently returns
    bytecode unchanged. Future: replace sequences of instructions
    with fused opcodes (e.g., LOAD+ADD+STORE -> FUSED_LOAD_ADD_STORE).
    """
    if not _phase2_enabled():
        raise RuntimeError("Advanced Protection must be enabled for fused operations")
    return bytecode


def _apply_instruction_splitting(bytecode: bytearray, opcode_map, rng) -> bytearray:
    """
    Apply instruction splitting transforms (placeholder).

    Requires Advanced Protection to be enabled. Currently returns
    bytecode unchanged. Future: split complex instructions into
    multiple smaller instructions with interleaved operations.
    """
    if not _phase2_enabled():
        raise RuntimeError("Advanced Protection must be enabled for instruction splitting")
    return bytecode


def _crypt_bytecode(plaintext: bytes, key: bytes, block_size: int, nonce: bytes) -> bytes:
    """Apply the per-block AES-256-CTR transform used by container format v1."""
    from encrypt.aes import derive_block_key, aes256_ctr_keystream

    encrypted = bytearray()
    for offset in range(0, len(plaintext), block_size):
        block = plaintext[offset:offset + block_size]
        block_key = derive_block_key(key, offset // block_size, len(block))
        block_nonce = hashlib.sha256(block_key + nonce).digest()[:_ENCRYPT_NONCE_SIZE]
        keystream = aes256_ctr_keystream(block_key, block_nonce, len(block))
        encrypted.extend(p ^ k for p, k in zip(block, keystream))
    return bytes(encrypted)


def encrypt_bytecode(
    bytecode: bytearray,
    key: bytes,
    block_size: int = 64,
) -> bytes:
    """Encrypt bytecode in the authenticated ``NVM1`` container format.

    The wire layout is ``header || nonce || ciphertext || HMAC-SHA256``.
    The header binds the magic, format version and block size.  The MAC covers
    the header, nonce and ciphertext and is verified before any decryption.
    Empty plaintext still produces a versioned, authenticated container.

    WARNING: key is bytes (immutable) and cannot be explicitly zeroed.
    """
    _validate_encryption_inputs(key, block_size)
    key = bytes(key)
    plaintext = bytes(bytecode)
    nonce = os.urandom(_ENCRYPT_NONCE_SIZE)
    header = _ENCRYPT_HEADER.pack(_ENCRYPT_MAGIC, _ENCRYPT_VERSION, block_size)
    ciphertext = _crypt_bytecode(plaintext, key, block_size, nonce)
    tag = hmac.new(key, header + nonce + ciphertext, hashlib.sha256).digest()
    return header + nonce + ciphertext + tag


def decrypt_bytecode(
    encrypted: bytes,
    key: bytes,
    block_size: int = 64,
) -> bytearray:
    """Authenticate and decrypt an ``NVM1`` bytecode container.

    ``block_size`` is retained for API compatibility; the authenticated header
    is authoritative.  Legacy unauthenticated ciphertext, wrong keys, truncated
    data and any tampering raise :class:`BytecodeAuthenticationError` before
    the CTR transform runs.
    """
    del block_size
    if not key:
        raise BytecodeAuthenticationError(
            "bytecode authentication failed: wrong key or tampered container")
    data = bytes(encrypted)
    if len(data) < _ENCRYPT_OVERHEAD:
        raise BytecodeAuthenticationError(
            "bytecode authentication failed: wrong key or tampered container")

    header = data[:_ENCRYPT_HEADER.size]
    magic, version, stored_block_size = _ENCRYPT_HEADER.unpack(header)
    if magic != _ENCRYPT_MAGIC or version != _ENCRYPT_VERSION:
        raise BytecodeAuthenticationError(
            "bytecode authentication failed: wrong key or tampered container")
    try:
        _validate_encryption_inputs(key, stored_block_size)
    except ValueError as exc:
        raise BytecodeAuthenticationError(
            "bytecode authentication failed: wrong key or tampered container") from exc
    nonce_end = _ENCRYPT_HEADER.size + _ENCRYPT_NONCE_SIZE
    nonce = data[_ENCRYPT_HEADER.size:nonce_end]
    ciphertext = data[nonce_end:-_ENCRYPT_TAG_SIZE]
    tag = data[-_ENCRYPT_TAG_SIZE:]
    expected = hmac.new(key, header + nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        raise BytecodeAuthenticationError(
            "bytecode authentication failed: wrong key or tampered container")
    return bytearray(_crypt_bytecode(ciphertext, key, stored_block_size, nonce))


class _Rng:
    """Deterministic forward-only SHA-256 register-allocation PRNG."""

    def __init__(self, seed: bytes):
        self.state = hashlib.sha256(seed).digest()

    def next(self) -> int:
        self.state = hashlib.sha256(self.state).digest()
        return int.from_bytes(self.state[:4], "little")

    def randint(self, low: int, high: int) -> int:
        if high < low:
            raise ValueError("randint upper bound is below lower bound")
        span = high - low + 1
        return low + self.next() % span
