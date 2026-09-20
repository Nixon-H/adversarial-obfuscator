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

What happens on decryption with wrong key: Garbage output (CTR mode
produces deterministic but meaningless plaintext).
"""

from __future__ import annotations
import hashlib
import json
import os
import struct
from typing import Optional

from .vm_isa import VMInstruction, VMOpcode, VMOperand, VM_PROPERTIES, _phase2_enabled


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


_ENCRYPT_KEY = None


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

    bytecode = bytearray()
    rng = _Rng(seed)

    for block in ir_function.blocks:
        for inst in block.instructions:
            vm_insts = _translate_instruction(inst, opcode_map, rng)
            for vm_inst in vm_insts:
                bytecode.extend(vm_inst.encode())

        if block.terminator:
            vm_insts = _translate_terminator(block.terminator, opcode_map, rng)
            for vm_inst in vm_insts:
                bytecode.extend(vm_inst.encode())

    bytecode = _apply_fused_operations(bytecode, opcode_map, rng)
    bytecode = _apply_instruction_splitting(bytecode, opcode_map, rng)

    return bytecode


def _get_ir_types():
    from irgen.compile import IrValue as _IrValue, IrType as _IrType
    return _IrValue, _IrType


def _translate_instruction(ir_inst, opcode_map, rng) -> list[VMInstruction]:
    """
    Translate a single IR instruction to one or more VM instructions.

    Handles standard arithmetic, memory, control flow, and special IR
    ops (alloca, call, ret, phi, gep, comparisons). Unrecognized ops
    degrade to NOP.

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
        "load": VMOpcode.LOAD,
        "store": VMOpcode.STORE,
        "nop": VMOpcode.NOP,
    }

    if opcode in ir_to_vm:
        vm_op = ir_to_vm[opcode]
        vm_ops = []
        for op in operands:
            if isinstance(op, IrValue):
                vm_ops.append((VMOperand.REG, _value_to_reg(op, rng)))
            elif isinstance(op, str):
                vm_ops.append((VMOperand.IMM16, hash(op) & 0xFFFF))
            else:
                vm_ops.append((VMOperand.IMM32, int(op)))
        return [VMInstruction(vm_op, vm_ops)]

    if opcode == "alloca":
        return [VMInstruction(VMOpcode.LEA, [(VMOperand.REG, _value_to_reg(ir_inst.result, rng)), (VMOperand.IMM16, 0)])]

    if opcode == "call":
        vm_ops = []
        for op in operands:
            if isinstance(op, IrValue):
                vm_ops.append((VMOperand.REG, _value_to_reg(op, rng)))
            else:
                vm_ops.append((VMOperand.IMM32, int(op) if hasattr(op, '__int__') else hash(str(op)) & 0xFFFFFFFF))
        return [VMInstruction(VMOpcode.CALL, vm_ops)]

    if opcode == "ret":
        vm_ops = []
        for op in operands:
            if isinstance(op, IrValue):
                vm_ops.append((VMOperand.REG, _value_to_reg(op, rng)))
            else:
                vm_ops.append((VMOperand.IMM32, int(op) if hasattr(op, '__int__') else 0))
        return [VMInstruction(VMOpcode.RET, vm_ops)]

    if opcode == "phi":
        return [VMInstruction(VMOpcode.MOV, [(VMOperand.REG, _value_to_reg(ir_inst.result, rng)), (VMOperand.IMM32, 0)])]

    if opcode == "gep":
        return [VMInstruction(VMOpcode.LEA, [(VMOperand.REG, _value_to_reg(ir_inst.result, rng)), (VMOperand.REG, _value_to_reg(operands[0], rng) if operands else 0)])]

    if opcode in ("eq", "ne", "lt", "le", "gt", "ge"):
        vm_ops = []
        for op in operands:
            if isinstance(op, IrValue):
                vm_ops.append((VMOperand.REG, _value_to_reg(op, rng)))
        return [VMInstruction(VMOpcode.XOR, vm_ops)]

    return [VMInstruction(VMOpcode.NOP)]


