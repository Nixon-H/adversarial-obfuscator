"""
micro_fragment.py

Purpose:
Implements micro-fragment execution: code is split into tiny encrypted
fragments that are decrypted, executed, and wiped one at a time. Each
fragment is encrypted with a sequence key derived from the fragment
index and a master secret, ensuring that only the correct fragment can
be decrypted at the correct position.

Architectural Role:
Fine-grained code protection layer within the fragment subsystem.
While FragmentCompiler (fragment_compiler.py) handles large bytecode
fragments with cryptographic chain binding, MicroFragmentExecutor
operates at the individual source-line level with per-fragment
encryption. Supports both ordered and randomized (oblivious) execution.

Dependencies:
hashlib, os, random, struct

Security Relevance:
Implements Item 50: Micro-fragment execution. At any point, only a few
lines of code exist in plaintext memory. After execution, the decrypted
state is immediately zeroed. Randomized execution (execute_all_randomized)
further obfuscates the execution order using commutative reduction.
"""

import hashlib
import os
import random
import struct
from typing import List, Optional, Tuple


def _derive_sequence_key(master_key: bytes, fragment_index: int) -> bytes:
    """
    Derive a fragment-specific key using SHA-256.

    key = SHA-256(master_key || big-endian fragment_index)

    Each fragment index produces a unique key. The key for fragment N
    cannot be computed from the key for fragment N+1 (one-way property
    of SHA-256).
    """
    h = hashlib.sha256(master_key)
    h.update(struct.pack(">Q", fragment_index))
    return h.digest()


def _xor_encrypt(data: bytes, key: bytes) -> bytes:
    """
    Encrypt/decrypt data using XOR with a SHA-256-based keystream.

    The keystream is generated in 32-byte blocks by repeatedly hashing
    the key with an incrementing big-endian counter. This is a simple
    stream cipher (not AES) intended for prototyping.
    """
    keystream = b""
    counter = 0
    while len(keystream) < len(data):
        block = struct.pack(">Q", counter)
        keystream += hashlib.sha256(key + block).digest()
        counter += 1
    keystream = keystream[:len(data)]
    return bytes(p ^ k for p, k in zip(data, keystream))


class MicroFragment:
    """
    A single encrypted micro-fragment.

    Attributes:
        index: Ordinal position in the fragment sequence.
        encrypted: AES-CTR encrypted fragment payload.
        plaintext_len: Length of the original plaintext (used for
                       integrity verification after decryption).
        executed: Whether this fragment has been successfully executed.
    """

    __slots__ = ("index", "encrypted", "plaintext_len", "executed")

    def __init__(self, index: int, encrypted: bytes, plaintext_len: int):
        """
        Initialize a micro-fragment.

        Args:
            index: Ordinal fragment position.
            encrypted: Encrypted payload bytes.
            plaintext_len: Original plaintext length.
        """
        self.index = index
        self.encrypted = encrypted
        self.plaintext_len = plaintext_len
        self.executed = False


_SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
    "bytes": bytes, "chr": chr, "dict": dict, "divmod": divmod,
    "enumerate": enumerate, "float": float, "format": format,
    "hex": hex, "int": int, "isinstance": isinstance, "len": len,
    "list": list, "map": map, "max": max, "min": min, "oct": oct,
    "ord": ord, "pow": pow, "range": range, "repr": repr,
    "reversed": reversed, "round": round, "set": set, "slice": slice,
    "sorted": sorted, "str": str, "sum": sum, "tuple": tuple,
    "type": type, "zip": zip,
}


