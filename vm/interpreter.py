"""
interpreter.py

Purpose:
Implements the Nixon Advanced Protection VM interpreter with support for
dynamic ISA mutation, state-dependent opcode rotation, periodic rekeying,
and multiple dispatch/encoding modes. Executes encrypted bytecode in a
software-simulated 16-register, 64KB-memory virtual machine.

Architectural Role:
The core execution engine for VM-protected code. Provides both a simple
fixed-ISA mode and a dynamic self-mutating ISA mode with runtime-derived
opcode mappings, dispatch modes, encoding modes, and field permutations.

Security Relevance:
This is the most security-critical component in the VM pipeline. It
implements:

1. Periodic rekeying (REKEY at opcode 255, auto-rekey every 1000 steps):
   - vm_rekey_seed() produces a new seed via
     SHA-256(current_seed || epoch || basic_block_hash).
   - The basic block hash (bb_hash) is a rolling hash of all executed
     bytes: bb_hash = ((bb_hash << 5) + bb_hash) ^ byte. This couples
     the rekeying to the actual execution path, preventing precomputation.
   - On rekey, the entire ISA table is regenerated, dispatch mode may
     change, encoding mode may change, and the handler order is shuffled.

2. Self-mutating ISA (dynamic_isa=True):
   - Dispatch modes: switch (direct table lookup), indirect (table lookup
     with shuffled keys), computed_goto (computed handler index from
     opcode * 7 + epoch).
   - Encoding modes: fixed (opcode byte + fixed operands), variable
     (length-prefixed), field_shuffle (operand bytes permuted).
   - Handler order is shuffled per epoch via Fisher-Yates.
   - These modes are selected at init and rekey time from the seed.

3. State-dependent ISA (state_isa=True):
   - Tracks the last 8 instruction IDs in a sliding window.
   - Computes SHA-256(window) and compares to a threshold.
   - When the threshold is crossed, a rotation offset is incremented,
     changing the physical-to-logical opcode mapping.

4. Encrypted memory ops (ENC_LOAD, ENC_STORE, ENC_ADD, ENC_MUL):
   - XOR-based encryption with a per-operation key byte.
   - Keys are stored in registers or embedded in the instruction stream.

5. Build-aware handler resolution (_resolve_handler):
   - Uses BLAKE2b(vm_state_hash + opcode + build_secret) to
     pseudo-randomly select a handler. This adds an additional layer
     of indirection that changes with VM state.

Threat model: Static analysis, dynamic tracing, opcode identification,
execution-path inference, replay attacks, bytecode modification.

What happens on invalid opcode: VM halts with state["halted"] = True.
The bytecode is zeroed on run() completion via secure_zero().

Dependencies:
  - vm.vm_isa (VMOpcode, VM_PROPERTIES, _phase2_enabled)
  - vm.ephemeral_isa (runtime_derive_isa, vm_rekey_seed, etc.)
  - config/default.json (for build secret derivation)
"""

from __future__ import annotations
import hashlib
import json
import os
import struct
from typing import Callable

from .vm_isa import VMOpcode, VM_PROPERTIES
# Re-exported: the interpreter's Phase 2 gate is monkeypatched through
# this module's namespace by the test suite, so the name must be bound
# here even though the module does not call it.
from .vm_isa import _phase2_enabled  # noqa: F401
from .ephemeral_isa import (select_dispatch_mode, select_encoding_mode,
                            generate_field_permutation, shuffle_handler_order)


def secure_zero(data):
    """
    Zero the contents of a mutable buffer.

    bytearray: each byte set to 0.
    list: each element set to 0.
    bytes: immutable — cannot be zeroed. Use bytearray for sensitive data.
    """
    if isinstance(data, bytearray):
        for i in range(len(data)):
            data[i] = 0
    elif isinstance(data, list):
        for i in range(len(data)):
            data[i] = 0


