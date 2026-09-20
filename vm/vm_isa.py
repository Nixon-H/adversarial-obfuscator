"""
vm_isa.py

Purpose:
Defines the core Virtual Machine Instruction Set Architecture (ISA)
for the Nixon Advanced Protection system. Contains opcode constants,
operand type constants, the VMInstruction container with encoding logic,
and VM configuration properties.

Architectural Role:
ISA definition layer. All other VM components (compiler, interpreter,
ephemeral ISA, state ISA) depend on the constants and classes defined
here. This file is the single source of truth for the VM's instruction
encoding scheme.

Security Relevance:
- Defines the 35-opcode ISA including encrypted operations (ENC_LOAD,
  ENC_STORE, ENC_ADD, ENC_MUL) and fused operations (FUSED_LOAD_ADD_STORE,
  FUSED_CMP_JMP) that reduce the attacker's ability to distinguish
  individual operations.
- Phase 2 gating (_phase2_enabled()) reads config/default.json to
  enable/disable advanced protection features. This is the central
  kill switch for all VM-based protections.
- VM_PROPERTIES describes the encoding scheme ("variable-width",
  "computed dispatch") which informs static analysis resistance.

Threat model: Static disassembly, instruction-boundary identification,
opcode identification.
"""

from __future__ import annotations
import json
import os
import struct


def _phase2_enabled() -> bool:
    """
    Check whether Advanced Protection (Phase 2) is enabled in config.

    Reads config/default.json from the project root (two levels up
    from this file's directory). Looks for:
      shadow_compiler.advanced_protection.enabled

    Falls back to False if the config file does not exist or is
    malformed JSON.

    Security note: This is the master gate for all VM protection
    features. If an attacker modifies config/default.json to disable
    Phase 2, all VM obfuscation is bypassed. The production pipeline
    should embed this decision at build time, not read a runtime file.
    """
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "default.json")
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        return cfg.get("shadow_compiler", {}).get("advanced_protection", cfg.get("shadow_compiler", {}).get("phase2", {})).get("enabled", False)
    except (FileNotFoundError, json.JSONDecodeError):
        return False


class VMOperand:
    """
    Operand type constants for VM instructions.

    Each constant represents an addressing mode or immediate size:
      IMM8, IMM16, IMM32, IMM64 — immediate values of various widths.
      REG — register direct.
      REG_INDIRECT — register indirect (register holds address).
      REL_OFFSET — relative offset (signed 16-bit) for jump targets.
      ABS_ADDR — absolute address (32-bit) for jump/call targets.

    These constants are used as the first byte of each operand entry
    in the bytecode stream.
    """
    IMM8 = 0
    IMM16 = 1
    IMM32 = 2
    IMM64 = 3
    REG = 4
    REG_INDIRECT = 5
    REL_OFFSET = 6
    ABS_ADDR = 7


class VMOpcode:
    """
    Opcode constants for the 35-instruction VM ISA.

    The opcode assignments here are the LOGICAL opcodes. The
    ephemeral ISA generator (ephemeral_isa.py) may shuffle these
    into different PHYSICAL opcode values per build.

    Encrypted operations (ENC_*) XOR operands with a key byte
    for basic in-memory data obfuscation. Fused operations combine
    multiple logical operations into one opcode to reduce pattern
    visibility.
    """
    NOP = 0
    ADD = 1
    SUB = 2
    MUL = 3
    DIV = 4
    MOD = 5
    AND = 6
    OR = 7
    XOR = 8
    NOT = 9
    SHL = 10
    SHR = 11
    LOAD = 12
    STORE = 13
    MOV = 14
    LEA = 15
    JMP = 16
    JZ = 17
    JNZ = 18
    JG = 19
    JL = 20
    JGE = 21
    JLE = 22
    CALL = 23
    RET = 24
    PUSH = 25
    POP = 26
    ENTER = 27
    LEAVE = 28
    ENC_LOAD = 29
    ENC_STORE = 30
    ENC_ADD = 31
    ENC_MUL = 32
    FUSED_LOAD_ADD_STORE = 33
    FUSED_CMP_JMP = 34

    LOGICAL_NAMES = {
        0: "NOP", 1: "ADD", 2: "SUB", 3: "MUL", 4: "DIV", 5: "MOD",
        6: "AND", 7: "OR", 8: "XOR", 9: "NOT", 10: "SHL", 11: "SHR",
        12: "LOAD", 13: "STORE", 14: "MOV", 15: "LEA",
        16: "JMP", 17: "JZ", 18: "JNZ", 19: "JG", 20: "JL",
        21: "JGE", 22: "JLE", 23: "CALL", 24: "RET",
        25: "PUSH", 26: "POP", 27: "ENTER", 28: "LEAVE",
        29: "ENC_LOAD", 30: "ENC_STORE", 31: "ENC_ADD", 32: "ENC_MUL",
        33: "FUSED_LOAD_ADD_STORE", 34: "FUSED_CMP_JMP",
    }


