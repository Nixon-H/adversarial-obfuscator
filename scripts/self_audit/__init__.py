"""
self_audit — Self-Audit Agent (F180)

Purpose:
    Runs a comprehensive self-audit across ten categories (source, tests,
    reachability, proofs, benchmarks, claims, metrics, debt, assumptions,
    reality). Produces an AuditReport with an overall score and grade (A-F).

Architectural Role:
    Top-level quality gate. Aggregates results from F167-F179 into a single
    actionable report. Designed to run in CI/CD as a pre-release gate.

Security Relevance:
    The self-audit is the final checkpoint before release. It ensures that
    all protection features are reachable, tested, evidenced, and free of
    false confidence patterns, providing a holistic security posture summary.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


@dataclass
class AuditFinding:
    """A single finding from the self-audit.

    Attributes:
        category: Which audit category (source, tests, reachability, etc.).
        severity: critical / major / minor.
        title: Short headline.
        description: Detailed explanation.
        recommendation: Actionable remediation.
        file / line: Optional source location.
        metric_name / metric_value / threshold: Optional numerical check details.
    """
    category: str
    severity: str
    title: str
    description: str
    recommendation: str
    file: Optional[str] = None
    line: Optional[int] = None
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None


@dataclass
class AuditCategory:
    """A single audit category with score, max, and findings.

    Attributes:
        name: Category name (e.g. "source", "tests").
        score: Actual score achieved.
        max_score: Maximum possible score.
        findings: List of AuditFinding instances.
    """

    name: str
    score: float
    max_score: float
    findings: List[AuditFinding] = field(default_factory=list)

    @property
    def percentage(self) -> float:
        return (self.score / self.max_score * 100) if self.max_score else 0.0

    @property
    def passed(self) -> bool:
        """Return True if the category score percentage is ≥ 70 %."""
        return self.percentage >= 70.0


@dataclass
class AuditReport:
    """The complete self-audit report with overall score, grade, and per-category breakdown.

    Attributes:
        timestamp: ISO-8601 audit timestamp.
        overall_score: 0-100 weighted composite.
        overall_grade: A-F letter grade.
        categories: Category name → AuditCategory.
        total_findings / critical_findings / major_findings / minor_findings: Severity counts.
    """

    timestamp: str
    overall_score: float
    overall_grade: str
    categories: Dict[str, AuditCategory] = field(default_factory=dict)
    total_findings: int = 0
    critical_findings: int = 0
    major_findings: int = 0
    minor_findings: int = 0

    def to_dict(self) -> dict:
        """Serialize the full report to a dict for JSON export."""
        return {
            "timestamp": self.timestamp,
            "overall_score": self.overall_score,
            "overall_grade": self.overall_grade,
            "total_findings": self.total_findings,
            "critical_findings": self.critical_findings,
            "major_findings": self.major_findings,
            "minor_findings": self.minor_findings,
            "categories": {
                name: {
                    "name": cat.name,
                    "score": cat.score,
                    "max_score": cat.max_score,
                    "percentage": cat.percentage,
                    "passed": cat.passed,
                    "findings": [
                        {
                            "category": f.category,
                            "severity": f.severity,
                            "title": f.title,
                            "description": f.description,
                            "recommendation": f.recommendation,
                            "file": f.file,
                            "line": f.line,
                            "metric_name": f.metric_name,
                            "metric_value": f.metric_value,
                            "threshold": f.threshold,
                        }
                        for f in cat.findings
                    ],
                }
                for name, cat in self.categories.items()
            },
        }


def score_to_grade(score: float) -> str:
    """Convert a numeric score (0-100) to a letter grade (A-F)."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 50:
        return "D"
    return "F"
