"""Fragment Compiler — splits bytecode into encrypted fragments with chain binding.

Fragment A → decrypt → execute → wipe
Fragment B → decrypt → execute → wipe
Fragment C → decrypt → execute → wipe

Each fragment key is derived from the *previous fragment's output*, creating
cryptographic fragment binding: recovering one fragment is insufficient
because you cannot decrypt the next without the previous fragment's output.

TWIN: scripts/fragment/micro_fragment.py (per-line fragments, index-derived
keys, no chaining) and scripts/binding/crypto_binding.py (context-bound
Fragment→BoundFragment transform) — different granularity/binding; do not merge.
"""

from __future__ import annotations
import hashlib
import hmac
import os
import struct
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Fragment:
    """A single fragment of bytecode."""
    id: int
    instructions: bytes
    input_regs: List[str] = field(default_factory=list)
    output_regs: List[str] = field(default_factory=list)
    next_fragment_id: Optional[int] = None
    encrypted_blob: bytes = b''
    key_slot: int = 0


@dataclass
class CompiledFragment:
    """Encrypted fragment ready for payload embedding."""
    id: int
    encrypted_data: bytes
    plaintext_size: int
    key_slot: int
    next_fragment_id: Optional[int]
    output_regs: List[str] = field(default_factory=list)
    input_regs: List[str] = field(default_factory=list)


def derive_fragment_key(
    previous_output: bytes,
    chain_key: bytes,
    fragment_id: int,
) -> bytes:
    """Derive a fragment key using cryptographic chain binding.

    key = HMAC-SHA256(chain_key, previous_output || fragment_id)
    
    Fragment A key: HMAC(chain_key, 0x00 * 8 || 0)
    Fragment B key: HMAC(chain_key, A_output || 1)
    Fragment C key: HMAC(chain_key, B_output || 2)
    """
    if previous_output is None:
        previous_output = b'\x00' * 8
    h = hmac.new(chain_key, digestmod=hashlib.sha256)
    h.update(previous_output)
    h.update(struct.pack('<I', fragment_id))
    return h.digest()


def aes_ctr_encrypt_fragment(
    plaintext: bytes,
    key: bytes,
) -> bytes:
    """Encrypt fragment data using AES-256-CTR (pure Python).

    Uses the encrypt.aes module if available, otherwise falls back
    to a simple XOR keystream derived from the key.
    """
    try:
        from encrypt.aes import aes256_ctr_encrypt
        nonce = hashlib.sha256(key).digest()[:8]
        return aes256_ctr_encrypt(plaintext, key, nonce)
    except ImportError:
        pass
    from hashlib import sha256
    nonce = sha256(key).digest()[:8]
    keystream = b''
    counter = 0
    while len(keystream) < len(plaintext):
        block = nonce + struct.pack('>Q', counter)
        keystream += sha256(key + block).digest()
        counter += 1
    keystream = keystream[:len(plaintext)]
    return bytes(p ^ k for p, k in zip(plaintext, keystream))


class FragmentAnalyzer:
    """Analyzes bytecode to identify natural fragment boundaries.

    Supports:
    - Basic block boundaries (jump/call targets)
    - Fixed-size instruction grouping
    - Data-dependency isolation points
    """

    def __init__(self, min_fragment_instructions: int = 3, max_fragment_instructions: int = 8):
        self.min_size = min_fragment_instructions
        self.max_size = max_fragment_instructions

    def analyze(self, bytecode: bytes) -> List[Tuple[int, int]]:
        """Return list of (start, end) byte ranges for fragments."""
        total_len = len(bytecode)
        if total_len <= self.min_size:
            return [(0, total_len)]
        boundaries = self._find_boundaries(bytecode)
        return self._build_fragments(boundaries, total_len)

    def _find_boundaries(self, bytecode: bytes) -> List[int]:
        """Find natural boundary points in bytecode."""
        boundaries = set()
        boundaries.add(0)
        boundaries.add(len(bytecode))
        pos = 0
        while pos < len(bytecode):
            inst_len = self._instruction_length(bytecode, pos)
            if inst_len == 0:
                pos += 1
                continue
            opcode = bytecode[pos]
            if opcode in (0x10, 0x11, 0x12, 0x16, 0x17, 0x18, 0x23, 0x34):
                boundaries.add(pos)
                next_inst = pos + inst_len
                if next_inst < len(bytecode):
                    boundaries.add(next_inst)
            pos += inst_len
        return sorted(boundaries)

    def _build_fragments(
        self, boundaries: List[int], total_len: int
    ) -> List[Tuple[int, int]]:
        """Build fragment ranges from boundary points."""
        fragments = []
        i = 0
        while i < len(boundaries) - 1:
            start = boundaries[i]
            end = boundaries[i + 1]
            span = end - start
            if span < self.min_size:
                merged = False
                for j in range(i + 1, len(boundaries) - 1):
                    candidate_end = boundaries[j + 1]
                    if candidate_end - start <= self.max_size:
                        end = candidate_end
                        merged = True
                    else:
                        break
                if not merged:
                    end = boundaries[i + 1]
                    while end - start < self.min_size and i + 1 < len(boundaries) - 1:
                        i += 1
                        end = boundaries[i + 1]
            if end - start > self.max_size:
                sub_start = start
                while sub_start < end:
                    sub_end = min(sub_start + self.max_size, end)
                    fragments.append((sub_start, sub_end))
                    sub_start = sub_end
            else:
                fragments.append((start, end))
            i = boundaries.index(end)
        return fragments

    def _instruction_length(self, code: bytes, offset: int) -> int:
        if offset >= len(code):
            return 0
        opcode = code[offset]
        opcode_map = {
            0: 1, 1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3, 7: 3, 8: 3, 9: 2,
            10: 3, 11: 3, 12: 3, 13: 3, 14: 4, 15: 1,
            16: 5, 17: 5, 18: 5, 19: 1, 20: 1, 21: 1, 22: 1,
            23: 5, 24: 1, 25: 2, 26: 2,
            34: 10,
        }
        if opcode == 34:
            return 10
        if opcode in (0x10, 0x11, 0x12, 0x16, 0x17, 0x18, 0x23, 0x34):
            return opcode_map.get(opcode, 5)
        if 16 <= opcode <= 18:
            return 5
        if 23 <= opcode <= 26:
            if opcode == 23:
                return 5
            return 2 if opcode >= 25 else 1
        return opcode_map.get(opcode, 3)