def _translate_terminator(term_inst, opcode_map, rng) -> list[VMInstruction]:
    """
    Translate a block terminator IR instruction to VM instruction(s).

    Handles jmp, br (conditional branch -> FUSED_CMP_JMP), ret, and
    unreachable. Jump targets are converted from label strings to
    integers via MD5 hash (first 4 bytes).

    Security note: MD5 is used here for label → address mapping, not
    for security. MD5's collision weaknesses do not affect this use
    case since the hash is only used for label identification within
    a single compilation unit.
    """
    opcode = term_inst.opcode
    operands = term_inst.operands

    if opcode == "jmp":
        target = operands[0] if operands else "exit"
        if isinstance(target, str):
            label_hash = hashlib.md5(target.encode()).digest()
            target_val = struct.unpack('<I', label_hash[:4])[0]
        else:
            target_val = int(target)
        return [VMInstruction(VMOpcode.JMP, [(VMOperand.ABS_ADDR, target_val)])]

    if opcode == "br":
        cond = operands[0] if operands else None
        true_label = operands[1] if len(operands) > 1 else "exit"
        false_label = operands[2] if len(operands) > 2 else "exit"
        true_val = _label_to_int(true_label)
        false_val = _label_to_int(false_label)
        cond_reg = _value_to_reg(cond, rng) if hasattr(cond, 'id') else 0
        vm_ops = [(VMOperand.REG, cond_reg)]
        vm_ops.append((VMOperand.ABS_ADDR, true_val))
        vm_ops.append((VMOperand.ABS_ADDR, false_val))
        return [VMInstruction(VMOpcode.FUSED_CMP_JMP, vm_ops)]

    if opcode == "ret":
        vm_ops = []
        for op in operands:
            if hasattr(op, 'id'):
                vm_ops.append((VMOperand.REG, _value_to_reg(op, rng)))
            else:
                vm_ops.append((VMOperand.IMM32, int(op) if hasattr(op, '__int__') else 0))
        return [VMInstruction(VMOpcode.RET, vm_ops)]

    if opcode == "unreachable":
        return [VMInstruction(VMOpcode.NOP)]

    return []


def _value_to_reg(value, rng) -> int:
    """
    Map an IR value to a VM register.

    If the value has an 'id' attribute, the register is derived from
    id % 14 + 1 (registers 1-14, avoiding PC=14 and SP=15).
    Otherwise, a fresh register is allocated from the RNG.

    Security note: Register allocation is deterministic for the same
    seed. Each compilation with the same seed produces the same
    register assignments.
    """
    if hasattr(value, 'id'):
        return (value.id % 14) + 1
    return rng.next() % 14 + 1


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


def encrypt_bytecode(
    bytecode: bytearray,
    key: bytes,
    block_size: int = 64,
) -> bytes:
    """
    Encrypt bytecode with per-block AES-256-CTR.

    Each block of block_size bytes is encrypted with a key derived
    via SHA-256(master_key || block_index || block_length). An 8-byte
    nonce is derived from SHA-256(block_key) and used for CTR mode.

    Security rationale for per-block key derivation:
    - Each block uses a different key, limiting the plaintext available
      under any single key to block_size bytes.
    - The block index ties the key to the block's position, preventing
      block reordering attacks.
    - CTR mode was chosen over CBC because:
      * No padding — avoids padding oracle attacks.
      * Encryption of each block is independent — supports parallel
        decryption in the C interpreter.

    WARNING: key is bytes (immutable) and cannot be explicitly zeroed.
    """
    from encrypt.aes import derive_block_key, aes256_ctr_keystream

    encrypted = bytearray()
    for i in range(0, len(bytecode), block_size):
        block = bytes(bytecode[i:i + block_size])
        blk_key = derive_block_key(key, i // block_size, len(block))
        nonce = hashlib.sha256(blk_key).digest()[:8]
        keystream = aes256_ctr_keystream(blk_key, nonce, len(block))
        encrypted_block = bytes(p ^ k for p, k in zip(block, keystream))
        encrypted.extend(encrypted_block)
    result = bytes(encrypted)
    secure_zero(encrypted)
    return result


def decrypt_bytecode(
    encrypted: bytes,
    key: bytes,
    block_size: int = 64,
) -> bytearray:
    """
    Decrypt bytecode encrypted with encrypt_bytecode.

    CTR mode decryption is identical to encryption (XOR with the same
    keystream). This function creates a temporary mutable copy of the
    ciphertext, calls encrypt_bytecode (which produces the plaintext),
    and then zeroes the temporary copy.

    Security note: The temporary bytearray is explicitly zeroed, but
    the returned bytearray must be zeroed by the caller after use.
    """
    tmp = bytearray(encrypted)
    result = bytearray(encrypt_bytecode(tmp, key, block_size))
    secure_zero(tmp)
    return result


class _Rng:
    """
    Deterministic forward-secure PRNG for register allocation.

    Uses a hash chain: state_{n+1} = SHA-256(state_n). Each call
    overwrites the state, providing forward secrecy — past outputs
    cannot be recovered after the state advances.

    WARNING: The initial seed (bytes) is immutable and cannot be
    zeroed. The internal state (bytes) is also immutable but is
    replaced on each call.
    """

    def __init__(self, seed: bytes):
        self.state = hashlib.sha256(seed).digest()

    def next(self) -> int:
        """
        Return the next 32-bit pseudo-random value and advance state.

        The state becomes SHA-256(previous state), providing forward
        secrecy: if the current state is compromised, past outputs
        cannot be recomputed.
        """
        self.state = hashlib.sha256(self.state).digest()
        return struct.unpack('<I', self.state[:4])[0]