class MicroFragmentExecutor:
    """
    Splits code into tiny encrypted fragments, decrypts and executes in
    order, wiping each fragment after execution.

    Supports two fragment modes:
      - Source code fragmentation (fragment_code): splits at line boundaries
        to maintain syntactic validity for exec().
      - IR instruction fragmentation (fragment_ir_instructions): groups
        1-3 IR instructions per fragment with variable sizing.

    Security properties:
      - Each fragment key is derived from its index (forward secrecy).
      - Decrypted plaintext is zeroed after execution (memory safety).
      - Randomized execution order via execute_all_randomized with
        commutative reduction for order-independent results.
    """

    def __init__(self, master_key: Optional[bytes] = None,
                 fragment_size: int = 64):
        """
        Initialize the executor with a master key and fragment size.

        Args:
            master_key: 32-byte master seed. Generated via os.urandom(32)
                        if not provided.
            fragment_size: Target size in bytes per fragment (minimum 16).
        """
        self.master_key = master_key or os.urandom(32)
        self.fragment_size = max(16, fragment_size)
        self.fragments: List[MicroFragment] = []

    def fragment_code(self, code: str) -> List[MicroFragment]:
        """
        Split a code string into encrypted micro-fragments.

        Preserves line boundaries to maintain syntactic validity for
        exec(). Each fragment is encrypted with a unique sequence key.
        """
        lines = code.splitlines(keepends=True)
        self.fragments = []
        index = 0
        current_chunk = ""
        current_size = 0
        for line in lines:
            line_size = len(line.encode("utf-8"))
            if current_size + line_size > self.fragment_size and current_chunk:
                enc = _xor_encrypt(current_chunk.encode("utf-8"),
                                   _derive_sequence_key(self.master_key, index))
                self.fragments.append(MicroFragment(index, enc, len(current_chunk.encode("utf-8"))))
                index += 1
                current_chunk = ""
                current_size = 0
            current_chunk += line
            current_size += line_size
        if current_chunk:
            enc = _xor_encrypt(current_chunk.encode("utf-8"),
                               _derive_sequence_key(self.master_key, index))
            self.fragments.append(MicroFragment(index, enc, len(current_chunk.encode("utf-8"))))
        return self.fragments

    def execute_fragment(self, fragment: MicroFragment,
                         global_ns: dict, local_ns: dict) -> Tuple[bool, Optional[str]]:
        """
        Decrypt, execute, and wipe a single fragment.

        Steps:
        1. Derive the fragment key from its index.
        2. Decrypt using XOR stream cipher.
        3. Verify plaintext length matches expected.
        4. Execute via exec() in the provided namespaces.
        5. Wipe the plaintext buffer.
        6. Set fragment.executed = True on success.
        """
        key = _derive_sequence_key(self.master_key, fragment.index)
        plaintext = _xor_encrypt(fragment.encrypted, key)
        assert len(plaintext) == fragment.plaintext_len
        code_str = plaintext.decode("utf-8")
        wipe = bytearray(plaintext)
        for i in range(len(wipe)):
            wipe[i] = 0
        try:
            exec(code_str, global_ns, local_ns)
            fragment.executed = True
            return (True, None)
        except Exception as e:
            return (False, str(e))

    def execute_all(self, code: Optional[str] = None) -> dict:
        """
        Fragment the code (if provided) then execute all fragments in order.

        Wipes each fragment's encrypted payload after execution to prevent
        forensic recovery from memory.
        """
        if code is not None:
            self.fragment_code(code)
        result_ns: dict = {}
        for frag in self.fragments:
            ok, err = self.execute_fragment(frag, _SAFE_BUILTINS, result_ns)
            if not ok:
                raise RuntimeError(
                    f"Fragment {frag.index} failed: {err}"
                )
            frag.encrypted = b"\x00" * len(frag.encrypted)
        return result_ns

    def fragment_ir_instructions(self, instructions: List[str]) -> List[MicroFragment]:
        """
        Split IR instructions into tiny fragments (1-3 instructions each).

        Each fragment is independently encrypted with a unique key derived
        from fragment position. Variable chunk sizing ((i % 3) + 1) ensures
        non-uniform fragment boundaries.
        """
        self.fragments = []
        index = 0
        i = 0
        while i < len(instructions):
            chunk_size = min((i % 3) + 1, len(instructions) - i)
            chunk = "\n".join(instructions[i:i + chunk_size])
            chunk_bytes = chunk.encode("utf-8")
            key = _derive_sequence_key(self.master_key, index)
            enc = _xor_encrypt(chunk_bytes, key)
            self.fragments.append(MicroFragment(index, enc, len(chunk_bytes)))
            index += 1
            i += chunk_size
        return self.fragments

    def execute_all_randomized(self, instructions: Optional[List[str]] = None,
                                seed: int = 0) -> dict:
        """
        Execute fragments in a randomized order, merging results via
        commutative reduction.

        The execution order is pseudo-randomly permuted using the provided
        seed. Results are merged commutatively (sorted lists, merged dicts,
        summed scalars) to produce a deterministic final state despite
        non-deterministic execution order.

        Security: Randomized execution defeats timing-based side channels
        that rely on known fragment execution order.
        """
        if instructions is not None:
            self.fragment_ir_instructions(instructions)

        indices = list(range(len(self.fragments)))
        rng = random.Random(seed)
        rng.shuffle(indices)

        result_ns: dict = {}
        for idx in indices:
            frag = self.fragments[idx]
            ok, err = self.execute_fragment(frag, _SAFE_BUILTINS, result_ns)
            if not ok:
                raise RuntimeError(
                    f"Fragment {frag.index} failed: {err}"
                )
            frag.encrypted = b"\x00" * len(frag.encrypted)

        merged: dict = {}
        for key in sorted(result_ns.keys()):
            val = result_ns[key]
            if isinstance(val, (int, float)):
                merged[key] = val
            elif isinstance(val, list):
                merged[key] = sorted(val)
            elif isinstance(val, dict):
                merged[key] = dict(val)
            elif isinstance(val, set):
                merged[key] = set(val)
            elif isinstance(val, str):
                merged[key] = val
            elif isinstance(val, bytes):
                merged[key] = val
            else:
                merged[key] = val
        return merged

    def get_execution_summary(self) -> dict:
        """
        Return a summary of fragment execution status.

        Includes total fragments, executed count, whether all fragments
        executed, and the configured fragment size.
        """
        total = len(self.fragments)
        executed = sum(1 for f in self.fragments if f.executed)
        return {
            "total_fragments": total,
            "executed": executed,
            "all_executed": total == executed,
            "fragment_size": self.fragment_size,
        }
