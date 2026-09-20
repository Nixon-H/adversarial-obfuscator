"""
proof_soundness — Proof Soundness Harness (F174)

Purpose:
    Tests the soundness of formal proof modules by generating semantically
    mutated variants of source code and verifying that proof systems correctly
    reject incorrect transformations while accepting correct ones.

Architectural Role:
    Validation layer for all proof modules (semantic preservation, mutation
    safety, VM correctness, fragment safety, watermark survivability, JIT
    reassembly). Runs as a CI step to detect proof regressions.

Security Relevance:
    A proof system that fails to detect incorrect transformations provides
    false assurance. The soundness harness is the safety net for all formal
    verification in the pipeline.
"""

"""
proof_soundness/__init__

Purpose:
Soundness testing harness for formal proof modules. Generates known-incorrect
transformations and checks that each prover correctly rejects them. A prover
that accepts a bad transformation is unsound.

Security Relevance:
A prover that certifies incorrect transformations as equivalent is worse than
no prover — it provides false confidence. The soundness harness is the primary
defense against prover bugs.

Dependencies:
- scripts.proof_soundness.harness  (test runner + report)
- scripts.proof_soundness.mutator  (known-bad mutation generation)
- scripts.proof_soundness.oracle   (runtime equivalence oracle)
"""
from .harness import ProofSoundnessHarness, SoundnessTest, SoundnessReport
from .harness import generate_soundness_tests, run_soundness_harness
from .mutator import ProofMutationEngine
from .oracle import TransformationOracle

__all__ = [
    "ProofSoundnessHarness",
    "SoundnessTest",
    "SoundnessReport",
    "ProofMutationEngine",
    "TransformationOracle",
    "generate_soundness_tests",
    "run_soundness_harness",
]