class VMInstruction:
    """
    Container for a single VM instruction with opcode and operands.

    Provides encode() to serialize to bytecode and byte_length()
    to compute encoded size without full encoding.
    """

    def __init__(self, opcode: int, operands: list | None = None):
        """
        Create a VM instruction.

        Args:
            opcode: Logical opcode (from VMOpcode).
            operands: List of operand values. Each operand can be an
                      int (raw value) or a tuple of (type, value) where
                      type is from VMOperand.
        """
        self.opcode = opcode
        self.operands = operands or []

    def __repr__(self):
        """Human-readable representation showing logical name and operands."""
        name = VMOpcode.LOGICAL_NAMES.get(self.opcode, f"OP_{self.opcode}")
        ops = ", ".join(repr(o) for o in self.operands)
        return f"<VMInst {name}[{self.opcode}] ({ops})>"

    def byte_length(self) -> int:
        """
        Compute the encoded byte length of this instruction.

        Uses operand size heuristics: ints < 256 => 1 byte,
        < 65536 => 2 bytes, else => 4 bytes. Tuples get 1 + size.
        """
        total = 1
        for op in self.operands:
            if isinstance(op, int):
                if op < 256:
                    total += 1
                elif op < 65536:
                    total += 2
                else:
                    total += 4
            elif isinstance(op, tuple):
                total += 1 + op[1]
            else:
                total += 1
        return total

    def encode(self, opcode_map: dict[int, int] | None = None) -> bytearray:
        """
        Encode this instruction to variable-width bytecode.

        The first byte is the opcode (mapped through opcode_map if
        provided). Then each operand is serialized:
        - Raw ints: 1, 2, or 4 bytes depending on magnitude.
        - Tuples (type, value): type byte followed by value encoded
          per type (IMM8=1B, IMM16=2B, IMM32=4B, REG/REG_INDIRECT=1B,
          REL_OFFSET=2B signed, ABS_ADDR=4B).

        Args:
            opcode_map: Optional mapping from logical to physical
                       opcode. If None, the logical opcode is used
                       directly.
        """
        physical_opcode = opcode_map.get(self.opcode, self.opcode) if opcode_map else self.opcode
        buf = bytearray([physical_opcode & 0xFF])
        for op in self.operands:
            if isinstance(op, int):
                if op < 256:
                    buf.append(op & 0xFF)
                elif op < 65536:
                    buf.extend(struct.pack('<H', op))
                else:
                    buf.extend(struct.pack('<I', op))
            elif isinstance(op, tuple):
                typ, val = op[0], op[1]
                buf.append(typ & 0xFF)
                if typ == VMOperand.IMM8:
                    buf.append(val & 0xFF)
                elif typ == VMOperand.IMM16:
                    buf.extend(struct.pack('<H', val))
                elif typ == VMOperand.IMM32:
                    buf.extend(struct.pack('<I', val))
                elif typ in (VMOperand.REG, VMOperand.REG_INDIRECT):
                    buf.append(val & 0xFF)
                elif typ == VMOperand.REL_OFFSET:
                    buf.extend(struct.pack('<h', val))
                elif typ == VMOperand.ABS_ADDR:
                    buf.extend(struct.pack('<I', val))
                else:
                    buf.append(val & 0xFF)
            else:
                buf.append(op & 0xFF)
        return buf


VM_PROPERTIES = {
    "encoding": "variable-width",
    "operands": "implicit",
    "dispatch": "computed",
    "opcode_width": "8-16 bits",
    "num_registers": 16,
    "register_width": 64,
}
