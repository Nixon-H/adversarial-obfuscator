"""
reproducibility/scorer.py — Reproducibility scoring engine (F178)

Purpose:
    Scans a build directory and scores each artefact on reproducibility
    (0-100) based on content type, presence of time/random dependencies,
    JSON structure, and environment fingerprint consistency.

Architectural Role:
    Core scoring engine. Consumed by the __init__ convenience layer and
    integrated into the pipeline as a quality gate.

Security Relevance:
    Identifies artefacts with non-deterministic content that would prevent
    bitwise-identical rebuilds, a prerequisite for supply-chain verification.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Tuple

from .environment import snapshot_environment, environment_fingerprint


@dataclass
class ReproducibilityResult:
    """Per-artefact reproducibility score.

    Attributes:
        artifact_type: Classification (benchmark, attack, proof, test).
        artifact_path: Relative path within the build directory.
        content_hash: SHA-256 of the file contents.
        metadata_hash: SHA-256 of (size, mode, uid, gid).
        environment_snapshot: Key environment variables at scoring time.
        reproducibility_score: 0-100 score.
        notes: Human-readable notes explaining the score.
    """
    artifact_type: str
    artifact_path: str
    content_hash: str
    metadata_hash: str
    environment_snapshot: Dict[str, str]
    reproducibility_score: float
    notes: List[str] = field(default_factory=list)


@dataclass
class ReproducibilityReport:
    """Aggregate reproducibility report.

    Attributes:
        overall_score: Mean of all per-artefact scores.
        results: All individual ReproducibilityResult entries.
        environment: Environment snapshot at scoring time.
        non_reproducible_artifacts: Artefacts scoring below 50.
        recommendations: Actionable text suggestions.
        timestamp: ISO-8601 generation timestamp.
    """

    overall_score: float
    results: List[ReproducibilityResult]
    environment: Dict[str, str]
    non_reproducible_artifacts: List[str]
    recommendations: List[str]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the report to a plain dict."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize the report to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


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


def _hash_metadata(path: str) -> str:
    """Compute a SHA-256 metadata fingerprint from file size, mode, uid, gid."""
    try:
        stat = os.stat(path)
        meta = f"{stat.st_size}:{stat.st_mode}:{stat.st_uid}:{stat.st_gid}"
        return hashlib.sha256(meta.encode()).hexdigest()
    except OSError:
        return hashlib.sha256(b"unknown").hexdigest()


def _classify_artifact_type(path: str) -> str:
    """Classify an artefact as benchmark, attack, proof, or test based on its filename."""
    basename = os.path.basename(path).lower()
    if "benchmark" in basename or "bench" in basename:
        return "benchmark"
    if "attack" in basename:
        return "attack"
    if "proof" in basename or "certificate" in basename:
        return "proof"
    if "test" in basename:
        return "test"
    if path.endswith(".ir"):
        return "proof"
    if path.endswith(".json"):
        return "benchmark"
    return "benchmark"


def _score_from_content(path: str, env: Dict[str, str], env_fp: str) -> Tuple[float, List[str]]:
    """Score a single file on reproducibility based on its extension, content, and environment match."""
    notes: List[str] = []
    try:
        stat = os.stat(path)
    except OSError:
        return 0.0, ["Cannot stat file"]

    size = stat.st_size

    if path.endswith(".json"):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "timestamp" in data:
                notes.append("Contains timestamp — scores 80")
                score = 80.0
            elif isinstance(data, dict) and "seed" in data:
                notes.append("Contains seed parameter — scores 90")
                score = 90.0
            else:
                notes.append("Static JSON content — scores 100")
                score = 100.0
        except (json.JSONDecodeError, UnicodeDecodeError):
            notes.append("Binary JSON-like — scores 90")
            score = 90.0
    elif path.endswith((".py", ".ir", ".ll", ".c", ".h")):
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            has_time = "time.time" in content or "datetime" in content or "timestamp" in content
            has_random = "random" in content or "secrets" in content or "os.urandom" in content
            if has_random:
                notes.append("Contains random/secret generation — scores 0")
                score = 0.0
            elif has_time:
                notes.append("Contains time-based generation — scores 50")
                score = 50.0
            else:
                notes.append("Static source content — scores 100")
                score = 100.0
        except UnicodeDecodeError:
            notes.append("Binary source-like — scores 90")
            score = 90.0
    elif path.endswith((".o", ".obj", ".bin", ".so", ".dylib", ".dll")):
        notes.append("Compiled binary — environment-sensitive, scores 60")
        score = 60.0
    elif path.endswith((".tar.gz", ".zip", ".tar")):
        notes.append("Archive — packaging-dependent, scores 70")
        score = 70.0
    else:
        if size > 1024 * 1024:
            notes.append("Large file — scores 80")
            score = 80.0
        else:
            notes.append("Unknown type — scores 50")
            score = 50.0

    env_fp_file = environment_fingerprint(env)
    if env_fp != env_fp_file:
        notes.append("Environment fingerprint mismatch — -5")
        score = max(0.0, score - 5.0)

    if size == 0:
        notes.append("Empty file — scores 0")
        score = 0.0

    return round(score, 1), notes


def compute_reproducibility(build_dir: str) -> ReproducibilityReport:
    """Compute reproducibility scores for all artefacts in a build directory.

    Snapshot the environment, walk the build directory, score each file,
    and return a ReproducibilityReport with aggregate and per-file results.
    """
    env = snapshot_environment()
    env_fp = environment_fingerprint(env)

    results: List[ReproducibilityResult] = []
    non_reproducible: List[str] = []
    all_scores: List[float] = []

    if not os.path.isdir(build_dir):
        report = ReproducibilityReport(
            overall_score=0.0,
            results=[],
            environment=env,
            non_reproducible_artifacts=[f"Build directory not found: {build_dir}"],
            recommendations=["Ensure build directory exists before reproducibility check"],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        return report

    for root, _dirs, files in os.walk(build_dir):
        for filename in files:
            path = os.path.join(root, filename)
            artifact_type = _classify_artifact_type(path)
            content_hash = _hash_file(path)
            metadata_hash = _hash_metadata(path)
            score, notes = _score_from_content(path, env, env_fp)

            result = ReproducibilityResult(
                artifact_type=artifact_type,
                artifact_path=os.path.relpath(path, build_dir),
                content_hash=content_hash,
                metadata_hash=metadata_hash,
                environment_snapshot=dict(env),
                reproducibility_score=score,
                notes=notes,
            )
            results.append(result)
            all_scores.append(score)

            if score < 50.0:
                non_reproducible.append(result.artifact_path)

    overall_score = round(sum(all_scores) / max(len(all_scores), 1), 1) if all_scores else 100.0

    recommendations: List[str] = []
    if non_reproducible:
        recommendations.append(f"Fix {len(non_reproducible)} non-reproducible artifacts")
    if any(r.reproducibility_score < 100 for r in results):
        recommendations.append("Remove time/random dependencies in artifact generation")
    if env.get("git_dirty") == "True":
        recommendations.append("Commit pending changes for deterministic builds")
    if not recommendations:
        recommendations.append("All artifacts are fully reproducible")

    report = ReproducibilityReport(
        overall_score=overall_score,
        results=results,
        environment=env,
        non_reproducible_artifacts=non_reproducible,
        recommendations=recommendations,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )

    return report
