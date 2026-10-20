"""
release_confidence/scorer.py

Purpose:
Computes a release confidence score (0-100) by combining five weighted
factors: proof coverage, evidence completeness, attack results, regression
status, and audit quality. Each factor is scored from 0.0 to 1.0.

Architectural Role:
Top-level aggregator in the meta-assurance pipeline. Consumes reports from
F183 (benchmark integrity), F187 (evidence completeness), F196 (attack corpus),
and other features to produce a single confidence score and grade (A-F).

Security Relevance:
The confidence score is the primary go/no-go metric for releases. A low score
indicates insufficient security assurance.
"""
from __future__ import annotations

import json
import math
import os
import re
import time
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class PerFactorScore:
    """
    PerFactorScore

    Purpose:
    Stores the raw and weighted score for a single confidence factor.

    Lifecycle:
    Created by compute(); aggregated into ConfidenceResult.
    """
    factor_name: str
    raw_score: float
    weight: float
    weighted_score: float
    source_file: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConfidenceResult:
    """
    ConfidenceResult

    Purpose:
    Stores the final confidence assessment including score, interval, per-factor
    breakdown, letter grade, and timestamp.

    Lifecycle:
    Created by compute(); returned via to_dict().
    """
    confidence_score: float
    confidence_interval: str
    per_factor_scores: list[PerFactorScore]
    confidence_grade: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence_score": self.confidence_score,
            "confidence_interval": self.confidence_interval,
            "per_factor_scores": [p.to_dict() for p in self.per_factor_scores],
            "confidence_grade": self.confidence_grade,
            "timestamp": self.timestamp,
        }


