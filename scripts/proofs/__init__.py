"""
proofs/__init__

Purpose:
Central export hub for all formal proof modules in the Nixon pipeline. Each
prover exposes a Z3 SMT-based equivalence proof between pre- and post-
transformation representations. All proofs are serializable into certificate
chains for independent re-verification.

Security Relevance:
This is the single point of integration between transformation passes and the
proof infrastructure. Every prover listed here must be exercised in CI. An
unexported prover means an untrusted transformation pass with no formal
guarantee.

Dependencies:
- scripts.proofs.vm_correctness     (VM instruction semantics)
- scripts.proofs.fragment_safety    (fragment chain isolation)
- scripts.proofs.watermark_survivability (watermark integrity)
- scripts.proofs.mutation_safety    (mutation equivalence)
- scripts.proofs.jit_reassembly     (JIT fragment correctness)
- scripts.proofs.semantic_preservation   (Python AST equivalence)
"""

from .vm_correctness import VMCorrectnessProver, VmProof
from .fragment_safety import FragmentSafetyProver, FragmentProof
from .watermark_survivability import WatermarkSurvivabilityProver, WatermarkProof
from .mutation_safety import MutationSafetyProver, MutationProof
from .jit_reassembly import JITReassemblyProver, JITProof
from .semantic_preservation import SemanticPreservationProver, PreservationProof

__all__ = [
    "VMCorrectnessProver", "VmProof",
    "FragmentSafetyProver", "FragmentProof",
    "WatermarkSurvivabilityProver", "WatermarkProof",
    "MutationSafetyProver", "MutationProof",
    "JITReassemblyProver", "JITProof",
    "SemanticPreservationProver", "PreservationProof",
]
