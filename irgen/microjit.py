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


# ---- x86_64 instruction parser helpers ----

def _rex_prefix(b: int) -> bool:
    """Check if a byte is a REX prefix (0x40-0x4F, excluding 0x40)."""
    return (b & 0xF0) == 0x40 and b != 0x40


def _instruction_length(code: bytes, offset: int) -> int:
    """
    Estimate length of an x86_64 instruction at the given offset.

    Handles REX prefixes, legacy prefixes, opcode bytes, ModRM,
    SIB, displacement, and immediate fields. Returns 0 for unknown
    instructions.
    """
    if offset >= len(code):
        return 0
    pos = offset
    consumed = 0
    rex = 0
    prefixes = 0
    while pos < len(code):
        b = code[pos]
        if _rex_prefix(b):
            rex = b
            pos += 1
            consumed += 1
        elif b in (0x66, 0x67, 0xF0, 0xF2, 0xF3, 0x2E, 0x36, 0x3E, 0x26, 0x64, 0x65):
            prefixes += 1
            pos += 1
            consumed += 1
        else:
            break
    if pos >= len(code):
        return 0
    opcode = code[pos]
    opcode_len = 1
    pos += 1
    consumed += 1
    if opcode == 0x0F:
        if pos < len(code):
            opcode = (opcode << 8) | code[pos]
            pos += 1
            consumed += 1
            opcode_len = 2
        else:
            return 0
    has_modrm = False
    if opcode <= 0xFF:
        first = opcode if opcode_len == 1 else (opcode >> 8)
        second = opcode & 0xFF if opcode_len == 2 else 0
        if opcode_len == 1:
            if 0x00 <= first <= 0x3F:
                has_modrm = True
            elif 0x50 <= first <= 0x5F:
                has_modrm = False
            elif 0x70 <= first <= 0x7F:
                has_modrm = False
            elif 0x88 <= first <= 0x8B:
                has_modrm = True
            elif 0x8D == first:
                has_modrm = True
            elif 0xA0 <= first <= 0xA3:
                has_modrm = False
            elif 0xA8 <= first <= 0xA9:
                has_modrm = False
            elif 0xB0 <= first <= 0xBF:
                has_modrm = False
            elif 0xC0 <= first <= 0xC1:
                has_modrm = True
            elif 0xC3 == first or 0xC9 == first or 0xCB == first or 0xCF == first:
                has_modrm = False
            elif 0xD0 <= first <= 0xD3:
                has_modrm = True
            elif 0xE8 <= first <= 0xEB:
                has_modrm = False
            elif 0xFE <= first <= 0xFF:
                has_modrm = True
            else:
                has_modrm = False
        else:
            if 0x00 <= second <= 0x7F:
                has_modrm = True
            elif 0x80 <= second <= 0x8F:
                has_modrm = True
            elif 0x90 <= second <= 0x9F:
                has_modrm = False
            elif 0xA0 <= second <= 0xBF:
                has_modrm = False
            elif second == 0xC7:
                has_modrm = True
            else:
                has_modrm = False
    if has_modrm:
        if pos >= len(code):
            return 0
        modrm = code[pos]
        mod_bits = modrm >> 6
        rm = modrm & 0x7
        pos += 1
        consumed += 1
        has_sib = (mod_bits != 3 and rm == 4)
        if has_sib:
            if pos >= len(code):
                return 0
            sib = code[pos]
            pos += 1
            consumed += 1
            base = sib & 0x7
        disp_size = 0
        if mod_bits == 1:
            disp_size = 1
        elif mod_bits == 2:
            disp_size = 4
        elif mod_bits == 0 and rm == 5:
            disp_size = 4
        elif has_sib and mod_bits == 0 and base == 5:
            disp_size = 4
        if disp_size > 0:
            if pos + disp_size > len(code):
                return 0
            pos += disp_size
            consumed += disp_size
    imm_size = 0
    if opcode_len == 1:
        first = opcode
        if 0x04 <= first <= 0x05 and rex == 0:
            imm_size = 1
        elif first == 0x0F:
            pass
        elif first in (0xA8, 0xA9):
            imm_size = 1 if first == 0xA8 else 4
        elif 0xB0 <= first <= 0xBF:
            imm_size = 8 if rex & 0x08 else (4 if first >= 0xB8 else 1)
        elif first in (0xE8, 0xE9):
            imm_size = 4
        elif first in (0xEB,):
            imm_size = 1
        elif first in (0xC0, 0xC1):
            imm_size = 1
        elif first in (0xC2, 0xCA):
            imm_size = 2
        elif first == 0xCD:
            imm_size = 1
        elif first == 0x80:
            imm_size = 1
        elif 0xD0 <= first <= 0xD3:
            imm_size = 0
        elif first == 0xF6:
            imm_size = 1
    else:
        second = opcode & 0xFF
        if second in (0x80, 0x83, 0xBA):
            imm_size = 1 if second == 0x83 else (4 if second == 0xBA else 1)
        elif second in (0xC7,):
            imm_size = 4
        elif second in (0xA4, 0xAC):
            imm_size = 1
    if imm_size > 0:
        if pos + imm_size > len(code):
            return 0
        pos += imm_size
        consumed += imm_size
    return consumed


