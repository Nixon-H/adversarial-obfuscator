"""Micro-JIT Fragment Reassembly — Ephemeral Execution Reconstruction.

Splits functions into encrypted fragments that are decrypted, executed,
and wiped one at a time. At any point, only a few instructions exist
in plaintext in memory.

Exports:
    FragmentCompiler: splits and encrypts function bytecode into fragments
    FragmentAnalyzer: identifies natural fragment boundaries
    derive_fragment_key: cryptographic chain key derivation
"""

from .fragment_compiler import (
    Fragment,
    CompiledFragment,
    FragmentAnalyzer,
    FragmentCompiler,
    derive_fragment_key,
    aes_ctr_encrypt_fragment,
)

__all__ = [
    "Fragment",
    "CompiledFragment",
    "FragmentAnalyzer",
    "FragmentCompiler",
    "derive_fragment_key",
    "aes_ctr_encrypt_fragment",
]
