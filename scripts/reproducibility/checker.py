"""
reproducibility/checker.py — Targeted reproducibility checks per artefact type (F178)

Purpose:
    Provides focused reproducibility check functions for individual result
    files, benchmarks, attack reports, proof certificates, and test results.
    Each check considers environment differences and content non-determinism.

Architectural Role:
    Targeted-check layer. Complements the bulk scorer by enabling per-artefact
    reproducibility verification, e.g. in CI/CD gates.

Security Relevance:
    Enables per-artefact gating: a benchmark that fails reproducibility can
    block a release, preventing non-deterministic results from entering
    audit trails.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from .environment import snapshot_environment, compare_environments, environment_fingerprint
from .scorer import ReproducibilityResult


def _hash_file(path: str) -> str:
    """Compute the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def check_result_reproducibility(
    artifact_path: str,
    original_env: Optional[Dict[str, str]] = None,
) -> ReproducibilityResult:
    """Check reproducibility of a single artefact: hash, classify, compare environments, score."""
    current_env = snapshot_environment()
    env = original_env or current_env

    if not os.path.isfile(artifact_path):
        return ReproducibilityResult(
            artifact_type="unknown",
            artifact_path=artifact_path,
            content_hash="",
            metadata_hash="",
            environment_snapshot=env,
            reproducibility_score=0.0,
            notes=["Artifact file not found"],
        )

    content_hash = _hash_file(artifact_path)
    try:
        stat = os.stat(artifact_path)
        meta_str = f"{stat.st_size}:{stat.st_mode}"
        metadata_hash = hashlib.sha256(meta_str.encode()).hexdigest()
    except OSError:
        metadata_hash = hashlib.sha256(b"unknown").hexdigest()

    artifact_type = _classify_type(artifact_path)
    score, notes = _compute_check_score(artifact_path, original_env, current_env)

    return ReproducibilityResult(
        artifact_type=artifact_type,
        artifact_path=os.path.abspath(artifact_path),
        content_hash=content_hash,
        metadata_hash=metadata_hash,
        environment_snapshot=env,
        reproducibility_score=score,
        notes=notes,
    )


def _classify_type(path: str) -> str:
    """Classify an artefact type by filename (benchmark, attack, proof, test)."""
    bname = os.path.basename(path).lower()
    if "benchmark" in bname or "bench" in bname:
        return "benchmark"
    if "attack" in bname:
        return "attack"
    if "proof" in bname or "certificate" in bname:
        return "proof"
    if "test" in bname:
        return "test"
    if path.endswith(".ir"):
        return "proof"
    return "benchmark"


def _compute_check_score(
    path: str,
    original_env: Optional[Dict[str, str]],
    current_env: Dict[str, str],
) -> Tuple[float, List[str]]:
    """Compute a reproducibility score by comparing environments and checking file content for non-determinism."""
    notes: List[str] = []
    score = 100.0

    if original_env is not None:
        identical, diffs = compare_environments(original_env, current_env)
        if not identical:
            diff_keys = ", ".join(list(diffs.keys())[:5])
            notes.append(f"Environment differs: {diff_keys}")
            penalty = min(len(diffs) * 10.0, 60.0)
            score -= penalty
        else:
            notes.append("Environment identical")

    try:
        with open(path, "rb") as f:
            head = f.read(4096)
        if b"random" in head.lower() or b"secrets" in head.lower():
            notes.append("Contains non-deterministic generation")
            score -= 40.0
        if b"time" in head.lower() or b"timestamp" in head.lower():
            notes.append("Contains time-dependent generation")
            score -= 20.0
    except Exception:
        notes.append("Cannot read file content")
        score -= 30.0

    score = max(0.0, min(100.0, score))
    return round(score, 1), notes


def check_benchmark_reproducibility(
    benchmark_file: str,
    original_env: Optional[Dict[str, str]] = None,
) -> ReproducibilityResult:
    """Check reproducibility of a benchmark result file (delegates to check_result_reproducibility)."""
    return check_result_reproducibility(benchmark_file, original_env)


def check_attack_reproducibility(
    attack_report: str,
    original_env: Optional[Dict[str, str]] = None,
) -> ReproducibilityResult:
    """Check reproducibility of an attack report: also checks for seed (bonus) and timestamp (penalty) fields."""
    if not os.path.isfile(attack_report):
        return ReproducibilityResult(
            artifact_type="attack",
            artifact_path=attack_report,
            content_hash="",
            metadata_hash="",
            environment_snapshot=snapshot_environment(),
            reproducibility_score=0.0,
            notes=["Attack report file not found"],
        )

    result = check_result_reproducibility(attack_report, original_env)
    try:
        with open(attack_report, encoding="utf-8") as f:
            data = json.load(f)
        if "seed" in data:
            result.notes.append("Contains seed — deterministic replay possible")
            result.reproducibility_score = min(100.0, result.reproducibility_score + 10.0)
        if "timestamp" in data:
            result.notes.append("Contains timestamp — may differ across runs")
            result.reproducibility_score = max(0.0, result.reproducibility_score - 10.0)
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass

    return result


def check_proof_reproducibility(
    proof_file: str,
    original_env: Optional[Dict[str, str]] = None,
) -> ReproducibilityResult:
    """Check reproducibility of a proof certificate (delegates to check_result_reproducibility)."""
    return check_result_reproducibility(proof_file, original_env)


def check_test_reproducibility(
    test_results: str,
    original_env: Optional[Dict[str, str]] = None,
) -> ReproducibilityResult:
    """Check reproducibility of test results: also checks empty files and pass/fail counts."""
    if not os.path.isfile(test_results):
        return ReproducibilityResult(
            artifact_type="test",
            artifact_path=test_results,
            content_hash="",
            metadata_hash="",
            environment_snapshot=snapshot_environment(),
            reproducibility_score=0.0,
            notes=["Test results file not found"],
        )

    result = check_result_reproducibility(test_results, original_env)

    try:
        stat = os.stat(test_results)
        if stat.st_size == 0:
            result.notes.append("Empty test results — scores 0")
            result.reproducibility_score = 0.0
    except OSError:
        pass

    try:
        with open(test_results, encoding="utf-8") as f:
            content = f.read()
        passed = content.count("PASS") + content.count("passed") + content.count("ok")
        failed = content.count("FAIL") + content.count("failed") + content.count("ERROR")
        total = passed + failed
        if total > 0:
            result.notes.append(f"{passed}/{total} tests passed")
            if failed > 0:
                result.reproducibility_score = max(0.0, result.reproducibility_score - (failed / total) * 30.0)
    except (UnicodeDecodeError, OSError):
        pass

    return result
