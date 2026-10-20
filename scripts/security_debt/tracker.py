"""
security_debt/tracker.py — Security debt item model and tracker (F170)

Purpose:
    Defines the data model for security debt items (DebtSeverity, DebtCategory,
    SecurityDebtItem) and the SecurityDebtTracker that records, queries, and
    aggregates debt items.

Architectural Role:
    Data layer used by SecurityDebtScorer to compute the Security Debt Index.
    Provides query methods for severity, category, and feature-based filtering.

Security Relevance:
    Each debt item represents a known gap between current and required
    protection, making technical debt visible and prioritizable.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


class DebtSeverity(Enum):
    """Severity levels for security debt items."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DebtCategory(Enum):
    """Categories of security debt, from missing protection to complexity risk."""
    UNPROTECTED_FUNCTION = "unprotected_function"
    WEAK_PROTECTION = "weak_protection"
    MISSING_COVERAGE = "missing_coverage"
    OUTDATED_MECHANISM = "outdated_mechanism"
    CONFIG_WEAKNESS = "config_weakness"
    KNOWN_VULNERABILITY = "known_vulnerability"
    EXPOSURE_RISK = "exposure_risk"
    COMPLEXITY_RISK = "complexity_risk"


@dataclass
class SecurityDebtItem:
    """A single security debt item with category, severity, and impact scoring.

    Attributes:
        category: Type of debt (unprotected_function, weak_protection, etc.).
        severity: Critical / High / Medium / Low / Info.
        description: Human-readable explanation of the debt.
        location: Filesystem path or logical location.
        feature: Feature name this debt relates to.
        impact_score: Numeric impact estimate (0.0 – 10.0).
        effort_to_fix: Estimated effort string (e.g. "2 days", "unknown").
        timestamp_ns: Monotonic timestamp for ordering.
        item_hash: SHA-256 prefix hash for deduplication.
    """

    category: DebtCategory
    severity: DebtSeverity
    description: str
    location: str
    feature: str
    impact_score: float = 0.0
    effort_to_fix: str = "unknown"
    timestamp_ns: int = 0
    item_hash: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp_ns:
            self.timestamp_ns = time.monotonic_ns()
        if not self.item_hash:
            raw = f"{self.category.value}:{self.description}:{self.location}:{self.feature}"
            self.item_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "location": self.location,
            "feature": self.feature,
            "impact_score": self.impact_score,
            "effort_to_fix": self.effort_to_fix,
            "timestamp_ns": self.timestamp_ns,
            "item_hash": self.item_hash,
        }


class SecurityDebtTracker:
    """Thread-safe tracker for security debt items with query and aggregation methods."""

    def __init__(self) -> None:
        self._items: list[SecurityDebtItem] = []

    def record_item(self, item: SecurityDebtItem) -> SecurityDebtItem:
        """Add a pre-built SecurityDebtItem to the tracker."""
        self._items.append(item)
        return item

    def record(
        self,
        category: DebtCategory,
        severity: DebtSeverity,
        description: str,
        location: str,
        feature: str,
        impact_score: float = 0.0,
        effort_to_fix: str = "unknown",
    ) -> SecurityDebtItem:
        """Convenience: create, add, and return a new SecurityDebtItem."""
        item = SecurityDebtItem(
            category=category,
            severity=severity,
            description=description,
            location=location,
            feature=feature,
            impact_score=impact_score,
            effort_to_fix=effort_to_fix,
        )
        self._items.append(item)
        return item

    def get_items(self) -> list[SecurityDebtItem]:
        """Return a copy of all tracked items."""
        return list(self._items)

    def get_items_by_severity(self, severity: DebtSeverity) -> list[SecurityDebtItem]:
        """Filter items by severity level."""
        return [i for i in self._items if i.severity == severity]

    def get_items_by_category(self, category: DebtCategory) -> list[SecurityDebtItem]:
        """Filter items by debt category."""
        return [i for i in self._items if i.category == category]

    def get_items_by_feature(self, feature: str) -> list[SecurityDebtItem]:
        """Filter items related to a specific feature."""
        return [i for i in self._items if i.feature == feature]

    def count(self) -> int:
        """Total number of tracked debt items."""
        return len(self._items)

    def count_by_severity(self) -> dict[str, int]:
        """Return a dict mapping severity values to item counts."""
        counts: dict[str, int] = {}
        for item in self._items:
            key = item.severity.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def count_by_category(self) -> dict[str, int]:
        """Return a dict mapping category values to item counts."""
        counts: dict[str, int] = {}
        for item in self._items:
            key = item.category.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def clear(self) -> None:
        """Remove all tracked items."""
        self._items.clear()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full tracker state (counts + items) to a dict."""
        return {
            "total_items": len(self._items),
            "by_severity": self.count_by_severity(),
            "by_category": self.count_by_category(),
            "items": [item.to_dict() for item in self._items],
        }
