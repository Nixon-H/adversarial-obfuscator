"""
microjit.py

Purpose:
Advanced Protection — Polymorphic In-Memory Reassembly (Micro-JIT).
Generates diverse machine code sequences for the same logical operation.
Different builds produce different sequences via seeded pseudo-random
transformations. Generates polymorphic function prologues, epilogues,
and performs instruction reordering, register swapping, and stack offset
shifting on existing x86_64 machine code.

Architectural Role:
Post-compilation machine code obfuscation. Operates directly on x86_64
binary code, rewriting it into structurally different but semantically
equivalent forms. Each build uses a different seed, ensuring per-build
diversity.

Security Relevance:
- Polymorphic prologue/epilogue: register save/restore order varies.
- Instruction reordering: independent instructions within basic blocks
  are shuffled, changing the execution trace.
- Register swapping: applies a random bijective register mapping,
  changing all register encodings in the code.
- Stack offset shifting: adjusts RBP/RSP-relative offsets.
- Insertion of functional NOPs (mov reg,reg; lea reg,[reg+0]; etc.)
  that are dead code to analysis but consume space.
- Seeds produce deterministic but unpredictable output; each build
  is unique.

Threat model: Static analysis, signature detection, binary diffing,
instruction-level reverse engineering.

Dependencies: None (standard library only).
"""

from __future__ import annotations
import argparse
import json
import os
import random
import struct
import sys


# ---- x86_64 register encodings ----

REG_RAX = 0
REG_RCX = 1
REG_RDX = 2
REG_RBX = 3
REG_RSP = 4
REG_RBP = 5
REG_RSI = 6
REG_RDI = 7

REG_R12 = 12
REG_R13 = 13
REG_R14 = 14
REG_R15 = 15

REG_NAMES = ['rax', 'rcx', 'rdx', 'rbx', 'rsp', 'rbp', 'rsi', 'rdi']


