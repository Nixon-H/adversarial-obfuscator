"""
phases/__init__.py

Purpose:
Phase registry — imports every pipeline stage function from its dedicated
module and re-exports them under a flat namespace. build.py imports the
entire pipeline as:
    from scripts.phases import phase_obfuscate, phase_generate_config, ...

Architectural Role:
Central wiring point. Each phase is developed in isolation in its own file;
this module assembles them into an ordered, importable catalog. Adding a
new phase requires (1) creating the module, (2) adding one import line here.

Execution Context:
Imported at module load time by build.py. All phase functions share a
convention-similar signature pattern that takes an opts namespace and/or
file paths.

Dependencies:
- All phase modules under scripts/phases/phase_*.py
"""

# ---- Stage 1–2: Obfuscation & Config ----
from .phase01_obfuscate import phase_obfuscate
from .phase02_config import phase_generate_config, load_advanced_protection_config

# ---- Stage 3: Compilation Pipeline (Relay, Cross, IR, LLVM) ----
from .phase03_compile import phase_compile_relay, phase_cross_compile, phase_ir_compile, phase_llvm_codegen

# ---- Stage 4: Encryption & Entropy ----
from .phase04_encrypt import phase_encrypt_binary, phase_entropy_flatten

# ---- Stage 5: Payload Header & Runtime Manifest ----
from .phase05_payload_h import phase_generate_payload_h, phase_embed_crypto_binding, phase_runtime_manifest

# ---- Stage 6: Packaging ----
from .phase06_package import phase_package, phase_optional_extras

# ---- Stage 7: Phase-2 Advanced Protection (Classification, VM, JIT, Watermark) ----
from .phase07_phase2 import (
    phase_classify,
    phase_variant_pool,
    phase_provenance_removal,
    phase_dataflow_obfuscation,
    phase_watermark_embedding,
    phase_vm_compile,
    phase_jit_generate,
    phase_adaptive_classifier_loop,
)

# ---- Stage 8: ROP Compilation ----
from .phase08_rop import phase_rop_compile

# ---- Stage 9: Adversarial Injection ----
from .phase09_adversarial import phase_adversarial_loop, phase_adversarial_injection

# ---- Stage 10: Provenance Poisoning ----
from .phase10_provenance import phase_provenance_poison

# ---- Stage 11–17: Runtime Evolution Research (Items 80–89) ----
from .phase11_cfg_mutation import phase_cfg_mutation
from .phase12_history_bound import phase_execution_history_binding
from .phase13_ssa_mutation import phase_ssa_mutation
from .phase14_per_exec_recompile import phase_per_exec_recompile
from .phase15_self_healing import phase_self_healing
from .phase16_code_genome import phase_code_genome
from .phase17_struct_random import phase_struct_randomization

# ---- Stage 18–28: Hardware Research Integration (Items 120–129) ----
from .phase18_hpc import phase_hpc
from .phase19_hpc_key import phase_hpc_key
from .phase25_tee import phase_tee
from .phase26_sgx import phase_sgx
from .phase27_cpu_port import phase_cpu_port
from .phase28_gpu_hybrid import phase_gpu_hybrid

# ---- Miscellaneous Pipeline Features (Class Dispatch, Keys, ISA) ----
from .phase_class_dispatch import phase_class_dispatch
from .phase_rolling_keys import phase_rolling_keys
from .phase_state_isa import phase_state_isa

# ---- Items 50, 58, 59, 69, 91, 101: Micro-Fragment, Poly-Engine, Dispersal, Proofs ----
from .phase30_micro_fragment import phase_micro_fragment
from .phase31_poly_engine import phase_poly_engine
from .phase32_temporal_keys import phase_temporal_keys
from .phase33_payload_dispersal import phase_payload_dispersal

# ---- Research Features: FHE-VM, Kernel Assist, IO, ZK State ----
from .phase_fhe_vm import phase_fhe_vm
from .phase_kernel_assist import phase_kernel_assist
from .phase_io_research import phase_io_research
from .phase_zk_state import phase_zk_state

# ---- Proof & Verification Features (153, 174) ----
from .phase_proof_coverage import phase_proof_coverage
from .phase_leakage import phase_leakage

# ---- Conflict Detection, Coverage, Synthesis, Artifacts ----
from .phase_conflicts import phase_check_conflicts
from .phase_coverage import phase_coverage
from .phase_redteam import phase_redteam
from .phase_exposure import phase_exposure
from .phase_artifacts import phase_artifacts
from .phase_synthesis import phase_synthesis
from .phase_security_gates import phase_security_gates
from .phase_knowledge_graph import phase_knowledge_graph
from .phase_attack_replay import phase_attack_replay

# ---- Feature Retirement Framework ----
from .phase_retirement import phase_retirement

# ---- Proof Soundness & Reproducibility ----
from .phase_proof_soundness import phase_proof_soundness
from .phase_reproducibility import phase_reproducibility
from .phase_reachability import phase_reachability

# ---- Adversarial Benchmark & Assumptions ----
from .phase_adversarial_bench import phase_adversarial_bench
from .phase_assumptions import phase_assumptions

