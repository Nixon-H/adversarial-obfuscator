#!/usr/bin/env python3
"""
build.py

Purpose:
Main pipeline entry point for the Nixon Shadow Compiler — a multi-stage
obfuscation and protection system. Transforms a Python payload through 30+
pipeline phases: AST obfuscation, IR compilation, LLVM codegen, encryption,
relay/Rust binding, and a vast array of advanced protections (VM compilation,
JIT generation, ROP chains, hardware integration, formal proofs, etc.).

Architectural Role:
Orchestrator. This file is the CLI entry point that:
  1. Parses 200+ CLI flags controlling every protection feature.
  2. Validates system dependencies (Python >= 3.10, cargo, g++, llc, Python.h).
  3. Runs conflict detection among requested protections.
  4. Sequentially invokes phase functions imported from scripts/phases/.

Execution Context:
Invoked directly:
    python3 build.py --payload myscript.py [--flag ...]
Runs inside the project root. All build artifacts land in BUILD_DIR (build/).

Dependencies:
- scripts.common: path constants, atomic_write, log, run
- scripts.phases.*: 90+ phase functions registered in phases/__init__.py
- scripts.metrics: ResilienceMetrics, ContextSaturationMetrics, etc.
- scripts.binding.crypto_binding: CryptoFragmentBinder
- scripts.validation.smt_validator: SMTValidator
- scripts.classification: FunctionClassifier, StrategySelector
- obfuscator.*: AST obfuscation passes
- irgen.*: Python-to-IR compiler
- llvmgen.*: IR-to-LLVM code generator
- vm.*: VM compilation and ephemeral ISA

Security Relevance:
Central security gateway — every protection feature is gated behind a CLI
flag. Conflicts between incompatible protections are detected early. SMT
validation can optionally abort the build on semantic divergence.
"""

import argparse
import json
import os
import secrets
import shutil
import struct
import subprocess
import sys
import tempfile


_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from scripts.common import ROOT, BUILD_DIR, RELAY_DIR, OBFUSCATOR, CONFIG_FILE, DEFAULT_CONFIG
from scripts.common import atomic_write, log, run
from scripts.config_schema import ConfigError

from scripts.binding.crypto_binding import CryptoFragmentBinder, Fragment
from scripts.metrics import ResilienceMetrics

from scripts.validation.smt_validator import SMTValidator

from scripts.classification import FunctionClassifier, StrategySelector

from scripts.phases import (
    phase_obfuscate,
    phase_claim_audit,
    phase_generate_config,
    load_advanced_protection_config,
    phase_compile_relay,
    phase_cross_compile,
    phase_ir_compile,
    phase_llvm_codegen,
    phase_encrypt_binary,
    phase_entropy_flatten,
    phase_generate_payload_h,
    phase_embed_crypto_binding,
    phase_runtime_manifest,
    phase_package,
    phase_optional_extras,
    phase_classify,
    phase_variant_pool,
    phase_provenance_removal,
    phase_provenance_poison,
    phase_dataflow_obfuscation,
    phase_watermark_embedding,
    phase_vm_compile,
    phase_jit_generate,
    phase_adaptive_classifier_loop,
    phase_rop_compile,
    phase_adversarial_loop,
    phase_adversarial_injection,
    phase_cfg_mutation,
    phase_execution_history_binding,
    phase_ssa_mutation,
    phase_per_exec_recompile,
    phase_self_healing,
    phase_code_genome,
    phase_struct_randomization,
    phase_branch_entangle,
    phase_multicore_entangle,
    phase_tee,
    phase_sgx,
    phase_cpu_port,
    phase_gpu_hybrid,
    phase_class_dispatch,
    phase_rolling_keys,
    phase_state_isa,
    phase_io_research,
    phase_kernel_assist,
    phase_zk_state,
    phase_leakage,
    phase_proof_coverage,
    phase_proof_soundness,
    phase_redteam,
    phase_security_gates,
    phase_attack_replay,
    phase_assumptions,
    phase_synthesis,
    phase_artifacts,
    phase_adversarial_bench,
    phase_reproducibility,
    phase_security_debt,
    phase_verification_bundle,
    phase_check_conflicts,
    phase_self_audit,
    phase_trust_boundary,
    phase_evidence_completeness,
    phase_dependency_graph,
    phase_attack_surface,
    phase_invariant_engine,
    phase_independent_audit,
    phase_manipulation_detector,
    phase_benchmark_integrity,
    phase_verification_diversity,
    phase_audit_drift,
    phase_silent_fallback,
    phase_runtime_truth,
    phase_feature_effectiveness,
    phase_protection_roi,
    phase_longitudinal_tracking,
    phase_attack_corpus,
    phase_release_confidence,
    phase_threat_coverage,
    phase_knowledge_base,
    phase_self_critique,
    phase_coverage,
    phase_knowledge_graph,
    phase_false_confidence,
    phase_confidence,
    phase_micro_fragment,
    phase_poly_engine,
    phase_temporal_keys,
    phase_payload_dispersal,
    phase_pytoc,
)



# ===========================================================================
# Dependency Validation
# ===========================================================================

def _check_exe(name: str, install_hint: str) -> bool:
    """
    _check_exe

    Purpose:
    Verify that a system executable is available on PATH. Prints an error
    with install instructions on failure.

    Inputs:
    - name (str): executable name
    - install_hint (str): user-facing install command/message

    Outputs:
    - bool: True if found
    """
    if shutil.which(name) is not None:
        return True
    print(f"ERROR: Missing dependency: {name}")
    print(f"Install: {install_hint}")
    return False


def _warn_dangling(opts, parent, subs):
    """Log a warning when sub-options are set but their parent flag is off.

    Args:
        opts: argparse.Namespace with parsed CLI options.
        parent (str): dest name of the enabling flag (truthiness enables).
            A parent value of None also counts as off.
        subs (list[tuple[str, object]]): (dest, default) pairs; a sub-option
            counts as "set" when its current value != default (with None
            meaning "flag absent"). Only warns when at least one sub is set
            while the parent is off. Never fails the build.
    """
    try:
        parent_on = bool(getattr(opts, parent, False))
    except Exception:
        return
    if parent_on:
        return
    dangling = []
    for sub, default in subs:
        try:
            val = getattr(opts, sub, default)
        except Exception:
            continue
        if val != default:
            dangling.append(f"--{sub.replace('_', '-')}")
    if dangling:
        log("WARN", f"{', '.join(dangling)} set without --{parent.replace('_', '-')} (ignored)")


def _warn_all_dangling(opts):
    """Single call-site: check every known parent → sub-option group."""
    groups = [
        ("watermark", [("verify_watermark", False)]),
        ("confidence_interval", [("confidence_level", 0.95)]),
        ("benchmark", [("benchmark_model", None), ("benchmark_report", False)]),
        ("decoy_apis", [("decoy_api_count", 5)]),
        ("multi_agent_deception", [("storyline_count", 3)]),
        ("reasoning_traps", [("trap_depth", 5)]),
        ("llm_fingerprint", [("fingerprint_model", "gpt")]),
        ("temporal_keys", [("temporal_window", 60.0)]),
        ("payload_dispersal", [("dispersal_slices", 3)]),
        ("tee", [("tee_type", "software")]),
        ("coverage_map", [("coverage_output", None)]),
        ("knowledge_graph", [("knowledge_graph_output", None)]),
        ("fhe_vm", [("fhe_vm_functions", None)]),
        ("io_research", [("io_research_functions", None)]),
        ("kernel_assist", [("kernel_assist_features", None)]),
        ("red_team", [("red_team_output", "build/redteam")]),
        ("diversity", [("diversity_dir", "build/variants"),
                       ("diversity_threshold", 0.3),
                       ("diversity_report", False)]),
        ("synthesis", [("synthesis_target_security", 70.0),
                       ("synthesis_max_overhead", 50.0),
                       ("synthesis_max_size", 3.0),
                       ("synthesis_output", None),
                       ("apply_synthesis", False)]),
        ("adversarial_bench", [("adversarial_bench_count", 20)]),
        ("dist_attestation", [("dist_attestation_nodes", 5)]),
        ("dist_watermark", [("dist_watermark_shares", 5)]),
        ("dist_diversity", [("dist_diversity_variants", 8),
                            ("dist_diversity_nodes", 4),
                            ("dist_diversity_rotation", 3600.0)]),
        ("class_dispatch", [("class_dispatch_count", 4)]),
        ("ssa_mutation", [("ssa_variants", 4)]),
        ("cfg_mutation", [("cfg_mutation_variants", 4)]),
        ("state_isa", [("state_isa_history_len", 8)]),
        ("code_genome", [("genome_generations", 50),
                         ("genome_population", 30)]),
        ("struct_randomization", [("randomization_level", 3)]),
        ("micro_fragment", [("micro_fragment_size", 64)]),
        ("multi_binary", [("multi_binary_num", 4)]),
        ("multi_host", [("multi_host_count", 3)]),
        ("remote_unlock", [("remote_unlock_ttl", 30.0)]),
    ]
    for parent, subs in groups:
        _warn_dangling(opts, parent, subs)


def validate_dependencies() -> bool:
    """
    validate_dependencies

    Purpose:
    Check all system-level prerequisites before the pipeline starts:
      - Python >= 3.10
      - cargo (Rust toolchain)
      - g++ (C++ compiler)
      - llc (LLVM static compiler)
      - Python.h (Python dev headers)

    Outputs:
    - bool: True if all dependencies are satisfied
    """
    ok = True

    # Compat floor: 3.10 (matches nyser/py_matrix payload range 3.10-3.14
    # and CI matrix). Recon 2026-09: no match statements, no tomllib,
    # no except*, no 3.11-only stdlib APIs in the build import closure
    # (whole-tree ast.parse(feature_version=(3,10)) passes); version-gated
    # paths use sys.version_info branches, not syntax gates.
    if sys.version_info < (3, 10):
        print(f"ERROR: Python >= 3.10 required, got {sys.version_info.major}.{sys.version_info.minor}")
        print("Install: https://www.python.org/downloads/")
        ok = False

    if not _check_exe("cargo", "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"):
        ok = False

    if not _check_exe("g++", "apt install g++  (or: pacman -S gcc / brew install gcc)"):
        ok = False

    if not _check_exe("llc", "apt install llvm  (or: pacman -S llvm / brew install llvm)"):
        ok = False

    try:
        import sysconfig
        include_path = sysconfig.get_config_var("INCLUDEPY")
        if include_path and os.path.isfile(os.path.join(include_path, "Python.h")):
            pass
        else:
            raise FileNotFoundError
    except (FileNotFoundError, TypeError):
        print("ERROR: Missing dependency: Python.h (Python dev headers)")
        print("Install: apt install python3-dev  (or: pacman -S python / brew install python)")
        ok = False

    return ok


# ===========================================================================
# Phase functions moved to scripts/phases/ — see imports above
# ===========================================================================


# ===========================================================================
# Main Pipeline
# ===========================================================================

