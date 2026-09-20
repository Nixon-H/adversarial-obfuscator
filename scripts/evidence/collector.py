"""
evidence/collector.py — Automated evidence collection from pipeline artefacts (F168)

Purpose:
    Walks the repository structure (phases, tests, benchmarks, native code,
    runtime, metrics) and registers claims + evidence in an EvidenceLedger.

Architectural Role:
    Collector layer: called by the build pipeline to populate the ledger
    automatically from the project's own source tree.

Security Relevance:
    Ensures that evidence gathering is systematic and repeatable, not reliant
    on manual claim-entry registration.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .ledger import EvidenceLedger, _compute_file_hash, _now_iso


class EvidenceCollector:
    """Walk repository directories and register claims + evidence in the ledger.

    Scans phases/, tests/, native/, runtime/, and metrics/ directories,
    mapping each discovered file to a predefined claim via internal tables.
    """
    def __init__(self, build_dir: str) -> None:
        self.build_dir = build_dir
        self.ledger = EvidenceLedger()

    def collect_from_phase(self, phase_name: str, args: Any) -> None:
        """Register a claim for the given pipeline phase and link its source file as evidence.

        Uses an internal mapping from phase names to predefined claims
        (claim text, feature name, claim type).
        """
        # Map each phase name to a canonical claim.
        phase_claim_map: dict[str, tuple[str, str, str]] = {
            "phase01_obfuscate": ("AST obfuscation preserves semantics", "obfuscator", "correctness"),
            "phase02_config": ("Configuration integrity", "config", "correctness"),
            "phase03_compile": ("Relay compilation correctness", "relay", "correctness"),
            "phase04_encrypt": ("Encrypted execution", "encrypt", "security"),
            "phase05_payload_h": ("Payload header integrity", "payload", "correctness"),
            "phase06_package": ("Package integrity", "package", "correctness"),
            "phase07_phase2": ("Advanced protection integration", "phase2", "security"),
            "phase08_rop": ("ROP chain integrity", "rop", "security"),
            "phase09_adversarial": ("Adversarial injection efficacy", "adversarial", "security"),
            "phase10_provenance": ("Provenance poisoning coverage", "provenance", "coverage"),
            "phase11_cfg_mutation": ("CFG mutation correctness", "cfg_mutation", "correctness"),
            "phase12_history_bound": ("History-bound decryption integrity", "history_bound", "security"),
            "phase13_ssa_mutation": ("SSA mutation correctness", "ssa_mutation", "correctness"),
            "phase14_per_exec_recompile": ("Per-exec recompile correctness", "recompile", "correctness"),
            "phase15_self_healing": ("Self-healing runtime integrity", "self_healing", "security"),
            "phase16_code_genome": ("Code genome evolution correctness", "code_genome", "correctness"),
            "phase17_struct_random": ("Struct randomization coverage", "struct_random", "coverage"),
            "phase18_hpc": ("HPC counter integration", "hpc", "performance"),
            "phase19_hpc_key": ("HPC key derivation correctness", "hpc_key", "security"),
            "phase20_hpc_detect": ("HPC emulator detection accuracy", "hpc_detect", "security"),
            "phase21_hw_entropy": ("Hardware entropy loop quality", "hw_entropy", "performance"),
            "phase22_cache_bound": ("Cache-bound execution isolation", "cache_bound", "security"),
            "phase23_branch_entangle": ("Branch predictor entanglement", "branch_entangle", "security"),
            "phase24_multicore_entangle": ("Multi-core timing entanglement", "multicore_entangle", "security"),
            "phase25_tee": ("TEE partition integrity", "tee", "security"),
            "phase26_sgx": ("SGX enclave correctness", "sgx", "security"),
            "phase27_cpu_port": ("CPU port entanglement", "cpu_port", "security"),
            "phase28_gpu_hybrid": ("GPU hybrid protection", "gpu_hybrid", "security"),
            "phase_coverage": ("Coverage analysis completeness", "coverage", "coverage"),
            "phase_security_gates": ("Security regression gate thresholds", "security_gates", "security"),
            "phase_redteam": ("Red team attack surface coverage", "redteam", "coverage"),
            "phase_attack_replay": ("Attack replay fidelity", "attack_replay", "correctness"),
            "phase_knowledge_graph": ("Knowledge graph integrity", "knowledge_graph", "coverage"),
            "phase_artifacts": ("Research artifact reproducibility", "artifacts", "coverage"),
            "phase_synthesis": ("Protection synthesis correctness", "synthesis", "correctness"),
            "phase_proof_coverage": ("Proof coverage completeness", "proof_coverage", "coverage"),
            "phase_fhe_vm": ("Encrypted execution", "FHE-VM", "security"),
            "phase_zk_state": ("ZK state proof validity", "zk_state", "correctness"),
            "phase_kernel_assist": ("Kernel-assisted execution integrity", "kernel_assist", "security"),
            "phase_io_research": ("iO research correctness", "io_research", "correctness"),
        }

        if phase_name in phase_claim_map:
            claim, feature, claim_type = phase_claim_map[phase_name]
            confidence = "measured"
            self.ledger.register_claim(claim, feature, claim_type, confidence)

            phase_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "phases",
            )
            phase_file = os.path.join(phase_dir, f"{phase_name}.py")
            if os.path.isfile(phase_file):
                self.ledger.add_evidence(claim, "source_code", phase_file)

    def collect_from_test(self, test_file: str) -> None:
        """Register a claim for the given test file and link it as evidence."""
        if not os.path.isfile(test_file):
            return
        # Map test file basenames to canonical claims.
        test_claim_map: dict[str, tuple[str, str, str, str]] = {
            "test_obfuscator": ("AST obfuscation preserves semantics", "obfuscator", "correctness", "measured"),
            "test_cfg_mutation": ("CFG mutation correctness", "cfg_mutation", "correctness", "measured"),
            "test_mba_validator": ("MBA substitutions resist SMT solvers", "obfuscator", "security", "estimated"),
            "test_encrypt": ("Encrypted execution", "encrypt", "security", "measured"),
            "test_vm_correctness": ("VM opcode obfuscation", "vm", "security", "measured"),
            "test_fragment_safety": ("Fragment isolation", "fragment", "security", "measured"),
            "test_watermark_survivability": ("Watermark survivability", "watermark", "correctness", "measured"),
            "test_semantic_preservation": ("Semantic preservation pipeline", "preservation", "correctness", "measured"),
            "test_proof_carrying": ("Proof-carrying equivalence", "proofs", "correctness", "measured"),
            "test_distributed": ("Distributed fragment binding", "distributed", "security", "theoretical"),
            "test_hardware": ("Cache-bound execution isolation", "hardware", "security", "estimated"),
            "test_microjit": ("Micro-JIT reassembly correctness", "microjit", "correctness", "measured"),
            "test_crypto_binding": ("Temporal key derivation", "binding", "security", "theoretical"),
            "test_zk_state": ("ZK state proof validity", "zk_state", "correctness", "measured"),
            "test_poly_engine": ("Poly-engine environmental adaptation", "environment", "performance", "measured"),
            "test_coverage": ("Coverage analysis completeness", "coverage", "coverage", "measured"),
            "test_proof_coverage": ("Proof coverage completeness", "proof_coverage", "coverage", "measured"),
            "test_security_gates": ("Security regression gate thresholds", "security_gates", "security", "measured"),
            "test_redteam": ("Red team attack surface coverage", "redteam", "coverage", "measured"),
            "test_attack_replay": ("Attack replay fidelity", "attack_replay", "correctness", "measured"),
            "test_artifacts": ("Research artifact reproducibility", "artifacts", "coverage", "measured"),
            "test_gpu_execution": ("GPU execution isolation", "gpu", "security", "estimated"),
            "test_exposure": ("Plaintext exposure minimization", "exposure", "security", "measured"),
            "test_synthesis": ("Protection synthesis correctness", "synthesis", "correctness", "measured"),
            "test_rop": ("ROP chain integrity", "rop", "security", "theoretical"),
        }
        basename = os.path.splitext(os.path.basename(test_file))[0]
        if basename in test_claim_map:
            claim, feature, claim_type, confidence = test_claim_map[basename]
            if claim not in self.ledger.claims:
                self.ledger.register_claim(claim, feature, claim_type, confidence)
            self.ledger.add_evidence(claim, "test", test_file)

    def collect_from_benchmark(self, benchmark_file: str) -> None:
        """Register a claim for the given benchmark file and link it as evidence."""
        if not os.path.isfile(benchmark_file):
            return
        # Map benchmark file basenames to canonical claims.
        bench_claim_map: dict[str, tuple[str, str, str, str]] = {
            "bench_conflicts": ("AST obfuscation preserves semantics", "obfuscator", "correctness", "measured"),
            "bench_coverage": ("Coverage analysis completeness", "coverage", "coverage", "measured"),
            "bench_proof_coverage": ("Proof coverage completeness", "proof_coverage", "coverage", "measured"),
            "bench_attack_replay": ("Attack replay fidelity", "attack_replay", "correctness", "measured"),
            "bench_artifacts": ("Research artifact reproducibility", "artifacts", "coverage", "measured"),
            "bench_redteam": ("Red team attack surface coverage", "redteam", "coverage", "measured"),
            "bench_fhe_vm": ("Encrypted execution", "FHE-VM", "security", "theoretical"),
            "bench_synthesis": ("Protection synthesis correctness", "synthesis", "correctness", "measured"),
            "bench_knowledge_graph": ("Knowledge graph integrity", "knowledge_graph", "coverage", "measured"),
            "bench_leakage": ("Semantic preservation pipeline", "preservation", "correctness", "measured"),
            "bench_security_gates": ("Security regression gate thresholds", "security_gates", "security", "measured"),
            "bench_kernel_assist": ("Kernel-assisted execution integrity", "kernel_assist", "security", "measured"),
        }
        basename = os.path.splitext(os.path.basename(benchmark_file))[0]
        if basename in bench_claim_map:
            claim, feature, claim_type, confidence = bench_claim_map[basename]
            if claim not in self.ledger.claims:
                self.ledger.register_claim(claim, feature, claim_type, confidence)
            self.ledger.add_evidence(claim, "benchmark", benchmark_file)

    def collect_from_runtime(self, runtime_path: str) -> None:
        """Register a claim for the given runtime/C++ trace file and link it as evidence."""
        if not os.path.isfile(runtime_path):
            return
        # Map runtime file basenames (without extension) to canonical claims.
        runtime_claim_map: dict[str, tuple[str, str, str, str]] = {
            "native_runtime": ("Encrypted execution", "encrypt", "security", "measured"),
            "fragment_runtime": ("Fragment isolation", "fragment", "security", "measured"),
            "cache_bound": ("Cache-bound execution isolation", "hardware", "security", "estimated"),
            "microjit": ("Micro-JIT reassembly correctness", "microjit", "correctness", "measured"),
            "attestation": ("Distributed fragment binding", "distributed", "security", "theoretical"),
        }
        basename = os.path.splitext(os.path.basename(runtime_path))[0]
        if basename in runtime_claim_map:
            claim, feature, claim_type, confidence = runtime_claim_map[basename]
            if claim not in self.ledger.claims:
                self.ledger.register_claim(claim, feature, claim_type, confidence)
            self.ledger.add_evidence(claim, "runtime_trace", runtime_path)

    def collect_from_metrics(self, build_dir: str) -> None:
        """Scan the metrics/ directory and register claims for each metric file found."""
        # Map metric file basenames to canonical claims.
        metrics_claim_map: dict[str, tuple[str, str, str, str]] = {
            "resilience": ("AST obfuscation preserves semantics", "obfuscator", "correctness", "measured"),
            "metrics_collector": ("Security regression gate thresholds", "security_gates", "security", "measured"),
            "pipeline_tracker": ("Coverage analysis completeness", "coverage", "coverage", "measured"),
            "context_saturation": ("Plaintext exposure minimization", "exposure", "security", "measured"),
            "prompt_resistance": ("Plaintext exposure minimization", "exposure", "security", "measured"),
        }
        metrics_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "metrics",
        )
        if os.path.isdir(metrics_dir):
            for fname in os.listdir(metrics_dir):
                if fname.endswith(".py"):
                    basename = os.path.splitext(fname)[0]
                    if basename in metrics_claim_map:
                        fpath = os.path.join(metrics_dir, fname)
                        claim, feature, claim_type, confidence = metrics_claim_map[basename]
                        if claim not in self.ledger.claims:
                            self.ledger.register_claim(claim, feature, claim_type, confidence)
                        self.ledger.add_evidence(claim, "metric", fpath)

    def collect_all(self, build_dir: str) -> EvidenceLedger:
        """Run all collectors (phases, tests, benchmarks, runtime, metrics) and return the populated ledger."""
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        phases_dir = os.path.join(root, "scripts", "phases")
        if os.path.isdir(phases_dir):
            for fname in sorted(os.listdir(phases_dir)):
                if fname.endswith(".py") and fname != "__init__.py":
                    phase_name = os.path.splitext(fname)[0]
                    self.collect_from_phase(phase_name, None)

        tests_dir = os.path.join(root, "tests")
        if os.path.isdir(tests_dir):
            for fname in sorted(os.listdir(tests_dir)):
                if fname.endswith(".py") and fname != "__init__.py" and fname != "conftest.py":
                    fpath = os.path.join(tests_dir, fname)
                    if "bench" in fname:
                        self.collect_from_benchmark(fpath)
                    else:
                        self.collect_from_test(fpath)

        native_dir = os.path.join(root, "native")
        if os.path.isdir(native_dir):
            for fname in sorted(os.listdir(native_dir)):
                if fname.endswith((".c", ".cpp")):
                    self.collect_from_runtime(os.path.join(native_dir, fname))

        runtime_dir = os.path.join(root, "runtime")
        if os.path.isdir(runtime_dir):
            for fname in sorted(os.listdir(runtime_dir)):
                if fname.endswith((".c", ".cpp", ".py")):
                    self.collect_from_runtime(os.path.join(runtime_dir, fname))

        self.collect_from_metrics(build_dir)

        return self.ledger