# ---- Evaluation & Reality Features (167–170) ----
from .phase_reality import phase_reality
from .phase_false_confidence import phase_false_confidence
from .phase_evidence import phase_evidence
from .phase_self_audit import phase_self_audit
from .phase_claim_auditor import phase_claim_audit
from .phase_security_debt import phase_security_debt
from .phase_verification_bundle import phase_verification_bundle
from .phase_confidence import phase_confidence

# ---- Trust, Evidence, Dependency, Attack Surface ----
from .phase_trust_boundary import phase_trust_boundary
from .phase_evidence_completeness import phase_evidence_completeness
from .phase_dependency_graph import phase_dependency_graph
from .phase_attack_surface import phase_attack_surface
from .phase_invariant_engine import phase_invariant_engine
from .phase_independent_audit import phase_independent_audit
from .phase_manipulation_detector import phase_manipulation_detector
from .phase_benchmark_integrity import phase_benchmark_integrity
from .phase_verification_diversity import phase_verification_diversity
from .phase_audit_drift import phase_audit_drift

# ---- Batch-2: PyTOC native extension path ----
from .phase_pytoc import phase_pytoc, cythonize_obfuscated

# ---- Runtime Integrity Features (191–199) ----
from .phase_silent_fallback import phase_silent_fallback
from .phase_runtime_truth import phase_runtime_truth
from .phase_feature_effectiveness import phase_feature_effectiveness
from .phase_protection_roi import phase_protection_roi
from .phase_longitudinal_tracking import phase_longitudinal_tracking
from .phase_attack_corpus import phase_attack_corpus
from .phase_release_confidence import phase_release_confidence
from .phase_threat_coverage import phase_threat_coverage
from .phase_knowledge_base import phase_knowledge_base
from .phase_self_critique import phase_self_critique

# Re-exported names: listed explicitly so the intent is
# unambiguous and the unused-import check does not flag them.
__all__ = [
    "cythonize_obfuscated",
    "load_advanced_protection_config",
    "phase_adaptive_classifier_loop",
    "phase_adversarial_bench",
    "phase_adversarial_injection",
    "phase_adversarial_loop",
    "phase_artifacts",
    "phase_assumptions",
    "phase_attack_corpus",
    "phase_attack_replay",
    "phase_attack_surface",
    "phase_audit_drift",
    "phase_benchmark_integrity",
    "phase_branch_entangle",
    "phase_cache_bound",
    "phase_cfg_mutation",
    "phase_check_conflicts",
    "phase_claim_audit",
    "phase_class_dispatch",
    "phase_classify",
    "phase_code_genome",
    "phase_compile_relay",
    "phase_confidence",
    "phase_coverage",
    "phase_cpu_port",
    "phase_cross_compile",
    "phase_dataflow_obfuscation",
    "phase_dependency_graph",
    "phase_embed_crypto_binding",
    "phase_encrypt_binary",
    "phase_entropy_flatten",
    "phase_evidence",
    "phase_evidence_completeness",
    "phase_execution_history_binding",
    "phase_exposure",
    "phase_false_confidence",
    "phase_feature_effectiveness",
    "phase_fhe_vm",
    "phase_generate_config",
    "phase_generate_payload_h",
    "phase_gpu_hybrid",
    "phase_hpc",
    "phase_hpc_detect",
    "phase_hpc_key",
    "phase_hw_entropy",
    "phase_independent_audit",
    "phase_invariant_engine",
    "phase_io_research",
    "phase_ir_compile",
    "phase_jit_generate",
    "phase_kernel_assist",
    "phase_knowledge_base",
    "phase_knowledge_graph",
    "phase_leakage",
    "phase_llvm_codegen",
    "phase_longitudinal_tracking",
    "phase_manipulation_detector",
    "phase_micro_fragment",
    "phase_multicore_entangle",
    "phase_obfuscate",
    "phase_optional_extras",
    "phase_package",
    "phase_payload_dispersal",
    "phase_per_exec_recompile",
    "phase_poly_engine",
    "phase_proof_coverage",
    "phase_proof_soundness",
    "phase_protection_roi",
    "phase_provenance_poison",
    "phase_provenance_removal",
    "phase_pytoc",
    "phase_reachability",
    "phase_reality",
    "phase_redteam",
    "phase_release_confidence",
    "phase_reproducibility",
    "phase_retirement",
    "phase_rolling_keys",
    "phase_rop_compile",
    "phase_runtime_manifest",
    "phase_runtime_truth",
    "phase_security_debt",
    "phase_security_gates",
    "phase_self_audit",
    "phase_self_critique",
    "phase_self_healing",
    "phase_sgx",
    "phase_silent_fallback",
    "phase_ssa_mutation",
    "phase_state_isa",
    "phase_struct_randomization",
    "phase_synthesis",
    "phase_tee",
    "phase_temporal_keys",
    "phase_threat_coverage",
    "phase_trust_boundary",
    "phase_variant_pool",
    "phase_verification_bundle",
    "phase_verification_diversity",
    "phase_vm_compile",
    "phase_watermark_embedding",
    "phase_zk_state",
]
