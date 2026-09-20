"""
feature_retirement/analyzer.py — Feature Retirement analysis engine (F176)

Purpose:
    For each feature in the feature map, computes effectiveness, overhead, and
    survivability scores. Combines them into an overall score and maps to a
    RetirementStatus recommendation (KEEP / MONITOR / OPTIMIZE / DEPRECATE).

Architectural Role:
    Analysis engine. Consumed by the __init__ convenience layer and the
    Self-Audit Agent (F180) for lifecycle recommendations.

Security Relevance:
    Systematic retirement prevents "bit rot" in the protection surface:
    features that are no longer effective impose overhead without benefit.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.reachability.feature_map import ALL_FEATURES


class RetirementStatus(Enum):
    """Recommended action for a feature based on retirement analysis."""
    DEPRECATE = "DEPRECATE"
    MONITOR = "MONITOR"
    KEEP = "KEEP"
    OPTIMIZE = "OPTIMIZE"


@dataclass
class RetirementAssessment:
    """Per-feature retirement assessment.

    Attributes:
        feature_name: Feature identifier.
        effectiveness_score: 0-1 — how effective the protection is.
        overhead_score: 0-1 — how costly (higher = more expensive).
        survivability_score: 0-1 — how many integration links exist.
        overall_score: Composite (40 % effectiveness + 35 % survivability - 25 % overhead).
        recommendation: KEEP / MONITOR / OPTIMIZE / DEPRECATE.
        reason: Human-readable justification.
        has_tests / has_runtime / has_implementation / cli_flag_present / phase_present: Integration flags.
    """

    feature_name: str
    effectiveness_score: float
    overhead_score: float
    survivability_score: float
    overall_score: float
    recommendation: RetirementStatus
    reason: str
    has_tests: bool = False
    has_runtime: bool = False
    has_implementation: bool = False
    cli_flag_present: bool = False
    phase_present: bool = False


@dataclass
class RetirementReport:
    """Aggregate retirement report across all features.

    Attributes:
        assessments: Feature-name → RetirementAssessment mapping.
        deprecate_count / monitor_count / keep_count / optimize_count: Counts.
        total_features: Number of features assessed.
        timestamp: ISO-8601 generation timestamp.
    """

    assessments: Dict[str, RetirementAssessment]
    deprecate_count: int
    monitor_count: int
    keep_count: int
    optimize_count: int
    total_features: int
    timestamp: str

    def to_dict(self) -> dict:
        """Serialize the report to a plain dict for JSON export."""
        return {
            "timestamp": self.timestamp,
            "total_features": self.total_features,
            "deprecate_count": self.deprecate_count,
            "monitor_count": self.monitor_count,
            "keep_count": self.keep_count,
            "optimize_count": self.optimize_count,
            "assessments": {
                name: {
                    "feature_name": a.feature_name,
                    "effectiveness_score": a.effectiveness_score,
                    "overhead_score": a.overhead_score,
                    "survivability_score": a.survivability_score,
                    "overall_score": a.overall_score,
                    "recommendation": a.recommendation.value,
                    "reason": a.reason,
                    "has_tests": a.has_tests,
                    "has_runtime": a.has_runtime,
                    "has_implementation": a.has_implementation,
                    "cli_flag_present": a.cli_flag_present,
                    "phase_present": a.phase_present,
                }
                for name, a in self.assessments.items()
            },
        }


_HIGH_EFFECTIVENESS = {
    "obfuscat", "encrypt", "vm", "jit", "fragment", "mba", "predicate",
    "flatten", "mutation", "poison", "watermark", "attest", "binding",
    "rop", "adversarial", "entangle", "dispersal", "zk", "proof",
    "security_gate", "redteam", "cfg", "ssa", "self", "genome",
    "branch", "multicore", "micro", "kill", "trap", "fingerprint",
    "deception", "storyline", "decoy", "attention", "dispers",
    "speculation", "struct", "randomization", "class_dispatch",
    "state_isa", "temporal", "rolling", "key", "poly",
}

_MEDIUM_EFFECTIVENESS = {
    "protect", "diversity", "key", "temporal", "self", "genome",
    "struct", "hpc", "tee", "sgx", "gpu", "simd", "speculation",
    "class", "state", "data", "intent", "fingerprint", "trap",
    "decoy", "story", "attention", "uarch", "certificate", "preserv",
    "cost", "survivability", "leakage", "exposure", "knowledge",
    "synthesis", "oram", "challenge", "response", "ephemeral",
    "history", "bound", "recompile", "healing",
}

_LOW_EFFECTIVENESS = {
    "compile", "relay", "llvm", "ir", "package", "payload",
    "manifest", "config", "cross", "metrics", "benchmark",
    "coverage", "reachability", "reproducibility", "reality",
    "artifact", "assumption", "false_confidence", "evidence",
    "ledger", "evaluate", "analysis", "classify", "diversity",
    "report", "summary", "index", "score",
}


def _match_keywords(name: str, keywords: set) -> bool:
    """Return True if any keyword (stripped of underscores/dashes) appears in the feature name."""
    name_lower = name.lower().replace("_", "").replace("-", "")
    for kw in keywords:
        kw_clean = kw.lower().replace("_", "").replace("-", "")
        if kw_clean in name_lower:
            return True
    return False


class RetirementAnalyzer:
    """Analyzes feature effectiveness, overhead, and survivability for retirement decisions.

    Uses keyword-based classification for effectiveness tiers, weighted scoring
    for overhead and survivability, and a heuristic rule set for the final
    RetirementStatus recommendation.
    """

    def __init__(self, feature_map: Optional[Dict[str, dict]] = None):
        self.feature_map = feature_map or ALL_FEATURES
        self._tests_dir: str = os.path.join(_ROOT, "tests")
        self._runtime_dir: str = os.path.join(_ROOT, "runtime", "src")
        self._scripts_dir: str = os.path.join(_ROOT, "scripts")

    def classify_feature_type(self, feature_name: str) -> str:
        """Classify a feature as 'high', 'medium', or 'low' effectiveness based on keyword matching."""
        if _match_keywords(feature_name, _HIGH_EFFECTIVENESS):
            return "high"
        if _match_keywords(feature_name, _MEDIUM_EFFECTIVENESS):
            return "medium"
        if _match_keywords(feature_name, _LOW_EFFECTIVENESS):
            return "low"
        return "medium"

    def compute_effectiveness(self, feature_name: str, info: dict) -> float:
        """Score 0-1: base from classification + bonus for each integration link present."""
        base_map = {"high": 0.80, "medium": 0.55, "low": 0.25}
        base = base_map.get(self.classify_feature_type(feature_name), 0.50)
        bonus = 0.0
        if info.get("cli_flag"):
            bonus += 0.05
        if info.get("phase_name"):
            bonus += 0.05
        if info.get("impl_module"):
            bonus += 0.05
        if info.get("runtime_file"):
            bonus += 0.05
        if info.get("test_file"):
            bonus += 0.05
        return min(base + bonus, 1.0)

    def compute_overhead(self, feature_name: str, info: dict) -> float:
        """Score 0-1: higher = more costly. Factors: runtime file, implementation complexity, heavy keywords."""
        base = 0.30
        if info.get("runtime_file"):
            base += 0.25
        if info.get("impl_module"):
            impl = info["impl_module"]
            if "obfuscator" in impl or "vm" in impl or "jit" in impl or "encrypt" in impl:
                base += 0.15
            elif "phase" in impl or "scripts" in impl:
                base += 0.05
        if info.get("test_file"):
            base -= 0.05
        has_heavy_keyword = _match_keywords(feature_name, {
            "vm", "jit", "encrypt", "fragment", "genome", "entangle",
            "gpu", "sgx", "tee", "hpc", "simd", "zk", "proof",
            "adversarial", "redteam",
        })
        if has_heavy_keyword:
            base += 0.15
        return min(max(base, 0.05), 1.0)

    def compute_survivability(self, feature_name: str, info: dict) -> float:
        """Score 0-1: how many integration links exist (CLI, phase, impl, runtime, tests) and whether files exist on disk."""
        base = 0.20
        links = 0
        if info.get("cli_flag"):
            links += 1
        if info.get("phase_name"):
            links += 1
        if info.get("impl_module"):
            links += 1
        if info.get("runtime_file"):
            links += 1
        if info.get("test_file"):
            links += 1
        base += links * 0.12
        if info.get("test_file"):
            base += 0.10
            test_path = os.path.join(self._tests_dir, info["test_file"])
            if os.path.exists(test_path):
                base += 0.05
        if info.get("runtime_file"):
            runtime_path = os.path.join(self._runtime_dir, info["runtime_file"])
            if os.path.exists(runtime_path):
                base += 0.05
        return min(base, 1.0)

    def _find_test_file(self, feature_name: str, info: dict) -> bool:
        """Check if a test file exists for this feature, by explicit name or slug matching."""
        explicit = info.get("test_file")
        if explicit:
            return os.path.exists(os.path.join(self._tests_dir, explicit))
        slug = feature_name.replace("_", "").lower()
        if os.path.isdir(self._tests_dir):
            for fname in os.listdir(self._tests_dir):
                if fname.endswith(".py") and fname.startswith("test_"):
                    base = fname.replace("test_", "").replace(".py", "").replace("_", "").lower()
                    if slug in base or base in slug:
                        return True
        return False

    def _find_runtime_file(self, feature_name: str, info: dict) -> bool:
        """Check if a runtime file exists for this feature, by explicit name or slug matching."""
        explicit = info.get("runtime_file")
        if explicit:
            return os.path.exists(os.path.join(self._runtime_dir, explicit))
        slug = feature_name.replace("_", "").lower()
        if os.path.isdir(self._runtime_dir):
            for fname in os.listdir(self._runtime_dir):
                if fname.endswith(".rs"):
                    base = fname.replace(".rs", "").replace("_", "").lower()
                    if slug in base or base in slug:
                        return True
        return False

    def _find_implementation(self, feature_name: str, info: dict) -> bool:
        """Check if the implementation module file exists, resolving both relative and scripts-prefixed paths."""
        impl_module = info.get("impl_module")
        if not impl_module:
            return False
        module_path = impl_module.replace(".", "/") + ".py"
        full_path = os.path.join(_ROOT, module_path)
        if os.path.exists(full_path):
            return True
        alt = os.path.join(_ROOT, "scripts", module_path.replace("scripts/", ""))
        if os.path.exists(alt):
            return True
        return False

    def assess_feature(self, feature_name: str) -> RetirementAssessment:
        """Full retirement assessment for a single feature.

        Computes effectiveness, overhead, survivability; checks file existence;
        applies heuristic rules to determine RetirementStatus.
        """
        info = self.feature_map.get(feature_name, {})
        effectiveness = self.compute_effectiveness(feature_name, info)
        overhead = self.compute_overhead(feature_name, info)
        survivability = self.compute_survivability(feature_name, info)

        has_tests = self._find_test_file(feature_name, info)
        has_runtime = self._find_runtime_file(feature_name, info)
        has_implementation = self._find_implementation(feature_name, info)
        cli_flag_present = info.get("cli_flag") is not None
        phase_present = info.get("phase_name") is not None

        overall = 0.40 * effectiveness + 0.35 * survivability - 0.25 * overhead
        overall = max(min(overall, 1.0), 0.0)

        deprecate_cond = effectiveness < 0.40 and overhead > 0.60 and survivability < 0.40
        low_impact_cond = effectiveness < 0.30 and overhead < 0.30 and survivability < 0.30
        optimize_cond = overhead > 0.70 and survivability > 0.50 and effectiveness > 0.50
        monitor_cond = (0.40 <= effectiveness < 0.60) or (0.40 <= survivability < 0.60)

        if deprecate_cond or low_impact_cond:
            recommendation = RetirementStatus.DEPRECATE
            if deprecate_cond:
                reason = (
                    f"Low effectiveness ({effectiveness:.2f}), high overhead ({overhead:.2f}), "
                    f"low survivability ({survivability:.2f})"
                )
            else:
                reason = (
                    f"Low overall impact: effectiveness={effectiveness:.2f}, "
                    f"survivability={survivability:.2f}"
                )
        elif optimize_cond:
            recommendation = RetirementStatus.OPTIMIZE
            reason = (
                f"High overhead ({overhead:.2f}) despite decent effectiveness "
                f"({effectiveness:.2f}) and survivability ({survivability:.2f})"
            )
        elif overall >= 0.55 and effectiveness >= 0.50:
            recommendation = RetirementStatus.KEEP
            reason = f"Good protection value: effectiveness={effectiveness:.2f}, overhead={overhead:.2f}"
        elif monitor_cond:
            recommendation = RetirementStatus.MONITOR
            reason = (
                f"Borderline metrics: effectiveness={effectiveness:.2f}, "
                f"survivability={survivability:.2f}, overhead={overhead:.2f}"
            )
        elif overall >= 0.40:
            recommendation = RetirementStatus.MONITOR
            reason = f"Moderate overall score ({overall:.2f}), needs monitoring"
        else:
            recommendation = RetirementStatus.DEPRECATE
            reason = f"Low overall score ({overall:.2f}) across all dimensions"

        return RetirementAssessment(
            feature_name=feature_name,
            effectiveness_score=round(effectiveness, 4),
            overhead_score=round(overhead, 4),
            survivability_score=round(survivability, 4),
            overall_score=round(overall, 4),
            recommendation=recommendation,
            reason=reason,
            has_tests=has_tests,
            has_runtime=has_runtime,
            has_implementation=has_implementation,
            cli_flag_present=cli_flag_present,
            phase_present=phase_present,
        )

    def assess_all_features(self) -> Dict[str, RetirementAssessment]:
        """Assess every feature in the feature map."""
        results: Dict[str, RetirementAssessment] = {}
        for feature_name in self.feature_map:
            results[feature_name] = self.assess_feature(feature_name)
        return results

    def generate_report(self) -> RetirementReport:
        """Assess all features and produce a RetirementReport with counts."""
        assessments = self.assess_all_features()
        deprecate = sum(1 for a in assessments.values() if a.recommendation == RetirementStatus.DEPRECATE)
        monitor = sum(1 for a in assessments.values() if a.recommendation == RetirementStatus.MONITOR)
        keep = sum(1 for a in assessments.values() if a.recommendation == RetirementStatus.KEEP)
        optimize = sum(1 for a in assessments.values() if a.recommendation == RetirementStatus.OPTIMIZE)
        timestamp = datetime.now(timezone.utc).isoformat()
        return RetirementReport(
            assessments=assessments,
            deprecate_count=deprecate,
            monitor_count=monitor,
            keep_count=keep,
            optimize_count=optimize,
            total_features=len(assessments),
            timestamp=timestamp,
        )
