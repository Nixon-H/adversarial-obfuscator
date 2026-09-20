"""
proof_coverage/coverage.py

Purpose:
Data structures for representing proof coverage per pipeline stage. Tracks
whether a proof exists, its type (z3/structural/none), the fraction of
functions covered, and its validation status.

Security Relevance:
The coverage data drives decisions about which stages need proof development.
A stage with has_proof=False but active transformations is a security gap.

Dependencies:
- standard library only
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List


@dataclass
class ProofCoverage:
    """
    ProofCoverage

    What it measures:
    - has_proof: whether a formal proof module exists for this stage
    - proof_type: 'z3' (SMT-based), 'structural' (manual reasoning), 'none'
    - functions_covered / functions_total: ratio of proven functions
    - proof_validated: whether the proof module passed validity checks
    - last_validated: ISO timestamp of last validation

    Security impact:
    stages with has_proof=False have NO formal correctness guarantee.
    stages with proof_validated=False have proofs that failed validation.

    Failure mode:
    Not directly a failure source — purely informational. But decisions
    based on stale coverage data may lead to accepting untrusted code.
    """
    stage: str
    has_proof: bool = False
    proof_type: str = "none"
    functions_covered: int = 0
    functions_total: int = 0
    coverage_percent: float = 0.0
    proof_validated: bool = False
    last_validated: str = ""

    def __post_init__(self):
        if not self.last_validated:
            self.last_validated = datetime.now(timezone.utc).isoformat()
        if self.functions_total > 0 and self.coverage_percent == 0.0:
            self.coverage_percent = (self.functions_covered / self.functions_total) * 100.0
        if self.has_proof and self.proof_type == "none":
            self.proof_type = "structural"

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "has_proof": self.has_proof,
            "proof_type": self.proof_type,
            "functions_covered": self.functions_covered,
            "functions_total": self.functions_total,
            "coverage_percent": round(self.coverage_percent, 2),
            "proof_validated": self.proof_validated,
            "last_validated": self.last_validated,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ProofCoverage:
        return cls(**d)


@dataclass
class ProofCoverageReport:
    overall_coverage: float = 0.0
    stage_scores: Dict[str, ProofCoverage] = field(default_factory=dict)
    uncovered_stages: List[str] = field(default_factory=list)
    partially_covered_stages: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "overall_coverage": round(self.overall_coverage, 2),
            "stage_scores": {k: v.to_dict() for k, v in self.stage_scores.items()},
            "uncovered_stages": self.uncovered_stages,
            "partially_covered_stages": self.partially_covered_stages,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ProofCoverageReport:
        stage_scores = {k: ProofCoverage.from_dict(v) for k, v in d.get("stage_scores", {}).items()}
        return cls(
            overall_coverage=d.get("overall_coverage", 0.0),
            stage_scores=stage_scores,
            uncovered_stages=d.get("uncovered_stages", []),
            partially_covered_stages=d.get("partially_covered_stages", []),
            recommendations=d.get("recommendations", []),
            generated_at=d.get("generated_at", ""),
        )
