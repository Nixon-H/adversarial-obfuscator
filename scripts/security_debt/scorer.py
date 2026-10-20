"""
security_debt/scorer.py — Security Debt Index scoring engine (F170)

Purpose:
    Consumes a SecurityDebtTracker and produces a normalized Security Debt
    Index (0-100) with category breakdowns, severity counts, top items, and
    actionable recommendations.

Architectural Role:
    Scoring layer on top of the tracker. Produces the SecurityDebtReport that
    is consumed by the Self-Audit Agent (F180) and monitoring dashboards.

Security Relevance:
    Transforms raw debt items into a measurable index that can be tracked
    over time, gated in CI/CD, and used to prioritise remediation.
"""

from __future__ import annotations

import json
import time  # noqa: F401 (this line binds a name used by an embedded template)
from dataclasses import dataclass, field
from typing import Any

from .tracker import SecurityDebtItem, SecurityDebtTracker

# Weighting factors for severity levels and debt categories.
_SEVERITY_WEIGHTS: dict[str, float] = {
    "critical": 10.0,
    "high": 5.0,
    "medium": 2.0,
    "low": 0.5,
    "info": 0.1,
}

_CATEGORY_WEIGHTS: dict[str, float] = {
    "unprotected_function": 10.0,
    "weak_protection": 7.0,
    "missing_coverage": 5.0,
    "known_vulnerability": 9.0,
    "exposure_risk": 6.0,
    "outdated_mechanism": 3.0,
    "config_weakness": 4.0,
    "complexity_risk": 2.0,
}

_MAX_RAW_DEBT = 10000.0