def _load_config():
    """Load project configuration from config/default.json."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "default.json")
    with open(config_path) as f:
        return json.load(f)


DISPATCH_SWITCH = 0
DISPATCH_INDIRECT = 1
DISPATCH_COMPUTED_GOTO = 2

ENCODING_FIXED = 0
ENCODING_VARIABLE = 1
ENCODING_FIELD_SHUFFLE = 2

DISPATCH_NAMES = ["switch", "indirect", "computed_goto"]
ENCODING_NAMES = ["fixed", "variable", "field_shuffle"]


class VMInterpreter:
    """
    The Nixon VM interpreter with dynamic ISA mutation.

    Supports both a simple fixed-ISA execution mode and a complex
    self-mutating mode with runtime opcode derivation, multiple
    dispatch/encoding modes, periodic rekeying, and state-dependent
    opcode rotation.

    Public methods:
      step() -> bool   — Execute one instruction, return False on halt.
      run(max_steps) -> dict  — Execute until halt or max_steps.
    """

    NUM_REGISTERS = VM_PROPERTIES["num_registers"]
    REG_PC = 14
    REG_FLAGS = 13
    REG_SP = 15

    FLAG_ZERO = 1
    FLAG_SIGN = 2
    FLAG_CARRY = 4

    VM_REKEY_INTERVAL = 1000
    VM_OPCODE_REKEY = 255

    def __init__(self, bytecode: bytes, state: dict | None = None, opcode_map: dict[int, int] | None = None,
                 dynamic_isa: bool = False, entropy_seed: bytes | None = None,
                 state_isa: bool = False):
        """
        Initialize the VM interpreter.

        Args:
            bytecode: The bytecode to execute (AES-decrypted before passing).
            state: Initial VM state dict with regs, memory, stack, halted.
            opcode_map: Mapping from logical opcode to physical opcode.
            dynamic_isa: Enable self-mutating ISA (dispatch/encoding modes).
            entropy_seed: Seed for dynamic ISA derivation (32 bytes).
            state_isa: Enable state-dependent opcode rotation.
        """
        self.bytecode = bytearray(bytecode)
        self.state = state or {
            "regs": [0] * self.NUM_REGISTERS,
            "memory": bytearray(65536),
            "stack": [],
            "halted": False,
        }
        self.opcode_map = opcode_map or {i: i for i in range(256)}
        self.inverse_map = self._build_inverse_map()
        self.handlers = self._init_handlers()
        self.build_secret = self._derive_build_secret()
        self.dynamic_isa = dynamic_isa
        self.state_isa = state_isa
        self.epoch = 0
        self.steps_until_rekey = self.VM_REKEY_INTERVAL
        self.bb_hash = 0

        self.dispatch_mode = DISPATCH_SWITCH
        self.encoding_mode = ENCODING_FIXED
        self.field_perm = list(range(16))
        self.handler_order = list(self.handlers.keys())
        self.dispatch_table = dict(self.handlers)
        self.shuffle_buf = bytearray()
        self.shuffle_pos = 0
        self.shuffle_active = False
        self.variable_instr_len = 0

        self.state_isa_history: list[int] = []
        self.state_isa_rotation = 0

        if dynamic_isa:
            from .ephemeral_isa import runtime_collect_entropy, runtime_derive_isa
            seed = entropy_seed if entropy_seed is not None else runtime_collect_entropy()
            self.entropy_seed = bytearray(seed)
            isa_table = runtime_derive_isa(bytes(self.entropy_seed))
            self.isa_table = isa_table
            self.inverse_map = {phys: logical for phys, logical in enumerate(isa_table)}

            self._init_mutating_isa(bytes(self.entropy_seed))
        else:
            self.entropy_seed = bytearray(32)
            self.isa_table = list(range(256))

    def _init_mutating_isa(self, seed: bytes):
        """
        Initialize the self-mutating ISA parameters from a seed.

        Determines dispatch mode, encoding mode, field permutation,
        and handler order via seeded selection/shuffle functions.

        Security note: The dispatch mode and encoding mode are selected
        once at initialization (and again at each rekey). An attacker
        observing one rekey can determine the mode for that epoch but
        not for future epochs.
        """
        from .ephemeral_isa import (select_dispatch_mode, select_encoding_mode,
                                   generate_field_permutation, shuffle_handler_order)
        dm = select_dispatch_mode(seed, self.epoch)
        em = select_encoding_mode(seed, self.epoch)
        self.dispatch_mode = DISPATCH_NAMES.index(dm)
        self.encoding_mode = ENCODING_NAMES.index(em)
        self.field_perm = generate_field_permutation(seed + struct.pack('<I', self.epoch), 16)

        handler_list = sorted(self.handlers.items())
        shuffled = shuffle_handler_order(seed + struct.pack('<I', self.epoch), handler_list)
        self.handler_order = [k for k, v in shuffled]
        self.dispatch_table = {}
        for opcode, fn in shuffled:
            self.dispatch_table[opcode] = fn

    def _build_inverse_map(self) -> dict[int, int]:
        """
        Build the inverse opcode mapping: physical -> logical.

        The forward map (opcode_map) maps logical -> physical.
        This inverts it for runtime decode: given a physical opcode
        from the bytecode, find the logical opcode for handler dispatch.
        """
        inverse = {}
        for logical, physical in self.opcode_map.items():
            inverse[physical] = logical
        return inverse

    def _derive_build_secret(self) -> bytes:
        """
        Derive a build-specific secret from project config.

        Reads the shadow_compiler.seed from config/default.json, or
        uses a default string if not configured. The secret is derived
        via BLAKE2b (32 bytes output).

        Security note: If the config seed is predictable, the build
        secret is predictable. The production pipeline should inject
        a high-entropy seed at build time.
        """
        cfg = _load_config()
        seed_str = cfg.get("shadow_compiler", {}).get("seed") if "shadow_compiler" in cfg else "nixon-vm-default"
        return hashlib.blake2b(str(seed_str).encode(), digest_size=32).digest()

    def _init_handlers(self) -> dict[int, Callable]:
        """
        Build the opcode-to-handler mapping for all 35 supported opcodes.

        Opcodes 0-34 map to named handler methods. Opcode 255 (REKEY)
        is handled separately in step().
        """
        return {
            VMOpcode.NOP: self._handle_nop,
            VMOpcode.ADD: self._handle_add,
            VMOpcode.SUB: self._handle_sub,
            VMOpcode.MUL: self._handle_mul,
            VMOpcode.DIV: self._handle_div,
            VMOpcode.MOD: self._handle_mod,
            VMOpcode.AND: self._handle_and,
            VMOpcode.OR: self._handle_or,
            VMOpcode.XOR: self._handle_xor,
            VMOpcode.NOT: self._handle_not,
            VMOpcode.SHL: self._handle_shl,
            VMOpcode.SHR: self._handle_shr,
            VMOpcode.LOAD: self._handle_load,
            VMOpcode.STORE: self._handle_store,
            VMOpcode.MOV: self._handle_mov,
            VMOpcode.LEA: self._handle_lea,
            VMOpcode.JMP: self._handle_jmp,
            VMOpcode.JZ: self._handle_jz,
            VMOpcode.JNZ: self._handle_jnz,
            VMOpcode.JG: self._handle_jg,
            VMOpcode.JL: self._handle_jl,
            VMOpcode.JGE: self._handle_jge,
            VMOpcode.JLE: self._handle_jle,
            VMOpcode.CALL: self._handle_call,
            VMOpcode.RET: self._handle_ret,
            VMOpcode.PUSH: self._handle_push,
            VMOpcode.POP: self._handle_pop,
            VMOpcode.ENTER: self._handle_enter,
            VMOpcode.LEAVE: self._handle_leave,
            VMOpcode.ENC_LOAD: self._handle_enc_load,
            VMOpcode.ENC_STORE: self._handle_enc_store,
            VMOpcode.ENC_ADD: self._handle_enc_add,
            VMOpcode.ENC_MUL: self._handle_enc_mul,
            VMOpcode.FUSED_LOAD_ADD_STORE: self._handle_fused_load_add_store,
            VMOpcode.FUSED_CMP_JMP: self._handle_fused_cmp_jmp,
        }

    def _resolve_handler(self, opcode: int) -> Callable:
        """
        Resolve a handler for an opcode using build-aware selection.

        Computes BLAKE2b(vm_state_hash + opcode + build_secret) and
        selects a handler from the shuffled handler list based on
        the hash output.

        Security note: This adds an additional layer of indirection
        that changes with VM state. Even with a known opcode map,
        an attacker cannot predict which handler will execute without
        knowing the VM state and build secret.
        """
        h = hashlib.blake2b(
            str(self._vm_state_hash()).encode() + struct.pack('<I', opcode) + self.build_secret,
            digest_size=32,
        ).digest()
        handler_idx = struct.unpack('<I', h[:4])[0] % len(self.handlers)
        logical = list(self.handlers.keys())[handler_idx]
        return self.handlers[logical]

    def _vm_state_hash(self) -> int:
        """
        Compute a hash of the current VM state (registers + PC).

        Uses MD5 for speed (not security). The hash is used to
        introduce VM state into the handler resolution, making
        handler selection state-dependent.
        """
        regs_hash = hashlib.md5(str(self.state["regs"]).encode()).hexdigest()
        pc = self.state["regs"][self.REG_PC] if len(self.state["regs"]) > self.REG_PC else 0
        return hash((regs_hash, pc))

    def _read_byte(self) -> int:
        """
        Read the next byte from bytecode (or shuffle buffer if active).

        Reads from bytecode at PC, then increments PC. Updates the
        basic block hash (bb_hash) with each byte:
          bb_hash = ((bb_hash << 5) + bb_hash) ^ byte

        This is a rolling hash (like a linear CRC) that captures the
        exact execution path. It is used in rekeying to tie the new
        ISA to the specific execution path.

        If field shuffle is active, reads from shuffle_buf instead.
        """
        if self.shuffle_active:
            if self.shuffle_pos >= len(self.shuffle_buf):
                self.state["halted"] = True
                return 0
            val = self.shuffle_buf[self.shuffle_pos]
            self.shuffle_pos += 1
            return val

        pc = self.state["regs"][self.REG_PC]
        if pc >= len(self.bytecode):
            self.state["halted"] = True
            return 0
        val = self.bytecode[pc]
        self.state["regs"][self.REG_PC] = pc + 1
        self.bb_hash = (((self.bb_hash << 5) + self.bb_hash) ^ val) & 0xFFFFFFFFFFFFFFFF
        return val

    def _read_u16(self) -> int:
        """Read a little-endian 16-bit value from bytecode."""
        lo = self._read_byte()
        hi = self._read_byte()
        return (hi << 8) | lo

    def _read_u32(self) -> int:
        """Read a little-endian 32-bit value from bytecode."""
        b0 = self._read_byte()
        b1 = self._read_byte()
        b2 = self._read_byte()
        b3 = self._read_byte()
        return (b3 << 24) | (b2 << 16) | (b1 << 8) | b0

    def _read_reg(self) -> int:
        """Read a register index (lower 4 bits) from bytecode."""
        return self._read_byte() & 0x0F

    def _reg(self, idx: int) -> int:
        """Read the value of a register. Returns 0 if index is out of bounds."""
        if 0 <= idx < len(self.state["regs"]):
            return self.state["regs"][idx]
        return 0

    def _set_reg(self, idx: int, val: int):
        """Set a register value, masked to 64 bits."""
        if 0 <= idx < len(self.state["regs"]):
            self.state["regs"][idx] = val & 0xFFFFFFFFFFFFFFFF

    def _set_flags(self, result: int, a: int = 0, b: int = 0):
        """
        Set condition flags based on operation result.

        FLAG_ZERO: result == 0
        FLAG_SIGN: bit 63 set (negative in signed interpretation)

        Note: FLAG_CARRY is defined but not currently set by any
        handler. It is reserved for future use or external tooling.
        """
        flags = 0
        if result == 0:
            flags |= self.FLAG_ZERO
        if result & 0x8000000000000000:
            flags |= self.FLAG_SIGN
        self._set_reg(self.REG_FLAGS, flags)

    def _handle_nop(self):
        """NOP: No operation."""
        pass

    def _handle_add(self):
        """ADD dst, src: dst = dst + src. Sets flags."""
        dst = self._read_reg()
        src = self._read_reg()
        a = self._reg(dst)
        b = self._reg(src)
        result = (a + b) & 0xFFFFFFFFFFFFFFFF
        self._set_reg(dst, result)
        self._set_flags(result, a, b)

    def _handle_sub(self):
        """SUB dst, src: dst = dst - src. Sets flags."""
        dst = self._read_reg()
        src = self._read_reg()
        a = self._reg(dst)
        b = self._reg(src)
        result = (a - b) & 0xFFFFFFFFFFFFFFFF
        self._set_reg(dst, result)
        self._set_flags(result, a, b)

    def _handle_mul(self):
        """MUL dst, src: dst = dst * src. Sets flags."""
        dst = self._read_reg()
        src = self._read_reg()
        a = self._reg(dst)
        b = self._reg(src)
        result = (a * b) & 0xFFFFFFFFFFFFFFFF
        self._set_reg(dst, result)
        self._set_flags(result)

    def _handle_div(self):
        """DIV dst, src: dst = dst / src. Halts on division by zero."""
        dst = self._read_reg()
        src = self._read_reg()
        a = self._reg(dst)
        b = self._reg(src)
        if b == 0:
            self.state["halted"] = True
            return
        result = (a // b) & 0xFFFFFFFFFFFFFFFF
        self._set_reg(dst, result)
        self._set_flags(result)

    def _handle_mod(self):
        """MOD dst, src: dst = dst % src. Halts on division by zero."""
        dst = self._read_reg()
        src = self._read_reg()
        a = self._reg(dst)
        b = self._reg(src)
        if b == 0:
            self.state["halted"] = True
            return
        result = (a % b) & 0xFFFFFFFFFFFFFFFF
        self._set_reg(dst, result)
        self._set_flags(result)

    def _handle_and(self):
        """AND dst, src: dst = dst & src. Sets flags."""
        dst = self._read_reg()
        src = self._read_reg()
        result = (self._reg(dst) & self._reg(src)) & 0xFFFFFFFFFFFFFFFF
        self._set_reg(dst, result)
        self._set_flags(result)

    def _handle_or(self):
        """OR dst, src: dst = dst | src. Sets flags."""
        dst = self._read_reg()
        src = self._read_reg()
        result = (self._reg(dst) | self._reg(src)) & 0xFFFFFFFFFFFFFFFF
        self._set_reg(dst, result)
        self._set_flags(result)

    def _handle_xor(self):
        """XOR dst, src: dst = dst ^ src. Sets flags."""
        dst = self._read_reg()
        src = self._read_reg()
        result = (self._reg(dst) ^ self._reg(src)) & 0xFFFFFFFFFFFFFFFF
        self._set_reg(dst, result)
        self._set_flags(result)

    def _handle_not(self):
        """NOT dst: dst = ~dst. Sets flags."""
        dst = self._read_reg()
        result = (~self._reg(dst)) & 0xFFFFFFFFFFFFFFFF
        self._set_reg(dst, result)
        self._set_flags(result)

    def _handle_shl(self):
        """SHL dst, src: dst = dst << (src & 63). Sets flags."""
        dst = self._read_reg()
        src = self._read_reg()
        shift = self._reg(src) & 63
        result = (self._reg(dst) << shift) & 0xFFFFFFFFFFFFFFFF
        self._set_reg(dst, result)
        self._set_flags(result)

    def _handle_shr(self):
        """SHR dst, src: dst = dst >> (src & 63). Sets flags."""
        dst = self._read_reg()
        src = self._read_reg()
        shift = self._reg(src) & 63
        result = (self._reg(dst) >> shift) & 0xFFFFFFFFFFFFFFFF
        self._set_reg(dst, result)
        self._set_flags(result)

    def _handle_load(self):
        """
        LOAD dst, addr_reg: dst = memory[reg[addr_reg]].

        Halts if address >= memory size (64KB).
        """
        dst = self._read_reg()
        addr_reg = self._read_reg()
        addr = self._reg(addr_reg)
        if 0 <= addr < len(self.state["memory"]):
            val = self.state["memory"][addr]
            self._set_reg(dst, val)
        else:
            self.state["halted"] = True

    def _handle_store(self):
        """
        STORE src, addr_reg: memory[reg[addr_reg]] = reg[src] & 0xFF.

        Halts if address >= memory size (64KB).
        """
        src = self._read_reg()
        addr_reg = self._read_reg()
        addr = self._reg(addr_reg)
        if 0 <= addr < len(self.state["memory"]):
            self.state["memory"][addr] = self._reg(src) & 0xFF
        else:
            self.state["halted"] = True

    def _handle_mov(self):
        """MOV dst, lo, hi: dst = (hi << 8) | lo. Loads 16-bit immediate."""
        dst = self._read_reg()
        val_lo = self._read_byte()
        val_hi = self._read_byte()
        val = (val_hi << 8) | val_lo
        self._set_reg(dst, val)

    def _handle_lea(self):
        """
        LEA dst, src: Load effective address (placeholder).

        Currently consumes operands without effect. In the C interpreter,
        this would compute address = reg[dst] + reg[src].
        """
        self._read_reg()
        self._read_reg()

    def _handle_jmp(self):
        """JMP target: PC = target (unconditional jump, absolute 32-bit)."""
        target = self._read_u32()
        self._set_reg(self.REG_PC, target)

    def _handle_jz(self):
        """JZ target: PC = target if ZERO flag is set."""
        target = self._read_u32()
        flags = self._reg(self.REG_FLAGS)
        if flags & self.FLAG_ZERO:
            self._set_reg(self.REG_PC, target)

    def _handle_jnz(self):
        """JNZ target: PC = target if ZERO flag is NOT set."""
        target = self._read_u32()
        flags = self._reg(self.REG_FLAGS)
        if not (flags & self.FLAG_ZERO):
            self._set_reg(self.REG_PC, target)

    def _handle_jg(self):
        """JG target: PC = target if ZERO=0 and SIGN=0 (signed greater than)."""
        target = self._read_u32()
        flags = self._reg(self.REG_FLAGS)
        if not (flags & self.FLAG_ZERO) and not (flags & self.FLAG_SIGN):
            self._set_reg(self.REG_PC, target)

    def _handle_jl(self):
        """JL target: PC = target if SIGN=1 (signed less than)."""
        target = self._read_u32()
        flags = self._reg(self.REG_FLAGS)
        if flags & self.FLAG_SIGN:
            self._set_reg(self.REG_PC, target)

    def _handle_jge(self):
        """JGE target: PC = target if SIGN=0 (signed greater or equal)."""
        target = self._read_u32()
        flags = self._reg(self.REG_FLAGS)
        if not (flags & self.FLAG_SIGN):
            self._set_reg(self.REG_PC, target)

    def _handle_jle(self):
        """JLE target: PC = target if ZERO=1 or SIGN=1 (signed less or equal)."""
        target = self._read_u32()
        flags = self._reg(self.REG_FLAGS)
        if (flags & self.FLAG_ZERO) or (flags & self.FLAG_SIGN):
            self._set_reg(self.REG_PC, target)

    def _handle_call(self):
        """
        CALL target: Push return address (PC after CALL) to stack, jump.

        Stack is used as a Python list (append/pop). There is no explicit
        stack limit beyond available memory.
        """
        target = self._read_u32()
        ret_addr = self._reg(self.REG_PC)
        self.state["stack"].append(ret_addr)
        self._set_reg(self.REG_PC, target)

    def _handle_ret(self):
        """
        RET: Pop return address from stack into PC.

        Halts if stack is empty (unmatched return).
        """
        if self.state["stack"]:
            ret_addr = self.state["stack"].pop()
            self._set_reg(self.REG_PC, ret_addr)
        else:
            self.state["halted"] = True

    def _handle_push(self):
        """PUSH src: Push reg[src] onto stack."""
        src = self._read_reg()
        self.state["stack"].append(self._reg(src))

    def _handle_pop(self):
        """
        POP dst: Pop top of stack into reg[dst].

        Sets dst = 0 if stack is empty.
        """
        dst = self._read_reg()
        if self.state["stack"]:
            self._set_reg(dst, self.state["stack"].pop())
        else:
            self._set_reg(dst, 0)

    def _handle_enter(self):
        """
        ENTER frame_size: Push PC and FLAGS onto stack for frame entry.

        frame_size is a 16-bit value read from the instruction stream
        but not currently used in the Python interpreter.
        """
        self._read_u16()
        self.state["stack"].append(self._reg(self.REG_PC))
        self.state["stack"].append(self._reg(self.REG_FLAGS))

    def _handle_leave(self):
        """
        LEAVE: Pop FLAGS and PC from stack (inverse of ENTER).

        Requires at least 2 entries on the stack. Does nothing if
        fewer than 2 entries are available (no halt).
        """
        if len(self.state["stack"]) >= 2:
            self.state["stack"].pop()
            self.state["stack"].pop()

    def _handle_enc_load(self):
        """
        ENC_LOAD dst, addr_reg, key_reg: dst = memory[reg[addr_reg]] ^ reg[key_reg].

        Loads a byte from memory and XORs with a key byte for decryption.
        The key byte is reg[key_reg] & 0xFF.
        """
        dst = self._read_reg()
        addr_reg = self._read_reg()
        key_reg = self._read_reg()
        addr = self._reg(addr_reg)
        key = self._reg(key_reg) & 0xFF
        if 0 <= addr < len(self.state["memory"]):
            val = self.state["memory"][addr] ^ key
            self._set_reg(dst, val)

    def _handle_enc_store(self):
        """
        ENC_STORE src, addr_reg, key_reg: memory[reg[addr_reg]] = reg[src] ^ reg[key_reg].

        XORs source value with key byte before storing. The key byte is
        reg[key_reg] & 0xFF.
        """
        src = self._read_reg()
        addr_reg = self._read_reg()
        key_reg = self._read_reg()
        addr = self._reg(addr_reg)
        key = self._reg(key_reg) & 0xFF
        if 0 <= addr < len(self.state["memory"]):
            self.state["memory"][addr] = (self._reg(src) ^ key) & 0xFF

    def _handle_enc_add(self):
        """
        ENC_ADD dst, src, key: dst = (dst ^ key) + (src ^ key) ^ key.

        Computes addition on XOR-decrypted operands and re-encrypts
        the result. The key is an 8-bit immediate from the instruction
        stream. All 64-bit operations.
        """
        dst = self._read_reg()
        src = self._read_reg()
        key = self._read_byte()
        a = self._reg(dst) ^ key
        b = self._reg(src) ^ key
        result = (a + b) ^ key
        self._set_reg(dst, result & 0xFFFFFFFFFFFFFFFF)
        self._set_flags(result)

    def _handle_enc_mul(self):
        """
        ENC_MUL dst, src, key: dst = (dst ^ key) * (src ^ key) ^ key.

        Computes multiplication on XOR-decrypted operands and re-encrypts
        the result. The key is an 8-bit immediate. All 64-bit operations.
        """
        dst = self._read_reg()
        src = self._read_reg()
        key = self._read_byte()
        a = self._reg(dst) ^ key
        b = self._reg(src) ^ key
        result = (a * b) ^ key
        self._set_reg(dst, result & 0xFFFFFFFFFFFFFFFF)
        self._set_flags(result)

    def _handle_fused_load_add_store(self):
        """
        FUSED_LOAD_ADD_STORE dst, base_reg, offset_reg:
          addr = reg[base_reg] + reg[offset_reg]
          loaded = memory[addr]
          result = loaded + reg[dst]
          memory[addr] = result & 0xFF
          reg[dst] = result

        Performs a load, add, and store as a single fused operation,
        reducing the instruction count and making the operation harder
        to distinguish in a trace.
        """
        dst = self._read_reg()
        base_reg = self._read_reg()
        offset_reg = self._read_reg()
        base = self._reg(base_reg)
        offset = self._reg(offset_reg)
        addr = (base + offset) & 0xFFFFFFFF
        if 0 <= addr < len(self.state["memory"]):
            loaded = self.state["memory"][addr]
            result = (loaded + self._reg(dst)) & 0xFFFFFFFFFFFFFFFF
            self.state["memory"][addr] = result & 0xFF
            self._set_reg(dst, result)
        else:
            self.state["halted"] = True

    def _handle_fused_cmp_jmp(self):
        """
        FUSED_CMP_JMP cond_reg, true_target, false_target:
          if reg[cond_reg] != 0: PC = true_target
          else: PC = false_target

        Combines a comparison and conditional jump into one opcode,
        reducing the attacker's ability to identify branch conditions.
        """
        cond_reg = self._read_reg()
        true_target = self._read_u32()
        false_target = self._read_u32()
        cond = self._reg(cond_reg)
        if cond != 0:
            self._set_reg(self.REG_PC, true_target)
        else:
            self._set_reg(self.REG_PC, false_target)

    def _rekey(self):
        """
        Perform a full VM rekey: derive new seed, regenerate ISA, update
        dispatch/encoding modes, shuffle handler order.

        Triggered by:
        1. The REKEY opcode (255) in the bytecode stream.
        2. Auto-trigger after VM_REKEY_INTERVAL (1000) steps.

        The new seed is derived via:
          new_seed = SHA-256(current_seed || epoch || bb_hash)

        Where bb_hash is a rolling hash of all executed bytes. This
        ties the rekey to the specific execution path, preventing
        an attacker from precomputing the post-rekey ISA without
        executing the exact same path.

        After rekey:
        - epoch increments.
        - A new ISA table is derived (runtime_derive_isa).
        - The inverse map is rebuilt.
        - Dispatch mode, encoding mode, and field permutation are
          re-selected.
        - Handler order is re-shuffled.
        """
        from .ephemeral_isa import vm_rekey_seed, runtime_derive_isa
        new_seed = vm_rekey_seed(bytes(self.entropy_seed), self.epoch, self.bb_hash)
        self.entropy_seed = bytearray(new_seed)
        self.epoch += 1
        self.steps_until_rekey = self.VM_REKEY_INTERVAL
        isa_table = runtime_derive_isa(bytes(self.entropy_seed))
        self.isa_table = isa_table
        self.inverse_map = {phys: logical for phys, logical in enumerate(isa_table)}

        seed = bytes(self.entropy_seed)
        dm = select_dispatch_mode(seed, self.epoch)
        em = select_encoding_mode(seed, self.epoch)
        self.dispatch_mode = DISPATCH_NAMES.index(dm)
        self.encoding_mode = ENCODING_NAMES.index(em)
        self.field_perm = generate_field_permutation(seed + struct.pack('<I', self.epoch), 16)

        handler_list = sorted(self.handlers.items())
        shuffled = shuffle_handler_order(seed + struct.pack('<I', self.epoch), handler_list)
        self.handler_order = [k for k, v in shuffled]
        self.dispatch_table = {}
        for opcode, fn in shuffled:
            self.dispatch_table[opcode] = fn

    def _update_state_isa(self, instruction_id: int):
        """
        Update state-ISA tracking and potentially rotate the opcode mapping.

        Maintains a sliding window of the last 8 instruction IDs.
        Computes SHA-256 over the packed window and compares the
        hash value to a threshold (0x10000000 + hash[4:8]).

        When the threshold is exceeded, the state_isa_rotation is
        incremented, which changes how physical opcodes map to
        logical opcodes.

        Security note: The threshold is dynamic (depends on the
        current hash), making the rotation timing unpredictable.
        """
        self.state_isa_history.append(instruction_id & 0xFF)
        if len(self.state_isa_history) > 8:
            self.state_isa_history.pop(0)

        if not self.state_isa_history:
            return

        import struct
        data = struct.pack(f"<{len(self.state_isa_history)}B", *self.state_isa_history)
        state_hash = hashlib.sha256(data).digest()
        state_val = struct.unpack("<Q", state_hash[:8])[0]

        threshold = 0x10000000 + struct.unpack("<I", state_hash[4:8])[0]
        if state_val > threshold:
            self.state_isa_rotation = (self.state_isa_rotation + 1) & 0xFF

    def _prepare_field_shuffle(self, logical_opcode: int):
        """
        Read operand bytes from bytecode and apply inverse field
        permutation to restore original operand order.

        Used when encoding_mode is ENCODING_FIELD_SHUFFLE. Reads
        n_op operand bytes (from OPCODE_OPERAND_BYTES), applies
        the inverse of the field permutation, and stores the
        result in shuffle_buf for subsequent operand reads.

        Security note: The field permutation is epoch-specific
        and seeded from the build seed. Without knowing the
        permutation, the operand bytes appear scrambled.
        """
        from .ephemeral_isa import OPCODE_OPERAND_BYTES, apply_field_unshuffle
        n_op = OPCODE_OPERAND_BYTES.get(logical_opcode, 0)
        raw = bytearray()
        for _ in range(n_op):
            pc = self.state["regs"][self.REG_PC]
            if pc >= len(self.bytecode):
                self.state["halted"] = True
                return
            val = self.bytecode[pc]
            self.state["regs"][self.REG_PC] = pc + 1
            self.bb_hash = ((self.bb_hash << 5) + self.bb_hash) ^ val
            raw.append(val)
        unshuffled = apply_field_unshuffle(bytes(raw), self.field_perm)
        self.shuffle_buf = bytearray(unshuffled)
        self.shuffle_pos = 0
        self.shuffle_active = True

    def step(self) -> bool:
        """
        Execute exactly one VM instruction.

        Returns True if the VM is still running, False if halted.

        Dynamic ISA mode (dynamic_isa=True):
        1. For variable encoding: read the instruction length prefix.
        2. Read the raw opcode byte.
        3. Check for REKEY opcode (255) or auto-rekey.
        4. For state ISA: update state history and apply rotation.
        5. Look up logical opcode via inverse_map.
        6. For field shuffle encoding: read and unshuffle operands.
        7. Dispatch to handler based on dispatch_mode:
           - DISPATCH_SWITCH: direct lookup in handlers dict.
           - DISPATCH_INDIRECT: lookup in shuffled dispatch_table.
           - DISPATCH_COMPUTED_GOTO: compute handler index from
             (opcode * 7 + epoch) % num_handlers.
        8. For variable encoding: pad/skip to declared instruction length.

        Fixed ISA mode (dynamic_isa=False):
        1. Read the raw opcode byte.
        2. Map through inverse_map.
        3. Look up handler and execute.
        """
        if self.state.get("halted", False):
            return False

        if self.dynamic_isa:
            instr_start = self.state["regs"][self.REG_PC]

            if self.encoding_mode == ENCODING_VARIABLE:
                self.variable_instr_len = self._read_byte()
                if self.state["halted"]:
                    return False

            raw_opcode = self._read_byte()
            if self.state["halted"]:
                return False

            if raw_opcode == self.VM_OPCODE_REKEY:
                self._rekey()
                return not self.state.get("halted", False)

            self.steps_until_rekey -= 1
            if self.steps_until_rekey <= 0:
                self._rekey()

            if self.state_isa:
                self._update_state_isa(raw_opcode)
                rotated = (raw_opcode + self.state_isa_rotation) & 0xFF
                logical_opcode = self.inverse_map.get(rotated, rotated)
            else:
                logical_opcode = self.inverse_map.get(raw_opcode, raw_opcode)

            if self.encoding_mode == ENCODING_FIELD_SHUFFLE:
                self._prepare_field_shuffle(logical_opcode)

            handler = None
            if self.dispatch_mode == DISPATCH_SWITCH:
                handler = self.handlers.get(logical_opcode)
            elif self.dispatch_mode == DISPATCH_INDIRECT:
                handler = self.dispatch_table.get(logical_opcode)
            elif self.dispatch_mode == DISPATCH_COMPUTED_GOTO:
                idx = (logical_opcode * 7 + self.epoch) % len(self.handlers)
                dispatched_op = list(self.handlers.keys())[idx]
                handler = self.handlers.get(dispatched_op)

            if handler is None:
                self.state["halted"] = True
                return False

            handler()

            self.shuffle_active = False

            if self.encoding_mode == ENCODING_VARIABLE and not self.state["halted"]:
                consumed = self.state["regs"][self.REG_PC] - instr_start
                if consumed < self.variable_instr_len:
                    self.state["regs"][self.REG_PC] = instr_start + self.variable_instr_len
                elif consumed > self.variable_instr_len:
                    self.state["halted"] = True
        else:
            raw_opcode = self._read_byte()

            self.steps_until_rekey -= 1

            logical_opcode = self.inverse_map.get(raw_opcode, raw_opcode)

            handler = self.handlers.get(logical_opcode)
            if handler is None:
                self.state["halted"] = True
                return False

            handler()

        return not self.state.get("halted", False)

    def run(self, max_steps: int = 1000000) -> dict:
        """
        Run the VM until halted or max_steps reached.

        After execution completes (or hits the step limit), the
        bytecode buffer is zeroed via secure_zero() to reduce
        the window for memory-dump-based extraction.

        Returns the final VM state dict.
        """
        steps = 0
        while not self.state.get("halted", False) and steps < max_steps:
            self.step()
            steps += 1
        if steps >= max_steps:
            self.state["halted"] = True
        secure_zero(self.bytecode)
        return self.state
