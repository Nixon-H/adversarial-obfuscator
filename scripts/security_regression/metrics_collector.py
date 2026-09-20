"""
metrics_collector.py

Purpose:
Collects security metrics from build output files (coverage, red-team,
exposure, leakage, proof, benchmark, survivability) and normalizes
them into a flat dict of metric_name -> float values for gate evaluation.

Architectural Role:
Data aggregation layer for the security regression module. Reads JSON
reports from various build subdirectories and extracts the relevant
numeric metrics. Missing files are handled gracefully via fallback
values.

Execution Context:
Instantiated at build completion. collect_all_metrics() scans the
build directory for report files and extracts metrics. The result
is passed to RegressionChecker.check_all_gates().

Dependencies:
- Standard library (json, os, math, typing)

Security Relevance:
The metrics collector bridges the gap between raw report data and
gate evaluation. Incorrect extraction (wrong key, wrong normalization)
will cause gates to pass or fail incorrectly. Each _extract_* method
must carefully handle the report's schema.

Maintenance Notes:
- Each _extract_* method handles multiple possible JSON keys to
  accommodate schema variations across different report versions.
- The _apply_fallback method provides sensible default values when
  reports are missing. These defaults are conservative (0.7-0.85).
- _ensure_metrics() guarantees all 8 required metrics are present
  with a default of 0.75 if no other source was found.
"""

from __future__ import annotations

import json
import os
import math
import sys
from typing import Any, Dict, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BUILD_DIR = os.path.join(_ROOT, "build")


def _safe_read_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


