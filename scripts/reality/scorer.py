"""
reality/scorer.py — Reality Score computation engine (F167)

Purpose:
    Evaluates each feature from the FEATURE_REGISTRY across four dimensions:
    implementation existence, CLI/phase reachability, runtime execution evidence,
    and attack-impact data. Produces a weighted per-feature reality score.

Architectural Role:
    Core scoring module consumed by the reality __init__.py aggregation layer.
    Reads pipeline artefacts from the build directory (manifest, metrics,
    red-team reports, benchmark data, security-gate results).

Security Relevance:
    Prevents "security theatre" by ensuring every claimed protection has
    verifiable artefacts (source, phase file, test, benchmark, runtime trace,
    attack result) backing it up.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR


@dataclass
class FeatureReality:
    """Per-feature reality breakdown across four scoring dimensions.

    Attributes:
        feature_name: Human-readable feature identifier.
        implemented_score: Weighted evidence that source/phases/tests/benchmarks exist.
        reachability_score: Evidence that the feature is wired into build.py CLI.
        runtime_execution_score: Evidence the feature executes at runtime (manifest + tests).
        attack_impact_score: Evidence from red-team, metrics, and security gates.
        reality_score: Composite weighted average (25 % each dimension).
        evidence_count: Number of distinct evidence categories present.
        missing_evidence: List of missing evidence labels for diagnostics.
    """
    feature_name: str
    implemented_score: float = 0.0
    reachability_score: float = 0.0
    runtime_execution_score: float = 0.0
    attack_impact_score: float = 0.0
    reality_score: float = 0.0
    evidence_count: int = 0
    missing_evidence: List[str] = field(default_factory=list)


@dataclass
class RealityReport:
    """Aggregate report across all registered features.

    Attributes:
        overall_reality_score: Mean of all per-feature reality scores.
        feature_scores: Mapping from feature name to FeatureReality.
        grade: Letter grade derived from the overall score.
        critical_gaps: Features with reality_score < 25 (urgent attention).
        timestamp: ISO-8601 generation timestamp.
    """

    overall_reality_score: float = 0.0
    feature_scores: Dict[str, FeatureReality] = field(default_factory=dict)
    grade: str = "F"
    critical_gaps: List[str] = field(default_factory=list)
    timestamp: str = ""


def score_to_grade(score: float) -> str:
    """Map a numeric score to a letter grade (A–F)."""
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 50:
        return "C"
    if score >= 25:
        return "D"
    return "F"


# ------------------------------------------------------------------ #
# Registry of every known protection feature. Each entry carries the
# feature name, optional module/class path, CLI flag, and pipeline phase.
# Used as the ground-truth list for reality scoring.
# ------------------------------------------------------------------ #
FEATURE_REGISTRY: List[Dict[str, Any]] = [
    {"name": "CFG Flattening", "module": "obfuscator.core", "class": None, "cli_flag": "--cfg-flatten", "phase": "phase01_obfuscate"},
    {"name": "Opaque Predicates", "module": "obfuscator.core", "class": None, "cli_flag": "--opaque-predicates", "phase": "phase01_obfuscate"},
    {"name": "MBA Substitutions", "module": "obfuscator.core", "class": None, "cli_flag": "--mba-subs", "phase": "phase01_obfuscate"},
    {"name": "Bogus Exceptions", "module": "obfuscator.core", "class": None, "cli_flag": "--bogus-exceptions", "phase": "phase01_obfuscate"},
    {"name": "String Fragmentation", "module": "obfuscator.core", "class": None, "cli_flag": "--fragment-strings", "phase": "phase01_obfuscate"},
    {"name": "SMT Validation", "module": "scripts.validation.smt_validator", "class": "SMTValidator", "cli_flag": "--validate", "phase": None},
    {"name": "Adversarial Injection", "module": None, "class": None, "cli_flag": "--adversarial-injection", "phase": "phase09_adversarial"},
    {"name": "Adversarial Loop", "module": None, "class": None, "cli_flag": "--adversarial-loop", "phase": "phase09_adversarial"},
    {"name": "ROP Compilation", "module": "scripts.rop.rop_compiler", "class": "RopCompiler", "cli_flag": "--rop", "phase": "phase08_rop"},
    {"name": "CFG Mutation", "module": None, "class": None, "cli_flag": "--cfg-mutation", "phase": "phase11_cfg_mutation"},
    {"name": "Class Dispatch", "module": None, "class": None, "cli_flag": "--class-dispatch", "phase": "phase_class_dispatch"},
    {"name": "Rolling Keys", "module": None, "class": None, "cli_flag": "--rolling-keys", "phase": "phase_rolling_keys"},
    {"name": "SSA Mutation", "module": None, "class": None, "cli_flag": "--ssa-mutation", "phase": "phase13_ssa_mutation"},
    {"name": "State ISA", "module": None, "class": None, "cli_flag": "--state-isa", "phase": "phase_state_isa"},
    {"name": "Per-Exec Recompile", "module": None, "class": None, "cli_flag": "--per-exec-recompile", "phase": "phase14_per_exec_recompile"},
    {"name": "Self-Healing", "module": None, "class": None, "cli_flag": "--self-healing", "phase": "phase15_self_healing"},
    {"name": "Code Genome", "module": None, "class": None, "cli_flag": "--code-genome", "phase": "phase16_code_genome"},
    {"name": "Structure Randomization", "module": None, "class": None, "cli_flag": "--struct-randomization", "phase": "phase17_struct_random"},
    {"name": "History-Bound Decryption", "module": None, "class": None, "cli_flag": "--history-bound-decryption", "phase": "phase12_history_bound"},
    {"name": "HPC Integration", "module": None, "class": None, "cli_flag": "--hpc", "phase": "phase18_hpc"},
    {"name": "HPC Key Derivation", "module": None, "class": None, "cli_flag": "--hpc-key", "phase": "phase19_hpc_key"},
    {"name": "Emulator Detection", "module": None, "class": None, "cli_flag": "--hpc-detect", "phase": "phase20_hpc_detect"},
    {"name": "Hardware Entropy", "module": None, "class": None, "cli_flag": "--hw-entropy", "phase": "phase21_hw_entropy"},
    {"name": "Cache-Bound Execution", "module": None, "class": None, "cli_flag": "--cache-bound", "phase": "phase22_cache_bound"},
    {"name": "Branch Entanglement", "module": None, "class": None, "cli_flag": "--branch-entangle", "phase": "phase23_branch_entangle"},
    {"name": "Multi-Core Entanglement", "module": None, "class": None, "cli_flag": "--multicore-entangle", "phase": "phase24_multicore_entangle"},
    {"name": "TEE Partition", "module": None, "class": None, "cli_flag": "--tee", "phase": "phase25_tee"},
    {"name": "SGX Enclave", "module": None, "class": None, "cli_flag": "--sgx", "phase": "phase26_sgx"},
    {"name": "CPU Port", "module": None, "class": None, "cli_flag": "--cpu-port", "phase": "phase27_cpu_port"},
    {"name": "GPU Hybrid", "module": None, "class": None, "cli_flag": "--gpu-hybrid", "phase": "phase28_gpu_hybrid"},
    {"name": "Micro-Fragment", "module": "scripts.fragment.micro_fragment", "class": "MicroFragmentExecutor", "cli_flag": "--micro-fragment", "phase": "phase30_micro_fragment"},
    {"name": "Poly-Engine", "module": "scripts.environment.poly_engine", "class": "EnvironmentalPolyEngine", "cli_flag": "--poly-engine", "phase": "phase31_poly_engine"},
    {"name": "Temporal Keys", "module": "scripts.binding.temporal_key", "class": "TemporalKeyChain", "cli_flag": "--temporal-keys", "phase": "phase32_temporal_keys"},
    {"name": "Payload Dispersal", "module": "scripts.payload.dispersal", "class": "PayloadDisperser", "cli_flag": "--payload-dispersal", "phase": "phase33_payload_dispersal"},
    {"name": "FHE-VM", "module": None, "class": None, "cli_flag": "--fhe-vm", "phase": "phase_fhe_vm"},
    {"name": "IO Research", "module": None, "class": None, "cli_flag": "--io-research", "phase": "phase_io_research"},
    {"name": "Kernel Assist", "module": None, "class": None, "cli_flag": "--kernel-assist", "phase": "phase_kernel_assist"},
    {"name": "ZK State", "module": None, "class": None, "cli_flag": "--zk-state", "phase": "phase_zk_state"},
    {"name": "Proof Coverage", "module": None, "class": None, "cli_flag": "--proof-coverage", "phase": "phase_proof_coverage"},
    {"name": "Semantic Leakage", "module": "scripts.phases.phase_leakage", "class": None, "cli_flag": "--semantic-leakage", "phase": "phase_leakage"},
    {"name": "Plaintext Exposure", "module": "scripts.exposure.tracker", "class": "ExposureTracker", "cli_flag": "--plaintext-exposure", "phase": "phase_exposure"},
    {"name": "Coverage Map", "module": "scripts.coverage.coverage_map", "class": None, "cli_flag": "--coverage-map", "phase": "phase_coverage"},
    {"name": "Security Gates", "module": "scripts.security_regression", "class": "RegressionChecker", "cli_flag": "--security-gates", "phase": "phase_security_gates"},
    {"name": "Knowledge Graph", "module": "scripts.knowledge_graph", "class": None, "cli_flag": "--knowledge-graph", "phase": "phase_knowledge_graph"},
    {"name": "Synthesis Engine", "module": "scripts.synthesis", "class": "SynthesisEngine", "cli_flag": "--synthesis", "phase": "phase_synthesis"},
    {"name": "Attack Replay", "module": "scripts.attack_replay.replay", "class": "AttackReplay", "cli_flag": "--capture-attacks", "phase": "phase_attack_replay"},
    {"name": "Artifact Generator", "module": None, "class": None, "cli_flag": "--generate-artifacts", "phase": "phase_artifacts"},
    {"name": "Red Team Pipeline", "module": None, "class": None, "cli_flag": "--red-team", "phase": "phase_redteam"},
]


def _check_source_exists(module_path: str, class_name: Optional[str] = None) -> bool:
    """Return True if the module file (or its __init__.py) exists on disk.

    Optionally checks that a given class name appears inside the file.
    """
    if module_path is None:
        return False
    file_path = os.path.join(_ROOT, *module_path.split(".")) + ".py"
    if not os.path.isfile(file_path):
        file_path = os.path.join(_ROOT, *module_path.split("."), "__init__.py")
        if not os.path.isfile(file_path):
            return False
    if class_name is None:
        return True
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        return f"class {class_name}" in content or f"def {class_name}" in content
    except OSError:
        return False


def _check_cli_flag_exists(feature: Dict[str, Any], build_py_source: str) -> bool:
    """Return True if the feature's CLI flag string appears in build.py source."""
    flag = feature.get("cli_flag", "")
    if not flag:
        return False
    return flag in build_py_source