def _load_config() -> dict:
    """Load the project config for phase2 gating."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", "default.json"
    )
    try:
        with open(config_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _phase2_enabled() -> bool:
    """Check if phase2 (advanced protection) is enabled in config."""
    cfg = _load_config()
    return cfg.get("shadow_compiler", {}).get("advanced_protection", cfg.get("shadow_compiler", {}).get("phase2", {})).get("enabled", False)


# ---- Functional NOP templates ----

_NOP_TEMPLATES: list[bytes] = [
    b'\x90',                                     # nop
    b'\x66\x90',                                 # 66 nop (2-byte)
    b'\x0f\x1f\x00',                             # nop dword ptr [rax] (3-byte)
    b'\x0f\x1f\x40\x00',                         # nop dword ptr [rax+0] (4-byte)
    b'\x0f\x1f\x44\x00\x00',                     # nop dword ptr [rax+rax+0] (5-byte)
    b'\x66\x0f\x1f\x44\x00\x00',                 # 66 nop dword ptr [rax+rax+0] (6-byte)
    b'\x0f\x1f\x80\x00\x00\x00\x00',             # nop dword ptr [rax+0] (7-byte)
    b'\x0f\x1f\x84\x00\x00\x00\x00\x00',         # nop dword ptr [rax+rax+0] (8-byte)
    b'\x66\x0f\x1f\x84\x00\x00\x00\x00\x00',     # 66 nop dword ptr [rax+rax+0] (9-byte)
    b'\x48\x89\xff',   # mov rdi, rdi
    b'\x48\x89\xc0',   # mov rax, rax
    b'\x48\x89\xdb',   # mov rbx, rbx
    b'\x48\x89\xc9',   # mov rcx, rcx
    b'\x48\x89\xd2',   # mov rdx, rdx
    b'\x48\x89\xf6',   # mov rsi, rsi
    b'\x48\x89\xe4',   # mov rsp, rsp
    b'\x48\x89\xed',   # mov rbp, rbp
    b'\x48\x8d\xa4\x24\x00\x00\x00\x00',  # lea rsp, [rsp+0]
    b'\x48\x8d\x6d\x00',                   # lea rbp, [rbp+0]
    b'\x48\x8d\x00',                       # lea rax, [rax]
    b'\x48\x87\xc0',   # xchg rax, rax
    b'\x48\x87\xdb',   # xchg rbx, rbx
    b'\x48\x87\xc9',   # xchg rcx, rcx
    b'\x48\x87\xd2',   # xchg rdx, rdx
    b'\x48\x87\xf6',   # xchg rsi, rsi
    b'\x48\x87\xff',   # xchg rdi, rdi
]


def _push_register(reg: int) -> bytes:
    if reg <= 7:
        return bytes((0x50 + reg,))
    return bytes((0x41, 0x50 + reg - 8))


def _pop_register(reg: int) -> bytes:
    if reg <= 7:
        return bytes((0x58 + reg,))
    return bytes((0x41, 0x58 + reg - 8))


def _add_rsp_immediate(size: int) -> bytes:
    if size == 0:
        return b""
    if size < 128:
        return b"\x48\x83\xc4" + bytes((size,))
    return b"\x48\x81\xc4" + struct.pack("<I", size)


def _sub_rsp_immediate(size: int) -> bytes:
    if size == 0:
        return b""
    if size < 128:
        return b"\x48\x83\xec" + bytes((size,))
    return b"\x48\x81\xec" + struct.pack("<I", size)


def _lea_rbp_from_rsp(frame_size: int) -> bytes:
    if frame_size == 0:
        return b"\x48\x89\xe5"
    if frame_size < 128:
        return b"\x48\x8d\x6c\x24" + bytes((frame_size,))
    return b"\x48\x8d\xac\x24" + struct.pack("<I", frame_size)


def _lea_rsp_from_rbp(frame_size: int) -> bytes:
    if frame_size == 0:
        return b"\x48\x89\xec"
    return b"\x48\x8d\xa5" + struct.pack("<i", -frame_size)


def _store_register_at_rbp(reg: int, offset: int) -> bytes:
    # mod=10b/rm=101b is [rbp + disp32].  mod=00b/rm=101b would be
    # [rip + disp32], silently storing nowhere near the frame slot.
    rex = 0x48 | (0x04 if reg >= 8 else 0)
    modrm = 0x80 | ((reg & 7) << 3) | 0x05
    return bytes((rex, 0x89, modrm)) + struct.pack("<i", offset)


def _load_register_from_rbp(reg: int, offset: int) -> bytes:
    rex = 0x48 | (0x04 if reg >= 8 else 0)
    modrm = 0x80 | ((reg & 7) << 3) | 0x05
    return bytes((rex, 0x8B, modrm)) + struct.pack("<i", offset)


# ---- x86_64 instruction parser helpers ----

def _rex_prefix(b: int) -> bool:
    """Check if a byte is a REX prefix (0x40-0x4F in 64-bit mode)."""
    return (b & 0xF0) == 0x40


def _is_vex(code: bytes, pos: int) -> bool:
    """True when ``code[pos:]`` starts with a VEX/EVEX prefix in 64-bit mode."""
    if pos + 1 >= len(code):
        return False
    first, second = code[pos], code[pos + 1]
    if first == 0xC5:  # VEX2: the mod field must be 11b in long mode
        return (second & 0xC0) == 0xC0
    if first == 0xC4:  # VEX3
        return (second & 0xC0) == 0xC0
    if first == 0x62:  # EVEX
        return (second & 0xC0) == 0xC0
    return False


def _fully_decodable(code: bytes) -> bool:
    """Conservative gate: refuse to rewrite a block with any unknown byte."""
    pos = 0
    while pos < len(code):
        length = _instruction_length(code, pos)
        if length <= 0:
            return False
        pos += length
    return True


# Opcodes whose operands include implicit registers (stack pointer, accumulator,
# flags or CL). Rewriting their register fields with a mapping that does not
# model those implicit uses silently changes semantics.
_IMPLICIT_FIRST = set(range(0x50, 0x60)) | set(range(0x90, 0x98)) | {
    0x9C, 0x9D, 0xC3, 0xC9, 0xCA, 0xCB, 0xCC, 0xCD, 0xCF,
    0xA4, 0xA5, 0xA6, 0xA7, 0xAA, 0xAB, 0xAC, 0xAD, 0xAE, 0xAF,
    0xD4, 0xD5, 0xE8, 0xE9, 0xEB, 0xF4, 0xFC, 0xFD,
}
_IMPLICIT_TWO = {0x05, 0x31, 0xA2, 0x0B}  # syscall, rdtsc, cpuid, ud2


def _uses_implicit_registers(code: bytes, offset: int, length: int) -> bool:
    """True if the instruction at ``offset`` has implicit register operands."""
    end = min(offset + length, len(code))
    pos = offset
    while pos < end and (_rex_prefix(code[pos]) or code[pos] in (
            0x66, 0x67, 0xF0, 0xF2, 0xF3, 0x2E, 0x36, 0x3E, 0x26, 0x64, 0x65)):
        pos += 1
    if pos >= end:
        return True
    opcode = code[pos]
    if opcode == 0x0F:
        if pos + 1 >= end or code[pos + 1] in _IMPLICIT_TWO:
            return True
        return False
    if opcode in _IMPLICIT_FIRST:
        return True
    # shift-by-CL uses the accumulator and CL even though ModRM encodes only
    # one operand; div/mul/idiv/imul write implicit EDX:EAX pairs.
    if opcode in (0xD0, 0xD1, 0xD2, 0xD3, 0xF6, 0xF7):
        if pos + 1 < end:
            reg_field = (code[pos + 1] >> 3) & 7
            if opcode in (0xF6, 0xF7) and reg_field in (4, 5, 6, 7):
                return True
            if opcode in (0xD0, 0xD1, 0xD2, 0xD3) and reg_field == 0:
                return True
    return False


def _adjusts_stack_pointer(code: bytes, offset: int, length: int) -> bool:
    """True if the instruction writes RSP/RBP or uses an implicit stack reg."""
    if _uses_implicit_registers(code, offset, length):
        return True
    end = min(offset + length, len(code))
    pos = offset
    while pos < end and (_rex_prefix(code[pos]) or code[pos] in (
            0x66, 0x67, 0xF0, 0xF2, 0xF3, 0x2E, 0x36, 0x3E, 0x26, 0x64, 0x65)):
        pos += 1
    if pos + 1 >= end:
        return False
    opcode = code[pos]
    # Arithmetic with a ModRM register destination (add/sub/and/or/xor/cmp)
    # and data moves whose destination is the stack pointer.
    arithmetic = {0x01, 0x03, 0x09, 0x0B, 0x21, 0x23, 0x29, 0x2B,
                  0x31, 0x33, 0x81, 0x83, 0x89, 0x8B}
    if opcode not in arithmetic:
        return False
    modrm = code[pos + 1]
    mod_bits = modrm >> 6
    reg_field = (modrm >> 3) & 7
    rm_field = modrm & 7
    if mod_bits == 3:
        # Register-register form: either side may be the stack pointer.
        return reg_field in (REG_RSP, REG_RBP) or rm_field in (REG_RSP, REG_RBP)
    # Memory form: RBP/RSP in rm is the address base, not a write to the
    # stack pointer, so only a stack register used as data is a problem.
    return reg_field in (REG_RSP, REG_RBP)


_LEGACY_PREFIXES = {
    0x66, 0x67, 0xF0, 0xF2, 0xF3,
    0x2E, 0x36, 0x3E, 0x26, 0x64, 0x65,
}


def _build_one_byte_modrm_table() -> set[int]:
    """Opcodes in the primary x86-64 map that have a ModRM byte."""
    ops: set[int] = set()
    # Integer ALU register/memory forms (the accumulator-immediate forms
    # at +4/+5 do not have ModRM).
    for base in (0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38):
        ops.update(base + i for i in range(4))
    ops.update({
        0x63, 0x69, 0x6B,
        0x80, 0x81, 0x83,
        0x84, 0x85, 0x86, 0x87,
        0x88, 0x89, 0x8A, 0x8B, 0x8C, 0x8D, 0x8E, 0x8F,
        0xC0, 0xC1, 0xC6, 0xC7,
        0xD0, 0xD1, 0xD2, 0xD3,
        0xD8, 0xD9, 0xDA, 0xDB, 0xDC, 0xDD, 0xDE, 0xDF,
        0xF6, 0xF7, 0xFE, 0xFF,
    })
    return ops


_ONE_BYTE_MODRM = _build_one_byte_modrm_table()

# Valid no-ModRM primary-map instructions this decoder accepts.  Opcodes
# that are invalid in 64-bit mode (pusha/popa, most segment pushes, BOUND,
# LES/LDS aliases of VEX, INTO, etc.) are deliberately absent.
_ONE_BYTE_NO_MODRM = (
    set(range(0x50, 0x60))                       # push/pop r64
    | set(range(0x70, 0x80))                     # Jcc rel8
    | set(range(0x90, 0x98))                     # nop / xchg rAX,rAX
    | set(range(0xA0, 0xB0))                     # moffs/string/test/imm8 ops
    | set(range(0xB0, 0xC0))                     # mov r*,imm*
    | set(range(0xE0, 0xEA))                     # loop/jrcxz/in/out/call/jmp
    | {0x04, 0x05, 0x0C, 0x0D, 0x14, 0x15, 0x1C, 0x1D,
       0x24, 0x25, 0x2C, 0x2D, 0x34, 0x35, 0x3C, 0x3D,
       0x68, 0x6A, 0x98, 0x99, 0x9B, 0x9C, 0x9D, 0x9E, 0x9F,
       0xC2, 0xC3, 0xC8, 0xC9, 0xCA, 0xCB, 0xCC, 0xCD, 0xCF,
       0xD7, 0xEB, 0xF1, 0xF4, 0xF5,
       0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD}
)

_TWO_BYTE_NO_MODRM = (
    {0x05, 0x07, 0x0B, 0x31, 0x32, 0x33, 0x34, 0x35, 0x37,
     0x77, 0xA0, 0xA1, 0xA2, 0xA8, 0xA9}
    | set(range(0x80, 0x90))                     # Jcc rel16/rel32
    | set(range(0xC8, 0xD0))                     # bswap r32/r64
)


def _two_byte_has_modrm(op: int) -> bool:
    """Conservative ModRM table for the 0F map."""
    if op in {
        0x00, 0x01, 0x02, 0x03, 0x0D,
        0xA3, 0xA4, 0xA5, 0xAB, 0xAC, 0xAD, 0xAE, 0xAF,
        0xB0, 0xB1, 0xB3, 0xB6, 0xB7, 0xBA, 0xBB, 0xBC, 0xBD, 0xBE, 0xBF,
        0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7,
    }:
        return True
    return (
        0x10 <= op <= 0x24
        or op == 0x26
        or 0x28 <= op <= 0x2F
        or 0x40 <= op <= 0x56
        or 0x58 <= op <= 0x6F
        or 0x70 <= op <= 0x76
        or 0x78 <= op <= 0x7F
        or 0x90 <= op <= 0x9F
        or 0xD0 <= op <= 0xFF
    )


def _decode_x86_instruction(code: bytes, offset: int) -> dict | None:
    """Decode one x86-64 instruction boundary conservatively.

    The decoder is deliberately small, but it is exact for every instruction
    it accepts: legacy/REX prefixes, primary/0F/0F38/0F3A opcode maps,
    ModRM, SIB, displacement, immediates, and the 15-byte architectural
    limit.  Unsupported or invalid encodings return ``None`` rather than a
    guessed length, so callers fail closed instead of splitting instructions.
    """
    if offset < 0 or offset >= len(code):
        return None

    start = pos = offset
    rex = 0
    rex_pos = -1
    last_legacy_pos = -1
    operand_16 = False
    address_32 = False

    while pos < len(code):
        b = code[pos]
        if b in _LEGACY_PREFIXES:
            if b == 0x66:
                operand_16 = True
            elif b == 0x67:
                address_32 = True
            last_legacy_pos = pos
            pos += 1
        elif _rex_prefix(b):
            rex = b
            rex_pos = pos
            pos += 1
        else:
            break
        if pos - start > 15:
            return None

    # In valid x86-64 a REX prefix must be the byte immediately before the
    # opcode.  A legacy prefix after a REX makes that REX inert.
    if rex_pos >= 0 and last_legacy_pos > rex_pos:
        rex = 0

    if pos >= len(code):
        return None
    opcode_pos = pos
    first = code[pos]

    # In 64-bit mode these bytes are VEX/EVEX prefixes or invalid opcodes;
    # this hand decoder does not model either opcode space.
    if first in (0x62, 0xC4, 0xC5):
        return None

    pos += 1
    map_id = 0
    opcode = first
    if first == 0x0F:
        if pos >= len(code):
            return None
        opcode = code[pos]
        pos += 1
        map_id = 0x0F
        if opcode in (0x38, 0x3A):
            if pos >= len(code):
                return None
            map_id = 0x0F00 | opcode
            opcode = code[pos]
            pos += 1

    has_modrm = False
    imm_kind: str | None = None
    rex_w = bool(rex & 0x08)
    zsize = 2 if operand_16 else 4

    if map_id == 0:
        if opcode in _ONE_BYTE_MODRM:
            has_modrm = True
            if opcode == 0x69:
                imm_kind = "immz"
            elif opcode in (0x6B, 0x80, 0x83, 0xC0, 0xC1, 0xC6):
                imm_kind = "imm8"
            elif opcode in (0x81, 0xC7):
                imm_kind = "immz"
            elif opcode == 0xF6:
                imm_kind = "group8"
            elif opcode == 0xF7:
                imm_kind = "groupz"
        elif opcode not in _ONE_BYTE_NO_MODRM:
            return None

        if opcode in (0x04, 0x0C, 0x14, 0x1C, 0x24, 0x2C, 0x34, 0x3C, 0xA8):
            imm_kind = "imm8"
        elif opcode in (0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x35, 0x3D,
                        0x68, 0xA9, 0xE8, 0xE9):
            imm_kind = "immz"
        elif opcode == 0x6A or 0x70 <= opcode <= 0x7F or 0xE0 <= opcode <= 0xE7 \
                or opcode in (0xEB, 0xCD):
            imm_kind = "imm8"
        elif 0xB0 <= opcode <= 0xB7:
            imm_kind = "imm8"
        elif 0xB8 <= opcode <= 0xBF:
            imm_kind = "immv"
        elif opcode in (0xC2, 0xCA):
            imm_kind = "imm16"
        elif opcode == 0xC8:
            imm_kind = "imm16plus8"
        elif 0xA0 <= opcode <= 0xA3:
            imm_kind = "moffs"
    elif map_id == 0x0F:
        if opcode in _TWO_BYTE_NO_MODRM:
            if 0x80 <= opcode <= 0x8F:
                imm_kind = "immz"
        elif _two_byte_has_modrm(opcode):
            has_modrm = True
            if opcode in (0x70, 0x71, 0x72, 0x73, 0xA4, 0xAC, 0xBA,
                          0xC2, 0xC4, 0xC5, 0xC6):
                imm_kind = "imm8"
        else:
            return None
    elif map_id == 0x0F38:
        # Every defined opcode in the 0F38 map uses ModRM and has no
        # immediate.  Reserved encodings are still length-decodable; unknown
        # opcode spaces (VEX/EVEX) are rejected above.
        has_modrm = True
    elif map_id == 0x0F3A:
        # Defined 0F3A opcodes use ModRM and end with an imm8.
        has_modrm = True
        imm_kind = "imm8"
    else:
        return None

    modrm_pos = -1
    sib_pos = -1
    disp_offset = -1
    disp_size = 0
    modrm = None
    sib = None
    modrm_reg = None

    if has_modrm:
        if pos >= len(code):
            return None
        modrm_pos = pos
        modrm = code[pos]
        modrm_reg = (modrm >> 3) & 7
        pos += 1
        mod_bits = modrm >> 6
        rm = modrm & 7
        if mod_bits != 3 and rm == 4:
            if pos >= len(code):
                return None
            sib_pos = pos
            sib = code[pos]
            pos += 1
        if mod_bits == 1:
            disp_size = 1
        elif mod_bits == 2:
            disp_size = 4
        elif mod_bits == 0 and rm == 5:
            disp_size = 4
        elif mod_bits == 0 and rm == 4 and sib is not None and (sib & 7) == 5:
            disp_size = 4
        if disp_size:
            if pos + disp_size > len(code):
                return None
            disp_offset = pos
            pos += disp_size

        # Validate opcode-extension fields whose spare encodings are not
        # instructions at all.  Otherwise random data can look decodable and
        # later rewriters would slice it at invented boundaries.
        if map_id == 0:
            if opcode in (0x8F, 0xC6, 0xC7) and modrm_reg != 0:
                return None
            if opcode == 0xFE and modrm_reg not in (0, 1):
                return None
            if opcode == 0xFF and modrm_reg == 7:
                return None
        elif map_id == 0x0F:
            if opcode == 0xBA and modrm_reg < 4:
                return None
            if opcode in (0x71, 0x72, 0x73) and modrm_reg in (0, 1):
                return None
            if opcode == 0xC3 and mod_bits == 3:  # movnti is memory-only
                return None

    imm_size = 0
    if imm_kind == "imm8":
        imm_size = 1
    elif imm_kind == "immz":
        imm_size = zsize
    elif imm_kind == "immv":
        imm_size = 8 if rex_w else zsize
    elif imm_kind == "imm16":
        imm_size = 2
    elif imm_kind == "imm16plus8":
        imm_size = 3
    elif imm_kind == "moffs":
        imm_size = 4 if address_32 else 8
    elif imm_kind == "group8":
        imm_size = 1 if modrm_reg in (0, 1) else 0
    elif imm_kind == "groupz":
        imm_size = zsize if modrm_reg in (0, 1) else 0

    imm_offset = -1
    if imm_size:
        if pos + imm_size > len(code):
            return None
        imm_offset = pos
        pos += imm_size

    length = pos - start
    if length <= 0 or length > 15:
        return None
    return {
        "length": length,
        "start": start,
        "prefix_end": opcode_pos,
        "opcode_pos": opcode_pos,
        "map": map_id,
        "opcode": opcode,
        "rex": rex,
        "rex_pos": rex_pos,
        "operand_16": operand_16,
        "address_32": address_32,
        "has_modrm": has_modrm,
        "modrm_pos": modrm_pos,
        "modrm": modrm,
        "modrm_reg": modrm_reg,
        "sib_pos": sib_pos,
        "sib": sib,
        "disp_offset": disp_offset,
        "disp_size": disp_size,
        "imm_offset": imm_offset,
        "imm_size": imm_size,
    }


def _instruction_length(code: bytes, offset: int) -> int:
    """
    Return the exact length of a supported x86-64 instruction at ``offset``.

    Unknown, invalid, truncated, VEX, or EVEX encodings return 0.  Callers
    must treat 0 as a refusal boundary, never as a one-byte instruction.
    """
    decoded = _decode_x86_instruction(code, offset)
    return decoded["length"] if decoded is not None else 0

def _instruction_boundaries(code: bytes) -> list[int]:
    """Byte offsets where an instruction starts (plus the end of the block)."""
    boundaries = []
    pos = 0
    while pos < len(code):
        boundaries.append(pos)
        length = _instruction_length(code, pos)
        if length <= 0:
            # Undecodable byte: treat it as a one-byte instruction so the
            # walk still terminates.
            length = 1
        pos += length
    boundaries.append(len(code))
    return boundaries


def _get_instruction_regs(code: bytes, offset: int) -> set[int]:
    """
    Extract x86 register numbers referenced by the instruction at ``offset``.

    This is an over-approximation for dependency analysis: every explicit
    register operand and addressing base/index is included.  RIP-relative
    addressing and absent SIB indices are not registers.  Returns an empty
    set for undecodable instructions.
    """
    meta = _decode_x86_instruction(code, offset)
    if meta is None:
        return set()
    regs: set[int] = set()
    rex = meta["rex"]
    rex_b = 8 if rex & 0x01 else 0
    rex_x = 8 if rex & 0x02 else 0
    rex_r = 8 if rex & 0x04 else 0
    opcode = meta["opcode"]

    if meta["map"] == 0:
        if 0x50 <= opcode <= 0x57:
            regs.add((opcode - 0x50) + rex_b)
            return regs
        if 0x58 <= opcode <= 0x5F:
            regs.add((opcode - 0x58) + rex_b)
            return regs
        if 0xB0 <= opcode <= 0xB7:
            regs.add((opcode - 0xB0) + rex_b)
            return regs
        if 0xB8 <= opcode <= 0xBF:
            regs.add((opcode - 0xB8) + rex_b)
            return regs
    elif meta["map"] == 0x0F and 0xC8 <= opcode <= 0xCF:
        regs.add((opcode - 0xC8) + rex_b)
        return regs

    if not meta["has_modrm"]:
        return regs
    modrm = meta["modrm"]
    mod_bits = modrm >> 6
    rm_low = modrm & 7
    # The ModRM reg field is sometimes an opcode extension rather than a
    # register.  Including it here is a safe over-approximation for dataflow
    # grouping; the rewrite path uses a stricter predicate before editing it.
    regs.add(((modrm >> 3) & 7) + rex_r)

    if mod_bits == 3:
        regs.add(rm_low + rex_b)
    elif rm_low == 4 and meta["sib"] is not None:
        sib = meta["sib"]
        base_low = sib & 7
        index_low = (sib >> 3) & 7
        if not (mod_bits == 0 and base_low == 5):
            regs.add(base_low + rex_b)
        if index_low != 4 or rex_x:
            regs.add(index_low + rex_x)
    elif not (mod_bits == 0 and rm_low == 5):
        regs.add(rm_low + rex_b)
    return regs


# ---- MicroJITEngine ----

class MicroJITEngine:
    """
    Generates polymorphic machine code sequences using a per-build seed.

    Provides methods for:
    - generate_prologue(): polymorphic function prologue.
    - generate_epilogue(): polymorphic function epilogue.
    - generate_nop_sled(length): functional NOP sled.
    - reorder_instructions(code, basic_blocks): reorder within blocks.
    - swap_registers(code, register_map): remap register encodings.
    - alter_stack_offsets(code, offset_delta): shift stack offsets.
    - polymorphic_rewrite(block): all transformations at once.
    """

    def __init__(self, seed: int, arch: str = 'x86_64'):
        """Initialize with a seed and target architecture."""
        self.seed = seed
        self.arch = arch
        self._rng = random.Random(seed)

    def _randrange(self, lo: int, hi: int) -> int:
        """Random integer in [lo, hi)."""
        return self._rng.randrange(lo, hi)

    def _choice(self, seq):
        """Random element from a sequence."""
        return self._rng.choice(seq)

    def _shuffle(self, seq):
        """In-place shuffle of a sequence."""
        self._rng.shuffle(seq)

    # ---- Shared prologue/epilogue layout ----

    def _frame_layout(self):
        """One deterministic layout plan shared by both halves of a function."""
        cached = getattr(self, "_cached_frame_layout", None)
        if cached is not None:
            return cached
        rng = random.Random(self.seed ^ 0x4D4943524F4A4954)
        saved = [REG_RBX, REG_R12, REG_R13, REG_R14, REG_R15]
        rng.shuffle(saved)
        cached = {
            "variant": rng.randrange(3),
            "frame": rng.choice([0, 8, 16, 24, 32, 64, 128]),
            "saved": saved,
        }
        self._cached_frame_layout = cached
        return cached

    def generate_prologue(self) -> bytes:
        """Generate a prologue whose exact inverse is ``generate_epilogue``."""
        layout = self._frame_layout()
        saved = layout["saved"]
        frame = layout["frame"]
        variant = layout["variant"]
        parts = []
        if variant in (0, 2):
            parts.extend((b"\x55", b"\x48\x89\xe5"))  # push rbp; mov rbp,rsp
        if variant == 2:
            parts.append(_sub_rsp_immediate(frame))
            parts.extend(_push_register(reg) for reg in saved)
        else:
            parts.extend(_push_register(reg) for reg in saved)
            if variant == 0:
                parts.append(_sub_rsp_immediate(frame))
            else:
                parts.append(b"\x55")  # push rbp after callee-saved registers
                parts.append(b"\x48\x89\xe5")
                parts.append(_sub_rsp_immediate(frame))
        return b"".join(parts)

    def generate_epilogue(self) -> bytes:
        """Generate the exact stack/register inverse of the shared layout."""
        layout = self._frame_layout()
        saved = list(reversed(layout["saved"]))
        frame = layout["frame"]
        variant = layout["variant"]
        parts = []
        if variant == 0:
            parts.append(_add_rsp_immediate(frame))
            parts.extend(_pop_register(reg) for reg in saved)
            parts.append(b"\x5d")  # pop rbp
        elif variant == 1:
            parts.append(_add_rsp_immediate(frame))
            parts.append(b"\xc9")  # leave: mov rsp,rbp; pop rbp
            parts.extend(_pop_register(reg) for reg in saved)
        else:
            parts.extend(_pop_register(reg) for reg in saved)
            parts.append(b"\x48\x89\xec")  # mov rsp,rbp (discard frame)
            parts.append(b"\x5d")
        parts.append(b"\xc3")
        return b"".join(parts)

    # ---- NOP sled generation ----

    def generate_nop_sled(self, length: int) -> bytes:
        """
        Generate functional NOPs of total `length` bytes.

        Selects from a pool of 26+ NOP templates including standard
        multi-byte NOPs, mov reg,reg, lea reg,[reg+0], and xchg reg,reg.
        """
        result = bytearray()
        while len(result) < length:
            remaining = length - len(result)
            candidates = [t for t in _NOP_TEMPLATES if len(t) <= remaining]
            if not candidates:
                candidates = [b'\x90']
            nop = self._choice(candidates)
            result.extend(nop)
        return bytes(result)

    # ---- Instruction reordering ----

    @staticmethod
    def _safe_to_reorder(instruction: bytes) -> bool:
        """Allow only decoded, flag-neutral, register-only instructions."""
        if instruction in _NOP_TEMPLATES or instruction == b"\xc3":
            return True
        if len(instruction) == 10 and instruction[0] & 0xF8 == 0x48 \
                and 0xB8 <= instruction[1] <= 0xBF:
            return True  # mov r64, imm64
        if len(instruction) == 3 and instruction[0] & 0xF8 == 0x48 \
                and instruction[1] == 0x89 and instruction[2] & 0xC0 == 0xC0:
            return True  # mov r64, r64 (register-direct ModRM)
        return False

    def reorder_instructions(self, code: bytes, basic_block: list) -> bytes:
        """Shuffle only independent safe instructions and insert boundary NOPs.

        Any undecodable, memory, flag-changing, control-flow, stack, VEX, or
        otherwise unmodeled instruction makes the entire rewrite fail closed.
        """
        if not basic_block:
            return code
        result = bytearray()
        prev_end = 0
        for start, end in sorted(basic_block):
            if start < prev_end or start < 0 or end > len(code) or end <= start:
                return code
            if start > prev_end:
                result.extend(code[prev_end:start])
            block = code[start:end]
            if not _fully_decodable(block):
                return code
            boundaries = _instruction_boundaries(block)
            instructions = []
            for left, right in zip(boundaries, boundaries[1:]):
                instruction = block[left:right]
                if not self._safe_to_reorder(instruction):
                    return code
                instructions.append(instruction)
            if b"\xc3" in instructions and instructions[-1] != b"\xc3":
                return code

            groups = []
            current = []
            used_regs = set()
            for instruction in instructions:
                if instruction == b"\xc3":
                    if current:
                        groups.append(current)
                        current = []
                        used_regs = set()
                    groups.append([instruction])
                    continue
                regs = _get_instruction_regs(instruction, 0)
                if current and used_regs & regs:
                    groups.append(current)
                    current = []
                    used_regs = set()
                current.append(instruction)
                used_regs |= regs
            if current:
                groups.append(current)

            for group in groups:
                if len(group) > 1:
                    self._shuffle(group)
                for instruction in group:
                    result.extend(instruction)
                    if instruction != b"\xc3" and self._randrange(0, 4) == 0:
                        result.extend(self.generate_nop_sled(self._randrange(1, 3)))
            prev_end = end
        if prev_end < len(code):
            result.extend(code[prev_end:])
        return bytes(result)

    def _slice_instructions(self, block: bytes) -> list[tuple[int, int, int]]:
        """Return list of (instruction_index, offset, length) within block."""
        instrs = []
        offset = 0
        idx = 0
        while offset < len(block):
            length = _instruction_length(block, offset)
            if length == 0:
                length = 1
            instrs.append((idx, offset, length))
            offset += length
            idx += 1
        return instrs

    def _find_independent_groups(self, block: bytes, instrs: list) -> list[list]:
        """Group instructions into dependency chains based on register usage."""
        if not instrs:
            return []
        groups: list[list] = []
        used_regs: set[int] = set()
        current_group: list = []
        for idx, offset, length in instrs:
            regs = _get_instruction_regs(block, offset)
            if regs & used_regs:
                if current_group:
                    groups.append(current_group)
                current_group = [(idx, offset, length)]
                used_regs = regs.copy()
            else:
                current_group.append((idx, offset, length))
                used_regs.update(regs)
        if current_group:
            groups.append(current_group)
        return groups

    # ---- Register swapping ----

    def swap_registers(self, code: bytes, register_map: dict) -> bytes:
        """
        Remap register encodings in x86_64 machine code using a random bijection.

        `register_map` maps old register number -> new register number (0-15).
        Handles REX prefix adjustments for extended registers.
        """
        if not register_map:
            return code
        if not _fully_decodable(code):
            # VEX/EVEX or an unknown opcode: a partial rewrite would corrupt
            # instruction boundaries, so leave the block untouched.
            return code
        # RSP and RBP are structural: remapping either one breaks every
        # stack access in the block, so they stay pinned.
        register_map = {old_r: new_r for old_r, new_r in register_map.items()
                        if old_r not in (REG_RSP, REG_RBP)}
        for pinned in (REG_RSP, REG_RBP):
            register_map[pinned] = pinned
        result = bytearray(code)
        pos = 0
        while pos < len(result):
            instr_len = _instruction_length(result, pos)
            if instr_len == 0 or _uses_implicit_registers(result, pos, instr_len):
                # A remap that ignores implicit stack/accumulator/CL operands
                # changes semantics; refuse the whole block.
                return code
            self._swap_regs_in_instruction(result, pos, instr_len, register_map)
            pos += instr_len
        return bytes(result)

    @staticmethod
    def _modrm_reg_is_register(meta: dict) -> bool:
        """True when the ModRM reg field is a register, not an opcode extension."""
        opcode = meta["opcode"]
        if meta["map"] == 0:
            return opcode not in {
                0x80, 0x81, 0x83, 0x8F,
                0xC0, 0xC1, 0xC6, 0xC7,
                0xD0, 0xD1, 0xD2, 0xD3,
                0xF6, 0xF7, 0xFE, 0xFF,
            }
        if meta["map"] == 0x0F:
            return opcode not in {0x00, 0x01, 0x71, 0x72, 0x73, 0xAE, 0xBA, 0xC7}
        return True

    def _swap_regs_in_instruction(self, code: bytearray, offset: int, length: int,
                                  reg_map: dict) -> None:
        """Apply register remapping within a single decoded instruction."""
        del length  # The decoder is authoritative; a mismatch must not truncate parsing.
        meta = _decode_x86_instruction(code, offset)
        if meta is None or meta["start"] != offset:
            return
        rex_idx = meta["rex_pos"]
        rex = meta["rex"]
        rex_b = 8 if rex & 0x01 else 0
        rex_x = 8 if rex & 0x02 else 0
        rex_r = 8 if rex & 0x04 else 0
        opcode = meta["opcode"]
        opcode_pos = meta["opcode_pos"]

        def rewrite_opcode_register(base: int, low_reg: int) -> None:
            old_reg = low_reg + rex_b
            if old_reg not in reg_map:
                return
            new_reg = reg_map[old_reg]
            if new_reg < 0 or new_reg > 15:
                return
            if new_reg >= 8 and rex_idx < 0:
                return
            code[opcode_pos] = base + (new_reg & 7)
            if rex_idx >= 0:
                new_rex = 0x40 | (rex & 0x0E)
                if new_reg >= 8:
                    new_rex |= 0x01
                else:
                    new_rex &= ~0x01
                code[rex_idx] = new_rex

        # push r64 and pop r64 are separate opcode bases; treating both as
        # 0x50+rd turned POP into PUSH while decoding r8 as rcx.
        if meta["map"] == 0 and 0x50 <= opcode <= 0x57:
            rewrite_opcode_register(0x50, opcode - 0x50)
            return
        if meta["map"] == 0 and 0x58 <= opcode <= 0x5F:
            rewrite_opcode_register(0x58, opcode - 0x58)
            return

        # mov r8/r16/r32/r64,imm: B0+rd is imm8 and B8+rd is imm16/32/64.
        if meta["map"] == 0 and 0xB0 <= opcode <= 0xB7:
            rewrite_opcode_register(0xB0, opcode - 0xB0)
            return
        if meta["map"] == 0 and 0xB8 <= opcode <= 0xBF:
            rewrite_opcode_register(0xB8, opcode - 0xB8)
            return

        if not meta["has_modrm"]:
            return

        modrm_pos = meta["modrm_pos"]
        modrm = meta["modrm"]
        mod_bits = modrm >> 6
        rm_low = modrm & 7
        reg_low = (modrm >> 3) & 7
        edit_reg = self._modrm_reg_is_register(meta)
        old_reg = reg_low + rex_r
        new_reg = reg_map.get(old_reg, old_reg) if edit_reg else old_reg

        new_rm_low = rm_low
        new_rm_high = rex_b
        rewrite_rm = False
        if mod_bits == 3:
            old_rm = rm_low + rex_b
            new_rm = reg_map.get(old_rm, old_rm)
            new_rm_low = new_rm & 7
            new_rm_high = 8 if new_rm >= 8 else 0
            rewrite_rm = True
        elif rm_low != 4 and not (mod_bits == 0 and rm_low == 5):
            old_rm = rm_low + rex_b
            new_rm = reg_map.get(old_rm, old_rm)
            new_rm_low = new_rm & 7
            new_rm_high = 8 if new_rm >= 8 else 0
            rewrite_rm = True

        sib_pos = meta["sib_pos"]
        new_sib = meta["sib"]
        new_x_high = rex_x
        if mod_bits != 3 and rm_low == 4 and new_sib is not None:
            scale = new_sib >> 6
            index_low = (new_sib >> 3) & 7
            base_low = new_sib & 7
            new_index_low = index_low
            new_base_low = base_low
            if index_low != 4 or rex_x:
                old_index = index_low + rex_x
                new_index = reg_map.get(old_index, old_index)
                new_index_low = new_index & 7
                new_x_high = 8 if new_index >= 8 else 0
            if not (mod_bits == 0 and base_low == 5):
                old_base = base_low + rex_b
                new_base = reg_map.get(old_base, old_base)
                new_base_low = new_base & 7
                new_rm_high = 8 if new_base >= 8 else 0
            new_sib = (scale << 6) | (new_index_low << 3) | new_base_low
            # The SIB byte carries base/index; rm stays 100b.
            new_rm_low = 4
            rewrite_rm = True

        need_r = new_reg >= 8
        need_b = bool(new_rm_high)
        need_x = bool(new_x_high)
        if rex_idx < 0 and (need_r or need_b or need_x):
            # Inserting a REX byte would shift immediates and every following
            # instruction.  Length-preserving rewrite cannot express it.
            return

        if edit_reg:
            modrm = (mod_bits << 6) | ((new_reg & 7) << 3) | (modrm & 7)
        if rewrite_rm:
            modrm = (modrm & 0xF8) | new_rm_low
        code[modrm_pos] = modrm
        if sib_pos >= 0 and new_sib is not None:
            code[sib_pos] = new_sib
        if rex_idx >= 0:
            new_rex = 0x40 | (rex & 0x08)
            if need_r:
                new_rex |= 0x04
            if need_x:
                new_rex |= 0x02
            if need_b:
                new_rex |= 0x01
            code[rex_idx] = new_rex

    # ---- Stack offset alteration ----

    def alter_stack_offsets(self, code: bytes, offset_delta: int) -> bytes:
        """
        Shift RBP/RSP-relative displacement fields by ``offset_delta``.

        Only decoded ModRM memory operands with a real RBP/RSP base are
        rewritten.  Instructions without ModRM, RIP-relative operands,
        immediates, and displacements that would overflow their encoded
        signed width make the whole transformation fail closed.
        """
        if offset_delta == 0:
            return code
        if not _fully_decodable(code):
            return code
        result = bytearray(code)
        pos = 0
        while pos < len(result):
            meta = _decode_x86_instruction(result, pos)
            if meta is None:
                return code
            length = meta["length"]
            if _adjusts_stack_pointer(result, pos, length):
                return code
            if meta["has_modrm"] and meta["disp_size"] in (1, 4):
                modrm = meta["modrm"]
                mod_bits = modrm >> 6
                rm_low = modrm & 7
                base = None
                if rm_low == 4 and meta["sib"] is not None:
                    base_low = meta["sib"] & 7
                    if not (mod_bits == 0 and base_low == 5):
                        base = base_low + (8 if meta["rex"] & 0x01 else 0)
                elif not (mod_bits == 0 and rm_low == 5):
                    base = rm_low + (8 if meta["rex"] & 0x01 else 0)
                if base in (REG_RSP, REG_RBP):
                    disp_offset = meta["disp_offset"]
                    if meta["disp_size"] == 1:
                        old = struct.unpack('<b', result[disp_offset:disp_offset + 1])[0]
                        new = old + offset_delta
                        if not -128 <= new <= 127:
                            return code
                        result[disp_offset] = new & 0xFF
                    else:
                        old = struct.unpack('<i', result[disp_offset:disp_offset + 4])[0]
                        new = old + offset_delta
                        if not -(1 << 31) <= new <= (1 << 31) - 1:
                            return code
                        result[disp_offset:disp_offset + 4] = struct.pack('<i', new)
            pos += length
        return bytes(result)

    # ---- Full polymorphic rewrite ----

    def polymorphic_rewrite(self, block: bytes) -> bytes:
        """
        Apply all transformations with random parameters.

        Applies register swapping, NOP insertion, and stack offset
        shifting to produce a semantically equivalent but structurally
        different code block.
        """
        if not _fully_decodable(block):
            # NOP insertion uses the hand decoder's boundaries; on VEX or an
            # unknown opcode those boundaries are guesses, so do nothing.
            return bytes(block)
        block = bytearray(block)
        reg_map = self.generate_random_register_map()
        block = bytearray(self.swap_regrites(bytes(block), reg_map))
        nop_count = self._randrange(1, 5)
        # Insert only at instruction boundaries: a NOP dropped inside an
        # instruction splits it and changes what the CPU decodes.
        boundaries = _instruction_boundaries(bytes(block))
        for _ in range(nop_count):
            if not boundaries or len(block) > 256:
                break
            pos = self._choice(boundaries)
            nop = self.generate_nop_sled(self._randrange(1, 4))
            block[pos:pos] = nop
            boundaries = [b + len(nop) if b >= pos else b for b in boundaries]
            boundaries.append(pos + len(nop))
        offset_delta = self._choice([8, 16, -8, -16, 32, -32, 0, 0])
        if offset_delta != 0:
            block = bytearray(self.alter_stack_offtsets(bytes(block), offset_delta))
        return bytes(block)

    def swap_regrites(self, code: bytes, reg_map: dict) -> bytes:
        """Alias for swap_registers (legacy name)."""
        return self.swap_registers(code, reg_map)

    def alter_stack_offtsets(self, code: bytes, offset_delta: int) -> bytes:
        """Alias for alter_stack_offsets (legacy name)."""
        return self.alter_stack_offsets(code, offset_delta)

    def generate_random_register_map(self) -> dict:
        """Generate a random bijective register mapping (RAX=0..RDI=7).

        RSP and RBP are pinned: shuffling them would break every stack
        access in the rewritten block.
        """
        movable = [r for r in range(8) if r not in (REG_RSP, REG_RBP)]
        shuffled = list(movable)
        # Derangement: a register that maps to itself leaves the code
        # unchanged, so retry until every movable register actually moves.
        for _ in range(64):
            self._shuffle(shuffled)
            if all(a != b for a, b in zip(movable, shuffled)):
                break
        mapping = {r: r for r in range(8)}
        mapping.update(dict(zip(movable, shuffled)))
        return mapping


# ---- CLI ----

def _cli_generate_prologue(args: list[str]):
    """CLI handler for prologue generation."""
    parser = argparse.ArgumentParser(description="Generate polymorphic prologue")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--hex", action="store_true", help="Output as hex string")
    pargs = parser.parse_args(args)
    engine = MicroJITEngine(pargs.seed)
    prologue = engine.generate_prologue()
    if pargs.hex:
        print(prologue.hex())
    else:
        sys.stdout.buffer.write(prologue)


def _cli_generate_epilogue(args: list[str]):
    """CLI handler for epilogue generation."""
    parser = argparse.ArgumentParser(description="Generate polymorphic epilogue")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--hex", action="store_true", help="Output as hex string")
    pargs = parser.parse_args(args)
    engine = MicroJITEngine(pargs.seed)
    epilogue = engine.generate_epilogue()
    if pargs.hex:
        print(epilogue.hex())
    else:
        sys.stdout.buffer.write(epilogue)


def _cli_polymorph(args: list[str]):
    """CLI handler for polymorphic rewrite."""
    parser = argparse.ArgumentParser(description="Polymorphically rewrite machine code")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--hex", action="store_true", help="Input/output as hex")
    parser.add_argument("input", help="Input machine code file (or hex string with --hex)")
    parser.add_argument("-o", "--output", help="Output file")
    pargs = parser.parse_args(args)
    engine = MicroJITEngine(pargs.seed)
    if pargs.hex:
        code = bytes.fromhex(pargs.input)
    else:
        with open(pargs.input, 'rb') as f:
            code = f.read()
    result = engine.polymorphic_rewrite(code)
    if pargs.hex:
        print(result.hex())
    elif pargs.output:
        with open(pargs.output, 'wb') as f:
            f.write(result)
    else:
        sys.stdout.buffer.write(result)


def main():
    """CLI entry point for Micro-JIT engine."""
    if not _phase2_enabled():
        _load_config()
        print("Advanced Protection disabled. Set advanced_protection.enabled = true in config/default.json")
        sys.exit(0)

    parser = argparse.ArgumentParser(
        description="Nixon Advanced Protection -- Micro-JIT In-Memory Reassembly Engine"
    )
    sub = parser.add_subparsers(dest="command")

    pp = sub.add_parser("prologue", help="Generate polymorphic prologue")
    pp.add_argument("--seed", type=int, default=0)
    pp.add_argument("--hex", action="store_true")

    ep = sub.add_parser("epilogue", help="Generate polymorphic epilogue")
    ep.add_argument("--seed", type=int, default=0)
    ep.add_argument("--hex", action="store_true")

    mp = sub.add_parser("polymorph", help="Polymorphic rewrite of machine code")
    mp.add_argument("--seed", type=int, required=True)
    mp.add_argument("--hex", action="store_true")
    mp.add_argument("input")
    mp.add_argument("-o", "--output")

    args = parser.parse_args()
    if args.command == "prologue":
        _cli_generate_prologue(sys.argv[2:])
    elif args.command == "epilogue":
        _cli_generate_epilogue(sys.argv[2:])
    elif args.command == "polymorph":
        _cli_polymorph(sys.argv[2:])
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