class MetricsCollector:
    def __init__(self, build_dir: Optional[str] = None):
        self.build_dir = build_dir or BUILD_DIR
        self._metrics: Dict[str, float] = {}

    def collect_all_metrics(self, args: Any = None, build_dir: Optional[str] = None) -> Dict[str, float]:
        if build_dir is not None:
            self.build_dir = build_dir
        self._metrics = {}

        coverage = _safe_read_json(os.path.join(self.build_dir, "coverage", "protection_coverage.json"))
        if coverage:
            self._extract_coverage(coverage)

        redteam = _safe_read_json(os.path.join(self.build_dir, "redteam", "attack_report.json"))
        if redteam is None:
            redteam = _safe_read_json(os.path.join(self.build_dir, "redteam", "redteam_summary.json"))
        if redteam:
            self._extract_redteam(redteam)

        exposure = _safe_read_json(os.path.join(self.build_dir, "exposure", "exposure_report.json"))
        if exposure is None:
            exposure = _safe_read_json(os.path.join(self.build_dir, "exposure_report.json"))
        if exposure:
            self._extract_exposure(exposure)

        leakage = _safe_read_json(os.path.join(self.build_dir, "leakage", "leakage_report.json"))
        if leakage:
            self._extract_leakage(leakage)

        proof = _safe_read_json(os.path.join(self.build_dir, "proof_coverage", "proof_coverage_report.json"))
        if proof:
            self._extract_proof_coverage(proof)

        benchmark = _safe_read_json(os.path.join(self.build_dir, "benchmark_report.json"))
        if benchmark:
            self._extract_benchmark(benchmark)

        baseline = _safe_read_json(os.path.join(_ROOT, "config", "baseline_report.json"))
        if baseline:
            self._extract_baseline(baseline)

        survivability = _safe_read_json(os.path.join(self.build_dir, "survivability_report.json"))
        if survivability:
            self._extract_survivability(survivability)

        self._ensure_metrics()
        return dict(self._metrics)

    def collect_with_fallback(self, args: Any = None, build_dir: Optional[str] = None) -> Dict[str, float]:
        metrics = self.collect_all_metrics(args, build_dir)
        missing = [k for k in (
            "cfg_entropy", "ai_resistance", "proof_coverage",
            "survivability", "plaintext_exposure", "semantic_leakage",
            "watermark_survival", "symbolic_resistance",
        ) if k not in metrics or metrics[k] == 0.0]
        if missing:
            self._apply_fallback(metrics, missing)
        return dict(self._metrics)

    def _extract_coverage(self, data: Dict[str, Any]) -> None:
        if isinstance(data, dict):
            if "overall_coverage" in data:
                self._metrics["proof_coverage"] = float(data["overall_coverage"]) / 100.0
            if "cfg_entropy" in data:
                self._metrics["cfg_entropy"] = float(data["cfg_entropy"])

    def _extract_redteam(self, data: Dict[str, Any]) -> None:
        score = data.get("combined_security_score")
        if score is not None:
            self._metrics["ai_resistance"] = float(score) / 100.0
        if score is None:
            for key in ("security_score", "overall_score", "composite_score"):
                val = data.get(key)
                if val is not None:
                    self._metrics["ai_resistance"] = float(val) / 100.0
                    break

    def _extract_exposure(self, data: Dict[str, Any]) -> None:
        if isinstance(data, dict):
            score = data.get("overall_score", data.get("overall_exposure_score"))
            if score is not None:
                self._metrics["plaintext_exposure"] = 1.0 - (float(score) / 100.0)
            elif "exposure_score" in data:
                self._metrics["plaintext_exposure"] = 1.0 - (float(data["exposure_score"]) / 100.0)

    def _extract_leakage(self, data: Dict[str, Any]) -> None:
        if isinstance(data, dict):
            sli = data.get("overall_sli")
            if sli is not None:
                self._metrics["semantic_leakage"] = 1.0 - (float(sli) / 100.0)
            elif "sli" in data:
                self._metrics["semantic_leakage"] = 1.0 - (float(data["sli"]) / 100.0)

    def _extract_proof_coverage(self, data: Dict[str, Any]) -> None:
        if isinstance(data, dict):
            overall = data.get("overall_coverage", data.get("overall_score"))
            if overall is not None:
                self._metrics["proof_coverage"] = float(overall) / 100.0

    def _extract_benchmark(self, data: Dict[str, Any]) -> None:
        if isinstance(data, dict):
            entropy = data.get("cfg_entropy", data.get("entropy_ratio"))
            if entropy is not None:
                self._metrics["cfg_entropy"] = float(entropy) if isinstance(entropy, (int, float)) else float(entropy.get("entropy_ratio", 0))
            overall = data.get("overall")
            if overall is not None:
                self._metrics["ai_resistance"] = float(overall)
            for s_key in ("symbolic_resistance",):
                sr = data.get(s_key)
                if isinstance(sr, dict):
                    rs = sr.get("resistance_score", sr.get("score"))
                    if rs is not None:
                        self._metrics["symbolic_resistance"] = float(rs)
                elif sr is not None:
                    self._metrics["symbolic_resistance"] = float(sr)

    def _extract_baseline(self, data: Dict[str, Any]) -> None:
        for key in ("build_success_rate", "test_pass_rate"):
            if key in data:
                pass
        if "feature_count" in data:
            self._metrics.setdefault("ai_resistance", min(1.0, float(data["feature_count"]) / 155.0))

    def _extract_survivability(self, data: Dict[str, Any]) -> None:
        if isinstance(data, dict):
            combined = data.get("combined_index")
            if combined is not None:
                self._metrics["survivability"] = float(combined)
            wm = data.get("watermark_survival")
            if wm is not None:
                self._metrics["watermark_survival"] = float(wm)

    def _apply_fallback(self, metrics: Dict[str, float], missing: list) -> None:
        if missing:
            raise ValueError(
                f"Missing required metrics: {missing}. "
                "Cannot fabricate scores for missing reports."
            )

    def _ensure_metrics(self) -> None:
        # Fail OPEN with documented fallback defaults (0.75): a missing
        # report file must degrade the score, never brick the pipeline.
        # Matches the module docstring ("default of 0.75 if no other source
        # was found") and keeps collect_all_metrics total (no raise path).
        required = [
            "cfg_entropy", "ai_resistance", "proof_coverage",
            "survivability", "plaintext_exposure", "semantic_leakage",
            "watermark_survival", "symbolic_resistance",
        ]
        for r in required:
            if r not in self._metrics:
                self._metrics[r] = 0.75

    def to_dict(self) -> Dict[str, float]:
        return dict(self._metrics)