@dataclass
class SecurityDebtReport:
    """Aggregate security debt report with index, breakdowns, and recommendations.

    Attributes:
        overall_index: Normalized debt index (0-100), higher = more debt.
        total_items: Total number of debt items.
        critical_count / high_count / medium_count / low_count / info_count: Severity tallies.
        raw_debt_score: Un-normalized weighted sum before clamping.
        normalized_index: Clamped and scaled to 0-100.
        category_breakdown: Percentage contribution per category.
        severity_breakdown: Raw count per severity level.
        top_items: Up to 10 highest-scoring items.
        recommendations: Actionable text suggestions.
    """

    overall_index: float = 0.0
    total_items: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    raw_debt_score: float = 0.0
    normalized_index: float = 0.0
    category_breakdown: dict[str, float] = field(default_factory=dict)
    severity_breakdown: dict[str, int] = field(default_factory=dict)
    top_items: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report to a plain dict (top items limited to 10)."""
        return {
            "overall_index": self.overall_index,
            "total_items": self.total_items,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "info_count": self.info_count,
            "raw_debt_score": self.raw_debt_score,
            "normalized_index": self.normalized_index,
            "category_breakdown": self.category_breakdown,
            "severity_breakdown": self.severity_breakdown,
            "top_items": self.top_items[:10],
            "recommendations": self.recommendations,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize the report to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class SecurityDebtScorer:
    """Computes weighted security debt scores from a SecurityDebtTracker.

    Uses severity × category weights × impact multipliers to produce a raw
    debt score, then normalizes it to a 0-100 index.
    """

    def __init__(self, tracker: SecurityDebtTracker) -> None:
        self._tracker = tracker

    def compute_raw_debt(self) -> float:
        """Compute the raw (un-normalized) weighted debt sum from all tracked items."""
        items = self._tracker.get_items()
        if not items:
            return 0.0
        total = 0.0
        for item in items:
            severity_weight = _SEVERITY_WEIGHTS.get(item.severity.value, 1.0)
            category_weight = _CATEGORY_WEIGHTS.get(item.category.value, 1.0)
            impact = max(0.0, min(10.0, item.impact_score))
            total += severity_weight * category_weight * (1.0 + impact)
        return total

    def compute_normalized_index(self, raw_debt: float) -> float:
        """Clamp raw_debt to MAX_RAW_DEBT and scale to a 0-100 percentage."""
        if raw_debt <= 0.0:
            return 0.0
        clamped = min(raw_debt, _MAX_RAW_DEBT)
        return round((clamped / _MAX_RAW_DEBT) * 100.0, 2)

    def compute_category_breakdown(self) -> dict[str, float]:
        """Compute percentage contribution of each debt category to the total raw debt."""
        items = self._tracker.get_items()
        breakdown: dict[str, float] = {}
        for item in items:
            key = item.category.value
            severity_weight = _SEVERITY_WEIGHTS.get(item.severity.value, 1.0)
            category_weight = _CATEGORY_WEIGHTS.get(item.category.value, 1.0)
            impact = max(0.0, min(10.0, item.impact_score))
            contribution = severity_weight * category_weight * (1.0 + impact)
            breakdown[key] = breakdown.get(key, 0.0) + contribution
        total = sum(breakdown.values()) or 1.0
        return {k: round((v / total) * 100.0, 2) for k, v in sorted(breakdown.items(), key=lambda x: -x[1])}

    def get_top_items(self, n: int = 10) -> list[SecurityDebtItem]:
        """Return the n highest-scoring debt items, sorted by composite weight descent."""
        items = self._tracker.get_items()
        scored = []
        for item in items:
            severity_weight = _SEVERITY_WEIGHTS.get(item.severity.value, 1.0)
            category_weight = _CATEGORY_WEIGHTS.get(item.category.value, 1.0)
            impact = max(0.0, min(10.0, item.impact_score))
            composite = severity_weight * category_weight * (1.0 + impact)
            scored.append((composite, item))
        scored.sort(key=lambda x: -x[0])
        return [item for _, item in scored[:n]]

    def generate_recommendations(self) -> list[str]:
        """Produce human-readable remediation recommendations based on current debt profile."""
        recs: list[str] = []
        by_severity = self._tracker.count_by_severity()
        by_category = self._tracker.count_by_category()

        critical = by_severity.get("critical", 0)
        high = by_severity.get("high", 0)
        if critical > 0:
            recs.append(f"Address {critical} critical-security debt item(s) immediately")
        if high > 0:
            recs.append(f"Resolve {high} high-severity debt item(s) in current sprint")
        if by_category.get("unprotected_function", 0) > 0:
            recs.append(f"Apply protection to {by_category['unprotected_function']} unprotected function(s)")
        if by_category.get("missing_coverage", 0) > 0:
            recs.append(f"Add test coverage for {by_category['missing_coverage']} uncovered area(s)")
        if by_category.get("known_vulnerability", 0) > 0:
            recs.append(f"Patch {by_category['known_vulnerability']} known vulnerabilit(y/ies)")
        if by_category.get("exposure_risk", 0) > 0:
            recs.append(f"Reduce exposure risk in {by_category['exposure_risk']} location(s)")

        total = self._tracker.count()
        if total > 0:
            recs.append(f"Track {total} total security debt item(s) across {len(by_category)} categor(y/ies)")

        return recs

    def generate_report(self) -> SecurityDebtReport:
        """Compute all score components and assemble a SecurityDebtReport."""
        items = self._tracker.get_items()
        by_severity = self._tracker.count_by_severity()
        raw = self.compute_raw_debt()
        normalized = self.compute_normalized_index(raw)

        report = SecurityDebtReport(
            overall_index=normalized,
            total_items=len(items),
            critical_count=by_severity.get("critical", 0),
            high_count=by_severity.get("high", 0),
            medium_count=by_severity.get("medium", 0),
            low_count=by_severity.get("low", 0),
            info_count=by_severity.get("info", 0),
            raw_debt_score=round(raw, 2),
            normalized_index=normalized,
            category_breakdown=self.compute_category_breakdown(),
            severity_breakdown=by_severity,
            top_items=[item.to_dict() for item in self.get_top_items()],
            recommendations=self.generate_recommendations(),
        )
        return report