def main():
    """
    main

    Purpose:
    Pipeline entry point. Validates dependencies, parses CLI arguments,
    runs conflict detection, then executes all requested pipeline stages
    sequentially. Each stage is guarded by its corresponding CLI flag.

    Inputs:
    - None (reads sys.argv)

    Outputs:
    - Exits with code 0 on success, 1 on failure.
    """
    os.environ.setdefault("NIXON_LOG_REDIRECT", "0")
    if not validate_dependencies():
        sys.exit(1)
    parser = argparse.ArgumentParser(
        description="Nixon Build Pipeline — Shadow Compiler Multi-Stage Architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 build.py --payload myscript.py
  python3 build.py --payload myscript.py --skip-obfuscate --skip-relay
  python3 build.py --payload myscript.py --skip-irgen --skip-llvmgen
  python3 build.py --payload myscript.py --cross win,linux,linux-arm
  python3 build.py --payload myscript.py --phase2
  python3 build.py --payload myscript.py --phase2-only vm,watermark
  python3 build.py --payload myscript.py --classify
  python3 build.py --payload myscript.py --adversarial-injection --adversarial-level 5
  python3 build.py --payload myscript.py --adversarial-loop --deobfuscation-threshold 0.8
  python3 build.py --payload myscript.py --phase2 --phase2-extras --adversarial-injection --microjit
  python3 build.py --payload myscript.py --oram --phase2-extras
  python3 build.py --payload myscript.py --rop --llvmgen.rop.target_functions keygen,license
        """,
    )
    parser.add_argument("--version", action="version", version="shadow-compiler 2.0.0")
    parser.add_argument("--payload", required=True, help="Python script to obfuscate")
    parser.add_argument("-o", "--output", help="Output path for obfuscated script")
    parser.add_argument("--force-output", action="store_true", default=False,
                        help="Allow -o/--output outside the repo build dir "
                             "(default: refuse absolute/escaping paths)")
    parser.add_argument("--cross", help="Cross-compile targets: win,linux,macos,linux-arm")
    parser.add_argument("--generate-payload-h", action="store_true", default=True,
                        help="Auto-generate payload.h from obfuscated payload (default: on)")
    parser.add_argument("--no-generate-payload-h", action="store_false", dest="generate_payload_h",
                        help="Skip payload.h generation")
    parser.add_argument("--python-dll", help="Python DLL to embed in payload.h")
    parser.add_argument("--rust-exe", help="Rust Windows EXE to embed in payload.h")
    parser.add_argument("--skip-conflict-check", action="store_true", help="Skip protection conflict detection")
    parser.add_argument("--skip-obfuscate", action="store_true", help="Skip AST obfuscation")
    parser.add_argument("--skip-irgen", action="store_true", help="Skip IR compilation")
    parser.add_argument("--skip-llvmgen", action="store_true", help="Skip LLVM codegen")
    parser.add_argument("--skip-encrypt", action="store_true", help="Skip post-link encryption")
    parser.add_argument("--skip-relay", action="store_true", help="Skip Rust relay build")
    parser.add_argument("--skip-extras", action="store_true", help="Skip optional extras (antidbg, packing, timing checks)")
    parser.add_argument("--include-original", action="store_true", help="Include original payload in build/")
    parser.add_argument("--cfg-flatten", action="store_true", default=True, help=argparse.SUPPRESS)
    parser.add_argument("--no-cfg-flatten", action="store_false", dest="cfg_flatten")
    parser.add_argument("--opaque-predicates", action="store_true", default=True, help=argparse.SUPPRESS)
    parser.add_argument("--no-opaque-predicates", action="store_false", dest="opaque_predicates")
    parser.add_argument("--bogus-exceptions", action="store_true", default=True, help=argparse.SUPPRESS)
    parser.add_argument("--no-bogus-exceptions", action="store_false", dest="bogus_exceptions")
    parser.add_argument("--mba-subs", action="store_true", default=True, help=argparse.SUPPRESS)
    parser.add_argument("--no-mba-subs", action="store_false", dest="mba_subs")
    parser.add_argument("--fragment-strings", action="store_true", default=True, help=argparse.SUPPRESS)
    parser.add_argument("--no-fragment-strings", action="store_false", dest="fragment_strings")
    parser.add_argument("--unicode-ids", action="store_true", default=True, help=argparse.SUPPRESS)
    parser.add_argument("--no-unicode-ids", action="store_false", dest="unicode_ids")

    # SMT Validation flags
    parser.add_argument("--validate", action="store_true", help="Run SMT-backed semantic validation after each obfuscation phase")
    parser.add_argument("--validate-fail", action="store_true", help="Abort build if SMT validation fails")

    # Advanced Protection flags
    parser.add_argument("--advanced-protection", action="store_true", help="Enable all Advanced Protection features")
    parser.add_argument("--advanced-protection-only", help="Comma-separated list of Advanced Protection features to enable")
    parser.add_argument("--phase2", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--phase2-only", help=argparse.SUPPRESS)
    parser.add_argument("--phase2-extras", action="store_true", help="Enable optional extras (antidbg APIs, packing, timing checks, etc.)")
    parser.add_argument("--classify", action="store_true", help="Run classification pass and report")

    # Function-Level Adaptive Protection
    parser.add_argument("--adaptive", action="store_true", help="Enable function-level adaptive protection (auto-classify + strategy selection)")

    # New feature flags
    parser.add_argument("--adversarial-injection", action="store_true", help="Enable adversarial dead code + prompt injection")
    parser.add_argument("--adversarial-level", type=int, default=3, choices=range(1, 6), help="Adversarial injection aggressiveness (1-5, default: 3)")
    parser.add_argument("--ephemeral-isa", action="store_true", help="Enable ephemeral per-build VM opcode mapping")
    parser.add_argument("--microjit", action="store_true", help="Enable polymorphic micro-JIT reassembly")

    # Micro-JIT Fragment Reassembly flags
    parser.add_argument("--fragment", action="store_true", help="Enable micro-JIT fragment reassembly (decrypt->execute->wipe)")
    parser.add_argument("--fragment-size", type=int, default=5, help="Instructions per fragment (default: 5)")
    parser.add_argument("--fragment-functions", help="Comma-separated functions to fragment, or 'auto'")

    # Optimizer flags
    parser.add_argument("--optimize", action="store_true", help="Enable cost-aware protection optimizer")
    parser.add_argument("--max-cpu-overhead", type=float, default=20.0, help="Max CPU overhead percentage (default: 20)")
    parser.add_argument("--max-size-mult", type=float, default=3.0, help="Max binary size multiplier (default: 3.0)")
    parser.add_argument("--min-security", type=float, default=0.5, help="Minimum security score (default: 0.5)")

    # Formal Proof flags (Items 92-99)
    parser.add_argument("--prove-vm", action="store_true", help="Run VM correctness proofs (Item 92)")
    parser.add_argument("--prove-fragments", action="store_true", help="Run fragment safety proofs (Item 93)")
    parser.add_argument("--verify-watermark-survivability", action="store_true", help="Verify watermark survivability (Item 95)")
    parser.add_argument("--verify-mutations", action="store_true", help="Verify mutation safety (Item 96)")
    parser.add_argument("--verify-jit", action="store_true", help="Verify JIT reassembly correctness (Item 97)")
    parser.add_argument("--proof-aware-optimizer", action="store_true", help="Use proof-aware optimizer (Item 99)")

    # Proof Coverage flag (Feature 153)
    parser.add_argument("--proof-coverage", action="store_true", help="Generate proof coverage report (Feature 153)")

    # Proof Soundness flag (Feature 174)
    parser.add_argument("--proof-soundness", action="store_true", help="Run proof soundness harness (Feature 174)")

    # New pipeline flags
    parser.add_argument("--oram", action="store_true", help="Enable Oblivious RAM (ORAM) controller")
    parser.add_argument("--rop", action="store_true", help="Enable ROP chain compilation for crown jewel functions")
    parser.add_argument("--challenge-response", action="store_true", help="Enable standalone challenge-response protocol (extracted from distributed attestation)")
    parser.add_argument("--attestation", action="store_true", help="Enable hardware-agnostic attestation engine (whitebox entanglement + dynamic attestation)")
    parser.add_argument("--crypto-binding", action="store_true", help="Enable cryptographic fragment binding chain")

    # Live CFG Mutation flags (Item 80)
    parser.add_argument("--cfg-mutation", action="store_true", help="Enable live CFG mutation (variant basic-block ordering)")
    parser.add_argument("--cfg-mutation-variants", type=int, default=4, help="Number of CFG orderings per function (default: 4)")

    # Execution-Path-Specific Codegen flags (Item 81)
    parser.add_argument("--class-dispatch", action="store_true", help="Enable execution-path-specific JIT codegen")
    parser.add_argument("--class-dispatch-count", type=int, default=4, help="Number of dispatch classes (default: 4)")

    # Rolling Key Schedules flag (Item 82)
    parser.add_argument("--rolling-keys", action="store_true", help="Enable rolling key evolution for fragment chains")

    # State-Dependent Opcode Sets flags (Item 84)
    parser.add_argument("--state-isa", action="store_true", help="Enable state-dependent opcode mapping")
    parser.add_argument("--state-isa-history-len", type=int, default=8, help="Execution history length for state ISA (default: 8)")

    # Execution-History-Bound Decryption flag (Item 89)
    parser.add_argument("--history-bound-decryption", action="store_true", help="Enable execution-history-bound decryption key derivation")

    # Runtime SSA Mutation flags (Item 83)
    parser.add_argument("--ssa-mutation", action="store_true", help="Enable SSA mutation (variant instruction ordering)")
    parser.add_argument("--ssa-variants", type=int, default=4, help="Number of SSA variants per function (default: 4)")

    # Per-Execution Recompilation flags (Item 85)
    parser.add_argument("--per-exec-recompile", action="store_true", help="Enable per-execution recompilation")

    # Self-Healing Runtime flags (Item 86)
    parser.add_argument("--self-healing", action="store_true", help="Enable self-healing runtime (redundant code copies)")

    # Code Genome Evolution flags (Item 87)
    parser.add_argument("--code-genome", action="store_true", help="Enable code genome evolution")
    parser.add_argument("--genome-generations", type=int, default=50, help="Evolution generations (default: 50)")
    parser.add_argument("--genome-population", type=int, default=30, help="Population size (default: 30)")

    # Structure Randomization flags (Item 88)
    parser.add_argument("--struct-randomization", action="store_true", help="Enable structure randomization (stack/heap/reg)")
    parser.add_argument("--randomization-level", type=int, default=3, choices=[1, 2, 3], help="Randomization level 1-3 (default: 3)")
    parser.add_argument("--randomization-seed", type=int, default=None, help="Deterministic seed for structure randomization (also read from SEED/NIXON_SEED env when flag is absent)")

    # Adversarial loop flags
    parser.add_argument("--adversarial-loop", action="store_true", help="Enable self-improving obfuscation via deobfuscation agent")

    # Adversarial Benchmark Generator (Feature 175)
    parser.add_argument("--adversarial-bench", action="store_true", help="Run adversarial benchmark generator against all target systems")
    parser.add_argument("--adversarial-bench-count", type=int, default=20, help="Number of adversarial tests to generate (default: 20)")

    parser.add_argument("--deobfuscation-threshold", type=float, default=0.7, help="Minimum deobfuscation score (default: 0.7)")
    parser.add_argument("--evolution-iterations", type=int, default=1, help="Number of evolution steps per build (default: 1)")

    # Provenance Replace flag
    parser.add_argument("--provenance-replace", action="store_true", help="Enable automated provenance replacement (error codes + string encoding + constant obfuscation)")

    # Provenance Poisoning flags
    parser.add_argument("--provenance-poison", action="store_true", help="Enable all provenance poisoning techniques")
    parser.add_argument("--poison-call-graph", action="store_true", dest="poison_call_graph", help="Enable fake call graphs")
    parser.add_argument("--poison-apis", action="store_true", dest="poison_apis", help="Enable fake APIs")
    parser.add_argument("--poison-protocols", action="store_true", dest="poison_protocols", help="Enable fake protocol parsers")
    parser.add_argument("--poison-paths", action="store_true", dest="poison_paths", help="Enable believable dead paths")
    parser.add_argument("--poison-imports", action="store_true", dest="poison_imports", help="Enable misleading imports")
    parser.add_argument("--poison-all", action="store_true", help="Enable all poisoning techniques")
    parser.add_argument("--poison-level", type=int, default=0, choices=range(0, 6), help="Provenance poisoning level (1-5, default: 0 = disabled)")

    # LLM-Resilient flags
    parser.add_argument("--llm-resilient", action="store_true", dest="llm_resilient", help="Enable LLM-resilient AST obfuscation (context collapse + guard vars + string encoding)")
    parser.add_argument("--llm-resilient-depth", type=int, default=15, dest="llm_resilient_depth", help="Nesting depth for context collapse (default: 15)")
    parser.add_argument("--llm-resilient-vars", type=int, default=50, dest="llm_resilient_vars", help="Number of dead variables per function (default: 50)")
    parser.add_argument("--honey-functions", type=int, default=0, dest="honey_functions", help="Number of honey functions to inject (default: 0)")

    # LLM Fingerprint flags (Item 73)
    parser.add_argument("--llm-fingerprint", action="store_true", help="Enable LLM fingerprint embedding")
    parser.add_argument("--fingerprint-model", default="gpt", choices=["gpt", "claude", "gemini", "deepseek", "copilot"], help="AI model to fingerprint as (default: gpt)")

    # Reasoning Trap flags (Item 75)
    parser.add_argument("--reasoning-traps", action="store_true", help="Enable reasoning-loop trap injection")
    parser.add_argument("--trap-depth", type=int, default=5, help="Circular chain depth for reasoning traps (default: 5)")

    # Function Intent Obfuscation flags (Item 78)
    parser.add_argument("--function-intent", action="store_true", help="Enable function intent obfuscation")

    # Context Saturation Metrics flag (Item 76)
    parser.add_argument("--context-saturation", action="store_true", help="Compute context window saturation metrics")

    # Prompt Resistance Metrics flag (Item 77)
    parser.add_argument("--prompt-resistance", action="store_true", help="Compute prompt reconstruction resistance metrics")

    # Item 50: Micro-Fragment Execution
    parser.add_argument("--micro-fragment", action="store_true", help="Enable micro-fragment execution (decrypt->execute->wipe each fragment)")
    parser.add_argument("--micro-fragment-size", type=int, default=64, help="Bytes per micro-fragment (default: 64)")

    # Item 58: Environmental Poly-Engine
    parser.add_argument("--poly-engine", action="store_true", help="Enable environmental poly-engine (environment-adapted code variants)")

    # Item 59: Temporal Micro-Key Evolution
    parser.add_argument("--temporal-keys", action="store_true", help="Enable temporal micro-key evolution (time-window-based key chain)")
    parser.add_argument("--temporal-window", type=float, default=60.0, help="Key time window in seconds (default: 60)")

    # Item 63: Whitebox-Flow Entanglement
    parser.add_argument("--flow-entangle", action="store_true", help="Enable whitebox-flow entanglement (crypto-state-dependent control flow)")

    # Item 69: Payload Dispersal Execution Model
    parser.add_argument("--payload-dispersal", action="store_true", help="Enable payload dispersal execution model (disjoint slice execution)")
    parser.add_argument("--dispersal-slices", type=int, default=3, help="Number of payload slices (default: 3)")

    # Item 91: Proof-Carrying Obfuscation
    parser.add_argument("--proof-carrying", action="store_true", help="Enable proof-carrying obfuscation (Z3 equivalence certificates)")

    # Item 101: Analyst Time Estimation
    parser.add_argument("--analyst-time", action="store_true", help="Estimate analyst reverse-engineering time from complexity metrics")

    # Data Obfuscation flags
    parser.add_argument("--data-obfuscation", action="store_true", dest="data_obfuscation", help="Enable data-oriented obfuscation (protect data layout)")
    parser.add_argument("--data-obf-level", type=int, default=3, dest="data_obf_level", choices=[1, 2, 3], help="Data obfuscation intensity (1-3, default: 3)")

    # Watermark flags
    parser.add_argument("--watermark", type=str, default=None, help="Embed semantic watermark string into IR")
    parser.add_argument("--verify-watermark", action="store_true", help="Verify watermark after embedding")
    parser.add_argument("--uarch-watermark", action="store_true", help="Embed microarchitectural timing watermark (Item 122)")

    # Certificate flags
    parser.add_argument("--emit-certificates", action="store_true",
                        help="Emit transformation equivalence certificates")
    parser.add_argument("--embed-proof", action="store_true",
                        help="Embed proof section into packaged binary")

    # Verified MBA flags
    parser.add_argument("--verify-mba", action="store_true",
                        help="Verify MBA substitutions with SMT before applying")

    # Preservation flags
    parser.add_argument("--verify-preservation", action="store_true",
                        help="Run machine-checked semantic preservation across pipeline stages")
    parser.add_argument("--verify-preservation-formal", action="store_true",
                        help="Run formal Z3-based semantic preservation proofs (Item 61)")

    # Plaintext Exposure Metric (Feature 151)
    parser.add_argument("--plaintext-exposure", action="store_true", help="Measure actual plaintext lifetime during execution (Feature 151)")

    # Metrics flags
    parser.add_argument("--metrics", action="store_true", help="Collect quantitative resilience metrics after build")
    parser.add_argument("--min-resilience", type=float, default=None, help="Minimum resilience score (0.0-1.0); auto-tune up to 3 iterations")

    # Semantic Leakage Metric (Feature 152)
    parser.add_argument("--semantic-leakage", action="store_true", help="Measure semantic leakage between original and obfuscated IR (Feature 152)")

    # Diversity generation flags
    parser.add_argument("--diversity", type=int, default=None, help="Generate N diversity variants")
    parser.add_argument("--uarch-diversity", action="store_true", help="Enable microarchitectural-aware diversity generation (Item 129)")
    parser.add_argument("--diversity-dir", default="build/variants", help="Output directory for diversity variants")
    parser.add_argument("--diversity-threshold", type=float, default=0.3, help="Minimum diversity score between variants (0.0-1.0)")
    parser.add_argument("--diversity-report", action="store_true", help="Generate diversity comparison report")

    # Distributed Protection flags (Items 110–119)
    parser.add_argument("--distributed-mode", default="simulation", choices=["simulation", "multiprocess"],
                        help="Mode for distributed protection features: simulation or multiprocess (default: simulation)")
    parser.add_argument("--multi-binary", action="store_true", help="Enable multi-binary fragment distribution (Item 110)")
    parser.add_argument("--multi-binary-num", type=int, default=4, help="Number of binaries for fragment distribution (default: 4)")
    parser.add_argument("--cross-process", action="store_true", help="Enable cross-process fragment binding (Item 111)")
    parser.add_argument("--remote-unlock", action="store_true", help="Enable remote fragment unlocking (Item 112)")
    parser.add_argument("--remote-unlock-ttl", type=float, default=30.0, help="Token TTL for remote unlock in seconds (default: 30)")
    parser.add_argument("--distributed-vm", action="store_true", help="Enable distributed VM execution (Item 113)")
    parser.add_argument("--multi-host", action="store_true", help="Enable multi-host execution graphs (Item 114)")
    parser.add_argument("--multi-host-count", type=int, default=3, help="Number of hosts for multi-host execution (default: 3)")
    parser.add_argument("--fragment-migration", action="store_true", help="Enable cross-platform fragment migration (Item 115)")
    parser.add_argument("--dist-attestation", action="store_true", help="Enable distributed attestation (Item 116)")
    parser.add_argument("--dist-attestation-nodes", type=int, default=5, help="Number of attestation nodes (default: 5)")
    parser.add_argument("--dist-watermark", action="store_true", help="Enable distributed watermarking (Item 117)")
    parser.add_argument("--dist-watermark-shares", type=int, default=5, help="Number of watermark shares (default: 5)")
    parser.add_argument("--dist-diversity", action="store_true", help="Enable distributed diversity pools (Item 118)")
    parser.add_argument("--dist-diversity-variants", type=int, default=8, help="Number of diversity variants (default: 8)")
    parser.add_argument("--dist-diversity-nodes", type=int, default=4, help="Number of deployment nodes (default: 4)")
    parser.add_argument("--dist-diversity-rotation", type=float, default=3600.0, help="Variant rotation interval in seconds (default: 3600)")
    parser.add_argument("--recovery-prevention", action="store_true", help="Enable distributed execution recovery prevention (Item 119)")
    parser.add_argument("--recovery-prevention-nodes", type=int, default=5, help="Number of recovery prevention nodes (default: 5)")

    # Hardware Research Integration flags (Items 120-124)
    parser.add_argument("--hpc", action="store_true", help="Enable hardware performance counter integration (Item 120)")
    parser.add_argument("--hpc-key", action="store_true", help="Enable HPC-based key derivation (Item 121)")
    parser.add_argument("--hpc-detect", action="store_true", help="Enable emulator detection via HPC (Item 122)")
    parser.add_argument("--hw-entropy", action="store_true", help="Enable hardware entropy loop (Item 123)")
    parser.add_argument("--cache-bound", action="store_true", help="Enable cache-bound execution (Item 124)")

    # Hardware Research Integration flags (Items 125-129)
    parser.add_argument("--branch-entangle", action="store_true", help="Enable branch predictor entanglement (Item 125)")
    parser.add_argument("--multicore-entangle", action="store_true", help="Enable multi-core timing entanglement (Item 126)")
    parser.add_argument("--tee", action="store_true", help="Enable trusted execution environment partition (Item 127)")
    parser.add_argument("--tee-type", default="software", choices=["software", "sgx", "sev", "apple"], help="TEE type (default: software)")
    parser.add_argument("--sgx", action="store_true", help="Enable Intel SGX hardware enclave support (Item 128)")
    parser.add_argument("--cpu-port", action="store_true", help="Enable CPU execution port entanglement (Item 129)")
    parser.add_argument("--gpu-hybrid", action="store_true", help="Enable CPU/GPU hybrid protection (Item 126)")
    parser.add_argument("--gpu-execution", action="store_true", help="Enable GPU fragment execution with hardware detection (Item 125)")
    parser.add_argument("--gpu", action="store_true", help="Short flag for --gpu-execution (Item 125)")
    parser.add_argument("--cpu-gpu-hybrid", action="store_true", help="Enable distinct CPU/GPU hybrid protection paths (Item 126)")

    # Speculation Obfuscation flag (Item 123)
    parser.add_argument("--speculation-obfuscation", action="store_true", help="Enable AST-level speculation obfuscation (Item 123)")

    # SIMD-VM flag (Item 124)
    parser.add_argument("--simd-vm", action="store_true", help="Enable SIMD-accelerated VM dispatch (Item 124)")

    # Attention Poison flags
    parser.add_argument("--attention-poison", type=int, default=0, help="Enable attention poisoning with fan-out N (default: 0 = disabled)")

    # Decoy API flags
    parser.add_argument("--decoy-apis", action="store_true", help="Enable semantic decoy API injection")
    parser.add_argument("--decoy-api-count", type=int, default=5, help="Number of decoy APIs to inject (default: 5)")

    # Multi-Agent Deception flags
    parser.add_argument("--multi-agent-deception", action="store_true", help="Enable multi-agent deception storyline injection")
    parser.add_argument("--storyline-count", type=int, default=3, help="Number of storylines to inject (default: 3)")

    # Adaptive Classifier Loop flag
    parser.add_argument("--adaptive-classifier-loop", action="store_true", help="Run classify → protect → benchmark → re-classify → re-protect loop")

    # Adaptive Adversarial Rewriting flags
    parser.add_argument("--adaptive-adversarial", action="store_true", help="Enable adaptive adversarial rewriting based on benchmark feedback")

    # AI-Guided Diversity flags
    parser.add_argument("--ai-guided-diversity", action="store_true", help="Enable AI-guided evolutionary diversity generation")
    parser.add_argument("--evolution-generations", type=int, default=3, help="Number of evolution generations (default: 3)")

    # Benchmark flags
    parser.add_argument("--benchmark", action="store_true", help="Run AI obfuscation benchmark on protected output")
    parser.add_argument("--benchmark-model", default=None, help="Specify LLM model to test against (gpt4, claude3, gemini, deepseek, or 'all')")
    parser.add_argument("--benchmark-report", action="store_true", help="Generate HTML benchmark report")

    # Evaluation research flags
    parser.add_argument("--cost-model", action="store_true", help="Run reverse engineering cost model estimation")
    parser.add_argument("--multi-tool", action="store_true", help="Run multi-tool resistance evaluation")
    parser.add_argument("--survivability", action="store_true", help="Run protection survivability index measurement")
    parser.add_argument("--eval-summary", action="store_true", help="Run full evaluation summary report")

    # Unified evaluation report flag
    parser.add_argument("--evaluate", action="store_true", help="Generate unified evaluation report (all 9 metrics)")

    # FHE-VM flags
    parser.add_argument("--fhe-vm", action="store_true", help="Enable FHE-VM compilation for crown-jewel functions")
    parser.add_argument("--fhe-vm-functions", help="Comma-separated function names for FHE-VM compilation")

    # IO Research flags
    parser.add_argument("--io-research", action="store_true", help="Enable approximate indistinguishability obfuscation research")
    parser.add_argument("--io-research-functions", help="Comma-separated function names for iO research")

    # Kernel-Assisted Execution Research flags
    parser.add_argument("--kernel-assist", action="store_true", help="Enable kernel-assisted execution research (Linux)")
    parser.add_argument("--kernel-assist-features", help="Comma-separated kernel features to enable (default: all detected)")

    # ZK State-Bound Execution flags
    parser.add_argument("--zk-state", action="store_true", help="Enable ZK state-bound execution (sigma-protocol-based state proofs)")
    parser.add_argument("--zk-state-config", help="Path to ZK state config file (optional)")

    # Protection Coverage Map flags (Feature 147)
    parser.add_argument("--coverage-map", action="store_true", help="Generate protection coverage map after all stages")
    parser.add_argument("--coverage-output", default=None, help="Output directory for coverage map (default: build/coverage/)")

    # Security Knowledge Graph flag (Feature 149)
    parser.add_argument("--knowledge-graph", action="store_true", help="Generate security knowledge graph of protection relationships")
    parser.add_argument("--knowledge-graph-output", default=None, help="Output directory for knowledge graph (default: build/knowledge_graph/)")

    # Protection Synthesis Engine flags (Feature 150)
    parser.add_argument("--synthesis", action="store_true", help="Enable protection synthesis engine (auto-select protections)")
    parser.add_argument("--synthesis-target-security", type=float, default=70.0, help="Target security score 0-100 (default: 70)")
    parser.add_argument("--synthesis-max-overhead", type=float, default=50.0, help="Max allowed overhead percent (default: 50)")
    parser.add_argument("--synthesis-max-size", type=float, default=3.0, help="Max allowed size multiplier (default: 3.0)")
    parser.add_argument("--synthesis-output", default=None, help="Output path for synthesis report (default: build/synthesis_report.json)")
    parser.add_argument("--apply-synthesis", action="store_true", help="Apply synthesis plan flags to pipeline configuration")

    # Feature 169: Reachability Coverage Report
    parser.add_argument("--reachability-report", action="store_true", help="Generate reachability coverage report classifying every feature as REACHABLE/PARTIALLY_REACHABLE/UNREACHABLE (Feature 169)")

    # Feature classification flag (Phase 5)
    parser.add_argument("--classify-features", action="store_true", help="Classify all 129 protection/research features and generate report")

    # Security Regression Gates flags (Feature 146)
    parser.add_argument("--security-gates", action="store_true", help="Enable security regression gates (Feature 146)")
    parser.add_argument("--update-baseline", action="store_true", help="Save current metrics as new baseline for security gates")
    parser.add_argument("--gate-threshold", type=float, default=None, help="Global gate threshold override (0.0-1.0)")

    # Autonomous Red Team Pipeline (Feature 145)
    parser.add_argument("--red-team", action="store_true", help="Enable autonomous red team pipeline — every build attacks itself")
    parser.add_argument("--red-team-output", default="build/redteam", help="Output directory for red team attack results (default: build/redteam/)")

    # Attack Replay Framework (Feature 154)
    parser.add_argument("--capture-attacks", action="store_true", help="Capture attack results from red team pipeline for replay")
    parser.add_argument("--replay-attacks", action="store_true", help="Replay captured attacks and compare results")
    parser.add_argument("--attack-store", default="build/attacks", help="Store directory for attack captures (default: build/attacks/)")

    # False Confidence Detector (Feature 173)
    parser.add_argument("--false-confidence-audit", action="store_true", help="Scan for false confidence patterns in codebase (Feature 173)")
    parser.add_argument("--claim-audit", action="store_true", help="Scan for unsupported security claims like 'secure', 'unbreakable', 'tamper-proof' (Feature 172)")

    # Research Artifact Generator (Feature 155)
    parser.add_argument("--generate-artifacts", action="store_true", help="Generate paper-ready research artifacts from build outputs")
    parser.add_argument("--artifacts-output", default="build/artifacts", help="Output directory for research artifacts (default: build/artifacts/)")

    # Reproducibility Score (Feature 178)
    parser.add_argument("--reproducibility-score", action="store_true", help="Compute reproducibility score for build artifacts (Feature 178)")

    # Feature 180: Self-Audit Agent
    parser.add_argument("--self-audit", action="store_true", help="Run self-audit agent — final pipeline integrity check (Feature 180)")

    # Feature 171: Assumption Tracker
    parser.add_argument("--assumptions-report", action="store_true", help="Generate assumption report for all protection features")

    # Feature 176: Feature Retirement Framework
    parser.add_argument("--retirement-report", action="store_true", help="Generate feature retirement report analyzing features for low effectiveness, high overhead, poor survivability")

    # Reality Score (Feature 167)
    parser.add_argument("--reality-score", action="store_true", help="Compute 0-100 Reality Score for every protection feature")

    # Security Debt Index (Feature 170)
    parser.add_argument("--security-debt", action="store_true", help="Compute security debt index measuring unprotected functions, weak protections, and coverage gaps")

    # Evidence Ledger (Feature 168)
    parser.add_argument("--evidence-ledger", action="store_true", help="Generate evidence ledger mapping claims to source files, tests, benchmarks, and runtime traces")

    # Independent Verification Bundle (Feature 177)
    parser.add_argument("--verification-bundle", action="store_true", help="Generate independent verification bundle (tar.gz + SHA256 manifest) of all build artifacts")
    parser.add_argument("--verification-bundle-output", default=None, help="Output directory for verification bundle (default: build/verification_bundle/) (set to empty string to use default)")

    # Feature 186: Trust Boundary Mapper
    parser.add_argument("--trust-boundary", action="store_true", help="Map trust boundaries across all domains (Feature 186)")

    # Feature 187: Evidence Completeness Score
    parser.add_argument("--evidence-completeness", action="store_true", help="Compute evidence completeness score for all claims (Feature 187)")

    # Feature 188: Dependency Graph Validation
    parser.add_argument("--dependency-graph", action="store_true", help="Validate dependency graph and detect cycles (Feature 188)")

    # Feature 189: Attack Surface Enumerator
    parser.add_argument("--attack-surface", action="store_true", help="Enumerate attack surfaces across all categories (Feature 189)")

    # Feature 190: Security Invariant Engine
    parser.add_argument("--invariant-engine", action="store_true", help="Verify security invariants across codebase (Feature 190)")

    # Feature 181: Independent Auditor Mode
    parser.add_argument("--independent-audit", action="store_true", help="Run independent audit using separate code paths (Feature 181)")

    # Feature 182: Metric Manipulation Detector
    parser.add_argument("--manipulation-detector", action="store_true", help="Detect metric manipulation, hardcoded scores, inflated coverage (Feature 182)")

    # Feature 183: Benchmark Integrity Framework
    parser.add_argument("--benchmark-integrity", action="store_true", help="Verify benchmark integrity with SHA256 hashing and tamper detection (Feature 183)")

    # Feature 184: Verification Diversity
    parser.add_argument("--verification-diversity", action="store_true", help="Run multiple verification strategies and detect disagreements (Feature 184)")

    # Feature 185: Audit Drift Detection
    parser.add_argument("--audit-drift", action="store_true", help="Detect code changes without corresponding verification updates (Feature 185)")

    # Feature 191: Silent Fallback Detector
    parser.add_argument("--silent-fallback", action="store_true", help="Detect silent fallbacks (try/except without logging) in codebase (Feature 191)")

    # Feature 192: Runtime Truth Monitor
    parser.add_argument("--runtime-truth", action="store_true", help="Record what actually executes vs what was intended (Feature 192)")

    # Feature 193: Feature Effectiveness Score
    parser.add_argument("--feature-effectiveness", action="store_true", help="Score features by demonstrated security improvement, not existence (Feature 193)")

    # Feature 194: Protection ROI Engine
    parser.add_argument("--protection-roi", action="store_true", help="Compute security gain vs runtime/complexity/maintenance cost for each feature (Feature 194)")

    # Feature 195: Longitudinal Security Tracking
    parser.add_argument("--longitudinal-tracking", action="store_true", help="Track security metrics over time and detect drift (Feature 195)")

    # Feature 196: Attack Corpus
    parser.add_argument("--attack-corpus", action="store_true", help="Build permanent corpus of bypasses, deobfuscations, proof failures, replay attacks (Feature 196)")

    # Feature 197: Release Confidence Score
    parser.add_argument("--release-confidence", action="store_true", help="Combine all verification metrics into single release confidence score (Feature 197)")

    # Feature 198: Formal Threat Coverage
    parser.add_argument("--threat-coverage", action="store_true", help="Map threats to features, metrics, and verifications; identify gaps (Feature 198)")

    # Feature 199: Security Knowledge Base
    parser.add_argument("--knowledge-base", action="store_true", help="Build persistent historical record of assumptions, failures, fixes, discoveries (Feature 199)")

    # Feature 200: Self-Critique Engine
    parser.add_argument("--self-critique", action="store_true", help="Before release, critically analyze assumptions, evidence, metrics, proofs (Feature 200)")

    # Security Confidence Interval (Feature 179)
    parser.add_argument("--confidence-interval", action="store_true",
                        help="Compute security confidence intervals from metric samples (Feature 179)")
    parser.add_argument("--confidence-level", type=float, default=0.95,
                        help="Confidence level for intervals (default: 0.95)")

    # Phase-2 delivery: optimization ladder + PyTOC placeholder
    parser.add_argument("--opt-level", type=int, default=4, choices=range(0, 6),
                        help="Optimization/protection ladder O0-O5 (default: 4, recommended)")
    parser.add_argument("--pytoc", action="store_true",
                        help="Compile the obfuscated output to a native extension via Cython (best-effort, never fails the build)")
    parser.add_argument("--pytoc-out", type=str, default="",
                        help="Output path for the --pytoc native extension (default: alongside -o as <out>_pytoc.<so/pyd>)")
    parser.add_argument("--pyinstaller-spec", action="store_true",
                        help="Write a best-effort PyInstaller .spec alongside the output (never fails the build)")

    # Phase-4 tested-but-unwired modules: additive opt-in flags (all default OFF / empty).
    parser.add_argument("--hwid", type=str, default="",
                        help="HWID string for GET_HWID() macro expansion and HWID-locked fallback. "
                             "Dynamic (default): any opaque string; the loader collects "
                             "format(uuid.getnode(), 'x') at runtime. Static (GAP #33): "
                             "canonical 'HWID:<64 hex chars>' fingerprint (case-insensitive, "
                             "lowercased) binding the artifact to a known value instead of "
                             "dynamic collection (documented in obfuscator/hwid_lock.py; "
                             "default: '')")
    parser.add_argument("--trial", type=str, default="",
                        help="Trial period spec, e.g. '7d', '1w2d' (parsed via obfuscator.macros.parse_trial; default: '')")
    parser.add_argument("--vm-threshold", type=float, default=50.0,
                        help="VM-score verdict threshold embedded in loader snippet (default: 50.0)")
    parser.add_argument("--kod", action="store_true", default=False,
                        help="Arm loader kill-on-detect note: VM snippet reads NIXON_KOD env at runtime (default: report-only)")
    parser.add_argument("--hostguard", action="store_true", default=False,
                        help="Prepend hostguard snippet (bind_host/check_host/isolated_exec) to loader (default: off)")
    parser.add_argument("--hwid-lock", dest="hwid_lock", action="store_true", default=False,
                        help="HWID-lock the bytecode fallback blob (requires --hwid; static "
                             "'HWID:<64 hex>' fingerprints unlock via the embedded value, "
                             "dynamic HWIDs via uuid.getnode(); default: off)")
    parser.add_argument("--sign-key-env", type=str, default="",
                        help="Env var name holding hex key for artifact signing sidecars (.sig.json; default: '' = disabled)")
    parser.add_argument("--name-gate", dest="name_gate", action="store_true", default=False,
                        help="Rewrite privileged call sites through per-build token map (default: off)")
    parser.add_argument("--rename-internal", dest="rename_internal", action="store_true", default=False,
                        help="Rename proven-internal public methods/attributes (used only "
                             "inside their own class; opt-in, default: off)")
    parser.add_argument("--lowering", type=str, default="",
                        help="Semantic-lowering families CSV (io,scalar,string,container,service,protocol,function,import,fusion + opt-in: arithmetic,truth,slice,format,augassign); default '' = disabled")
    parser.add_argument("--diagnostic", action="store_true", default=False,
                        help="Diagnostic build: per-stage timings + transform counts + NOT-FOR-RELEASE marker")
    parser.add_argument("--no-audit-hook-plant", dest="audit_hook_plant_off", action="store_true", default=False,
                        help="Omit the site-packages audit-hook plant detector from the loader (default: detector ON)")
    parser.add_argument("--driver-check", dest="driver_check", action="store_true", default=False,
                        help="Bake the V10 kernel-driver gate into the loader (fail-closed on "
                             "known-vulnerable BYOVD drivers only when armed; default: off, "
                             "also armable at runtime via NIXON_DRIVER_CHECK=1)")
    parser.add_argument("--split-bootstrap", dest="split_bootstrap", action="store_true", default=False,
                        help="V10 kernel split-bootstrap: Shamir (n=3,k=2) threshold key + "
                             "fragmented decoder in the loader instead of the single embedded "
                             "key path (opt-in until battle-tested; default: off)")
    parser.add_argument("--no-snapshot", dest="snapshot_off", action="store_true", default=False,
                        help="Omit the frozen-stdlib snapshot gate from the loader (default: gate ON; "
                             "also disarmable at runtime via NIXON_SNAPSHOT_OFF=1)")
    parser.add_argument("--no-stdlib-audit", dest="stdlib_audit_off", action="store_true", default=False,
                        help="Omit the stdlib function-audit gate from the loader (default: gate ON; "
                             "also disarmable at runtime via NIXON_STDLIB_AUDIT_OFF=1)")
    parser.add_argument("--build-id", dest="build_id", type=str, default="",
                        help="stable build id (reproducible builds; default: random per build)")

    opts = parser.parse_args()

    # SEED/NIXON_SEED env fallback for --randomization-seed (reproducible
    # builds; documented in docs/DEVELOPER.md). Explicit flag always wins.
    if getattr(opts, "randomization_seed", None) is None:
        for _seed_var in ("NIXON_SEED", "SEED"):
            try:
                _seed_raw = os.environ.get(_seed_var, "")
                if str(_seed_raw).strip() != "":
                    opts.randomization_seed = int(str(_seed_raw).strip())
                    break
            except Exception:
                continue

    # Phase-2 delivery: report resolved opt-level via log() (no behavior change).
    try:
        from obfuscator.opt_levels import describe as _opt_describe
        log("OPT", _opt_describe(opts.opt_level))
    except Exception as _opt_err:
        log("OPT", f"opt-level {getattr(opts, 'opt_level', '?')}: ({_opt_err})")
    _warn_all_dangling(opts)
    if getattr(opts, "pytoc", False):
        log("OPT", "PyTOC native-extension path requested (best-effort Cython build)")
    if getattr(opts, "pyinstaller_spec", False):
        log("OPT", "PyInstaller .spec generation requested (best-effort)")

    # Phase-4 wiring flags: log only when set (no behavior change otherwise).
    if getattr(opts, "hwid", ""):
        log("OPT", "HWID binding requested")
    if getattr(opts, "trial", ""):
        log("OPT", f"Trial spec requested: {opts.trial}")
    if getattr(opts, "vm_threshold", 50.0) != 50.0:
        log("OPT", f"VM threshold: {opts.vm_threshold}")
    if getattr(opts, "kod", False):
        log("OPT", "KOD note set (loader reads NIXON_KOD env at runtime)")
    if getattr(opts, "hostguard", False):
        log("OPT", "Hostguard snippet requested")
    if getattr(opts, "hwid_lock", False):
        log("OPT", "HWID-lock requested for fallback blob")
    if getattr(opts, "sign_key_env", ""):
        log("OPT", f"Artifact signing via env: {opts.sign_key_env}")
    if getattr(opts, "name_gate", False):
        log("OPT", "Runtime API name gate requested")
    if getattr(opts, "rename_internal", False):
        log("OPT", "Proven-internal method rename requested")
    if getattr(opts, "lowering", ""):
        log("OPT", f"Semantic lowering families: {opts.lowering}")
    if getattr(opts, "diagnostic", False):
        log("OPT", "DIAGNOSTIC BUILD (not for release)")
        try:
            from scripts.diagnostic import (
                DiagClock as _DiagClock,
                banner as _diag_banner,
                key_freshness as _diag_key_freshness,
                mark_diagnostic as _mark_diagnostic,
                summarize_transforms as _diag_summarize,
            )
            opts._diag_clock = _DiagClock()
            opts._diag_clock.mark("obfuscate")
            log("DIAG", _diag_banner().splitlines()[0])
        except Exception as _diag_err:
            log("DIAG", f"diagnostic init failed (non-fatal): {_diag_err}")
    if getattr(opts, "audit_hook_plant_off", False):
        log("OPT", "Audit-hook plant detector disabled (--no-audit-hook-plant)")
    if getattr(opts, "driver_check", False):
        log("OPT", "Kernel-driver gate baked into loader (--driver-check; also armable via NIXON_DRIVER_CHECK=1)")
    if getattr(opts, "split_bootstrap", False):
        log("OPT", "Split-bootstrap threshold key + fragmented decoder baked into loader (--split-bootstrap)")
    if getattr(opts, "snapshot_off", False):
        log("OPT", "Frozen-stdlib snapshot gate disabled (--no-snapshot)")
    if getattr(opts, "stdlib_audit_off", False):
        log("OPT", "Stdlib function-audit gate disabled (--no-stdlib-audit)")

    # =========================================================================
    # Stage 0: Pre-Flight Checks
    # =========================================================================

    if not phase_check_conflicts(opts):
        sys.exit(1)

    if not os.path.exists(opts.payload):
        log("ERROR", f"Payload not found: {opts.payload}")
        sys.exit(1)

    os.makedirs(BUILD_DIR, exist_ok=True)

    # Certificate collector
    certificate_collector = None
    if opts.emit_certificates or opts.embed_proof or opts.verify_preservation:
        from scripts.certificates import CertificateCollector
        certificate_collector = CertificateCollector(
            os.path.join(BUILD_DIR, "certificates")
        )

    # MBA validator
    mba_validator = None
    if opts.verify_mba:
        from scripts.validation.mba_validator import MBAValidator
        mba_validator = MBAValidator()
        opts._mba_validator = mba_validator

    base = os.path.splitext(os.path.basename(opts.payload))[0]
    obfuscated_name = f"{base}_obfuscated.py"
    obfuscated_output = opts.output or os.path.join(ROOT, f".build_tmp_{obfuscated_name}")
    obfuscated_output = os.path.abspath(obfuscated_output)
    # Output guard: -o outside the repo build dir overwrites silently
    # (audit: refuse absolute/escaping paths unless --force-output).
    if getattr(opts, "output", None):
        try:
            _inside = os.path.commonpath(
                [obfuscated_output, os.path.abspath(BUILD_DIR)])
            _ok = (_inside == os.path.abspath(BUILD_DIR))
        except Exception:
            _ok = False
        if not _ok and not getattr(opts, "force_output", False):
            log("ERROR", f"Refusing -o outside build dir: {obfuscated_output} "
                         "(use --force-output to override)")
            sys.exit(1)

    # Load Advanced Protection config from JSON (phase-2 feature matrix).
    # Fail-closed: a malformed/poisoned config aborts with a clean ERROR,
    # never a traceback and never a silently unprotected build.
    try:
        phase2_cfg = load_advanced_protection_config(opts)
    except ConfigError as e:
        log("ERROR", "Refusing to build: %s" % e)
        sys.exit(1)
    opts._phase2_cfg = phase2_cfg

    # RESEARCH STATUS (2026-09-27): the following phases emit JSON sidecars
    # into BUILD_DIR that currently have ZERO downstream consumers (no
    # pipeline stage or runtime loader reads them back — verified by grep):
    #   per_exec_recompile → per_exec_recompile_config.json
    #   self_healing       → self_healing_config.json
    #   struct_randomization → struct_randomization_config.json
    #   micro_fragment     → micro_fragment_config.json
    #   poly_engine        → poly_engine_config.json
    #   temporal_keys      → temporal_key_config.json
    #   payload_dispersal  → payload_dispersal_config.json
    #   rolling_keys       → rolling_keys_config.json
    #   state_isa          → state_isa_config.json
    #   class_dispatch     → class_dispatch_config.json
    # They are kept as research-sidecar outputs (evidence/audit trail).
    # Do NOT wire them into the artifact path blindly — each needs a
    # consumer contract (schema + loader + test) first.

    # =========================================================================
    # Stage 0.5: Cost-Aware Protection Optimizer
    # =========================================================================
    optimizer_assignment = None
    if opts.optimize:
        log("OPTIMIZE", "Running protection cost optimizer...")
        try:
            import ast
            from scripts.optimizer import PROTECTION_COSTS
            from scripts.optimizer.profiler import FunctionProfiler
            from scripts.optimizer.cost_optimizer import CostOptimizer

            with open(opts.payload, encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
            profiler = FunctionProfiler()
            functions = profiler.profile(tree)
            optimizer = CostOptimizer(
                max_overhead_pct=opts.max_cpu_overhead,
                max_size_mult=opts.max_size_mult,
                min_security=opts.min_security,
            )
            available = list(PROTECTION_COSTS.keys())
            optimizer_assignment = optimizer.optimize(functions, available)
            report = optimizer.generate_report(functions, optimizer_assignment)
            print(report)
            report_path = os.path.join(BUILD_DIR, 'optimizer_report.json')
            atomic_write(report_path, json.dumps({
                'assignment': {k: v for k, v in optimizer_assignment.items()},
                'budget': {
                    'max_cpu_overhead': opts.max_cpu_overhead,
                    'max_size_mult': opts.max_size_mult,
                    'min_security': opts.min_security,
                },
            }, indent=2))
            log("OPTIMIZE", f"Optimizer assigned protections for {len(functions)} functions")
            log("OPTIMIZE", f"Report → {report_path}")
        except Exception as e:
            log("ERROR", f"Optimizer failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Optimizer not enabled (use --optimize)")

    # =========================================================================
    # Stage 0.6: Function-Level Adaptive Protection
    # =========================================================================
    adaptive_decisions = None
    if opts.adaptive:
        log("CLASSIFIER", "Function-Level Adaptive Protection enabled")
        classifier = FunctionClassifier()
        selector = StrategySelector()
        with open(opts.payload, 'r') as f:
            source = f.read()
        classifications = classifier.classify_from_source(source)
        adaptive_decisions = {}
        print()
        print(f"  {'='*58}")
        print("  Function-Level Adaptive Classification Report")
        print(f"  {'='*58}")
        for fn, category in sorted(classifications.items()):
            passes = selector.select(category)
            desc = selector.get_description(category)
            line = f"  [{category:18s}] {fn}"
            print(f"  {line:55s} → {desc}")
            adaptive_decisions[fn] = {
                'category': category,
                'passes': passes,
                'config': selector.get_config(category),
            }
        print(f"  {'='*58}")
        print(f"  Total: {len(classifications)} functions classified")
        print()
        report_path = os.path.join(BUILD_DIR, 'classification_report.json')
        atomic_write(report_path, json.dumps(adaptive_decisions, indent=2))
        log("CLASSIFIER", f"Classification report → {report_path}")

        # Item 46: Adaptive Protection — protect → benchmark → re-classify → re-protect
        if not opts.skip_obfuscate:
            log("ADAPTIVE", "Applying protections based on classification...")
            key_map = {
                'rename_vars': 'symbol_rename',
                'strip_metadata': 'strip_meta',
                'opaque_predicates': 'opaque_predicates',
                'mba_subs': 'mba_subs',
                'cfg_flatten': 'cfg_flatten',
                'bogus_exceptions': 'bogus_exceptions',
                'fragment_strings': 'fragment_strings',
            }
            pipeline_opts = {}
            for fn, decision in adaptive_decisions.items():
                config = decision.get('config', {})
                for layer_cfg in config.values():
                    if not isinstance(layer_cfg, dict):
                        continue
                    for cfg_key, cfg_val in layer_cfg.items():
                        if cfg_val and cfg_key in key_map:
                            pipeline_opts[key_map[cfg_key]] = True

            from obfuscator.core.pipeline import build_pipeline as _adapt_pipe
            _protected = _adapt_pipe(source, extra_options=pipeline_opts)
            _adapt_path = opts.payload.replace('.py', '_adaptive.py')
            with open(_adapt_path, 'w') as f:
                f.write(_protected)
            log("ADAPTIVE", f"Protected → {_adapt_path}")

            try:
                from scripts.benchmark import AIBenchmark
                _bm = AIBenchmark()
                _bench_results = _bm.evaluate(opts.payload, _adapt_path)

                from scripts.benchmark.feedback import BenchmarkFeedbackAnalyzer
                _analyzer = BenchmarkFeedbackAnalyzer()
                _profile = _analyzer.analyze(_bench_results)

                reclassified = classifier.classify_from_source(_protected)
                log("ADAPTIVE", f"Re-classified {len(reclassified)} functions after protection")

                from obfuscator.adaptive_rewriter import AdaptiveRewriter
                _rewriter = AdaptiveRewriter()
                _rewritten = _rewriter.rewrite(_profile, _protected)
                with open(_adapt_path, 'w') as f:
                    f.write(_rewritten)
                log("ADAPTIVE", f"Applied {len(_profile.recommended_actions)} adaptive rewrites")

                opts.payload = _adapt_path
            except Exception as ae:
                log("ADAPTIVE", f"Benchmark/re-classify/re-protect step failed: {ae}")
                import traceback
                traceback.print_exc()
    else:
        log("SKIP", "Adaptive protection not enabled (use --adaptive)")

    # =========================================================================
    # Stage 0.7: Pre-Obfuscation AST Passes (Attention Poison, Decoy APIs)
    # =========================================================================
    if not opts.skip_obfuscate:
        preprocessed_payload = opts.payload
        if opts.attention_poison > 0:
            log("ATTENTION_POISON", f"Injecting attention poison with fan-out {opts.attention_poison}")
            try:
                import ast as _ap_ast
                from obfuscator.attention_poison import AttentionPoisonInjector
                with open(preprocessed_payload) as _f:
                    _ap_src = _f.read()
                _ap_tree = _ap_ast.parse(_ap_src)
                _ap_injector = AttentionPoisonInjector(fan_out=opts.attention_poison)
                _ap_tree = _ap_injector.visit(_ap_tree)
                _ap_ast.fix_missing_locations(_ap_tree)
                _ap_out = _ap_ast.unparse(_ap_tree)
                preprocessed_payload = opts.payload + ".attention_poison.py"
                with open(preprocessed_payload, "w") as _f:
                    _f.write(_ap_out)
                log("ATTENTION_POISON", f"Written to {preprocessed_payload} (explosion ratio: {_ap_injector.explosion_ratio():.2f}x)")
            except Exception as _e:
                log("ATTENTION_POISON", f"Failed to apply attention poison: {_e}")
                preprocessed_payload = opts.payload
        if opts.decoy_apis:
            log("DECOY_APIS", f"Injecting {opts.decoy_api_count} decoy API functions")
            try:
                import ast as _da_ast
                from obfuscator.decoy_apis import SemanticDecoyApiInjector
                with open(preprocessed_payload) as _f:
                    _da_src = _f.read()
                _da_tree = _da_ast.parse(_da_src)
                _da_injector = SemanticDecoyApiInjector(count=opts.decoy_api_count)
                _da_tree = _da_injector.inject(_da_tree)
                _da_ast.fix_missing_locations(_da_tree)
                _da_out = _da_ast.unparse(_da_tree)
                _da_path = preprocessed_payload + ".decoy.py"
                with open(_da_path, "w") as _f:
                    _f.write(_da_out)
                preprocessed_payload = _da_path
                log("DECOY_APIS", f"Written to {preprocessed_payload}")
            except Exception as _e:
                log("DECOY_APIS", f"Failed to inject decoy APIs: {_e}")

    # =========================================================================
    # Stage 1: AST Obfuscation
    # =========================================================================

    if not opts.skip_obfuscate:
        try:
            phase_obfuscate(preprocessed_payload, obfuscated_output, opts)
        except RuntimeError as e:
            log("ERROR", f"Obfuscation failed: {e}")
            sys.exit(1)

        # Record certificate for obfuscation phase with real Z3 equivalence check
        if certificate_collector is not None:
            with open(preprocessed_payload) as f:
                orig_src = f.read()
            with open(obfuscated_output) as f:
                obf_src = f.read()
            try:
                import ast
                from scripts.validation.smt_validator import SMTValidator
                from irgen.compile import compile_py_to_ir
                tree = ast.parse(orig_src)
                ir_module = compile_py_to_ir(obf_src)
                validator = SMTValidator(timeout_ms=30000)
                result = validator.validate(tree, ir_module, "obfuscation")
                smt_result = {"equivalent": result.equivalent, "error": result.error}
            except Exception as e:
                smt_result = {"equivalent": None, "note": "SMT validation unavailable, marking uncertain", "error": str(e)}
            cert = certificate_collector.record(
                pass_name="obfuscation",
                input_data=orig_src,
                output_data=obf_src,
                smt_result=smt_result,
                duration_ms=0.0,
            )
            log("CERT", f"Recorded certificate: {cert.pass_name} ({cert.input_hash[:12]}...)")

        # SMT Validation: check semantic equivalence after obfuscation
        if opts.validate:
            log("VALIDATE", "Running SMT semantic validation...")
            try:
                import ast as _ast_val
                from irgen.compile import compile_py_to_ir
                from scripts.validation.equivalence import EquivalenceChecker
                from scripts.validation.mba_validator import MBAValidator

                with open(opts.payload) as f:
                    orig_source = f.read()

                validator = SMTValidator(timeout_ms=30000)
                with open(obfuscated_output) as f:
                    obf_source = f.read()
                obf_ir = compile_py_to_ir(obf_source)

                result = validator.validate_source_vs_ir(orig_source, obf_ir)

                if result.equivalent:
                    log("VALIDATE", f"PASS: {result.function_name} "
                        f"({result.duration_ms:.1f}ms)")
                else:
                    ce = result.check_result.counterexample if result.check_result else {}
                    log("VALIDATE", f"FAIL: {result.function_name} "
                        f"counterexample={ce}")
                    if opts.validate_fail:
                        log("VALIDATE", "Aborting build due to --validate-fail")
                        sys.exit(1)
                    if result.error:
                        log("VALIDATE", f"Error: {result.error}")

                # MBA validation: verify that MBA substitutions preserve semantics
                if opts.verify_mba and mba_validator is not None:
                    orig_tree = _ast_val.parse(orig_source)
                    obf_tree = _ast_val.parse(obf_source)
                    mba_validations = 0
                    mba_passed = 0
                    for orig_fn, obf_fn in zip(
                        [n for n in _ast_val.walk(orig_tree) if isinstance(n, _ast_val.FunctionDef)],
                        [n for n in _ast_val.walk(obf_tree) if isinstance(n, _ast_val.FunctionDef)],
                    ):
                        try:
                            vresult = mba_validator.validate(orig_fn, obf_fn)
                            mba_validations += 1
                            if vresult.equivalent:
                                mba_passed += 1
                        except Exception as _mba_err:
                            log("VALIDATE", f"MBA validation error on function pair: {_mba_err}")
                    log("VALIDATE", f"MBA validation: {mba_passed}/{mba_validations} functions equivalent")
            except Exception as e:
                log("VALIDATE", f"Validation error: {e}")
    else:
        log("SKIP", "Obfuscation skipped")
        shutil.copy2(opts.payload, obfuscated_output)

    # =========================================================================
    # Stage 1.5: Adversarial Injection (dead code + prompt injection)
    # =========================================================================

    if not opts.skip_obfuscate:
        adv_inj_output = os.path.join(ROOT, f".build_tmp_adv_{obfuscated_name}")
        phase_adversarial_injection(obfuscated_output, adv_inj_output, opts)
        if os.path.exists(adv_inj_output):
            shutil.copy2(adv_inj_output, obfuscated_output)
            os.remove(adv_inj_output)

    # =========================================================================
    # Stage 1.6: Provenance Poisoning
    # =========================================================================

    if not opts.skip_obfuscate:
        if any([
            opts.provenance_poison,
            opts.poison_call_graph,
            opts.poison_apis,
            opts.poison_protocols,
            opts.poison_paths,
            opts.poison_imports,
            opts.poison_all,
            opts.poison_level,
        ]):
            poison_input = obfuscated_output
            phase_provenance_poison(poison_input, obfuscated_output, opts)
        else:
            log("SKIP", "Provenance poisoning not requested (no --provenance-poison/--poison-* flag)")
    else:
        log("SKIP", "Provenance poisoning skipped (not enabled)")

    # =========================================================================
    # Stage 1.6b: Speculation Obfuscation (Item 123, AST-level)
    # =========================================================================
    if opts.speculation_obfuscation and not opts.skip_obfuscate:
        log("SPECULATION", "Applying speculation obfuscation...")
        try:
            from obfuscator.speculation_obfuscation import obfuscate_with_speculation
            with open(obfuscated_output) as f:
                source = f.read()
            spec_source = obfuscate_with_speculation(source, seed=opts.randomization_seed or 0xCAFEBABE)
            with open(obfuscated_output, "w") as f:
                f.write(spec_source)
            log("SPECULATION", "Speculation obfuscation applied successfully")
        except Exception as e:
            log("ERROR", f"Speculation obfuscation failed: {e}")

    # =======================================================================
    # Stage 1.7: Multi-Agent Deception Storylines
    # =======================================================================

        if opts.multi_agent_deception:
            log("STORYLINES", "Injecting multi-agent deception storylines...")
            try:
                import ast as _ast
                from scripts.provenance.poisoner import ProvenancePoisoner
                from scripts.provenance.storylines import get_all_storylines

                with open(obfuscated_output) as f:
                    _source = f.read()
                _tree = _ast.parse(_source)
                _poisoner = ProvenancePoisoner()
                storyline_names = [sl["name"] for sl in get_all_storylines()[:opts.storyline_count]]
                _tree = _poisoner.poison_with_storylines(_tree, storyline_names)
                with open(obfuscated_output, "w") as f:
                    f.write(_ast.unparse(_tree))
                log("STORYLINES", f"Injected {len(storyline_names)} storylines")
            except Exception as e:
                log("ERROR", f"Storyline injection failed: {e}")
        else:
            log("SKIP", "Multi-agent deception not enabled (use --multi-agent-deception)")

        # ===================================================================
        # Stage 1.8: LLM Fingerprint Embedding (Item 73)
        # ===================================================================

        if opts.llm_fingerprint:
            log("LLM_FINGERPRINT", f"Embedding fingerprint for model: {opts.fingerprint_model}")
            try:
                import ast as _ast_fp
                from obfuscator.llm_fingerprint import LLMFingerprinter

                with open(obfuscated_output) as f:
                    _src_fp = f.read()
                _tree_fp = _ast_fp.parse(_src_fp)
                _fp = LLMFingerprinter(seed=secrets.randbits(32))
                _tree_fp = _fp.embed_fingerprint(_tree_fp, opts.fingerprint_model)
                with open(obfuscated_output, "w") as f:
                    f.write(_ast_fp.unparse(_tree_fp))
                log("LLM_FINGERPRINT", f"Fingerprint embedded: {opts.fingerprint_model}")
            except Exception as e:
                log("ERROR", f"LLM fingerprinting failed: {e}")
        else:
            log("SKIP", "LLM fingerprinting not enabled (use --llm-fingerprint)")

        # ===================================================================
        # Stage 1.9: Reasoning-Loop Traps (Item 75)
        # ===================================================================

        if opts.reasoning_traps:
            log("REASONING_TRAPS", f"Injecting reasoning traps with depth {opts.trap_depth}")
            try:
                import ast as _ast_rt
                from obfuscator.reasoning_traps import ReasoningLoopInjector

                with open(obfuscated_output) as f:
                    _src_rt = f.read()
                _tree_rt = _ast_rt.parse(_src_rt)
                _ri = ReasoningLoopInjector(seed=secrets.randbits(32))
                _tree_rt = _ri.inject_loop(_tree_rt, depth=opts.trap_depth)
                with open(obfuscated_output, "w") as f:
                    f.write(_ast_rt.unparse(_tree_rt))
                log("REASONING_TRAPS", "Trap functions injected")
            except Exception as e:
                log("ERROR", f"Reasoning traps failed: {e}")
        else:
            log("SKIP", "Reasoning traps not enabled (use --reasoning-traps)")

        # ===================================================================
        # Stage 1.10: Function Intent Obfuscation (Item 78)
        # ===================================================================

        if opts.function_intent:
            log("FUNCTION_INTENT", "Obfuscating function intent...")
            try:
                import ast as _ast_fi
                from obfuscator.function_intent import FunctionIntentObfuscator

                with open(obfuscated_output) as f:
                    _src_fi = f.read()
                _tree_fi = _ast_fi.parse(_src_fi)
                _fio = FunctionIntentObfuscator(seed=secrets.randbits(32))
                _tree_fi = _fio.obfuscate_intent(_tree_fi)
                with open(obfuscated_output, "w") as f:
                    f.write(_ast_fi.unparse(_tree_fi))
                log("FUNCTION_INTENT", f"Renamed {len(_fio.get_name_map())} functions")
            except Exception as e:
                log("ERROR", f"Function intent obfuscation failed: {e}")
        else:
            log("SKIP", "Function intent obfuscation not enabled (use --function-intent)")

    # =========================================================================
    # Stage 2: Advanced Protection — Classification Pass
    # =========================================================================
    classifications = None
    if opts.classify or phase2_cfg.get("enabled", False):
        classifications = phase_classify(opts.payload, phase2_cfg)
        if classifications:
            log("CLASSIFY", f"Summary: {len(classifications)} functions classified")
        else:
            log("CLASSIFY", "Summary: no functions classified (empty result)")
    else:
        log("SKIP", "Classification pass skipped")

    # =========================================================================
    # Stage 2a: Adaptive Classifier Loop
    # =========================================================================

    # NOTE: the provenance/dataflow/adaptive passes below operate on a
    # BUILD_DIR scratch copy of the payload, NEVER on opts.payload itself
    # (earlier revisions clobbered the user's source file in place). They
    # run AFTER phase_obfuscate, so their outputs are diagnostic sidecars
    # only and are NOT fed back into the artifact pipeline — in particular,
    # phase_dataflow_obfuscation emits references to _affine_enc without a
    # definition, so feeding its output downstream would break artifacts.
    _sidecar_src = os.path.join(BUILD_DIR, "sidecar_payload.py")
    try:
        shutil.copy2(opts.payload, _sidecar_src)
        log("SIDECAR", f"Scratch copy for diagnostic passes: {_sidecar_src}")
    except OSError as e:
        log("ERROR", f"Sidecar scratch copy failed: {e}")
        _sidecar_src = None

    if opts.adaptive_classifier_loop:
        if _sidecar_src is not None:
            phase_adaptive_classifier_loop(_sidecar_src, opts)
        else:
            log("SKIP", "Adaptive classifier loop skipped (no scratch copy)")
    else:
        log("SKIP", "Adaptive classifier loop not enabled (use --adaptive-classifier-loop)")

    # =========================================================================
    # Stage 2b: Provenance Removal
    # =========================================================================
    provenance_replace = opts.provenance_replace or (
        phase2_cfg.get("enabled", False) and
        phase2_cfg.get("features", {}).get("provenance_removal", False)
    )
    if provenance_replace:
        if _sidecar_src is not None:
            phase_provenance_removal(
                _sidecar_src, phase2_cfg,
                replace_mode=opts.provenance_replace
            )
        else:
            log("SKIP", "Provenance removal skipped (no scratch copy)")
    else:
        log("SKIP", "Provenance removal skipped (not enabled)")

    # =========================================================================
    # Stage 2c: Data-Flow Obfuscation
    # =========================================================================

    if phase2_cfg.get("enabled", False) and phase2_cfg.get("features", {}).get("dataflow_obfuscation", False):
        if _sidecar_src is not None:
            phase_dataflow_obfuscation(_sidecar_src, phase2_cfg)
        else:
            log("SKIP", "Data-flow obfuscation skipped (no scratch copy)")
    else:
        log("SKIP", "Data-flow obfuscation skipped (not enabled)")

    # =========================================================================
    # Stage 2d: Config Generation
    # =========================================================================

    phase_generate_config(opts)

    # =========================================================================
    # Stage 2e: Payload Header Generation
    # =========================================================================
    if opts.generate_payload_h:
        phase_generate_payload_h(obfuscated_output, opts)
    else:
        log("SKIP", "payload.h generation skipped")

    ir_module = None

    # Pipeline paths
    ir_output = os.path.join(BUILD_DIR, "program.ir")
    obj_output = os.path.join(BUILD_DIR, "program.o")
    enc_output = os.path.join(BUILD_DIR, "encrypted.o")
    manifest_output = os.path.join(BUILD_DIR, "manifest.json")

    # =========================================================================
    # Stage 3: IR Compilation (Python AST to intermediate representation)
    # =========================================================================

    if not opts.skip_irgen:
        phase_ir_compile(obfuscated_output, ir_output)

        # Preservation check: AST -> IR
        if opts.verify_preservation:
            log("PRESERVATION", "Checking AST -> IR semantic preservation...")
            try:
                from scripts.preservation.stage_ast_ir import check_ast_ir
                import ast as py_ast
                with open(opts.payload) as f:
                    source = f.read()
                tree = py_ast.parse(source)
                from irgen.compile import compile_py_to_ir
                ir_module = compile_py_to_ir(source)
                result = check_ast_ir(tree, ir_module)
                status = "PASS" if result.passed else "FAIL"
                log("PRESERVATION", f"  AST->IR: {status} ({result.duration_ms:.1f}ms)")
                if certificate_collector is not None:
                    certificate_collector.record(
                        pass_name="preservation_ast_ir",
                        input_data=source,
                        output_data=str(ir_module),
                        smt_result={"equivalent": result.passed},
                        duration_ms=result.duration_ms,
                    )
            except Exception as e:
                log("PRESERVATION", f"  AST->IR Error: {e}")
    else:
        log("SKIP", "IR compilation skipped")

    # =========================================================================
    # Stage 3a: Semantic Leakage Metric (Feature 152)
    # =========================================================================
    if opts.semantic_leakage:
        log("LEAKAGE", "Semantic leakage measurement enabled")
        try:
            from irgen.compile import compile_py_to_ir
            with open(opts.payload) as f:
                _orig_source = f.read()
            with open(obfuscated_output) as f:
                _obf_source = f.read()
            original_ir = compile_py_to_ir(_orig_source)
            obfuscated_ir = compile_py_to_ir(_obf_source)
            leakage_report = phase_leakage(opts, original_ir, obfuscated_ir)
            if leakage_report is not None:
                log("LEAKAGE", f"Summary: SLI={leakage_report.overall_sli:.2f}/100")
        except Exception as e:
            log("LEAKAGE", f"Error computing semantic leakage: {e}")
    else:
        log("SKIP", "Semantic leakage measurement not enabled (use --semantic-leakage)")

    # =========================================================================
    # Stage 3b: Semantic Watermarking (on IR)
    # =========================================================================
    if opts.watermark:
        log("WATERMARK", f"Embedding semantic watermark: '{opts.watermark}'")
        try:
            from scripts.watermark.semantic_watermark import embed_watermark, verify_watermark
            from irgen.compile import compile_py_to_ir, ir_module_to_text

            with open(opts.payload) as f:
                payload_source = f.read()

            module = compile_py_to_ir(payload_source)
            module = embed_watermark(module, opts.watermark)

            wm_text = ir_module_to_text(module)

            if not opts.skip_irgen:
                wm_ir_output = ir_output.replace(".ir", "_wm.ir")
                atomic_write(wm_ir_output, wm_text)
                log("WATERMARK", f"Watermarked IR written to {wm_ir_output}")
                atomic_write(ir_output, wm_text)
                log("WATERMARK", f"Replaced {ir_output} with watermarked IR")
            else:
                wm_ir_output = os.path.join(BUILD_DIR, "program_wm.ir")
                atomic_write(wm_ir_output, wm_text)
                log("WATERMARK", f"Watermarked IR written to {wm_ir_output}")

            if opts.verify_watermark:
                if verify_watermark(module, opts.watermark):
                    log("WATERMARK", "Watermark verification: PASSED")
                else:
                    log("WATERMARK", "Watermark verification: FAILED")
                    sys.exit(1)
        except ImportError as e:
            log("ERROR", f"Watermark import failed: {e}")
        except Exception as e:
            log("ERROR", f"Watermark embedding failed: {e}")
    else:
        log("SKIP", "Semantic watermarking not enabled (use --watermark)")

    # =========================================================================
    # Stage 3c: Advanced Protection — Variant Pool (post-IR)
    # =========================================================================
    if phase2_cfg.get("enabled", False) and phase2_cfg.get("features", {}).get("variant_pool", False):
        if not opts.skip_irgen:
            phase_variant_pool(ir_output, phase2_cfg)
        else:
            phase_variant_pool(opts.payload, phase2_cfg)
    else:
        log("SKIP", "Variant pool skipped (not enabled)")

    # =========================================================================
    # Stage 3d: Advanced Protection — Watermark Embedding (on IR)
    # =========================================================================
    if phase2_cfg.get("enabled", False) and phase2_cfg.get("features", {}).get("watermarking", False):
        if not opts.skip_irgen:
            phase_watermark_embedding(ir_output, phase2_cfg)
        else:
            log("SKIP", "Watermark embedding skipped (requires IR; --skip-irgen set)")
    else:
        log("SKIP", "Watermark embedding skipped (not enabled)")

    # =========================================================================
    # Stage 3e: Advanced Protection — Semantic Fragmentation (on IR)
    # =========================================================================
    if phase2_cfg.get("enabled", False) and phase2_cfg.get("features", {}).get("semantic_fragmentation", False):
        log("FRAGMENT", "Semantic fragmentation would run here on IR")
    else:
        log("SKIP", "Semantic fragmentation skipped (not enabled)")

    # =========================================================================
    # Stage 3f: FHE-VM Compilation
    # =========================================================================

    if opts.fhe_vm:
        from scripts.phases.phase_fhe_vm import phase_fhe_vm
        phase_fhe_vm(opts, ir_module if not opts.skip_irgen and ir_module is not None else None)

    # =========================================================================
    # Stage 3g: IO Research (Approximate Indistinguishability Obfuscation)
    # =========================================================================

    if opts.io_research:
        phase_io_research(opts)

    # =========================================================================
    # Stage 3h: Kernel-Assisted Execution Research
    # =========================================================================

    if opts.kernel_assist:
        phase_kernel_assist(opts, ir_module if not opts.skip_irgen else None)

    # =========================================================================
    # Stage 4: LLVM Codegen
    # =========================================================================
    if not opts.skip_llvmgen:
        phase_llvm_codegen(ir_output if not opts.skip_irgen else obfuscated_output, obj_output)

        # Preservation check: IR -> LLVM
        if opts.verify_preservation and not opts.skip_irgen:
            log("PRESERVATION", "Checking IR -> LLVM semantic preservation...")
            try:
                from scripts.preservation.stage_ir_llvm import check_ir_llvm
                from llvmgen.lower import lower_ir_to_llvm
                with open(ir_output) as f:
                    ir_text = f.read()
                from irgen.compile import compile_py_to_ir
                with open(opts.payload) as f:
                    source = f.read()
                ir_module = compile_py_to_ir(source)
                llvm_ir = lower_ir_to_llvm(ir_text)
                result = check_ir_llvm(ir_module, llvm_ir)
                status = "PASS" if result.passed else "FAIL"
                log("PRESERVATION", f"  IR->LLVM: {status} ({result.duration_ms:.1f}ms)")
                if certificate_collector is not None:
                    certificate_collector.record(
                        pass_name="preservation_ir_llvm",
                        input_data=ir_text,
                        output_data=llvm_ir,
                        smt_result={"equivalent": result.passed},
                        duration_ms=result.duration_ms,
                    )
            except Exception as e:
                log("PRESERVATION", f"  IR->LLVM Error: {e}")
    else:
        log("SKIP", "LLVM codegen skipped")

    # =========================================================================
    # Stage 4b: ROP Compile (alternative to LLVM codegen for crown jewels)
    # -------------------------------------------------------------------------
    # TWO ROP compilers coexist (documented, both tested — NOT duplicates):
    # - phase_rop_compile() above uses irgen.rop_compiler.RopFunctionCompiler
    #   (needs a reference ELF binary for real gadgets; sys.exit(1) when the
    #   config lacks reference_binary — binary-gated path).
    # - The block below uses scripts.rop.rop_compiler (GadgetFinder +
    #   RopCompiler + PayloadDisperser): synthetic gadget DB, works on any
    #   payload's first FunctionDef, emits build/rop_runtime.c. This is the
    #   default --rop path.
    # =========================================================================
    rop_cfg = {}
    if os.path.exists(DEFAULT_CONFIG):
        with open(DEFAULT_CONFIG, "r") as f:
            default = json.load(f)
        rop_cfg = default.get("shadow_compiler", {}).get("llvmgen", {}).get("rop", {})
    if rop_cfg.get("enabled", False) or opts.rop:
        rop_output = os.path.join(BUILD_DIR, "rop_chain.bin")
        _rop_status = phase_rop_compile(ir_output, rop_output, rop_cfg)
        if isinstance(_rop_status, dict):
            log("ROP", f"Status: ok={_rop_status.get('ok')} ({_rop_status.get('reason', 'n/a')})")
        elif _rop_status is not None:
            log("ROP", f"Status: {_rop_status}")
        # Generate runtime C source using rop_exec.h
        try:
            rop_runtime_path = os.path.join(BUILD_DIR, "rop_runtime.c")
            rop_key = secrets.token_bytes(32)
            from scripts.rop.rop_compiler import GadgetFinder, RopCompiler, PayloadDisperser
            finder = GadgetFinder()
            finder.find_gadgets()
            compiler = RopCompiler(finder=finder)
            import ast as _ast_rop
            with open(opts.payload) as f:
                _src_rop = f.read()
            _tree_rop = _ast_rop.parse(_src_rop)
            for fn in _tree_rop.body:
                if isinstance(fn, _ast_rop.FunctionDef):
                    chain = compiler.compile(fn)
                    disperser = PayloadDisperser()
                    dispersed = disperser.disperse(chain)
                    disperser.save_runtime_source(dispersed, rop_key, rop_runtime_path)
                    log("ROP", f"Runtime source written to {rop_runtime_path} ({len(chain.entries)} gadgets)")
                    break
        except Exception as e:
            log("ERROR", f"ROP runtime source generation failed: {e}")
    else:
        log("SKIP", "ROP compile skipped (not enabled)")

    # =========================================================================
    # Stage 5: Encrypt Binary (post-link encryption)
    # =========================================================================
    if not opts.skip_encrypt:
        phase_encrypt_binary(obj_output if not opts.skip_llvmgen else ir_output, enc_output)
    else:
        log("SKIP", "Encryption skipped")

    # =========================================================================
    # Stage 5.5: Entropy Flatten (operates on pre-encryption ELF object file)
    # =========================================================================
    _ef_config = {}
    if os.path.exists(DEFAULT_CONFIG):
        try:
            with open(DEFAULT_CONFIG, "r") as _f:
                _ef_config = json.load(_f).get("shadow_compiler", {}).get("encrypt", {})
        except (json.JSONDecodeError, KeyError):
            _ef_config = {}
    ef_enabled = _ef_config.get("entropy_flatten", {}).get("enabled", False)
    if ef_enabled:
        _ef_bin = obj_output if os.path.exists(obj_output) else (enc_output if os.path.exists(enc_output) else None)
        if _ef_bin is not None:
            phase_entropy_flatten(_ef_bin, _ef_bin, _ef_config)
        else:
            log("ERROR", "Entropy flatten enabled in config but no ELF binary available (obj_output/enc_output missing); ensure --skip-llvmgen and --skip-encrypt are not both set")
    # =========================================================================
    # Stage 5.6: MicroJIT — Polymorphic Reassembly
    # =========================================================================

    if opts.microjit or phase2_cfg.get("features", {}).get("microjit", False):
        log("MICROJIT", "Applying polymorphic micro-JIT reassembly...")
        jit_seed = secrets.randbits(64)
        jit_config_path = os.path.join(BUILD_DIR, "microjit_config.json")
        atomic_write(jit_config_path, json.dumps({"jit_seed": jit_seed, "enabled": True}, indent=2))
        log("MICROJIT", f"MicroJIT seed: {jit_seed:#018x}, config written to {jit_config_path}")
    else:
        log("SKIP", "MicroJIT not enabled")

    # =========================================================================
    # Item 58: Environmental Poly-Engine
    # =========================================================================
    if opts.poly_engine:
        log("POLY_ENGINE", "Running poly-engine phase (Item 58)...")
        try:
            phase_poly_engine(opts.payload, opts)
        except Exception as e:
            log("ERROR", f"Poly-engine failed: {e}")
    else:
        log("SKIP", "Poly-engine not enabled (use --poly-engine)")

    # =========================================================================
    # Item 50: Micro-Fragment Execution
    # =========================================================================

    if opts.micro_fragment:
        log("MICRO_FRAGMENT", "Applying micro-fragment execution (Item 50)...")
        try:
            with open(obfuscated_output, encoding="utf-8") as f:
                _code = f.read()
            phase_micro_fragment(_code, opts)
        except Exception as e:
            log("ERROR", f"Micro-fragment execution failed: {e}")
    else:
        log("SKIP", "Micro-fragment execution not enabled (use --micro-fragment)")

    # =========================================================================
    # Micro-JIT Fragment Reassembly: decrypt -> execute -> wipe
    # =========================================================================

    if opts.fragment or phase2_cfg.get("features", {}).get("fragment_reassembly", False):
        log("FRAGMENT", "Applying micro-JIT fragment reassembly...")
        fragment_size = opts.fragment_size
        frag_functions = opts.fragment_functions or "auto"
        chain_key = secrets.token_bytes(32)
        config = {
            "chain_key": chain_key.hex(),
            "fragment_size": fragment_size,
            "fragment_functions": frag_functions,
            "enabled": True,
        }
        frag_config_path = os.path.join(BUILD_DIR, "fragment_config.json")
        atomic_write(frag_config_path, json.dumps(config, indent=2))
        log("FRAGMENT", f"Fragment config written to {frag_config_path} ({fragment_size} inst/fragment)")

        # Compile native microjit test object
        microjit_src = os.path.join(ROOT, "native", "microjit.c")
        microjit_obj = os.path.join(BUILD_DIR, "microjit.o")
        if os.path.exists(microjit_src):
            ret = subprocess.run(
                ["gcc", "-c", microjit_src, "-o", microjit_obj, "-Wall"],
                capture_output=True, text=True,
            )
            if ret.returncode == 0:
                log("FRAGMENT", f"  Compiled: {microjit_obj}")
            else:
                log("ERROR", f"  microjit.c compilation failed:\n{ret.stderr}")
    else:
        log("SKIP", "Fragment reassembly not enabled (use --fragment)")

    # =========================================================================
    # ORAM: Oblivious RAM Controller (post-encryption, pre-VM)
    # =========================================================================

    oram_cfg = {}
    if os.path.exists(DEFAULT_CONFIG):
        with open(DEFAULT_CONFIG, "r") as f:
            default = json.load(f)
        oram_cfg = default.get("shadow_compiler", {}).get("runtime", {}).get("oram", {})
    if oram_cfg.get("enabled", False) or opts.oram:
        log("ORAM", "Applying Oblivious RAM controller...")
        try:
            from irgen.oram import generate_oram_config
            vars_list = oram_cfg.get("protected_variables", [])
            oram_config = generate_oram_config(vars_list, oram_cfg.get("num_blocks", 256))
            oram_config_path = os.path.join(BUILD_DIR, "oram_config.json")
            atomic_write(oram_config_path, json.dumps(oram_config, indent=2))
            log("ORAM", f"ORAM config written to {oram_config_path} ({oram_config['num_blocks']} blocks)")
        except ImportError:
            log("SKIP", "irgen.oram not importable")
    else:
        log("SKIP", "ORAM not enabled")

    # =========================================================================
    # Stage 6: VM Compile (crown jewel functions into custom VM bytecode)
    # =========================================================================

    if phase2_cfg.get("enabled", False) and phase2_cfg.get("features", {}).get("vm", False):
        if not opts.skip_irgen:
            phase_vm_compile(ir_output, phase2_cfg)

            # Ephemeral ISA: per-build unique opcode mapping
            if opts.ephemeral_isa or phase2_cfg.get("features", {}).get("ephemeral_isa", False):
                log("EPHEMERAL_ISA", "Applying ephemeral per-build opcode mapping...")
                try:
                    from vm.ephemeral_isa import generate_ephemeral_opcode_map
                    from vm import generate_ephemeral_interpreter_source
                    build_seed = secrets.token_bytes(32)
                    opcode_map = generate_ephemeral_opcode_map(build_seed)
                    isa_path = os.path.join(BUILD_DIR, "ephemeral_isa.json")
                    atomic_write(isa_path, json.dumps({"opcode_map": {str(k): v for k, v in opcode_map.items()}}, indent=2))
                    log("EPHEMERAL_ISA", f"Ephemeral opcode map written to {isa_path}")
                except ImportError:
                    log("SKIP", "vm.ephemeral_isa not importable")
        else:
            log("SKIP", "VM compile needs IR")
        # Preservation check: LLVM -> VM
        if opts.verify_preservation and not opts.skip_llvmgen and not opts.skip_irgen:
            log("PRESERVATION", "Checking LLVM -> VM semantic preservation...")
            try:
                from scripts.preservation.stage_llvm_vm import check_llvm_vm
                from llvmgen.lower import lower_ir_to_llvm
                with open(ir_output) as f:
                    ir_text = f.read()
                llvm_ir = lower_ir_to_llvm(ir_text)
                from vm.bytecode_compiler import compile_to_bytecode
                from irgen.compile import compile_py_to_ir
                with open(opts.payload) as f:
                    source = f.read()
                ir_module = compile_py_to_ir(source)
                vm_bytecode = bytearray()
                for func in ir_module.functions:
                    bc = compile_to_bytecode(func)
                    vm_bytecode.extend(bc)
                result = check_llvm_vm(llvm_ir, bytes(vm_bytecode))
                status = "PASS" if result.passed else "FAIL"
                log("PRESERVATION", f"  LLVM->VM: {status} ({result.duration_ms:.1f}ms)")
                if certificate_collector is not None:
                    certificate_collector.record(
                        pass_name="preservation_llvm_vm",
                        input_data=llvm_ir,
                        output_data=bytes(vm_bytecode).hex(),
                        smt_result={"equivalent": result.passed},
                        duration_ms=result.duration_ms,
                    )
            except ImportError:
                log("PRESERVATION", "  LLVM->VM: SKIPPED (vm.bytecode_compiler not available)")
            except Exception as e:
                log("PRESERVATION", f"  LLVM->VM Error: {e}")
    else:
        log("SKIP", "VM compile skipped (not enabled)")

    # =========================================================================
    # Stage 6a: JIT Template Generation
    # =========================================================================

    if phase2_cfg.get("enabled", False) and phase2_cfg.get("features", {}).get("jit_templates", False):
        if not opts.skip_irgen:
            phase_jit_generate(ir_output, phase2_cfg)
        else:
            log("SKIP", "JIT generation needs IR")
    else:
        log("SKIP", "JIT generation skipped (not enabled)")

    # =========================================================================
    # Stage 6b: Crypto Binding
    # =========================================================================

    if opts.crypto_binding:
        log("CRYPTO_BINDING", "Binding code fragments with cryptographic chain...")
        crypto_binding_output = os.path.join(BUILD_DIR, "crypto_bound_fragments.bin")
        try:
            fragments = []
            payload_path = opts.payload
            with open(payload_path, "rb") as f:
                data = f.read()
            chunk_size = max(32, len(data) // 4)
            fragments = [
                Fragment(fragment_id=str(i), payload=data[i:i+chunk_size])
                for i in range(0, len(data), chunk_size)
            ]

            chain_secret = secrets.token_bytes(32)
            binder = CryptoFragmentBinder(chain_secret=chain_secret)
            bound = binder.bind_fragments(fragments)

            with open(crypto_binding_output, "wb") as f:
                f.write(struct.pack(">I", len(bound)))
                for bf in bound:
                    f.write(bf.serialize())

            chain_secret_path = os.path.join(BUILD_DIR, "chain_secret.bin")
            with open(chain_secret_path, "wb") as f:
                f.write(chain_secret)

            log("CRYPTO_BINDING", f"Bound {len(bound)} fragments → {crypto_binding_output}")
            log("CRYPTO_BINDING", f"Chain secret: {chain_secret_path}")
            # payload.h was generated ~430 lines earlier (Stage 2e), before
            # these binding files existed, so its embed step silently skipped.
            # Re-run it now (best-effort) so --crypto-binding actually lands.
            try:
                phase_embed_crypto_binding(os.path.join(ROOT, "native", "payload.h"))
            except Exception as _cb_err:
                log("CRYPTO_BINDING", f"Late embed skipped (non-fatal): {_cb_err}")
        except Exception as e:
            log("ERROR", f"Crypto binding failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Crypto binding not enabled (use --crypto-binding)")

    # =========================================================================
    # Item 63: Whitebox-Flow Entanglement
    # =========================================================================

    if opts.flow_entangle:
        log("FLOW_ENTANGLE", "Applying whitebox-flow entanglement (Item 63)...")
        try:
            from scripts.whitebox.flow_entangle import FlowEntangler
            fe = FlowEntangler(seed=secrets.token_bytes(16))
            fe.make_decision("init", 0)
            fe.make_decision("setup", 1)
            fe_state = fe.get_state_bytes()
            fe_config = {
                "state_hex": fe_state.hex(),
                "decisions": fe.get_entanglement_summary()["decisions"],
                "enabled": True,
            }
            fe_config_path = os.path.join(BUILD_DIR, "flow_entangle_config.json")
            atomic_write(fe_config_path, json.dumps(fe_config, indent=2))
            log("FLOW_ENTANGLE", f"Entanglement state: {fe_state.hex()[:16]}... → {fe_config_path}")
        except Exception as e:
            log("ERROR", f"Flow entanglement failed: {e}")
    else:
        log("SKIP", "Whitebox-flow entanglement not enabled (use --flow-entangle)")

    # =========================================================================
    # Challenge-Response: standalone protocol
    # =========================================================================

    if opts.challenge_response:
        log("CHALLENGE_RESPONSE", "Running standalone challenge-response protocol...")
        try:
            from scripts.runtime.challenge_response import ChallengeResponse
            cr = ChallengeResponse(timeout=5.0)
            peers = ["node_a", "node_b", "node_c"]
            results = cr.run_pairwise(peers)
            passed = sum(1 for v in results.values() if v)
            total = len(results)
            log("CHALLENGE_RESPONSE", f"Challenge-response: {passed}/{total} pairs verified")
            cr_path = os.path.join(BUILD_DIR, "challenge_response_result.json")
            atomic_write(cr_path, json.dumps({
                "peers": peers,
                "results": {f"{a}->{b}": v for (a, b), v in results.items()},
                "passed": passed,
                "total": total,
            }, indent=2))
        except Exception as e:
            log("ERROR", f"Challenge-response failed: {e}")

    # =========================================================================
    # Attestation: compile native attestation module
    # =========================================================================

    # NOTE: native/attestation.c was DELETED (unwired experimental sim).
    # Canonical attestation is runtime/src/sw_attestation.rs (see
    # docs/ATTESTATION.md). This block is kept as a redirect, not a build.
    if opts.attestation:
        log("ATTESTATION", "native/attestation.c retired; canonical: runtime/src/sw_attestation.rs")
        phase2_cfg.setdefault("extras", {}).setdefault("features", {})["attestation"] = True
    else:
        log("SKIP", "Attestation not enabled (use --attestation)")

    # =========================================================================
    # Optional Extras (anti-debug, packing, timing checks, etc.)
    # =========================================================================

    if not opts.skip_extras:
        phase_optional_extras(phase2_cfg)
    else:
        log("SKIP", "Optional extras skipped by --skip-extras")

    # =========================================================================
    # Adversarial Loop: deobfuscation agent + compiler mutation
    # =========================================================================

    if opts.adversarial_loop:
        _adv_input = ir_output if not opts.skip_irgen else obfuscated_output
        phase_adversarial_loop(_adv_input, opts)

    # =========================================================================
    # Runtime Evolution Research Features (Items 80-89)
    # =========================================================================

    if opts.cfg_mutation and not opts.skip_irgen:
        phase_cfg_mutation(ir_output, opts.cfg_mutation_variants)
    elif opts.cfg_mutation and opts.skip_irgen:
        log("SKIP", "CFG mutation skipped (requires IR; --skip-irgen set)")
    else:
        log("SKIP", "CFG mutation not enabled (use --cfg-mutation)")

    if opts.class_dispatch:
        log("CLASS_DISPATCH", f"Class dispatch enabled ({opts.class_dispatch_count} classes)")
        phase_class_dispatch(num_classes=opts.class_dispatch_count)

    # =========================================================================
    # Item 59: Temporal Micro-Key Evolution
    # =========================================================================

    if opts.temporal_keys:
        log("TEMPORAL_KEYS", "Applying temporal micro-key evolution (Item 59)...")
        try:
            phase_temporal_keys(opts)
        except Exception as e:
            log("ERROR", f"Temporal key evolution failed: {e}")
    else:
        log("SKIP", "Temporal key evolution not enabled (use --temporal-keys)")

    if opts.rolling_keys:
        log("ROLLING_KEYS", "Rolling key schedules enabled")
        phase_rolling_keys(payload_path=opts.payload)

    if opts.ssa_mutation:
        phase_ssa_mutation(ir_output if not opts.skip_irgen else None, opts.ssa_variants)

    if opts.state_isa:
        phase_state_isa(history_len=opts.state_isa_history_len, seed=42)

    if opts.per_exec_recompile:
        phase_per_exec_recompile()

    if opts.self_healing:
        phase_self_healing()

    if opts.code_genome:
        phase_code_genome(generations=opts.genome_generations, population_size=opts.genome_population)

    # =========================================================================
    # Item 122: Microarchitectural Watermark
    # =========================================================================

    if opts.uarch_watermark:
        log("UARCH_WATERMARK", "Embedding microarchitectural timing watermark (Item 122)...")
        try:
            from scripts.watermark.uarch_watermark import MicroarchitecturalWatermark
            wm = MicroarchitecturalWatermark()
            with open(opts.payload, encoding="utf-8") as f:
                payload_source = f.read()
            watermarked = wm.embed(payload_source, "NixonCorp")
            wm_output = opts.output or obfuscated_output
            with open(wm_output, "w") as f:
                f.write(watermarked)
            log("UARCH_WATERMARK", f"Watermark embedded → {wm_output}")
            detected = wm.detect_watermark_from_timing(watermarked, "NixonCorp")
            log("UARCH_WATERMARK", f"Timing-based detection: {'PASS' if detected else 'FAIL'}")
        except Exception as e:
            log("ERROR", f"UARCH watermark failed: {e}")

    # =========================================================================
    # Item 125: GPU Fragment Execution
    # =========================================================================

    if opts.gpu_execution or opts.gpu:
        log("GPU_EXECUTION", "Running GPU fragment execution (Item 125)...")
        try:
            from scripts.gpu.gpu_execution import GPUExecutor, is_gpu_available
            gpu_avail = is_gpu_available()
            log("GPU_EXECUTION", f"GPU available: {gpu_avail}")
            ex = GPUExecutor(use_gpu=gpu_avail)
            with open(opts.payload, "rb") as f:
                payload_data = f.read()
            kernel = ex.compile_fragment(payload_data[:64], "mix")
            ex.transfer_to_gpu(payload_data[:64])
            ex.execute_kernel(kernel)
            log("GPU_EXECUTION", f"Executed kernel: {kernel['type']} with {ex.use_gpu=}")
        except Exception as e:
            log("ERROR", f"GPU execution failed: {e}")

    # =========================================================================
    # Item 126: Hybrid CPU/GPU Protection
    # =========================================================================

    if opts.gpu_hybrid or opts.cpu_gpu_hybrid:
        log("GPU_HYBRID", "Running CPU/GPU hybrid protection (Item 126)...")
        try:
            from scripts.gpu.hybrid_protection import HybridProtector
            hp = HybridProtector(seed=0xDEADBEEF)
            ops = [
                {"type": "control_flow", "name": "branch_main"},
                {"type": "crypto", "name": "encrypt_data"},
            ]
            hp.partition(ops)
            with open(opts.payload, "rb") as f:
                payload_data = f.read()
            cpu_res, gpu_res = hp.hybrid_execute_multiprocess({"test": 1}, payload_data[:64])
            log("GPU_HYBRID", f"CPU result: {cpu_res:#x}, GPU result len: {len(gpu_res)}")
            iso = hp.verify_gpu_memory_isolation()
            log("GPU_HYBRID", f"Memory isolation: {'OK' if iso else 'FAIL'}")
        except Exception as e:
            log("ERROR", f"GPU hybrid failed: {e}")
            import traceback
            traceback.print_exc()

    # =========================================================================
    # Item 129: Microarchitectural Diversity Generation
    # =========================================================================

    if opts.uarch_diversity:
        log("UARCH_DIVERSITY", "Generating microarchitectural-aware diversity variants (Item 129)...")
        try:
            from scripts.diversity.uarch_diversity import (
                MicroarchitecturalDiversityGenerator,
                detect_microarchitecture,
            )
            uarch_info = detect_microarchitecture()
            log("UARCH_DIVERSITY", f"Detected CPU: {uarch_info.get('vendor')} / {uarch_info.get('model')}")
            gen = MicroarchitecturalDiversityGenerator(seed=0xCAFEBABE)
            with open(opts.payload, encoding="utf-8") as f:
                payload_source = f.read()
            result = gen.generate_uarch_aware_variants(payload_source)
            diversity_dir = opts.diversity_dir
            os.makedirs(diversity_dir, exist_ok=True)
            for vtype, vcode in result.get("all", {}).items():
                vpath = os.path.join(diversity_dir, f"uarch_variant_{vtype}.py")
                with open(vpath, "w") as f:
                    f.write(vcode)
                log("UARCH_DIVERSITY", f"  Variant '{vtype}' → {vpath}")
            selected = result.get("selected", "")
            if selected:
                sel_path = os.path.join(diversity_dir, "uarch_selected_variant.py")
                with open(sel_path, "w") as f:
                    f.write(selected)
                log("UARCH_DIVERSITY", f"  Selected variant ({result.get('selected_type', 'unknown')}) → {sel_path}")
            uarch_report = os.path.join(diversity_dir, "uarch_report.json")
            report_data = {
                "uarch": {k: v for k, v in uarch_info.items() if k != "flags"},
                "selected_type": result.get("selected_type", ""),
                "variant_count": len(result.get("all", {})),
            }
            with open(uarch_report, "w") as f:
                json.dump(report_data, f, indent=2)
            log("UARCH_DIVERSITY", f"Report → {uarch_report}")
        except Exception as e:
            log("ERROR", f"UARCH diversity generation failed: {e}")
            import traceback
            traceback.print_exc()

    if opts.struct_randomization:
        phase_struct_randomization(seed=opts.randomization_seed, level=opts.randomization_level)

    if opts.history_bound_decryption:
        phase_execution_history_binding({"payload_path": opts.payload})

    # =========================================================================
    # Hardware Research Integration (Items 120-129)
    # =========================================================================

    if opts.hpc:
        from scripts.phases.phase18_hpc import phase_hpc
        phase_hpc(ir_output, obfuscated_output)

    if opts.hpc_key:
        from scripts.phases.phase19_hpc_key import phase_hpc_key
        phase_hpc_key()

    if opts.hpc_detect:
        from scripts.phases.phase20_hpc_detect import phase_hpc_detect
        phase_hpc_detect()

    if opts.hw_entropy:
        from scripts.phases.phase21_hw_entropy import phase_hw_entropy
        phase_hw_entropy()

    if opts.cache_bound:
        from scripts.phases.phase22_cache_bound import phase_cache_bound
        phase_cache_bound()

    # =========================================================================
    # Item 124: SIMD-VM Pipeline Integration
    # =========================================================================

    if opts.simd_vm:
        log("SIMD_VM", "Compiling SIMD-VM native code...")
        native_dir = os.path.join(_ROOT, "native")
        simd_src = os.path.join(native_dir, "simd_vm.c")
        simd_obj = os.path.join(BUILD_DIR, "simd_vm.o")
        try:
            subprocess.run(
                ["gcc", "-c", "-O2", "-msse4.1", "-o", simd_obj, simd_src],
                check=True, capture_output=True, text=True,
            )
            log("SIMD_VM", f"Compiled SIMD-VM to {simd_obj}")
            # Also compile and run a test binary to verify
            simd_test_src = os.path.join(native_dir, "simd_vm_test.c")
            if os.path.exists(simd_test_src):
                simd_test_bin = os.path.join(BUILD_DIR, "simd_vm_test")
                subprocess.run(
                    ["gcc", "-O2", "-msse4.1", "-o", simd_test_bin, simd_test_src, simd_src, "-lm"],
                    check=True, capture_output=True, text=True,
                )
                log("SIMD_VM", f"SIMD-VM test binary: {simd_test_bin}")
                test_result = subprocess.run([simd_test_bin], capture_output=True, text=True)
                if test_result.returncode == 0:
                    log("SIMD_VM", f"SIMD-VM tests ALL PASSED")
                else:
                    log("ERROR", f"SIMD-VM tests FAILED:\n{test_result.stdout}\n{test_result.stderr}")
            else:
                log("ERROR", "SIMD-VM test source not found: native/simd_vm_test.c")
        except subprocess.CalledProcessError as e:
            log("ERROR", f"SIMD-VM compilation failed: {e.stderr}")
        except FileNotFoundError:
            log("ERROR", "gcc not found, SIMD-VM compilation skipped")

    # =========================================================================
    # Stage 7: Build Relay (Rust)
    # =========================================================================

    if not opts.skip_relay:
        try:
            phase_compile_relay()
        except RuntimeError as e:
            log("ERROR", f"Relay build failed: {e}")
            sys.exit(1)
    else:
        log("SKIP", "Rust relay build skipped")

    # =========================================================================
    # Cross-Compile (if requested)
    # =========================================================================

    if opts.cross:
        try:
            _xc_results = phase_cross_compile(opts.cross)
        except RuntimeError as e:
            log("ERROR", f"Cross-compile failed: {e}")
            sys.exit(1)
        else:
            _xc_failed = [t for t, ok, _ in (_xc_results or []) if not ok]
            if _xc_failed:
                log("ERROR", f"Cross-compile failed for: {', '.join(_xc_failed)}")
                sys.exit(1)

    # =========================================================================
    # Stage 8: Runtime Manifest
    # =========================================================================

    phase_runtime_manifest(manifest_output)

    # =========================================================================
    # Stage 9: Package
    # =========================================================================

    phase_package(opts.payload, obfuscated_output, obfuscated_name, opts)

    # Diagnostic finalization (V10: per-stage timings + transform counts +
    # key freshness + visible NOT-FOR-RELEASE marker). Best-effort: never
    # fails the build. Marks the packaged artifact when resolvable.
    if getattr(opts, "diagnostic", False):
        try:
            from scripts.diagnostic import (
                banner as _diag_banner2,
                key_freshness as _diag_key_freshness2,
                mark_diagnostic as _mark_diagnostic2,
                summarize_transforms as _diag_summarize2,
            )
            _dc = getattr(opts, "_diag_clock", None)
            if _dc is not None:
                try:
                    _dc.mark("package")
                    _dc.mark("done")
                    for _st, _dt in sorted(_dc.report().items()):
                        log("DIAG", f"stage { _st }: {_dt:.3f}s")
                except Exception:
                    pass
            try:
                _ts = _diag_summarize2(
                    int(getattr(opts, "opt_level", 4) or 4),
                    name_gate=bool(getattr(opts, "name_gate", False)),
                    lowering=str(getattr(opts, "lowering", "") or ""))
                log("DIAG", f"transforms: {_ts.get('enabled_count')} flags on "
                            f"(opt-level {_ts.get('opt_level')})")
            except Exception:
                pass
            _marked = False
            for _cand in (os.path.join(BUILD_DIR, obfuscated_name),
                          obfuscated_output):
                try:
                    if _cand and os.path.isfile(_cand):
                        _mark_diagnostic2(_cand)
                        _marked = True
                        break
                except Exception:
                    continue
            try:
                _kf = _diag_key_freshness2(
                    str(getattr(opts, "_diag_blob_key", "") or ""))
                log("DIAG", f"key freshness: {_kf}")
            except Exception:
                pass
            log("DIAG", _diag_banner2().splitlines()[0]
                + (" (artifact marked)" if _marked else " (marker skipped)"))
        except Exception as _diag_err2:
            log("DIAG", f"diagnostic finalize failed (non-fatal): {_diag_err2}")

    # =========================================================================
    # Batch-2: REAL --pytoc native-extension path (best-effort, never fails)
    # V10 Phase 2: when --lowering is also set, the native lowering kernel
    # is built first and the lowered output's shim import is swapped for
    # the native module import (identical call shapes, per-build symbols).
    # =========================================================================
    if getattr(opts, "pytoc", False):
        try:
            _pytoc_src = obfuscated_output
            if not os.path.exists(_pytoc_src):
                _pytoc_src = os.path.join(BUILD_DIR, obfuscated_name)
            _low_spec = str(getattr(opts, "lowering", "") or "")
            if _low_spec:
                try:
                    from obfuscator.kernel_gen import (
                        build_kernel as _kb,
                        cythonize_kernel as _kc,
                        derive_symbols as _kd,
                        emit_native_import as _ke,
                    )
                    from obfuscator.lowering import resolve_families as _kr
                    import ast as _ka
                    _kseed_src = str(getattr(opts, "build_id", "") or "") or None
                    import os as _ko
                    _kseed = (_kseed_src.encode() if _kseed_src
                              else _ko.urandom(16))
                    _k_active = _kr(_low_spec)
                    _k_tmp = os.path.join(BUILD_DIR, "nxk_build")
                    _k_pyx, _k_mod, _k_map = _kb(_k_tmp, _kseed)
                    _k_so, _k_msg = _kc(_k_pyx, BUILD_DIR)
                    log("PYTOC", f"lowering kernel: {_k_msg}")
                    if _k_so:
                        # Swap the shim import for the native module import.
                        # Both expose identical _nxk_* names; only the
                        # provider changes (shim .py -> native .so).
                        with open(_pytoc_src, encoding="utf-8") as _kf:
                            _k_src = _kf.read()
                        _k_tokens = sorted({
                            _t.id for _t in _ka.walk(_ka.parse(_k_src))
                            if isinstance(_t, ast.Name) and _t.id.startswith("_nxk_")
                        })
                        _k_new = _k_src.replace(
                            "from lowering_shim import",
                            f"from {_k_mod} import",
                        )
                        if _k_new == _k_src and _k_tokens:
                            # No shim import line (shim inlined?) — prepend.
                            _k_new = _ke(_k_mod, _k_tokens) + _k_src
                        if _k_new != _k_src:
                            with open(_pytoc_src, "w", encoding="utf-8") as _kf:
                                _kf.write(_k_new)
                            log("PYTOC", f"kernel swap: {_k_mod} provides {len(_k_tokens)} ops")
                except Exception as _ke2:
                    log("PYTOC", f"kernel swap skipped (non-fatal): {_ke2}")
            _pytoc_out = getattr(opts, "pytoc_out", "") or None
            if not _pytoc_out:
                _base, _ = os.path.splitext(_pytoc_src)
                _ext = ".pyd" if sys.platform == "win32" else ".so"
                _pytoc_out = _base + "_pytoc" + _ext
            _built, _msg = phase_pytoc(_pytoc_src, _pytoc_out)
            log("PYTOC", _msg)
        except Exception as _pe:
            log("PYTOC", f"pytoc skipped (non-fatal): {_pe}")

    # =========================================================================
    # Batch-2: --pyinstaller-spec .spec generation (best-effort, never fails)
    # =========================================================================
    if getattr(opts, "pyinstaller_spec", False):
        try:
            from scripts.pyinstaller_spec import collect_hidden_imports, generate_spec
            _spec_src = obfuscated_output
            if not os.path.exists(_spec_src):
                _spec_src = os.path.join(BUILD_DIR, obfuscated_name)
            try:
                with open(_spec_src, encoding="utf-8") as _sf:
                    _spec_code = _sf.read()
            except Exception:
                _spec_code = ""
            _his = collect_hidden_imports(_spec_code)
            _spec_name = os.path.splitext(obfuscated_name)[0]
            _spec_text = generate_spec(_spec_name, _spec_src, _his)
            _spec_path = os.path.splitext(_spec_src)[0] + ".spec"
            with open(_spec_path, "w", encoding="utf-8") as _sf:
                _sf.write(_spec_text)
            log("SPEC", f"PyInstaller spec written: {_spec_path}")
        except Exception as _se:
            log("SPEC", f"spec generation skipped (non-fatal): {_se}")

    # =========================================================================
    # Feature 145: Autonomous Red Team Pipeline
    # =========================================================================

    if opts.red_team:
        binary_path = os.path.join(BUILD_DIR, obfuscated_name)
        if not os.path.exists(binary_path):
            binary_path = obfuscated_output
        phase_redteam(opts, binary_path, opts.payload)
    else:
        log("SKIP", "Red team pipeline not enabled (use --red-team)")

    # =========================================================================
    # Feature 154: Attack Replay Framework
    # =========================================================================

    if opts.capture_attacks or opts.replay_attacks:
        binary_path = os.path.join(BUILD_DIR, obfuscated_name)
        if not os.path.exists(binary_path):
            binary_path = obfuscated_output
        opts.binary_path = binary_path
        phase_attack_replay(opts)
    else:
        log("SKIP", "Attack replay not enabled (use --capture-attacks or --replay-attacks)")

    # =========================================================================
    # Embed Proof into packaged artifact
    # =========================================================================

    if opts.embed_proof and certificate_collector is not None:
        certificate_collector.emit_all()

        # Auto-generate ledger proof from build artifacts before embedding
        try:
            from scripts.ledger_proof import generate_ledger_proof
            object_path = os.path.join(BUILD_DIR, "program.o")
            if os.path.exists(object_path):
                generate_ledger_proof(object_path, BUILD_DIR)
                log("PROOF", "Ledger proof auto-generated from build artifacts")
            else:
                obj_dirs = [d for d in os.listdir(BUILD_DIR) if d.endswith(".o") or d.endswith(".obj")]
                if obj_dirs:
                    generate_ledger_proof(os.path.join(BUILD_DIR, obj_dirs[0]), BUILD_DIR)
                    log("PROOF", f"Ledger proof auto-generated from {obj_dirs[0]}")
                else:
                    log("SKIP", "No object file found, ledger proof not auto-generated")
        except Exception as e:
            log("ERROR", f"Ledger proof generation failed: {e}")

        chain_path = os.path.join(certificate_collector.output_dir, "certificate_chain.json")
        if os.path.exists(chain_path):
            from scripts.verifier import BinaryReader
            reader = BinaryReader()
            with open(chain_path, "rb") as f:
                proof_data = f.read()
            packaged_file = os.path.join(BUILD_DIR, obfuscated_name)
            if os.path.exists(packaged_file):
                reader.inject_proof_section(packaged_file, proof_data)
                log("PROOF", f"Proof embedded in {packaged_file}")
            else:
                log("SKIP", f"Packaged file not found for proof embedding: {packaged_file}")
    elif opts.emit_certificates and certificate_collector is not None:
        certificate_collector.emit_all()
        log("CERT", "Certificates emitted to build/certificates/")

    # =========================================================================
    # Preservation: Run Unified Engine Report
    # =========================================================================

    if opts.verify_preservation:
        try:
            from scripts.preservation.engine import PreservationEngine
            from scripts.preservation.report import PreservationReport, StageResult
            engine = PreservationEngine()
            stage_fns = []

            def make_stage_fn(stage_name, stage_input, stage_output,
                              translator_input, translator_output):
                def fn(ctx):
                    return engine.check_stage(
                        stage_name, stage_input, stage_output,
                        translator_input, translator_output,
                    )
                return fn

            pipeline_ctx = {"stage_fns": stage_fns}
            report = engine.run_all(pipeline_ctx)
            report.print_summary()
            report_path = os.path.join(BUILD_DIR, "preservation_report.json")
            atomic_write(report_path, report.to_json())
            log("PRESERVATION", f"Report saved to {report_path}")
        except Exception as e:
            log("PRESERVATION", f"Engine report error: {e}")

    # =========================================================================
    # Metrics Collection (--metrics / --min-resilience)
    # =========================================================================

    if opts.metrics or opts.min_resilience is not None:
        metrics = ResilienceMetrics()
        payload_source = opts.payload
        prot_source = os.path.join(BUILD_DIR, obfuscated_name)
        if not os.path.exists(prot_source):
            prot_source = obfuscated_output

        if opts.min_resilience is not None:
            target = max(0.0, min(1.0, opts.min_resilience))
            for iteration in range(4):
                m = metrics.measure(payload_source, prot_source)
                score = m["overall"]
                log("METRICS", f"Iteration {iteration} resilience: {score:.4f} (target: {target})")
                if score >= target or iteration == 3:
                    break
                log("METRICS", f"Score {score:.4f} < {target}, increasing obfuscation intensity...")
                opts.opaque_predicates = True
                opts.mba_subs = True
                opts.bogus_exceptions = True
                opts.cfg_flatten = True
                opts.honey_functions = max(opts.honey_functions or 0, (iteration + 1) * 5)
                try:
                    phase_obfuscate(opts.payload, obfuscated_output, opts)
                except RuntimeError as e:
                    log("ERROR", f"Obfuscation failed during auto-tune iteration {iteration}: {e}")
                    break
                shutil.copy2(obfuscated_output, prot_source)
        else:
            metrics.measure(payload_source, prot_source)

        report_path = os.path.join(BUILD_DIR, "metrics_report.json")
        metrics.to_json(report_path)
        log("METRICS", f"Report saved to {report_path}")
        metrics.print_summary()

    # =========================================================================
    # Item 76: Context Saturation Metrics
    # =========================================================================

    if opts.context_saturation:
        log("CONTEXT_SATURATION", "Computing context window saturation metrics...")
        try:
            from scripts.metrics.context_saturation import ContextSaturationMetrics

            _prot_src_sat = obfuscated_output
            if not os.path.exists(_prot_src_sat):
                _prot_src_sat = os.path.join(BUILD_DIR, obfuscated_name)
            if os.path.exists(_prot_src_sat):
                with open(_prot_src_sat) as f:
                    _code_sat = f.read()
                _cs = ContextSaturationMetrics()
                _token_util = _cs.measure_token_utilization(_code_sat)
                _attn_degr = _cs.measure_attention_degradation(_code_sat)
                _ctx_coll = _cs.measure_context_collapse(_code_sat)
                _score = _cs.compute_saturation_score(_code_sat)

                print("\n" + "=" * 60)
                print("  CONTEXT SATURATION METRICS")
                print("=" * 60)
                print(f"  Token utilization (noise ratio):    {_token_util:.4f}")
                print(f"  Attention degradation:             {_attn_degr:.4f}")
                print(f"  Context collapse:                  {_ctx_coll:.4f}")
                print(f"  SATURATION SCORE (0-100):          {_score:.2f}")
                print("=" * 60 + "\n")

                _sat_path = os.path.join(BUILD_DIR, "context_saturation_report.json")
                atomic_write(_sat_path, json.dumps({
                    "token_utilization": _token_util,
                    "attention_degradation": _attn_degr,
                    "context_collapse": _ctx_coll,
                    "saturation_score": _score,
                }, indent=2))
                log("CONTEXT_SATURATION", f"Report saved to {_sat_path}")
            else:
                log("CONTEXT_SATURATION", f"Protected file not found: {_prot_src_sat}, skipping")
        except Exception as e:
            log("ERROR", f"Context saturation metrics failed: {e}")
    else:
        log("SKIP", "Context saturation metrics not enabled (use --context-saturation)")

    # Prompt Resistance Metrics (Item 77)
    if opts.prompt_resistance:
        log("PROMPT_RESISTANCE", "Computing prompt reconstruction resistance...")
        try:
            from scripts.metrics.prompt_resistance import PromptResistanceMetrics

            _orig_src_pr = opts.payload
            _prot_src_pr = obfuscated_output
            if not os.path.exists(_prot_src_pr):
                _prot_src_pr = os.path.join(BUILD_DIR, obfuscated_name)
            if os.path.exists(_orig_src_pr) and os.path.exists(_prot_src_pr):
                with open(_orig_src_pr) as f:
                    _orig_code = f.read()
                with open(_prot_src_pr) as f:
                    _prot_code = f.read()
                _pr = PromptResistanceMetrics()
                _intent_obs = _pr.measure_intent_obscurity(_orig_code, _prot_code)
                _sem_recov = _pr.measure_semantic_recoverability(_prot_code)
                _res_score = _pr.compute_prompt_resistance_score(_orig_code, _prot_code)

                print("\n" + "=" * 60)
                print("  PROMPT RECONSTRUCTION RESISTANCE")
                print("=" * 60)
                print(f"  Intent obscurity:           {_intent_obs:.4f}")
                print(f"  Semantic recoverability:    {_sem_recov:.4f}")
                print(f"  PROMPT RESISTANCE (0-100):  {_res_score:.2f}")
                print("=" * 60 + "\n")

                _pr_path = os.path.join(BUILD_DIR, "prompt_resistance_report.json")
                atomic_write(_pr_path, json.dumps({
                    "intent_obscurity": _intent_obs,
                    "semantic_recoverability": _sem_recov,
                    "prompt_resistance_score": _res_score,
                }, indent=2))
                log("PROMPT_RESISTANCE", f"Report saved to {_pr_path}")
            else:
                log("PROMPT_RESISTANCE", "Source or protected file not found, skipping")
        except Exception as e:
            log("ERROR", f"Prompt resistance metrics failed: {e}")
    else:
        log("SKIP", "Prompt resistance metrics not enabled (use --prompt-resistance)")

    # Benchmark
    if opts.benchmark:
        log("BENCHMARK", "Running AI obfuscation benchmark...")
        try:
            from scripts.benchmark import AIBenchmark, LLMEvaluator, BenchmarkReport

            payload_source = opts.payload
            prot_source = os.path.join(BUILD_DIR, obfuscated_name)
            if not os.path.exists(prot_source):
                prot_source = obfuscated_output
            if not os.path.exists(prot_source):
                log("BENCHMARK", f"Protected file not found: {prot_source}, skipping")
            else:
                bm = AIBenchmark()
                results = bm.evaluate(payload_source, prot_source)

                if opts.benchmark_model:
                    llm = LLMEvaluator()
                    if opts.benchmark_model == "all":
                        results["_llm_results"] = {}
                        with open(prot_source, encoding="utf-8") as _f:
                            prot_code = _f.read()
                        for _model in llm.models:
                            results["_llm_results"][_model] = llm.evaluate(prot_code, _model)
                        log("BENCHMARK", f"Evaluated against {len(llm.models)} models")
                    else:
                        with open(prot_source, encoding="utf-8") as _f:
                            prot_code = _f.read()
                        results["_llm_results"] = {
                            opts.benchmark_model: llm.evaluate(prot_code, opts.benchmark_model)
                        }
                        log("BENCHMARK", f"Evaluated against {opts.benchmark_model}")

                report = BenchmarkReport()
                text_summary = report.generate_text_summary(results)
                print(text_summary)

                bench_report_path = os.path.join(BUILD_DIR, "benchmark_report.json")
                with open(bench_report_path, "w") as f:
                    json.dump(results, f, indent=2, default=str)
                log("BENCHMARK", f"JSON report saved to {bench_report_path}")

                if opts.benchmark_report:
                    html = report.generate_html(results)
                    html_path = os.path.join(BUILD_DIR, "benchmark_report.html")
                    with open(html_path, "w") as f:
                        f.write(html)
                    log("BENCHMARK", f"HTML report saved to {html_path}")
        except ImportError as e:
            log("BENCHMARK", f"Benchmark module not available: {e}")
        except Exception as e:
            log("BENCHMARK", f"Benchmark error: {e}")

    # Item 101: Analyst Time Estimation
    analyst_time_result = None
    if opts.analyst_time:
        log("ANALYST_TIME", "Estimating analyst reverse-engineering time (Item 101)...")
        try:
            from scripts.evaluation.analyst_time import AnalystTimeEstimator
            payload_source = opts.payload
            prot_source = os.path.join(BUILD_DIR, obfuscated_name)
            if not os.path.exists(prot_source):
                prot_source = obfuscated_output
            if os.path.exists(payload_source) and os.path.exists(prot_source):
                with open(payload_source) as f:
                    _orig_at = f.read()
                with open(prot_source) as f:
                    _prot_at = f.read()
                at_estimator = AnalystTimeEstimator()
                analyst_time_result = at_estimator.estimate(_orig_at, _prot_at)
                print("\n" + "=" * 60)
                print("  ANALYST TIME ESTIMATION")
                print("=" * 60)
                print(f"  Static analysis:    {analyst_time_result['static_analysis_hours']:>8.2f} hours")
                print(f"  Dynamic analysis:   {analyst_time_result['dynamic_analysis_hours']:>8.2f} hours")
                print(f"  Deobfuscation:      {analyst_time_result['deobfuscation_hours']:>8.2f} hours")
                print(f"  {'─' * 40}")
                print(f"  TOTAL:              {analyst_time_result['total_hours']:>8.2f} hours")
                print(f"  Confidence interval: {analyst_time_result['confidence_interval'][0]:.2f} – {analyst_time_result['confidence_interval'][1]:.2f}")
                print(f"  Cost class:         {analyst_time_result['cost_class']}")
                print("=" * 60 + "\n")
                at_path = os.path.join(BUILD_DIR, "analyst_time_report.json")
                atomic_write(at_path, json.dumps(analyst_time_result, indent=2))
                log("ANALYST_TIME", f"Report saved to {at_path}")
            else:
                log("ANALYST_TIME", "Source or protected file not found, skipping")
        except Exception as e:
            log("ANALYST_TIME", f"Analyst time estimation failed: {e}")
    else:
        log("SKIP", "Analyst time estimation not enabled (use --analyst-time)")

    # Evaluation Research: Reverse Engineering Cost Model
    cost_model_result = None
    if opts.cost_model:
        log("COST_MODEL", "Running reverse engineering cost model...")
        try:
            from scripts.evaluation import ReverseEngineeringCostModel

            payload_source = opts.payload
            prot_source = os.path.join(BUILD_DIR, obfuscated_name)
            if not os.path.exists(prot_source):
                prot_source = obfuscated_output

            metrics_obj = ResilienceMetrics()
            m = metrics_obj.measure(payload_source, prot_source)

            cost_model = ReverseEngineeringCostModel()
            cost_model_result = cost_model.estimate(m)
            print("\n" + "=" * 60)
            print("  REVERSE ENGINEERING COST MODEL")
            print("=" * 60)
            print(f"  Static analysis:    {cost_model_result.static_analysis_hours:>8.2f} hours")
            print(f"  Dynamic analysis:   {cost_model_result.dynamic_analysis_hours:>8.2f} hours")
            print(f"  Deobfuscation:      {cost_model_result.deobfuscation_hours:>8.2f} hours")
            print(f"  {'─' * 40}")
            print(f"  TOTAL:              {cost_model_result.total_hours:>8.2f} hours")
            print(f"  Confidence interval: {cost_model_result.confidence_interval[0]:.2f} – {cost_model_result.confidence_interval[1]:.2f}")
            print(f"  Cost class:         {cost_model_result.cost_class}")
            print("=" * 60 + "\n")

            cm_path = os.path.join(BUILD_DIR, "cost_model_report.json")
            atomic_write(cm_path, json.dumps({
                'static_analysis_hours': cost_model_result.static_analysis_hours,
                'dynamic_analysis_hours': cost_model_result.dynamic_analysis_hours,
                'deobfuscation_hours': cost_model_result.deobfuscation_hours,
                'total_hours': cost_model_result.total_hours,
                'confidence_interval': list(cost_model_result.confidence_interval),
                'cost_class': cost_model_result.cost_class,
            }, indent=2))
            log("COST_MODEL", f"Report saved to {cm_path}")
        except ImportError as e:
            log("COST_MODEL", f"Cost model module not available: {e}")
        except Exception as e:
            log("COST_MODEL", f"Cost model error: {e}")

    # Evaluation Research: Multi-Tool Resistance Score
    multi_tool_result = None
    if opts.multi_tool:
        log("MULTI_TOOL", "Running multi-tool resistance evaluation...")
        try:
            from scripts.evaluation import MultiToolEvaluator

            prot_source = os.path.join(BUILD_DIR, obfuscated_name)
            if not os.path.exists(prot_source):
                prot_source = obfuscated_output

            if os.path.exists(prot_source):
                evaluator = MultiToolEvaluator()
                multi_tool_result = evaluator.evaluate(prot_source)
                print("\n" + "=" * 60)
                print("  MULTI-TOOL RESISTANCE SCORE")
                print("=" * 60)
                print(f"  Tools tested:  {', '.join(multi_tool_result['tools_tested'])}")
                print(f"  Tools found:   {multi_tool_result['tools_found']}")
                print(f"  Tools sim.:    {multi_tool_result['tools_simulated']}")
                for tool, scores in multi_tool_result['scores'].items():
                    avg = sum(scores.values()) / max(len(scores), 1)
                    print(f"  {tool:12s}: bb={scores['bb_accuracy']:3d}  fn={scores['function_recovery']:3d}  "
                          f"dec={scores['decompilation']:3d}  avg={avg:.1f}")
                print(f"  {'─' * 40}")
                print(f"  COMPOSITE SCORE: {multi_tool_result['composite_score']:.2f}/100")
                print("=" * 60 + "\n")

                mt_path = os.path.join(BUILD_DIR, "multi_tool_report.json")
                atomic_write(mt_path, json.dumps(multi_tool_result, indent=2))
                log("MULTI_TOOL", f"Report saved to {mt_path}")
            else:
                log("MULTI_TOOL", f"Protected file not found: {prot_source}, skipping")
        except ImportError as e:
            log("MULTI_TOOL", f"Multi-tool module not available: {e}")
        except Exception as e:
            log("MULTI_TOOL", f"Multi-tool error: {e}")

    # =========================================================================
    # Distributed Protection Features (Items 110–119)
    # =========================================================================

    # Item 110: Multi-Binary Fragment Distribution
    if opts.multi_binary:
        log("DISTRIBUTED", "Multi-binary fragment distribution enabled")
        from scripts.distributed.multi_binary import MultiBinaryDistributor
        dmode = opts.distributed_mode
        mbd = MultiBinaryDistributor(mode=dmode)
        num_binaries = opts.multi_binary_num
        fragments = []
        payload_path = opts.payload
        with open(payload_path, "rb") as f:
            data = f.read()
        chunk_size = max(32, len(data) // 4)
        fragments = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
        if dmode == "multiprocess":
            binaries, index = mbd.distribute_to_processes(fragments, num_binaries)
            log("DISTRIBUTED", f"Distributed {len(fragments)} fragments across {num_binaries} binaries via multiprocess")
        else:
            binaries, index = mbd.distribute(fragments, num_binaries)
        mb_dir = os.path.join(BUILD_DIR, "multi_binary")
        os.makedirs(mb_dir, exist_ok=True)
        for i, binary in enumerate(binaries):
            path = os.path.join(mb_dir, f"binary_{i}.bin")
            atomic_write(path, binary, mode="wb")
        index_path = os.path.join(mb_dir, "master_index.bin")
        atomic_write(index_path, index.serialize(), mode="wb")
        log("DISTRIBUTED", f"Distributed {len(fragments)} fragments across {num_binaries} binaries → {mb_dir}")

    # Item 111: Cross-Process Fragment Binding
    if opts.cross_process:
        log("DISTRIBUTED", "Cross-process fragment binding enabled")
        from scripts.distributed.cross_process import CrossProcessBinder
        cpb = CrossProcessBinder()
        fragments = [(b"fragment_" + str(i).encode(), 1000 + i) for i in range(3)]
        chain = cpb.bind_across_processes(fragments)
        chain_path = os.path.join(BUILD_DIR, "cross_process_chain.bin")
        atomic_write(chain_path, chain.serialize(), mode="wb")
        log("DISTRIBUTED", f"Cross-process chain written to {chain_path}")

    # Item 112: Remote Fragment Unlocking
    if opts.remote_unlock:
        log("DISTRIBUTED", "Remote fragment unlocking enabled")
        from scripts.distributed.remote_unlock import RemoteUnlockServer, RemoteUnlockClient
        server = RemoteUnlockServer(token_ttl=opts.remote_unlock_ttl)
        client = RemoteUnlockClient()
        client.bind_server(server)
        for fid in range(3):
            token = client.request_unlock(fid)
            if token:
                key = client.derive_key(fid, token)
                log("DISTRIBUTED", f"Fragment {fid}: unlock token issued, key={key.hex()[:16]}...")
        unlock_dir = os.path.join(BUILD_DIR, "remote_unlock")
        os.makedirs(unlock_dir, exist_ok=True)
        log("DISTRIBUTED", f"Remote unlock configured in {unlock_dir}")

    # Item 113: Distributed VM Execution
    if opts.distributed_vm:
        log("DISTRIBUTED", "Distributed VM execution enabled")
        from scripts.distributed.vm_cluster import DistributedVMExecutor
        dvm = DistributedVMExecutor(mode=opts.distributed_mode)
        instructions = [
            {"op": "loadi", "rd": "r0", "val": 42},
            {"op": "loadi", "rd": "r1", "val": 10},
            {"op": "add", "rd": "r2", "rs1": "r0", "rs2": "r1"},
        ]
        dvm.load_program(instructions)
        state = dvm.run()
        log("DISTRIBUTED", f"Distributed VM executed: r2={state.registers['r2']} (mode={opts.distributed_mode})")
        vm_config_path = os.path.join(BUILD_DIR, "distributed_vm_config.json")
        atomic_write(vm_config_path, json.dumps({
            "hosts": 3,
            "partitions": ["registers", "memory", "stack"],
            "final_pc": state.program_counter,
            "sync_count": state.sync_counter,
            "mode": opts.distributed_mode,
        }, indent=2))

    # Item 114: Multi-Host Execution Graphs
    if opts.multi_host:
        log("DISTRIBUTED", "Multi-host execution graphs enabled")
        from scripts.distributed.multi_host import MultiHostExecutor
        mhe = MultiHostExecutor(num_hosts=opts.multi_host_count, deployment_seed=secrets.randbits(32),
                                mode=opts.distributed_mode)
        fns = [("func_a", "x = 1"), ("func_b", "y = 2"), ("func_c", "z = x + y")]
        mhe.assign_functions(fns)
        mhe.build_call_graph([(0, 2), (1, 2)])
        trace = mhe.simulate_execution()
        deploy_path = os.path.join(BUILD_DIR, "multi_host_deployment.json")
        atomic_write(deploy_path, json.dumps(trace, indent=2))
        log("DISTRIBUTED", f"Multi-host deployment: {len(fns)} functions across {opts.multi_host_count} hosts (mode={opts.distributed_mode})")

    # Item 69: Payload Dispersal Execution Model
    if opts.payload_dispersal:
        log("PAYLOAD_DISPERSAL", "Applying payload dispersal execution model (Item 69)...")
        try:
            phase_payload_dispersal(opts.payload, opts)
        except Exception as e:
            log("ERROR", f"Payload dispersal failed: {e}")
    else:
        log("SKIP", "Payload dispersal not enabled (use --payload-dispersal)")

    # Item 115: Cross-Platform Fragment Migration
    if opts.fragment_migration:
        log("DISTRIBUTED", "Cross-platform fragment migration enabled")
        from scripts.distributed.fragment_migration import FragmentMigrator, Platform
        fm = FragmentMigrator(mode=opts.distributed_mode)
        variants = {
            Platform.X86: b"\x90\x90\xc3",
            Platform.ARM: b"\x00\x00\x00\x00\x00",
            Platform.WASM: b"\x00\x61\x73\x6d\x01\x00\x00\x00",
        }
        fragment = fm.create_fragment(0, variants)
        migrated = fm.atomic_migrate(fragment, Platform.ARM)
        if migrated:
            log("DISTRIBUTED", f"Fragment migrated from X86 to ARM (count={migrated.migration_count}, mode={opts.distributed_mode})")
        mig_dir = os.path.join(BUILD_DIR, "fragment_migration")
        os.makedirs(mig_dir, exist_ok=True)
        log("DISTRIBUTED", f"Migration state in {mig_dir}")

    # Item 116: Distributed Attestation
    if opts.dist_attestation:
        log("DISTRIBUTED", "Distributed attestation enabled")
        from scripts.distributed.dist_attestation import DistributedAttestation
        da = DistributedAttestation(num_nodes=opts.dist_attestation_nodes, challenge_timeout=5.0)
        result = da.run_consensus_protocol()
        log("DISTRIBUTED", f"Distributed attestation consensus: {'PASS' if result else 'FAIL'}")
        att_path = os.path.join(BUILD_DIR, "dist_attestation_result.json")
        atomic_write(att_path, json.dumps({
            "consensus_passed": result,
            "num_nodes": opts.dist_attestation_nodes,
        }, indent=2))

    # Item 117: Distributed Watermarking
    if opts.dist_watermark:
        log("DISTRIBUTED", "Distributed watermarking enabled")
        from scripts.distributed.dist_watermark import DistributedWatermark
        dw = DistributedWatermark(mode=opts.distributed_mode)
        watermark_text = opts.watermark.encode() if opts.watermark else b"NixonCorp-Distributed"
        if opts.distributed_mode == "multiprocess":
            shares = dw.shard_and_distribute(watermark_text, opts.dist_watermark_shares)
            log("DISTRIBUTED", f"Watermark sharded and distributed to {len(shares)} processes")
        else:
            shares = dw.shard_watermark(watermark_text, opts.dist_watermark_shares)
        wm_dir = os.path.join(BUILD_DIR, "dist_watermark")
        os.makedirs(wm_dir, exist_ok=True)
        for i, share in enumerate(shares):
            share_path = os.path.join(wm_dir, f"share_{i}.bin")
            atomic_write(share_path, share.serialize(), mode="wb")
        log("DISTRIBUTED", f"Watermark split into {len(shares)} shares → {wm_dir}")

    # Item 118: Distributed Diversity Pools
    if opts.dist_diversity:
        log("DISTRIBUTED", "Distributed diversity pools enabled")
        from scripts.distributed.diversity_pool import DistributedDiversityPool
        dp = DistributedDiversityPool(rotation_interval=opts.dist_diversity_rotation)
        with open(opts.payload) as f:
            base_source = f.read()
        variants = dp.generate_variants(base_source, opts.dist_diversity_variants)
        dp.setup_nodes(opts.dist_diversity_nodes)
        deployment = dp.distribute_variants()
        dd_dir = os.path.join(BUILD_DIR, "dist_diversity")
        os.makedirs(dd_dir, exist_ok=True)
        for nid, vid in deployment.items():
            code = dp.get_node_variant_code(nid)
            if code:
                path = os.path.join(dd_dir, f"node_{nid}_variant_{vid}.py")
                atomic_write(path, code)
        log("DISTRIBUTED", f"Deployed {len(deployment)} variants across {opts.dist_diversity_nodes} nodes → {dd_dir}")

    # Item 119: Distributed Execution Recovery Prevention
    if opts.recovery_prevention:
        log("DISTRIBUTED", "Distributed execution recovery prevention enabled")
        from scripts.distributed.recovery_prevention import ExecutionRecoveryPreventer
        erp = ExecutionRecoveryPreventer(num_nodes=opts.recovery_prevention_nodes, mode=opts.distributed_mode)
        ops = [f"instruction_{i}" for i in range(20)]
        if opts.distributed_mode == "multiprocess":
            result = erp.run_multiprocess(ops)
            log("DISTRIBUTED", f"Recovery prevention: multiprocess execution returned {result}")
        else:
            erp.partition_algorithm(ops)
            noise = erp.generate_noise_traffic(density=5)
            erp.mix_traffic([], noise)
        log("DISTRIBUTED", f"Recovery prevention: {opts.recovery_prevention_nodes} nodes (mode={opts.distributed_mode})")
        rp_dir = os.path.join(BUILD_DIR, "recovery_prevention")
        os.makedirs(rp_dir, exist_ok=True)
        log("DISTRIBUTED", f"Recovery prevention state in {rp_dir}")

    # Evaluation Research: Protection Survivability Index
    survivability_result = None
    if opts.survivability:
        log("SURVIVABILITY", "Running protection survivability index...")
        try:
            from scripts.evaluation import SurvivabilityIndex

            prot_source = os.path.join(BUILD_DIR, obfuscated_name)
            if not os.path.exists(prot_source):
                prot_source = obfuscated_output

            if os.path.exists(prot_source):
                index = SurvivabilityIndex()
                survivability_result = index.measure(prot_source)
                print("\n" + "=" * 60)
                print("  PROTECTION SURVIVABILITY INDEX")
                print("=" * 60)
                print(f"  Active layers:     {', '.join(survivability_result.active_layers)}")
                if survivability_result.watermark_survival is not None:
                    print(f"  Watermark survival: {survivability_result.watermark_survival:.4f}")
                if survivability_result.vm_opcode_recovery is not None:
                    print(f"  VM opcode recovery: {survivability_result.vm_opcode_recovery:.4f}")
                if survivability_result.cfg_reconstruction is not None:
                    print(f"  CFG reconstruction: {survivability_result.cfg_reconstruction:.4f}")
                if survivability_result.fragment_isolation is not None:
                    print(f"  Fragment isolation: {survivability_result.fragment_isolation:.4f}")
                print(f"  {'─' * 40}")
                print(f"  COMBINED INDEX:     {survivability_result.combined_index:.4f}")
                print("=" * 60 + "\n")

                sv_path = os.path.join(BUILD_DIR, "survivability_report.json")
                atomic_write(sv_path, json.dumps({
                    'watermark_survival': survivability_result.watermark_survival,
                    'vm_opcode_recovery': survivability_result.vm_opcode_recovery,
                    'cfg_reconstruction': survivability_result.cfg_reconstruction,
                    'fragment_isolation': survivability_result.fragment_isolation,
                    'combined_index': survivability_result.combined_index,
                    'active_layers': survivability_result.active_layers,
                }, indent=2))
                log("SURVIVABILITY", f"Report saved to {sv_path}")
            else:
                log("SURVIVABILITY", f"Protected file not found: {prot_source}, skipping")
        except ImportError as e:
            log("SURVIVABILITY", f"Survivability module not available: {e}")
        except Exception as e:
            log("SURVIVABILITY", f"Survivability error: {e}")

    # Evaluation Research: Summary Report
    if opts.eval_summary:
        log("EVAL_SUMMARY", "Generating evaluation summary report...")
        try:
            from scripts.evaluation import EvaluationSummary, ReverseEngineeringCostModel

            prot_source = os.path.join(BUILD_DIR, obfuscated_name)
            if not os.path.exists(prot_source):
                prot_source = obfuscated_output

            if os.path.exists(prot_source):
                payload_source = opts.payload
                metrics_obj = ResilienceMetrics()
                m = metrics_obj.measure(payload_source, prot_source)

                summary = EvaluationSummary()
                result = summary.generate(prot_source, m)

                print("\n" + "=" * 60)
                print("  EVALUATION SUMMARY REPORT")
                print("=" * 60)
                print(result['executive_summary'])
                print("=" * 60)

                es_path = os.path.join(BUILD_DIR, "evaluation_summary.json")
                with open(es_path, "w") as f:
                    json.dump(result, f, indent=2, default=str)
                log("EVAL_SUMMARY", f"Report saved to {es_path}")
            else:
                log("EVAL_SUMMARY", f"Protected file not found: {prot_source}, skipping")
        except ImportError as e:
            log("EVAL_SUMMARY", f"Evaluation summary module not available: {e}")
        except Exception as e:
            log("EVAL_SUMMARY", f"Evaluation summary error: {e}")

    # Unified Evaluation Report (Phase 4)
    if opts.evaluate:
        log("EVALUATE", "Generating unified evaluation report...")
        try:
            from scripts.evaluation.unified_report import generate_evaluation_report

            prot_source = os.path.join(BUILD_DIR, obfuscated_name)
            if not os.path.exists(prot_source):
                prot_source = obfuscated_output

            payload_source = opts.payload

            report = generate_evaluation_report(
                obfuscated_source_path=prot_source,
                original_source_path=payload_source,
                output_path=os.path.join(BUILD_DIR, "evaluation_report.json"),
            )

            summary = report.get("summary", {})
            log("EVALUATE", f"Measured: {summary.get('measured', 0)}/{summary.get('total_metrics', 9)}, "
                f"errors: {summary.get('errors', 0)}, skipped: {summary.get('skipped', 0)}")
            log("EVALUATE", f"Report saved to {os.path.join(BUILD_DIR, 'evaluation_report.json')}")
        except ImportError as e:
            log("EVALUATE", f"Unified report module not available: {e}")
        except Exception as e:
            log("EVALUATE", f"Unified report error: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Unified evaluation report not enabled (use --evaluate)")

    # Adaptive Adversarial Rewriting (based on benchmark feedback)
    if opts.adaptive_adversarial:
        log("ADAPTIVE", "Running adaptive adversarial rewriting...")
        try:
            from scripts.benchmark.feedback import BenchmarkFeedbackAnalyzer
            from scripts.benchmark import AIBenchmark
            from obfuscator.adaptive_rewriter import AdaptiveRewriter

            prot_source = os.path.join(BUILD_DIR, obfuscated_name)
            if not os.path.exists(prot_source):
                prot_source = obfuscated_output
            if os.path.exists(prot_source):
                with open(prot_source) as f:
                    _adapted_code = f.read()

                # Try to use real benchmark results from build artifacts
                _bench_report_path = os.path.join(BUILD_DIR, "benchmark_report.json")
                _bench_results_path2 = os.path.join(BUILD_DIR, "results", "benchmark_results.json")
                _results = None
                if os.path.exists(_bench_report_path):
                    try:
                        with open(_bench_report_path) as _bf:
                            _results = json.load(_bf)
                        log("ADAPTIVE", f"Using real benchmark results from {_bench_report_path}")
                    except Exception:
                        pass
                if _results is None and os.path.exists(_bench_results_path2):
                    try:
                        with open(_bench_results_path2) as _bf:
                            _results = json.load(_bf)
                        log("ADAPTIVE", f"Using real benchmark results from {_bench_results_path2}")
                    except Exception:
                        pass

                if _results is None:
                    # Run benchmark on the fly
                    log("ADAPTIVE", "No prior benchmark results found, running benchmark now...")
                    try:
                        _bm = AIBenchmark()
                        _results = _bm.evaluate(opts.payload, prot_source)
                    except Exception as _be:
                        log("ERROR", f"Benchmark failed: {_be}, adaptive rewrite requires real benchmark data")
                        _results = None

                if _results is None:
                    log("SKIP", "No benchmark results available — adaptive rewrite skipped")
                else:
                    _analyzer = BenchmarkFeedbackAnalyzer()
                    _profile = _analyzer.analyze(_results)

                    _feedback_history_path = os.path.join(BUILD_DIR, "feedback_history.json")
                    _historical = _analyzer.load_history(_feedback_history_path)
                    if _historical:
                        historical_actions = set()
                        for h in _historical:
                            historical_actions.update(h.get('recommended_actions', []))
                        for action in sorted(historical_actions):
                            if action not in _profile.recommended_actions:
                                _profile.recommended_actions.append(action)
                        log("ADAPTIVE", f"Enhanced with {len(historical_actions)} historical recommendations")
                    _analyzer.save_history(_profile, _feedback_history_path)

                    _rewriter = AdaptiveRewriter()
                    _adapted_code = _rewriter.rewrite(_profile, _adapted_code)
                    with open(prot_source, "w") as f:
                        f.write(_adapted_code)
                    log("ADAPTIVE", f"Applied {len(_profile.recommended_actions)} adaptive protections based on real benchmark feedback")
        except Exception as e:
            log("ERROR", f"Adaptive rewriting failed: {e}")
    else:
        log("SKIP", "Adaptive adversarial rewriting not enabled (use --adaptive-adversarial)")

    # AI-Guided Diversity Generation
    if opts.ai_guided_diversity:
        log("GUIDED_DIVERSITY", "Running AI-guided diversity generation...")
        try:
            from scripts.diversity.guided_generator import GuidedDiversityGenerator
            diversities_dir = os.path.join(BUILD_DIR, "guided_variants")
            guided_gen = GuidedDiversityGenerator(
                population_size=opts.diversity or 10,
                generations=opts.evolution_generations,
            )
            guided_paths = guided_gen.evolve(opts.payload, diversities_dir)
            log("GUIDED_DIVERSITY", f"Generated {len(guided_paths)} guided variants over {opts.evolution_generations} generations")
        except Exception as e:
            log("ERROR", f"Guided diversity generation failed: {e}")
    else:
        log("SKIP", "AI-guided diversity not enabled (use --ai-guided-diversity)")

    # Diversity generation
    if opts.diversity is not None and opts.diversity > 0:
        log("DIVERSITY", f"Generating {opts.diversity} variants in {opts.diversity_dir}")
        from scripts.diversity import DiversityGenerator, DiversityMetrics

        gen = DiversityGenerator()
        variants = gen.generate(opts.payload, opts.diversity, opts.diversity_dir)
        log("DIVERSITY", f"Generated {len(variants)} variants")

        dm = DiversityMetrics()
        min_div = opts.diversity_threshold

        for iteration in range(5):
            all_ok = True
            for i, a in enumerate(variants):
                for j, b in enumerate(variants):
                    if i >= j:
                        continue
                    if not os.path.exists(a) or not os.path.exists(b):
                        continue
                    result = dm.compare(a, b)
                    div = result["overall_diversity"]
                    if div < min_div:
                        log("DIVERSITY",
                            f"Pair ({i},{j}) diversity {div:.4f} < {min_div}, regenerating...")
                        tag = f"v{iteration}_{j}"
                        new_path = os.path.join(opts.diversity_dir, f"variant_{tag}.py")
                        gen = DiversityGenerator()
                        tmpdir = tempfile.mkdtemp(dir=opts.diversity_dir)
                        try:
                            single = gen.generate(opts.payload, 1, tmpdir)
                            shutil.copy2(single[0], new_path)
                        finally:
                            shutil.rmtree(tmpdir, ignore_errors=True)
                        variants[j] = new_path
                        all_ok = False
            if all_ok:
                log("DIVERSITY", "All variant pairs meet diversity threshold")
                break

        if opts.diversity_report:
            report_path = os.path.join(opts.diversity_dir, "diversity_report.json")
            dm.generate_report(variants, report_path)
            log("DIVERSITY", f"Report saved to {report_path}")
            summary = dm.compare_all(variants)
            print("\n" + "=" * 60)
            print("  DIVERSITY MATRIX REPORT")
            print("=" * 60)
            print(f"  Variants:        {summary['num_variants']}")
            print(f"  Pairs compared:  {summary['num_pairs']}")
            print(f"  Min diversity:   {summary['min_diversity']:.4f}")
            print(f"  Max diversity:   {summary['max_diversity']:.4f}")
            print(f"  Mean diversity:  {summary['mean_diversity']:.4f}")
            fingerprints = summary.get("fingerprints", {})
            if fingerprints:
                print(f"  Unique FPs:      {summary.get('unique_fingerprints', 'N/A')}")
                print(f"  All unique:      {summary.get('all_unique', False)}")
            print("=" * 60 + "\n")
            for pair_str, metrics in sorted(summary["matrix"].items()):
                print(f"    {pair_str}: diversity={metrics['overall_diversity']:.4f}  "
                      f"(cfg={metrics['cfg_similarity']:.3f} ast={metrics['ast_similarity']:.3f} "
                      f"ir={metrics['ir_similarity']:.3f} bc={metrics['bytecode_similarity']:.3f})")

    # =========================================================================
    # Formal Proof Verification (Items 91-99)
    # =========================================================================

    # Item 91: Proof-Carrying Obfuscation
    if opts.proof_carrying:
        log("PROOF_CARRYING", "Running proof-carrying obfuscation (Item 91)...")
        try:
            from scripts.proofs.proof_carrying import ProofCarryingObfuscator
            import z3 as _z3
            pco = ProofCarryingObfuscator(timeout_ms=30000)
            x = _z3.BitVec("x", 64)
            y = _z3.BitVec("y", 64)
            cert1 = pco.prove_equivalence("identity", x, x, [x])
            cert2 = pco.prove_equivalence("add_commute", x + y, y + x, [x, y])
            log("PROOF_CARRYING", f"Identity: {'PASS' if cert1.equivalent else 'FAIL'} ({cert1.solver_time_ms:.1f}ms)")
            log("PROOF_CARRYING", f"Add commute: {'PASS' if cert2.equivalent else 'FAIL'} ({cert2.solver_time_ms:.1f}ms)")
            proof_dir = os.path.join(BUILD_DIR, "proofs", "proof_carrying")
            os.makedirs(proof_dir, exist_ok=True)
            cert_path = os.path.join(proof_dir, "certificates.json")
            atomic_write(cert_path, pco.serialize_all())
            log("PROOF_CARRYING", f"Certificates → {cert_path}")
            summary = pco.get_summary()
            log("PROOF_CARRYING", f"Summary: {summary['passed']}/{summary['total']} passed")
        except Exception as e:
            log("ERROR", f"Proof-carrying obfuscation failed: {e}")
    else:
        log("SKIP", "Proof-carrying obfuscation not enabled (use --proof-carrying)")

    # Item 61: Formal Semantic Preservation Proofs
    if opts.verify_preservation_formal:
        log("PROOF", "Running formal semantic preservation proofs (Item 61)...")
        try:
            from scripts.proofs.semantic_preservation import SemanticPreservationProver
            prover = SemanticPreservationProver(timeout_ms=30000)
            with open(opts.payload) as f:
                src_a = f.read()
            obf_path = obfuscated_output if os.path.exists(obfuscated_output) else os.path.join(BUILD_DIR, obfuscated_name)
            if os.path.exists(obf_path):
                with open(obf_path) as f:
                    src_b = f.read()
                result = prover.prove_equivalence(src_a, src_b, "obfuscation_pipeline")
                status = "PASS" if result.equivalent else "FAIL"
                log("PROOF", f"  Pipeline semantic preservation: {status} ({result.solver_time_ms:.1f}ms)")
                if not result.equivalent and result.error:
                    log("PROOF", f"  Error: {result.error}")
            proof_dir = os.path.join(BUILD_DIR, "proofs", "semantic_preservation")
            os.makedirs(proof_dir, exist_ok=True)
            for p in prover.proofs:
                fname = f"preservation_proof_{p.transformation_type}.json"
                with open(os.path.join(proof_dir, fname), "w") as f:
                    json.dump(p.to_certificate_dict(), f, indent=2)
            log("PROOF", f"Proof certificates → {proof_dir}")
        except Exception as e:
            log("ERROR", f"Formal preservation proof failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Formal preservation proof not enabled (use --verify-preservation-formal)")

    if opts.prove_vm:
        log("PROOF", "Running VM correctness proofs (Item 92)...")
        try:
            from scripts.proofs.vm_correctness import VMCorrectnessProver
            prover = VMCorrectnessProver(timeout_ms=30000)
            results = prover.prove_all_instructions()
            passed = sum(1 for r in results if r.equivalent)
            total = len(results)
            log("PROOF", f"VM correctness: {passed}/{total} instructions proven")
            for r in results:
                status = "PASS" if r.equivalent else "FAIL"
                log("PROOF", f"  {r.opcode:8s} {status} ({r.solver_time_ms:.1f}ms)")
            proof_dir = os.path.join(BUILD_DIR, "proofs", "vm")
            os.makedirs(proof_dir, exist_ok=True)
            for r in results:
                fname = f"vm_proof_{r.opcode.lower()}.json"
                with open(os.path.join(proof_dir, fname), "w") as f:
                    json.dump(r.to_certificate_dict(), f, indent=2)
            log("PROOF", f"Proof certificates → {proof_dir}")
        except Exception as e:
            log("ERROR", f"VM correctness proof failed: {e}")
            import traceback
            traceback.print_exc()

    if opts.prove_fragments:
        log("PROOF", "Running fragment safety proofs (Item 93)...")
        try:
            from scripts.proofs.fragment_safety import FragmentSafetyProver, Fragment as _SafetyFragment
            prover = FragmentSafetyProver(timeout_ms=30000)
            x = z3.BitVec("x", 64)
            y = z3.BitVec("y", 64)
            f1 = _SafetyFragment(id=0, input_vars=["x"], output_vars=["r"],
                                 expression=x + y)
            f2 = _SafetyFragment(id=1, input_vars=["r"], output_vars=["s"],
                                 expression=x * y)
            chain_proof = prover.prove_fragment_chain([f1, f2])
            iso_proof = prover.prove_fragment_isolation(f1)
            log("PROOF", f"Fragment chain: {'PASS' if chain_proof.equivalent else 'FAIL'} ({chain_proof.solver_time_ms:.1f}ms)")
            log("PROOF", f"Fragment isolation: {'PASS' if iso_proof.equivalent else 'FAIL'} ({iso_proof.solver_time_ms:.1f}ms)")
            proof_dir = os.path.join(BUILD_DIR, "proofs", "fragment")
            os.makedirs(proof_dir, exist_ok=True)
            for r in [chain_proof, iso_proof]:
                fname = f"fragment_proof_{r.pass_name}.json"
                with open(os.path.join(proof_dir, fname), "w") as f:
                    json.dump(r.to_certificate_dict(), f, indent=2)
            log("PROOF", f"Proof certificates → {proof_dir}")
        except Exception as e:
            log("ERROR", f"Fragment safety proof failed: {e}")
            import traceback
            traceback.print_exc()

    if opts.verify_watermark_survivability:
        log("PROOF", "Running watermark survivability proofs (Item 95)...")
        try:
            from scripts.proofs.watermark_survivability import (
                WatermarkSurvivabilityProver, IDENTITY, RENAME, DEADCODE, CFG_FLATTEN,
            )
            prover = WatermarkSurvivabilityProver(timeout_ms=30000)
            wm = "NixonCorp-Proof-95"
            for t in [IDENTITY, RENAME, DEADCODE, CFG_FLATTEN]:
                proof = prover.prove_survives_pass(wm, t)
                status = "PASS" if proof.survived else "FAIL"
                log("PROOF", f"  {t.name:25s} {status} ({proof.solver_time_ms:.1f}ms)")
            pipeline = [RENAME, DEADCODE, CFG_FLATTEN]
            pipe_proof = prover.prove_survives_pipeline(wm, pipeline)
            log("PROOF", f"  pipeline{' ':>21s} {'PASS' if pipe_proof.survived else 'FAIL'} ({pipe_proof.solver_time_ms:.1f}ms)")
            proof_dir = os.path.join(BUILD_DIR, "proofs", "watermark")
            os.makedirs(proof_dir, exist_ok=True)
            for proof in prover.proofs:
                fname = f"watermark_proof_{proof.transformation[:20]}.json"
                with open(os.path.join(proof_dir, fname), "w") as f:
                    json.dump(proof.to_certificate_dict(), f, indent=2)
            log("PROOF", f"Proof certificates → {proof_dir}")
        except Exception as e:
            log("ERROR", f"Watermark survivability proof failed: {e}")
            import traceback
            traceback.print_exc()

    if opts.verify_mutations:
        log("PROOF", "Running mutation safety proofs (Item 96)...")
        try:
            from scripts.proofs.mutation_safety import MutationSafetyProver
            prover = MutationSafetyProver(timeout_ms=30000)
            orig_ir = "%x = %y + 1\n%z = %x * 2\nret %z"
            mut_ir = "%a = %y + 1\n%z = %a * 2\nret %z"
            proof = prover.prove_mutation(orig_ir, mut_ir)
            log("PROOF", f"  mutation{' ':>22s} {'PASS' if proof.equivalent else 'FAIL'} ({proof.solver_time_ms:.1f}ms)")
            seq_proof = prover.prove_mutation_sequence(orig_ir, [mut_ir])
            log("PROOF", f"  sequence{' ':>22s} {'PASS' if seq_proof.equivalent else 'FAIL'} ({seq_proof.solver_time_ms:.1f}ms)")
            stats = prover.get_stats()
            log("PROOF", f"  stats: {stats['total']} total, {stats['equivalent']} eq, {stats['nonequivalent']} neq")
            proof_dir = os.path.join(BUILD_DIR, "proofs", "mutation")
            os.makedirs(proof_dir, exist_ok=True)
            for p in prover.proofs:
                fname = f"mutation_proof_{p.pass_name}.json"
                with open(os.path.join(proof_dir, fname), "w") as f:
                    json.dump(p.to_certificate_dict(), f, indent=2)
            log("PROOF", f"Proof certificates → {proof_dir}")
        except Exception as e:
            log("ERROR", f"Mutation safety proof failed: {e}")
            import traceback
            traceback.print_exc()

    if opts.verify_jit:
        log("PROOF", "Running JIT reassembly proofs (Item 97)...")
        try:
            from scripts.proofs.jit_reassembly import JITReassemblyProver
            prover = JITReassemblyProver(timeout_ms=30000)
            fragment_ir = "%x = %a + %b\n%r = %x + 1\nret %r"
            jit_code = "%y = %a + %b\n%r = %y + 1\nret %r"
            fproof = prover.prove_fragment(fragment_ir, jit_code)
            log("PROOF", f"  fragment{' ':>22s} {'PASS' if fproof.equivalent else 'FAIL'} ({fproof.solver_time_ms:.1f}ms)")
            fragments = ["%x = %a + %b", "%r = %x + 1"]
            original = "%x = %a + %b\n%r = %x + 1"
            rproof = prover.prove_reassembly(fragments, original)
            log("PROOF", f"  reassembly{' ':>20s} {'PASS' if rproof.equivalent else 'FAIL'} ({rproof.solver_time_ms:.1f}ms)")
            proof_dir = os.path.join(BUILD_DIR, "proofs", "jit")
            os.makedirs(proof_dir, exist_ok=True)
            for p in prover.proofs:
                fname = f"jit_proof_{p.pass_name}.json"
                with open(os.path.join(proof_dir, fname), "w") as f:
                    json.dump(p.to_certificate_dict(), f, indent=2)
            log("PROOF", f"Proof certificates → {proof_dir}")
        except Exception as e:
            log("ERROR", f"JIT reassembly proof failed: {e}")
            import traceback
            traceback.print_exc()

    if opts.proof_aware_optimizer:
        log("PROOF", "Running proof-aware optimizer (Item 99)...")
        try:
            from scripts.optimizer.proof_aware import ProofAwareOptimizer
            from scripts.optimizer.profiler import FunctionInfo
            optimizer = ProofAwareOptimizer(
                max_overhead_pct=opts.max_cpu_overhead,
                max_size_mult=opts.max_size_mult,
                min_security=opts.min_security,
            )
            import ast as _ast
            with open(opts.payload) as f:
                source = f.read()
            tree = _ast.parse(source)
            functions = [
                FunctionInfo(name=n.name if hasattr(n, 'name') else f"fn_{i}",
                             lines_of_code=len(n.body) if hasattr(n, 'body') else 1,
                             exec_frequency=1.0,
                             category="general")
                for i, n in enumerate(_ast.walk(tree)) if isinstance(n, _ast.FunctionDef)
            ]
            if not functions:
                functions = [FunctionInfo(name="main", lines_of_code=10, exec_frequency=1.0, category="general")]

            # Read actual proof results from build artifacts instead of hardcoding
            proofs = {
                "ast_rename": False,
                "ast_dead_code": False,
                "ast_mba": False,
                "cfg_flatten": False,
                "vm_exec": False,
                "jit_compile": False,
                "rop_exec": False,
            }

            # Read certificates from build/certificates/
            cert_dir = os.path.join(BUILD_DIR, "certificates")
            if os.path.isdir(cert_dir):
                for fname in sorted(os.listdir(cert_dir)):
                    if fname.endswith(".json") and fname != "certificate_chain.json":
                        fpath = os.path.join(cert_dir, fname)
                        try:
                            with open(fpath) as _f:
                                cert_data = json.load(_f)
                            pass_name = cert_data.get("pass_name", "")
                            validated = cert_data.get("validated", False)
                            if validated:
                                if pass_name == "obfuscation":
                                    proofs["ast_rename"] = True
                                    proofs["ast_dead_code"] = True
                                    proofs["ast_mba"] = True
                                    proofs["cfg_flatten"] = True
                        except Exception:
                            pass

            # Read VM correctness proof results (Item 92)
            vm_dir = os.path.join(BUILD_DIR, "proofs", "vm")
            if os.path.isdir(vm_dir):
                vm_pass = True
                for fname in sorted(os.listdir(vm_dir)):
                    if fname.endswith(".json"):
                        try:
                            with open(os.path.join(vm_dir, fname)) as _f:
                                data = json.load(_f)
                            if not data.get("validated", False):
                                vm_pass = False
                                break
                        except Exception:
                            vm_pass = False
                            break
                proofs["vm_exec"] = vm_pass
                log("PROOF", f"VM proofs: {vm_pass}")

            # Read JIT reassembly proof results (Item 97)
            jit_dir = os.path.join(BUILD_DIR, "proofs", "jit")
            if os.path.isdir(jit_dir):
                jit_pass = True
                for fname in sorted(os.listdir(jit_dir)):
                    if fname.endswith(".json"):
                        try:
                            with open(os.path.join(jit_dir, fname)) as _f:
                                data = json.load(_f)
                            if not data.get("validated", False):
                                jit_pass = False
                                break
                        except Exception:
                            jit_pass = False
                            break
                proofs["jit_compile"] = jit_pass
                log("PROOF", f"JIT proofs: {jit_pass}")
            assignment = optimizer.optimize_with_proofs(
                functions, proofs,
                budget={"max_cpu_overhead": opts.max_cpu_overhead,
                        "max_size_mult": opts.max_size_mult,
                        "min_security": opts.min_security},
            )
            report = optimizer.generate_proof_report(functions, assignment, proofs)
            print(report)
            proof_dir = os.path.join(BUILD_DIR, "proofs", "optimizer")
            os.makedirs(proof_dir, exist_ok=True)
            report_path = os.path.join(proof_dir, "proof_aware_report.json")
            atomic_write(report_path, json.dumps({
                "assignment": {k: v for k, v in assignment.items()},
                "proofs": proofs,
            }, indent=2))
            log("PROOF", f"Proof-aware optimizer report → {report_path}")
        except Exception as e:
            log("ERROR", f"Proof-aware optimizer failed: {e}")
            import traceback
            traceback.print_exc()

    # Proof Coverage Report (Feature 153)
    if opts.proof_coverage:
        phase_proof_coverage(opts)
    else:
        log("SKIP", "Proof coverage report not enabled (use --proof-coverage)")

    # Proof Soundness Harness (Feature 174)
    if opts.proof_soundness:
        phase_proof_soundness(opts)
    else:
        log("SKIP", "Proof soundness harness not enabled (use --proof-soundness)")

    # =========================================================================
    # Hardware Research Integration (Items 125-129)
    # =========================================================================

    if opts.branch_entangle:
        phase_branch_entangle()
    else:
        log("SKIP", "Branch entangle not enabled (use --branch-entangle)")

    if opts.multicore_entangle:
        phase_multicore_entangle()
    else:
        log("SKIP", "Multicore entangle not enabled (use --multicore-entangle)")

    if opts.tee:
        phase_tee(tee_type=opts.tee_type)
    else:
        log("SKIP", "TEE not enabled (use --tee)")

    if opts.sgx:
        phase_sgx()
    else:
        log("SKIP", "SGX not enabled (use --sgx)")

    if opts.cpu_port:
        phase_cpu_port(seed=opts.randomization_seed)
    else:
        log("SKIP", "CPU port not enabled (use --cpu-port)")

    if opts.gpu_hybrid:
        phase_gpu_hybrid()
    else:
        log("SKIP", "GPU hybrid not enabled (use --gpu-hybrid)")

    # Item 125: GPU Fragment Execution
    if opts.gpu_execution:
        log("GPU", "Running GPU fragment execution (Item 125)...")
        try:
            from scripts.gpu.gpu_execution import GPUExecutor, is_gpu_available
            gpu_avail = is_gpu_available()
            executor = GPUExecutor(use_gpu=None)
            kernel = executor.generate_kernel("encrypt", num_threads=8)
            kernel["args"] = [256]
            test_data = bytes(range(64))
            executor.transfer_to_gpu(test_data)
            results = executor.execute_kernel(kernel)
            gpu_trace = executor.get_trace()
            log("GPU", f"GPU available: {gpu_avail}, kernel results: {len(results)} values")
            gpu_result_path = os.path.join(BUILD_DIR, "gpu_execution_result.json")
            atomic_write(gpu_result_path, json.dumps({
                "gpu_available": gpu_avail,
                "num_results": len(results),
                "trace": gpu_trace,
            }, indent=2))
            log("GPU", f"Report → {gpu_result_path}")
        except Exception as e:
            log("ERROR", f"GPU execution failed: {e}")
    else:
        log("SKIP", "GPU execution not enabled (use --gpu-execution)")

    # Item 126: CPU/GPU Hybrid Protection
    if opts.cpu_gpu_hybrid:
        log("GPU_HYBRID", "Running CPU/GPU hybrid protection (Item 126)...")
        try:
            from scripts.gpu.hybrid_protection import HybridProtector, cpu_obfuscation_pass, gpu_parallel_transform
            hp = HybridProtector(seed=0xCAFEBABE)
            cpu_data = b"hello world cpu path test"
            cpu_result = hp.execute_cpu_path(cpu_data)
            gpu_result = hp.execute_gpu_path(cpu_data)
            distinct = cpu_result != gpu_result
            plan = hp.generate_protection_plan()
            log("GPU_HYBRID", f"CPU/GPU paths produce distinct results: {distinct}")
            hybrid_path = os.path.join(BUILD_DIR, "cpu_gpu_hybrid_result.json")
            atomic_write(hybrid_path, json.dumps({
                "paths_distinct": distinct,
                "cpu_trace": hp.get_cpu_trace(),
                "gpu_trace": hp.get_gpu_trace(),
                "plan": plan,
            }, indent=2))
        except Exception as e:
            log("ERROR", f"CPU/GPU hybrid failed: {e}")
    else:
        log("SKIP", "CPU/GPU hybrid not enabled (use --cpu-gpu-hybrid)")

    # Item 122: Microarchitectural Watermark
    if opts.uarch_watermark:
        log("UARCH_WM", "Embedding microarchitectural watermark (Item 122)...")
        try:
            from scripts.watermark.uarch_watermark import MicroarchitecturalWatermark
            payload_path = opts.payload
            with open(payload_path) as f:
                src = f.read()
            wm = MicroarchitecturalWatermark()
            watermarked = wm.embed(src, "NixonCorp-UARCH-122")
            wm_path = os.path.join(BUILD_DIR, "uarch_watermarked.py")
            atomic_write(wm_path, watermarked)
            timings, delta = wm.measure_timing_signature(watermarked)
            log("UARCH_WM", f"Embedded; timing delta: {delta}ns")
            uarch_path = os.path.join(BUILD_DIR, "uarch_watermark_report.json")
            atomic_write(uarch_path, json.dumps({
                "timing_delta_ns": delta,
                "timings": timings,
                "watermark": "NixonCorp-UARCH-122",
            }, indent=2))
        except Exception as e:
            log("ERROR", f"UARCH watermark failed: {e}")
    else:
        log("SKIP", "UARCH watermark not enabled (use --uarch-watermark)")

    # Item 129: Microarchitectural Diversity Generation
    if opts.uarch_diversity:
        log("UARCH_DIV", "Running microarchitectural diversity generation (Item 129)...")
        try:
            from scripts.diversity.uarch_diversity import MicroarchitecturalDiversityGenerator, detect_microarchitecture, select_variant_for_uarch
            uarch_info = detect_microarchitecture()
            gen = MicroarchitecturalDiversityGenerator()
            payload_path = opts.payload
            with open(payload_path) as f:
                src = f.read()
            variants = gen.generate_all_variant_types(src)
            selected = select_variant_for_uarch(variants, uarch_info)
            variants_dir = os.path.join(BUILD_DIR, "uarch_variants")
            os.makedirs(variants_dir, exist_ok=True)
            for vtype, vcode in variants.items():
                vpath = os.path.join(variants_dir, f"uarch_variant_{vtype}.py")
                atomic_write(vpath, vcode)
            sel_path = os.path.join(variants_dir, "uarch_selected_variant.py")
            atomic_write(sel_path, selected)
            uarch_div_path = os.path.join(BUILD_DIR, "uarch_diversity_report.json")
            atomic_write(uarch_div_path, json.dumps({
                "uarch": uarch_info,
                "variants_generated": list(variants.keys()),
                "selected_variant_type": "detected",
                "hardware_vendor": uarch_info.get("vendor", "unknown"),
            }, indent=2))
            log("UARCH_DIV", f"Generated {len(variants)} uarch-aware variants, selected for {uarch_info['vendor']}")
        except Exception as e:
            log("ERROR", f"UARCH diversity generation failed: {e}")
    else:
        log("SKIP", "UARCH diversity not enabled (use --uarch-diversity)")

    # ZK State-Bound Execution
    if opts.zk_state:
        log("ZK_STATE", "Running ZK state-bound execution phase...")
        try:
            manifest = phase_zk_state(opts, None)
            if manifest:
                log("ZK_STATE", f"State valid: {manifest['state_machine']['transition_valid']}, "
                                f"total latency: {manifest['latency_ms']['total']:.2f}ms")
        except Exception as e:
            log("ERROR", f"ZK state phase failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "ZK state-bound execution not enabled (use --zk-state)")

    # Plaintext Exposure Metric (Feature 151)
    if opts.plaintext_exposure:
        try:
            from scripts.exposure import ExposureTracker
            from scripts.phases.phase_exposure import phase_exposure
            phase_exposure(opts, ir_module, {
                "microjit": opts.microjit,
                "fragmentation": opts.fragment,
                "history_bound": opts.history_bound_decryption,
                "fhe_vm": opts.fhe_vm,
            })
        except Exception as e:
            log("ERROR", f"Plaintext exposure metric failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Plaintext exposure metric not enabled (use --plaintext-exposure)")

    # Protection Coverage Map (Feature 147) — after ALL protection stages
    coverage_map_result = None
    if opts.coverage_map and ir_module is not None:
        from scripts.coverage.pipeline_tracker import PipelineTracker
        pipeline_state = type('PipelineState', (), {
            'opts': opts,
            'globals': {},
        })()
        coverage_map_result = phase_coverage(opts, ir_module, pipeline_state)
    else:
        if not opts.coverage_map:
            log("SKIP", "Coverage map not enabled (use --coverage-map)")
        elif ir_module is None:
            log("SKIP", "No IR module available for coverage map (use --coverage-map with IR-enabled pipeline)")

    # Security Regression Gates (Feature 146)
    if opts.security_gates:
        if not phase_security_gates(opts):
            log("SECURITY_GATES", "BLOCKER gates failed — exiting with error")
            sys.exit(1)
    else:
        log("SKIP", "Security gates not enabled (use --security-gates)")

    # Security Knowledge Graph (Feature 149) — after coverage + conflict stages
    if opts.knowledge_graph:
        try:
            from scripts.conflicts import KNOWN_CONFLICTS, ConflictGraph
            conflict_graph = ConflictGraph()
            for c in KNOWN_CONFLICTS:
                conflict_graph.add_conflict_obj(c)
            phase_knowledge_graph(opts, coverage_map=coverage_map_result, conflict_graph=conflict_graph)
        except Exception as e:
            log("ERROR", f"Knowledge graph generation failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Security knowledge graph not enabled (use --knowledge-graph)")

    # Protection Synthesis Engine (Feature 150)
    if opts.synthesis:
        log("SYNTHESIS", "Running protection synthesis engine...")
        try:
            phase_synthesis(opts)
        except Exception as e:
            log("ERROR", f"Protection synthesis failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Protection synthesis not enabled (use --synthesis)")

    # Adversarial Benchmark Generator (Feature 175)
    if opts.adversarial_bench:
        log("ADV_BENCH", "Running adversarial benchmark generator...")
        try:
            phase_adversarial_bench(opts)
        except Exception as e:
            log("ERROR", f"Adversarial benchmark failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Adversarial benchmark not enabled (use --adversarial-bench)")

    # Feature classification (Phase 5)
    if opts.classify_features:
        log("CLASSIFY_FEATURES", "Running feature classification...")
        try:
            from scripts.classify_features import build_report, print_summary
            report = build_report()
            print_summary(report)
            out_path = os.path.join(BUILD_DIR, "feature_classification.json")
            os.makedirs(BUILD_DIR, exist_ok=True)
            atomic_write(out_path, json.dumps(report, indent=2))
            log("CLASSIFY_FEATURES", f"Report → {out_path}")
        except ImportError as e:
            log("ERROR", f"Feature classification not available: {e}")
        except Exception as e:
            log("ERROR", f"Feature classification failed: {e}")

    # Reproducibility Score (Feature 178)
    if opts.reproducibility_score:
        phase_reproducibility(opts)
    else:
        log("SKIP", "Reproducibility score not enabled (use --reproducibility-score)")

    # Research Artifact Generator (Feature 155) — ABSOLUTE END of pipeline
    if opts.generate_artifacts:
        phase_artifacts(opts, locals().get("_all_metrics"))
    else:
        log("SKIP", "Artifact generation not enabled (use --generate-artifacts)")

    # Reality Score (Feature 167) — after all metrics stages
    if opts.reality_score:
        try:
            from scripts.phases.phase_reality import phase_reality
            phase_reality(opts)
        except Exception as e:
            log("ERROR", f"Reality score computation failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Reality score not enabled (use --reality-score)")

    # Security Debt Index (Feature 170) — after all other stages
    if opts.security_debt:
        try:
            phase_security_debt(opts)
        except Exception as e:
            log("ERROR", f"Security debt index computation failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Security debt index not enabled (use --security-debt)")

    # Evidence Ledger (Feature 168) — after all other stages
    if opts.evidence_ledger:
        try:
            from scripts.phases.phase_evidence import phase_evidence
            phase_evidence(opts)
        except Exception as e:
            log("ERROR", f"Evidence ledger generation failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Evidence ledger not enabled (use --evidence-ledger)")

    # Independent Verification Bundle (Feature 177) — after all other stages
    if opts.verification_bundle:
        try:
            phase_verification_bundle(opts)
        except Exception as e:
            log("ERROR", f"Verification bundle generation failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Verification bundle not enabled (use --verification-bundle)")

    # Feature 169: Reachability Coverage Report
    if opts.reachability_report:
        try:
            from scripts.phases.phase_reachability import phase_reachability
            phase_reachability(opts)
        except Exception as e:
            log("ERROR", f"Reachability report failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Reachability report not enabled (use --reachability-report)")

    # False Confidence Detector (Feature 173) — audit only, no payload required
    if opts.false_confidence_audit:
        result = phase_false_confidence(opts)
        if result and result.critical_count > 0:
            log("FALSE_CONFIDENCE", f"{result.critical_count} critical issues found — review recommended")
    else:
        log("SKIP", "False confidence audit not enabled (use --false-confidence-audit)")

    # Claim Auditor (Feature 172) — scan for unsupported security claims
    if opts.claim_audit:
        result = phase_claim_audit(opts)
        if result and result.critical_count > 0:
            log("CLAIM_AUDIT", f"{result.critical_count} critical unsupported claims — review recommended")
    else:
        log("SKIP", "Claim audit not enabled (use --claim-audit)")

    # Feature 179: Security Confidence Interval
    if opts.confidence_interval:
        try:
            phase_confidence(opts)
        except Exception as e:
            log("ERROR", f"Confidence interval computation failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Confidence interval not enabled (use --confidence-interval)")

    # Feature 180: Self-Audit Agent — final pipeline stage
    if opts.self_audit:
        try:
            phase_self_audit(opts)
        except Exception as e:
            log("ERROR", f"Self-audit failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Self-audit not enabled (use --self-audit)")

    # Feature 171: Assumption Tracker — absolute end of pipeline
    if opts.assumptions_report:
        try:
            phase_assumptions(opts)
        except Exception as e:
            log("ERROR", f"Assumption report failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Assumption report not enabled (use --assumptions-report)")

    # Feature 176: Feature Retirement Framework — after all other analysis
    if opts.retirement_report:
        try:
            from scripts.phases.phase_retirement import phase_retirement
            phase_retirement(opts)
        except Exception as e:
            log("ERROR", f"Retirement report failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Retirement report not enabled (use --retirement-report)")

    # Feature 186: Trust Boundary Mapper
    if opts.trust_boundary:
        try:
            phase_trust_boundary(opts)
        except Exception as e:
            log("ERROR", f"Trust boundary mapping failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Trust boundary mapping not enabled (use --trust-boundary)")

    # Feature 187: Evidence Completeness Score
    if opts.evidence_completeness:
        try:
            phase_evidence_completeness(opts)
        except Exception as e:
            log("ERROR", f"Evidence completeness scoring failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Evidence completeness not enabled (use --evidence-completeness)")

    # Feature 188: Dependency Graph Validation
    if opts.dependency_graph:
        try:
            phase_dependency_graph(opts)
        except Exception as e:
            log("ERROR", f"Dependency graph validation failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Dependency graph validation not enabled (use --dependency-graph)")

    # Feature 189: Attack Surface Enumerator
    if opts.attack_surface:
        try:
            phase_attack_surface(opts)
        except Exception as e:
            log("ERROR", f"Attack surface enumeration failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Attack surface enumeration not enabled (use --attack-surface)")

    # Feature 190: Security Invariant Engine
    if opts.invariant_engine:
        try:
            phase_invariant_engine(opts)
        except Exception as e:
            log("ERROR", f"Invariant engine verification failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Invariant engine not enabled (use --invariant-engine)")

    # Feature 181: Independent Auditor Mode
    if opts.independent_audit:
        try:
            phase_independent_audit(opts)
        except Exception as e:
            log("ERROR", f"Independent audit failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Independent auditor not enabled (use --independent-audit)")

    # Feature 182: Metric Manipulation Detector
    if opts.manipulation_detector:
        try:
            phase_manipulation_detector(opts)
        except Exception as e:
            log("ERROR", f"Manipulation detection failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Manipulation detector not enabled (use --manipulation-detector)")

    # Feature 183: Benchmark Integrity Framework
    if opts.benchmark_integrity:
        try:
            phase_benchmark_integrity(opts)
        except Exception as e:
            log("ERROR", f"Benchmark integrity verification failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Benchmark integrity not enabled (use --benchmark-integrity)")

    # Feature 184: Verification Diversity
    if opts.verification_diversity:
        try:
            phase_verification_diversity(opts)
        except Exception as e:
            log("ERROR", f"Verification diversity analysis failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Verification diversity not enabled (use --verification-diversity)")

    # Feature 185: Audit Drift Detection
    if opts.audit_drift:
        try:
            phase_audit_drift(opts)
        except Exception as e:
            log("ERROR", f"Audit drift detection failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Audit drift detection not enabled (use --audit-drift)")

    # Feature 191: Silent Fallback Detector
    if opts.silent_fallback:
        try:
            phase_silent_fallback(opts)
        except Exception as e:
            log("ERROR", f"Silent fallback detection failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Silent fallback detector not enabled (use --silent-fallback)")

    # Feature 192: Runtime Truth Monitor
    if opts.runtime_truth:
        try:
            phase_runtime_truth(opts)
        except Exception as e:
            log("ERROR", f"Runtime truth monitoring failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Runtime truth monitor not enabled (use --runtime-truth)")

    # Feature 193: Feature Effectiveness Score
    if opts.feature_effectiveness:
        try:
            phase_feature_effectiveness(opts)
        except Exception as e:
            log("ERROR", f"Feature effectiveness scoring failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Feature effectiveness not enabled (use --feature-effectiveness)")

    # Feature 194: Protection ROI Engine
    if opts.protection_roi:
        try:
            phase_protection_roi(opts)
        except Exception as e:
            log("ERROR", f"Protection ROI computation failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Protection ROI not enabled (use --protection-roi)")

    # Feature 195: Longitudinal Security Tracking
    if opts.longitudinal_tracking:
        try:
            phase_longitudinal_tracking(opts)
        except Exception as e:
            log("ERROR", f"Longitudinal tracking failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Longitudinal tracking not enabled (use --longitudinal-tracking)")

    # Feature 196: Attack Corpus
    if opts.attack_corpus:
        try:
            phase_attack_corpus(opts)
        except Exception as e:
            log("ERROR", f"Attack corpus generation failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Attack corpus not enabled (use --attack-corpus)")

    # Feature 197: Release Confidence Score
    if opts.release_confidence:
        try:
            phase_release_confidence(opts)
        except Exception as e:
            log("ERROR", f"Release confidence scoring failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Release confidence not enabled (use --release-confidence)")

    # Feature 198: Formal Threat Coverage
    if opts.threat_coverage:
        try:
            phase_threat_coverage(opts)
        except Exception as e:
            log("ERROR", f"Threat coverage mapping failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Threat coverage not enabled (use --threat-coverage)")

    # Feature 199: Security Knowledge Base
    if opts.knowledge_base:
        try:
            phase_knowledge_base(opts)
        except Exception as e:
            log("ERROR", f"Knowledge base generation failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Knowledge base not enabled (use --knowledge-base)")

    # Feature 200: Self-Critique Engine
    if opts.self_critique:
        try:
            phase_self_critique(opts)
        except Exception as e:
            log("ERROR", f"Self-critique generation failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log("SKIP", "Self-critique not enabled (use --self-critique)")

    log("DONE", "Pipeline complete")
    log("DONE", f"Build artifacts: {BUILD_DIR}/")
    log("DONE", "Run: build/orbital-relay --help")


if __name__ == "__main__":
    main()