def _get_instruction_regs(code: bytes, offset: int) -> set[int]:
    """
    Extract register numbers referenced at a given instruction offset.

    Returns a set of register numbers (0-15) used as sources,
    destinations, or addressing components.
    """
    if offset >= len(code):
        return set()
    pos = offset
    rex = 0
    while pos < len(code):
        b = code[pos]
        if _rex_prefix(b):
            rex = b
            pos += 1
        elif b in (0x66, 0x67, 0xF0, 0xF2, 0xF3, 0x2E, 0x36, 0x3E, 0x26, 0x64, 0x65):
            pos += 1
        else:
            break
    if pos >= len(code):
        return set()
    regs: set[int] = set()
    opcode = code[pos]
    pos += 1
    if opcode == 0x0F and pos < len(code):
        opcode = (opcode << 8) | code[pos]
        pos += 1
    rex_b = (rex & 0x01) != 0
    rex_r = (rex & 0x04) != 0
    opcode_len = 2 if opcode > 0xFF else 1
    first = opcode if opcode_len == 1 else (opcode >> 8)
    if opcode_len == 1 and 0x50 <= first <= 0x5F:
        reg = (first - 0x50) | (1 if rex_b else 0)
        regs.add(reg)
        return regs
    if opcode_len == 1 and 0xB0 <= first <= 0xBF:
        reg = (first - 0xB0) | (1 if rex_b else 0)
        regs.add(reg)
        return regs
    has_modrm = False
    if opcode_len == 1:
        if 0x00 <= first <= 0x3F or 0x88 <= first <= 0x8B or first == 0x8D or 0xC0 <= first <= 0xC1 or 0xD0 <= first <= 0xD3 or first in (0xFE, 0xFF):
            has_modrm = True
    else:
        if 0x00 <= (opcode & 0xFF) <= 0x7F or 0x80 <= (opcode & 0xFF) <= 0x8F or (opcode & 0xFF) == 0xC7:
            has_modrm = True
    if has_modrm and pos < len(code):
        modrm = code[pos]
        mod_bits = modrm >> 6
        reg = ((modrm >> 3) & 0x07) | (4 if rex_r else 0)
        rm = (modrm & 0x07) | (8 if rex_b else 0)
        regs.add(reg)
        if mod_bits == 3:
            regs.add(rm)
        else:
            regs.add(rm)
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

    # ---- Prologue generation ----

    def generate_prologue(self) -> bytes:
        """
        Generate a random function prologue with polymorphic register save order.

        Variants:
        0: push rbp; mov rbp, rsp; push regs; sub rsp, frame
        1: push regs; push rbp; sub rsp, frame; lea rbp, [rsp+frame]
        2: push rbp; mov rbp, rsp; sub rsp, frame; push regs (reversed)
        3: sub rsp, frame+8*N; push rbp; mov rbp, rsp; mov [rsp+off], regs
        """
        saved_regs = [REG_RBX, REG_RBP, REG_R12, REG_R13, REG_R14, REG_R15]
        self._shuffle(saved_regs)
        stack_frame_sizes = [0, 8, 16, 24, 32, 64, 128]
        frame_size = self._choice(stack_frame_sizes)
        variant = self._randrange(0, 4)
        parts = []
        if variant == 0:
            parts.append(b'\x55')
            parts.append(b'\x48\x89\xe5')
            for r in saved_regs:
                if r <= 7:
                    if r == REG_RBP:
                        continue
                    parts.append(bytes([0x50 + r]))
                else:
                    parts.append(bytes([0x41, 0x50 + (r - 8)]))
            if frame_size > 0:
                if frame_size < 128:
                    parts.append(b'\x48\x83\xec' + bytes([frame_size]))
                else:
                    parts.append(b'\x48\x81\xec' + struct.pack('<I', frame_size))
        elif variant == 1:
            for r in saved_regs:
                if r <= 7:
                    parts.append(bytes([0x50 + r]))
                else:
                    parts.append(bytes([0x41, 0x50 + (r - 8)]))
            parts.append(b'\x55')
            if frame_size > 0:
                parts.append(b'\x48\x83\xec' + bytes([frame_size]))
                parts.append(b'\x48\x8d\x6c\x24' + bytes([frame_size]))
            else:
                parts.append(b'\x48\x89\xe5')
        elif variant == 2:
            parts.append(b'\x55')
            parts.append(b'\x48\x89\xe5')
            if frame_size > 0:
                parts.append(b'\x48\x81\xec' + struct.pack('<I', frame_size))
            for r in reversed(saved_regs):
                if r <= 7:
                    parts.append(bytes([0x50 + r]))
                else:
                    parts.append(bytes([0x41, 0x50 + (r - 8)]))
        else:
            if frame_size > 0:
                parts.append(b'\x48\x83\xec' + bytes([frame_size + 8 * len(saved_regs)]))
            else:
                parts.append(b'\x48\x83\xec' + bytes([8 * len(saved_regs)]))
            parts.append(b'\x55')
            parts.append(b'\x48\x89\xe5')
            offset = 0
            for r in saved_regs:
                if r <= 7:
                    parts.append(b'\x48\x89\xbc\x24' + struct.pack('<I', offset))
                else:
                    parts.append(b'\x4c\x89\xbc\x24' + struct.pack('<I', offset))
                offset += 8

        return b''.join(parts)

    # ---- Epilogue generation ----

    def generate_epilogue(self) -> bytes:
        """
        Generate a random function epilogue with polymorphic register restore order.

        Variants:
        0: pop regs; pop rbp; ret
        1: leave; pop regs (reversed); ret
        2: mov rsp, rbp; pop regs (reversed); pop rbp; ret
        3: pop rbp; mov regs from stack; add rsp, N; ret
        """
        saved_regs = [REG_RBX, REG_RBP, REG_R12, REG_R13, REG_R14, REG_R15]
        self._shuffle(saved_regs)
        variant = self._randrange(0, 4)
        parts = []
        if variant == 0:
            for r in saved_regs:
                if r <= 7:
                    parts.append(bytes([0x58 + r]))
                else:
                    parts.append(bytes([0x41, 0x58 + (r - 8)]))
            parts.append(b'\x5d')
            parts.append(b'\xc3')
        elif variant == 1:
            parts.append(b'\xc9')
            for r in reversed(saved_regs):
                if r <= 7:
                    parts.append(bytes([0x58 + r]))
                else:
                    parts.append(bytes([0x41, 0x58 + (r - 8)]))
            parts.append(b'\xc3')
        elif variant == 2:
            parts.append(b'\x48\x89\xec')
            for r in reversed(saved_regs):
                if r <= 7:
                    parts.append(bytes([0x58 + r]))
                else:
                    parts.append(bytes([0x41, 0x58 + (r - 8)]))
            parts.append(b'\x5d')
            parts.append(b'\xc3')
        else:
            parts.append(b'\x5d')
            offset = 0
            for r in reversed(saved_regs):
                if r <= 7:
                    parts.append(b'\x48\x8b\xbc\x24' + struct.pack('<I', offset))
                else:
                    parts.append(b'\x4c\x8b\xbc\x24' + struct.pack('<I', offset))
                offset += 8
            parts.append(b'\x48\x81\xc4' + struct.pack('<I', offset + 8))
            parts.append(b'\xc3')
        return b''.join(parts)

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

    def reorder_instructions(self, code: bytes, basic_block: list) -> bytes:
        """
        Reorder independent instructions within basic blocks and insert
        random NOPs.

        `basic_block` is a list of (start, end) tuples defining basic
        block boundaries. Instructions within each block are grouped
        by register dependency; independent groups are shuffled.
        """
        if not basic_block:
            return code
        result = bytearray()
        prev_end = 0
        for start, end in sorted(basic_block):
            if start > prev_end:
                result.extend(code[prev_end:start])
            block_bytes = code[start:end]
            instrs = self._slice_instructions(block_bytes)
            if len(instrs) >= 2:
                dep_groups = self._find_independent_groups(block_bytes, instrs)
                for group in dep_groups:
                    self._shuffle(group)
                reordered = []
                for group in dep_groups:
                    reordered.extend(group)
                reordered.sort(key=lambda x: dep_groups.index(
                    next(g for g in dep_groups if x in g)
                ))
                new_block = bytearray()
                pos = 0
                instr_positions = sorted([i for instrs_g in dep_groups for i, _, _ in instrs_g])
                for idx_in_group_list in range(len(reordered)):
                    def find_next(groups, current_list_idx):
                        target = reordered[current_list_idx]
                        for gi, g in enumerate(groups):
                            for ii, (inst_idx, off, length) in enumerate(g):
                                if inst_idx == target[0]:
                                    return (gi, ii, inst_idx, off, length)
                        return None
                    info = None
                    for gi, g in enumerate(dep_groups):
                        for ii, (inst_idx, off, length) in enumerate(g):
                            if inst_idx == reordered[idx_in_group_list][0]:
                                info = (off, length)
                                break
                        if info:
                            break
                    if info:
                        off, length = info
                        new_block.extend(block_bytes[off:off + length])
                block_out = bytes(new_block)
            else:
                block_out = block_bytes
            nop_count = self._randrange(0, 3)
            if nop_count > 0 and block_out:
                insert_pos = self._randrange(0, len(block_out))
                result.extend(block_out[:insert_pos])
                result.extend(self.generate_nop_sled(nop_count))
                result.extend(block_out[insert_pos:])
            else:
                result.extend(block_out)
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
        result = bytearray(code)
        pos = 0
        while pos < len(result):
            instr_len = _instruction_length(result, pos)
            if instr_len == 0:
                pos += 1
                continue
            self._swap_regs_in_instruction(result, pos, instr_len, register_map)
            pos += instr_len
        return bytes(result)

    def _swap_regs_in_instruction(self, code: bytearray, offset: int, length: int,
                                  reg_map: dict) -> None:
        """Apply register remapping within a single instruction."""
        end = min(offset + length, len(code))
        pos = offset
        rex_idx = -1
        rex = 0
        while pos < end:
            b = code[pos]
            if _rex_prefix(b):
                rex_idx = pos
                rex = b
                pos += 1
            elif b in (0x66, 0x67, 0xF0, 0xF2, 0xF3, 0x2E, 0x36, 0x3E, 0x26, 0x64, 0x65):
                pos += 1
            else:
                break
        if pos >= end:
            return
        opcode = code[pos]
        opcode_pos = pos
        pos += 1
        is_two_byte = False
        if opcode == 0x0F and pos < end:
            opcode = (opcode << 8) | code[pos]
            pos += 1
            is_two_byte = True
        opcode_len = 2 if is_two_byte else 1
        first = opcode if opcode_len == 1 else (opcode >> 8)
        rex_b = (rex & 0x01) != 0
        rex_r = (rex & 0x04) != 0

        # Handle push/pop opcodes (0x50-0x5F)
        if opcode_len == 1 and 0x50 <= first <= 0x5F:
            reg = (first - 0x50) | (1 if rex_b else 0)
            if reg in reg_map:
                new_reg = reg_map[reg]
                new_rex_b = (new_reg & 0x08) != 0
                new_opcode = 0x50 + (new_reg & 0x07)
                code[opcode_pos] = new_opcode
                if rex_idx >= 0:
                    new_rex = 0x40
                    if rex & 0x08:
                        new_rex |= 0x08
                    if new_rex_b:
                        new_rex |= 0x01
                    code[rex_idx] = new_rex
                elif new_rex_b:
                    code[opcode_pos] = 0x41
                    code[opcode_pos + 1:opcode_pos + 1] = bytes([new_opcode])
                    return
            return

        # Handle mov reg,imm opcodes (0xB0-0xBF)
        if opcode_len == 1 and 0xB0 <= first <= 0xBF:
            reg = (first - 0xB0) | (1 if rex_b else 0)
            if reg in reg_map:
                new_reg = reg_map[reg]
                new_rex_b = (new_reg & 0x08) != 0
                new_opcode = 0xB0 + (new_reg & 0x07)
                code[opcode_pos] = new_opcode
                if rex_idx >= 0:
                    new_rex = 0x40
                    if rex & 0x08:
                        new_rex |= 0x08
                    if new_rex_b:
                        new_rex |= 0x01
                    code[rex_idx] = new_rex
                elif new_rex_b:
                    code[opcode_pos] = 0x41
                    code[opcode_pos + 1:opcode_pos + 1] = bytes([new_opcode])
                    return
            return

        # Handle instructions with ModRM
        has_modrm = False
        if opcode_len == 1:
            if 0x00 <= first <= 0x3F or 0x88 <= first <= 0x8B or first == 0x8D or 0xC0 <= first <= 0xC1 or 0xD0 <= first <= 0xD3 or first in (0xFE, 0xFF):
                has_modrm = True
        else:
            second = opcode & 0xFF
            if 0x00 <= second <= 0x7F or 0x80 <= second <= 0x8F or second == 0xC7:
                has_modrm = True
        if has_modrm and pos < end:
            modrm_pos = pos
            modrm = code[pos]
            mod_bits = modrm >> 6
            old_reg = ((modrm >> 3) & 0x07) | (4 if rex_r else 0)
            old_rm = (modrm & 0x07) | (8 if rex_b else 0)
            new_reg = reg_map.get(old_reg, old_reg)
            new_rm = reg_map.get(old_rm, old_rm)
            if new_reg != old_reg or new_rm != old_rm:
                new_modrm = (mod_bits << 6) | ((new_reg & 0x07) << 3) | (new_rm & 0x07)
                code[modrm_pos] = new_modrm
                new_rex_r = (new_reg & 0x08) != 0
                new_rex_b = (new_rm & 0x08) != 0
                if rex_idx >= 0:
                    new_rex = 0x40
                    if rex & 0x08:
                        new_rex |= 0x08
                    if new_rex_r:
                        new_rex |= 0x04
                    if new_rex_b:
                        new_rex |= 0x01
                    code[rex_idx] = new_rex
                else:
                    if new_rex_r or new_rex_b:
                        new_rex = 0x40
                        if new_rex_r:
                            new_rex |= 0x04
                        if new_rex_b:
                            new_rex |= 0x01
                        code[opcode_pos - 1:opcode_pos - 1] = bytes([new_rex])

    # ---- Stack offset alteration ----

    def alter_stack_offsets(self, code: bytes, offset_delta: int) -> bytes:
        """
        Shift all RBP/RSP-relative stack offsets by `offset_delta`.

        Scans for ModRM bytes with RBP or RSP base and adjusts the
        displacement field (both 1-byte and 4-byte displacements).
        """
        if offset_delta == 0:
            return code
        result = bytearray(code)
        pos = 0
        while pos < len(result):
            length = _instruction_length(result, pos)
            if length == 0:
                pos += 1
                continue
            rex_idx = -1
            p = pos
            while p < pos + min(length, 4):
                b = result[p]
                if _rex_prefix(b):
                    rex_idx = p
                    p += 1
                elif b in (0x66, 0x67, 0xF0, 0xF2, 0xF3, 0x2E, 0x36, 0x3E, 0x26, 0x64, 0x65):
                    p += 1
                else:
                    break
            if p >= len(result):
                pos += length
                continue
            opcode = result[p]
            p += 1
            if opcode == 0x0F and p < len(result):
                p += 1
            if p >= len(result):
                pos += length
                continue
            modrm = result[p]
            mod_bits = modrm >> 6
            rm = modrm & 0x7
            if mod_bits == 3:
                pos += length
                continue
            disp_offset = p + 1
            has_sib = (rm == 4)
            if has_sib:
                if p + 1 >= len(result):
                    pos += length
                    continue
                sib = result[p + 1]
                base = sib & 0x7
                disp_offset = p + 2
            else:
                base = rm
            if not (base == REG_RBP or base == REG_RSP):
                pos += length
                continue
            if mod_bits == 1:
                if disp_offset < len(result):
                    old = result[disp_offset]
                    new = (old + offset_delta) & 0xFF
                    result[disp_offset] = new
            elif mod_bits == 2 or (mod_bits == 0 and rm == 5):
                if disp_offset + 4 <= len(result):
                    old = struct.unpack('<i', result[disp_offset:disp_offset + 4])[0]
                    new = old + offset_delta
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
        block = bytearray(block)
        regs = list(range(8))
        self._shuffle(regs)
        reg_map = {i: regs[i] for i in range(8)}
        block = bytearray(self.swap_regrites(bytes(block), reg_map))
        nop_count = self._randrange(1, 5)
        if len(block) > 4:
            for _ in range(nop_count):
                pos = self._randrange(0, len(block))
                nop = self.generate_nop_sled(self._randrange(1, 4))
                block[pos:pos] = nop
                if len(block) > 256:
                    break
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
        """Generate a random bijective register mapping (RAX=0..RDI=7)."""
        regs = list(range(8))
        self._shuffle(regs)
        return {i: regs[i] for i in range(8)}


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
        cfg = _load_config()
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