class ReleaseConfidenceScorer:
    """
    ReleaseConfidenceScorer

    Purpose:
    Computes release confidence by scoring five factors: proof coverage,
    evidence completeness, attack results, regression status, and audit quality.

    Lifecycle:
    Created with a build_dir; compute() drives the scoring.
    """
    def __init__(self, build_dir: str) -> None:
        self.build_dir = build_dir
        self.factors: list[PerFactorScore] = []

    def score_proof_coverage(self) -> float:
        """
        score_proof_coverage

        Purpose:
        Scores proof coverage by reading proof_coverage_report.json from the
        build directory.

        Inputs:
        None

        Outputs:
        Float between 0.0 and 1.0.
        """
        path = os.path.join(self.build_dir, "proof_coverage_report.json")
        if not os.path.isfile(path):
            return 0.0
        try:
            with open(path) as f:
                data = json.load(f)
            return float(data.get("overall_coverage", 0)) / 100.0
        except (json.JSONDecodeError, OSError):
            return 0.0

    def score_evidence_completeness(self) -> float:
        """
        score_evidence_completeness

        Purpose:
        Scores evidence completeness by reading evidence_report.json or
        evidence_ledger.json from the build directory.

        Inputs:
        None

        Outputs:
        Float between 0.0 and 1.0.
        """
        path = os.path.join(self.build_dir, "evidence_report.json")
        if not os.path.isfile(path):
            path = os.path.join(self.build_dir, "evidence_ledger.json")
        if not os.path.isfile(path):
            return 0.0
        try:
            with open(path) as f:
                data = json.load(f)
            claim_cov = float(data.get("claim_coverage_pct", 0))
            ev_cov = float(data.get("coverage_pct", 0))
            return (claim_cov + ev_cov) / 200.0
        except (json.JSONDecodeError, OSError):
            return 0.0

    def score_attack_results(self) -> float:
        """
        score_attack_results

        Purpose:
        Scores attack results by reading attack_corpus_report.json or
        attack_report.md and computing a weighted severity score.

        Inputs:
        None

        Outputs:
        Float between 0.0 and 1.0.
        """
        path = os.path.join(self.build_dir, "attack_corpus_report.json")
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                dist = data.get("severity_distribution", {})
            except (json.JSONDecodeError, OSError):
                dist = {}
            total = sum(dist.values())
            if total == 0:
                return 1.0
            weighted = (
                dist.get("critical", 0) * 1.0
                + dist.get("high", 0) * 0.7
                + dist.get("medium", 0) * 0.4
                + dist.get("low", 0) * 0.1
            )
            return max(0.0, 1.0 - weighted / (total * 1.0))
        alt = os.path.join(self.build_dir, "attack_report.md")
        if os.path.isfile(alt):
            with open(alt) as f:
                content = f.read()
            criticals = len(re.findall(r"\*\*CRITICAL\*\*", content))
            highs = len(re.findall(r"\*\*HIGH\*\*", content))
            mediums = len(re.findall(r"\*\*MEDIUM\*\*", content))
            lows = len(re.findall(r"\*\*LOW\*\*", content))
            total = criticals + highs + mediums + lows
            if total == 0:
                return 1.0
            weighted = criticals * 1.0 + highs * 0.7 + mediums * 0.4 + lows * 0.1
            return max(0.0, 1.0 - weighted / (total * 1.0))
        return 0.5

    def score_regression(self) -> float:
        """
        score_regression

        Purpose:
        Scores regression test results by reading regression_report.md or
        security_gate_report.json.

        Inputs:
        None

        Outputs:
        Float between 0.0 and 1.0.
        """
        path = os.path.join(self.build_dir, "regression_report.md")
        if os.path.isfile(path):
            with open(path) as f:
                content = f.read()
            passes = len(re.findall(r"✅ PASS", content))
            fails = len(re.findall(r"❌ FAIL|❌ MISSING", content))
            total = passes + fails
            if total == 0:
                return 0.5
            return passes / total
        path = os.path.join(self.build_dir, "security_gate_report.json")
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                return 0.5
            if data.get("all_passed"):
                return 1.0
            gates = data.get("gates", [])
            if gates:
                passed = sum(1 for g in gates if g.get("passed"))
                return passed / len(gates)
        return 0.5

    def score_audit_quality(self) -> float:
        """
        score_audit_quality

        Purpose:
        Scores audit quality by reading security_audit.json or falling back
        to a default if only security_audit.md exists.

        Inputs:
        None

        Outputs:
        Float between 0.0 and 1.0.
        """
        path = os.path.join(self.build_dir, "security_audit.json")
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                score = float(data.get("overall_score", 50))
                return score / 100.0
            except (json.JSONDecodeError, OSError):
                pass
        path = os.path.join(self.build_dir, "security_audit.md")
        if os.path.isfile(path):
            return 0.6
        return 0.0

    def compute(self) -> ConfidenceResult:
        """
        compute

        Purpose:
        Main entry point — scores all five factors with equal weight (0.2 each),
        computes the weighted total, calculates variance for the confidence
        interval, and assigns a letter grade.

        Inputs:
        None

        Outputs:
        ConfidenceResult with all scores, interval, and grade.
        """
        weights = {
            "proof_coverage": 0.20,
            "evidence": 0.20,
            "attack_results": 0.20,
            "regression": 0.20,
            "audit": 0.20,
        }

        raw_scores = {
            "proof_coverage": self.score_proof_coverage(),
            "evidence": self.score_evidence_completeness(),
            "attack_results": self.score_attack_results(),
            "regression": self.score_regression(),
            "audit": self.score_audit_quality(),
        }

        self.factors = []
        total = 0.0
        for name, raw in raw_scores.items():
            weighted = raw * weights[name]
            total += weighted
            self.factors.append(
                PerFactorScore(
                    factor_name=name,
                    raw_score=round(raw, 4),
                    weight=weights[name],
                    weighted_score=round(weighted, 4),
                    source_file=os.path.join(self.build_dir, f"{name}_report"),
                )
            )

        confidence = round(total * 100, 1)
        variance = sum(
            (raw_scores[k] - total) ** 2 for k in raw_scores
        ) / max(len(raw_scores), 1)
        std = math.sqrt(variance) * 100
        interval = f"{confidence} ± {std:.1f}"

        grade = self._grade(confidence)

        return ConfidenceResult(
            confidence_score=confidence,
            confidence_interval=interval,
            per_factor_scores=self.factors,
            confidence_grade=grade,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        )

    def _grade(self, score: float) -> str:
        """
        _grade

        Purpose:
        Converts a numeric confidence score (0-100) to a letter grade (A-F).

        Inputs:
        score — numeric confidence score

        Outputs:
        Letter grade string.
        """
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "F"


def compute_release_confidence(build_dir: str) -> dict:
    """
    compute_release_confidence

    Purpose:
    Convenience function that creates a ReleaseConfidenceScorer and runs
    the full confidence computation.

    Inputs:
    build_dir — path to the build directory containing report artifacts

    Outputs:
    Dict with confidence_score, confidence_interval, per_factor_scores,
    confidence_grade, timestamp.

    Security:
    Module entry point for F197.
    """
    scorer = ReleaseConfidenceScorer(build_dir)
    result = scorer.compute()
    return result.to_dict()