def _check_cli_wired(feature: Dict[str, Any], build_py_source: str) -> bool:
    """Return True if the CLI flag var (opts.xxx) is referenced in build.py."""
    flag = feature.get("cli_flag", "")
    if not flag:
        phase_name = feature.get("phase", "")
        return phase_name in build_py_source if phase_name else False
    flag_var = flag.lstrip("-").replace("-", "_")
    return f"opts.{flag_var}" in build_py_source


def _check_phase_exists(feature: Dict[str, Any]) -> bool:
    """Return True if the feature's pipeline phase file exists on disk."""
    phase_name = feature.get("phase", "")
    if not phase_name:
        return False
    phase_file = os.path.join(_ROOT, "scripts", "phases", f"{phase_name}.py")
    return os.path.isfile(phase_file)


def _load_manifest() -> Dict[str, Any]:
    """Load the build manifest JSON from BUILD_DIR."""
    manifest_path = os.path.join(BUILD_DIR, "manifest.json")
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _load_metrics_report() -> Dict[str, Any]:
    """Load the metrics report JSON from BUILD_DIR."""
    metrics_path = os.path.join(BUILD_DIR, "metrics_report.json")
    if os.path.isfile(metrics_path):
        try:
            with open(metrics_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _load_redteam_report() -> Dict[str, Any]:
    """Load the red-team attack report JSON from BUILD_DIR/redteam/."""
    rt_path = os.path.join(BUILD_DIR, "redteam", "attack_report.json")
    if os.path.isfile(rt_path):
        try:
            with open(rt_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _load_benchmark_report() -> Dict[str, Any]:
    """Load the benchmark report JSON from BUILD_DIR."""
    bm_path = os.path.join(BUILD_DIR, "benchmark_report.json")
    if os.path.isfile(bm_path):
        try:
            with open(bm_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _load_security_gate_report() -> Dict[str, Any]:
    """Load the security-gate report JSON from BUILD_DIR."""
    sg_path = os.path.join(BUILD_DIR, "security_gate_report.json")
    if os.path.isfile(sg_path):
        try:
            with open(sg_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _check_test_exists(feature_name: str) -> bool:
    """Return True if any test file name loosely matches the feature name."""
    test_name = feature_name.lower().replace(" ", "_").replace("-", "_").replace("/", "_")
    test_dir = os.path.join(_ROOT, "tests")
    if not os.path.isdir(test_dir):
        return False
    for fname in os.listdir(test_dir):
        if fname.endswith(".py") and fname != "__init__.py":
            if test_name in fname.lower().replace("test_", "").replace("_test", ""):
                return True
    return False


def _check_benchmark_exists(feature_name: str) -> bool:
    """Return True if any bench_*.py file name loosely matches the feature name."""
    bench_name = feature_name.lower().replace(" ", "_").replace("-", "_").replace("/", "_")
    test_dir = os.path.join(_ROOT, "tests")
    if not os.path.isdir(test_dir):
        return False
    for fname in os.listdir(test_dir):
        if fname.startswith("bench_") and fname.endswith(".py"):
            if bench_name in fname.lower():
                return True
    return False


def compute_feature_reality(feature: Dict[str, Any], pipeline_state: Dict[str, Any]) -> FeatureReality:
    """Compute the four-dimensional reality score for a single feature.

    Scoring breakdown:
        - implementation (30 % module, 30 % phase, 25 % test, 15 % benchmark)
        - reachability   (40 % CLI flag, 40 % CLI wired, 20 % phase)
        - runtime exec   (40 % manifest, 20 % phase, 20 % test, 20 % benchmark)
        - attack impact  (60 % red-team, 30 % metrics, 10 % security gates)
    The final reality_score weights each dimension at 25 %.
    """
    name = feature["name"]
    # Accumulate missing evidence labels and total evidence count.
    missing: List[str] = []
    evidence_count = 0

    build_py_source = pipeline_state.get("build_py_source", "")

    # ---- Implementation dimension (module, phase, test, benchmark) ---- #
    impl_score = 0.0
    mod_path = feature.get("module")
    class_name = feature.get("class")
    module_ok = _check_source_exists(mod_path, class_name) if mod_path else False
    phase_ok = _check_phase_exists(feature)
    test_ok = _check_test_exists(name)
    bench_ok = _check_benchmark_exists(name)

    if module_ok:
        impl_score += 30.0
        evidence_count += 1
    else:
        missing.append(f"module/{feature.get('module', 'N/A')}")
    if phase_ok:
        impl_score += 30.0
        evidence_count += 1
    else:
        missing.append("phase_file")
    if test_ok:
        impl_score += 25.0
        evidence_count += 1
    else:
        missing.append("tests")
    if bench_ok:
        impl_score += 15.0
        evidence_count += 1
    else:
        missing.append("benchmarks")
    impl_score = min(impl_score, 100.0)

    # ---- Reachability dimension (CLI flag, CLI wired, phase) ---- #
    reachability_score = 0.0
    cli_flag_exists = _check_cli_flag_exists(feature, build_py_source)
    cli_wired = _check_cli_wired(feature, build_py_source)
    if cli_flag_exists:
        reachability_score += 40.0
        evidence_count += 1
    else:
        missing.append("cli_flag")
    if cli_wired:
        reachability_score += 40.0
        evidence_count += 1
    else:
        missing.append("cli_wired")
    if phase_ok:
        reachability_score += 20.0
    reachability_score = min(reachability_score, 100.0)

    # ---- Runtime execution dimension (manifest, phase, test, bench) ---- #
    runtime_execution_score = 0.0
    manifest = pipeline_state.get("manifest", {})
    manifest_features = set()
    for entry in manifest.get("features", []):
        if isinstance(entry, dict):
            manifest_features.add(entry.get("name", ""))
        elif isinstance(entry, str):
            manifest_features.add(entry)
    feature_name_lower = name.lower()
    in_manifest = any(feature_name_lower in mf.lower() for mf in manifest_features) if manifest_features else False
    if in_manifest:
        runtime_execution_score += 40.0
        evidence_count += 1
    else:
        missing.append("manifest_entry")
    if phase_ok:
        runtime_execution_score += 20.0
    if test_ok:
        runtime_execution_score += 20.0
    if bench_ok:
        runtime_execution_score += 20.0
    runtime_execution_score = min(runtime_execution_score, 100.0)

    # ---- Attack-impact dimension (red-team, metrics, security gates) ---- #
    attack_impact_score = 0.0
    redteam = pipeline_state.get("redteam_report", {})
    metrics = pipeline_state.get("metrics_report", {})
    security_gates = pipeline_state.get("security_gate_report", {})

    rt_score = 0.0
    for attack_type in ["angr_result", "ghidra_result", "bninja_result", "llm_result", "symbolic_result"]:
        attack_data = redteam.get(attack_type, {})
        if attack_data and isinstance(attack_data, dict) and attack_data.get("status") in ("completed", "passed"):
            rt_score = max(rt_score, 60.0)
    if rt_score > 0:
        attack_impact_score += rt_score
        evidence_count += 1
    else:
        missing.append("redteam_results")

    metrics_overall = metrics.get("overall", 0.0) if metrics else 0.0
    if isinstance(metrics_overall, (int, float)) and metrics_overall > 0:
        attack_impact_score += min(metrics_overall * 30.0, 30.0)
        evidence_count += 1
    else:
        missing.append("metrics_data")

    if security_gates and isinstance(security_gates, dict) and security_gates.get("all_passed", False):
        attack_impact_score += 10.0
        evidence_count += 1
    else:
        missing.append("security_gates")

    attack_impact_score = min(attack_impact_score, 100.0)

    # ---- Composite reality score: equal-weight four dimensions ---- #
    reality_score = (
        0.25 * impl_score
        + 0.25 * reachability_score
        + 0.25 * runtime_execution_score
        + 0.25 * attack_impact_score
    )

    # Apply penalties for missing evidence and missing metrics data.
    if evidence_count == 0:
        reality_score = max(reality_score - 10.0, 0.0)
    if "metrics_data" in missing:
        reality_score = max(reality_score - 20.0, 0.0)

    return FeatureReality(
        feature_name=name,
        implemented_score=round(impl_score, 1),
        reachability_score=round(reachability_score, 1),
        runtime_execution_score=round(runtime_execution_score, 1),
        attack_impact_score=round(attack_impact_score, 1),
        reality_score=round(reality_score, 1),
        evidence_count=evidence_count,
        missing_evidence=missing,
    )


def compute_reality_scores(pipeline_state: Dict[str, Any]) -> RealityReport:
    """Compute reality scores for every feature in the registry.

    Iterates FEATURE_REGISTRY, computes per-feature reality, and
    aggregates into a RealityReport with an overall grade.
    """
    feature_scores: Dict[str, FeatureReality] = {}
    critical_gaps: List[str] = []

    for feat in FEATURE_REGISTRY:
        fr = compute_feature_reality(feat, pipeline_state)
        feature_scores[fr.feature_name] = fr
        if fr.reality_score < 25.0:
            critical_gaps.append(
                f"{fr.feature_name}: score={fr.reality_score}, missing={', '.join(fr.missing_evidence)}"
            )

    report = RealityReport(
        feature_scores=feature_scores,
        timestamp=datetime.now(timezone.utc).isoformat(),
        critical_gaps=critical_gaps,
    )
    report.overall_reality_score = aggregate_reality_score(report)
    report.grade = score_to_grade(report.overall_reality_score)
    return report


def aggregate_reality_score(report: RealityReport) -> float:
    """Compute the mean reality score across all features in the report."""
    scores = [fr.reality_score for fr in report.feature_scores.values()]
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 1)


def load_from_build(build_dir: str) -> RealityReport:
    """Load all pipeline artefacts from a build directory and compute reality scores.

    Reads build.py source, manifest, metrics, red-team, benchmark, and
    security-gate reports, then delegates to compute_reality_scores.
    """
    build_py_path = os.path.join(_ROOT, "scripts", "build.py")
    build_py_source = ""
    if os.path.isfile(build_py_path):
        with open(build_py_path) as f:
            build_py_source = f.read()

    pipeline_state: Dict[str, Any] = {
        "build_py_source": build_py_source,
        "manifest": _load_manifest(),
        "metrics_report": _load_metrics_report(),
        "redteam_report": _load_redteam_report(),
        "benchmark_report": _load_benchmark_report(),
        "security_gate_report": _load_security_gate_report(),
    }
    return compute_reality_scores(pipeline_state)