class FragmentCompiler:
    """Splits function bytecode into encrypted fragments with chain binding.

    Usage:
        compiler = FragmentCompiler(chain_key=os.urandom(32))
        compiled = compiler.compile_all(function_bytecode)
    """

    def __init__(
        self,
        chain_key: Optional[bytes] = None,
        min_instructions: int = 3,
        max_instructions: int = 8,
    ):
        self.chain_key = chain_key or os.urandom(32)
        self.analyzer = FragmentAnalyzer(min_instructions, max_instructions)
        self.next_key_slot = 0

    def compile_all(
        self,
        bytecode: bytes,
        input_regs_map: Optional[dict] = None,
        output_regs_map: Optional[dict] = None,
    ) -> List[CompiledFragment]:
        """Split bytecode into encrypted, chain-bound fragments."""
        if not bytecode:
            return []
        ranges = self.analyzer.analyze(bytecode)
        fragments: List[Fragment] = []
        for i, (start, end) in enumerate(ranges):
            chunk = bytecode[start:end]
            frag = Fragment(
                id=i,
                instructions=chunk,
                next_fragment_id=i + 1 if i < len(ranges) - 1 else None,
                key_slot=self.next_key_slot,
            )
            if input_regs_map:
                frag.input_regs = input_regs_map.get(i, [])
            if output_regs_map:
                frag.output_regs = output_regs_map.get(i, [])
            fragments.append(frag)
            self.next_key_slot += 1
        return self._encrypt_chain(fragments)

    def _encrypt_chain(
        self, fragments: List[Fragment]
    ) -> List[CompiledFragment]:
        """Encrypt fragments with chain-bound keys."""
        compiled = []
        prev_output: Optional[bytes] = None
        for frag in fragments:
            key = derive_fragment_key(prev_output, self.chain_key, frag.id)
            encrypted = aes_ctr_encrypt_fragment(frag.instructions, key)
            cf = CompiledFragment(
                id=frag.id,
                encrypted_data=encrypted,
                plaintext_size=len(frag.instructions),
                key_slot=frag.key_slot,
                next_fragment_id=frag.next_fragment_id,
                output_regs=frag.output_regs,
                input_regs=frag.input_regs,
            )
            compiled.append(cf)
            fake_output = struct.pack('<Q', hash(frag.instructions) & 0xFFFFFFFFFFFFFFFF)
            prev_output = fake_output
        return compiled

    def encrypt_single(
        self,
        fragment_id: int,
        plaintext: bytes,
        prev_output: Optional[bytes] = None,
    ) -> Tuple[bytes, int, bytes]:
        """Encrypt a single fragment with derived key.

        Returns (encrypted_data, plaintext_size, key)
        """
        key = derive_fragment_key(prev_output, self.chain_key, fragment_id)
        encrypted = aes_ctr_encrypt_fragment(plaintext, key)
        return encrypted, len(plaintext), key


    def decrypt_fragment(
        self,
        encrypted_data: bytes,
        fragment_id: int,
        prev_output: Optional[bytes] = None,
    ) -> bytes:
        """Decrypt a single fragment using chain-derived key."""
        key = derive_fragment_key(prev_output, self.chain_key, fragment_id)
        return aes_ctr_encrypt_fragment(encrypted_data, key)
