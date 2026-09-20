"""
taxonomy.py

Purpose:
Defines the semantic leakage taxonomy: four levels of analysis
(variable, function, intent, architecture) and the data structures
(LeakageScore, LeakageReport) used to represent measurement results.

Architectural Role:
Shared type definitions for the semantic leakage metric. All analyzers
(scorer.py, analyzers.py) produce LeakageScore instances. The SLI
overall score is reported as a LeakageReport.

Execution Context:
Imported by all leakage submodules. LeakageScore and LeakageReport are
instantiated by analyzers and the scorer, serialized to JSON for
consumption by the security regression gates.

Dependencies:
- Standard library only (time, enum, dataclasses, typing)

Security Relevance:
The taxonomy defines what "semantic leakage" means at each level.
Variable leakage measures name/type preservation; function leakage
measures structural recovery; intent leakage measures algorithm
recovery; architecture leakage measures call-graph recovery.
Each level corresponds to a different attacker capability.

Maintenance Notes:
- Adding a new LeakageLevel requires updates to all four analyzers
  and the scorer's weight dict.
- LeakageScore.__post_init__ validates range (0-100 for score, 0-1
  for confidence). This is a safety check, not a security boundary.
"""

from __future__ import annotations
import logging
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class LeakageLevel(Enum):
    """Hierarchical levels of semantic leakage analysis."""
    VARIABLE = "variable"
    FUNCTION = "function"
    INTENT = "intent"
    ARCHITECTURE = "architecture"


@dataclass
class LeakageScore:
    """
    A single leakage measurement at one taxonomy level.

    Attributes:
        level: Which taxonomy level (variable, function, intent, architecture).
        score: Leakage score 0-100 (higher = more leakage).
        method: How the score was computed (e.g. 'static_analysis', 'structural').
        confidence: Confidence in the measurement (0.0-1.0).
        evidence: Dict with detailed sub-scores and raw data.
    """

    level: LeakageLevel
    score: float
    method: str
    confidence: float
    evidence: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate types, clamp score to [0, 100] and confidence to [0, 1]."""
        if not isinstance(self.score, (int, float)):
            logger.warning("LeakageScore.score is not numeric (got %s) — coercing to 0.0", type(self.score).__name__)
            self.score = 0.0
        if not isinstance(self.confidence, (int, float)):
            logger.warning("LeakageScore.confidence is not numeric (got %s) — coercing to 0.0", type(self.confidence).__name__)
            self.confidence = 0.0
        if not isinstance(self.level, LeakageLevel):
            logger.warning("LeakageScore.level is not a LeakageLevel enum (got %s) — allowing but unexpected", type(self.level).__name__)
        self.score = max(0.0, min(100.0, self.score))
        self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class LeakageReport:
    overall_sli: float
    variable_leakage: LeakageScore
    function_leakage: LeakageScore
    intent_leakage: LeakageScore
    architecture_leakage: LeakageScore
    per_function_scores: dict[str, dict[str, float]] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        def _safe_score(value: Any, field_name: str) -> float:
            if not isinstance(value, LeakageScore):
                logger.warning("LeakageReport.%s is not a LeakageScore (got %s) — using 0.0 fallback", field_name, type(value).__name__)
                return {"score": 0.0, "method": "unknown", "confidence": 0.0, "evidence": {}}
            return {
                "score": value.score,
                "method": value.method,
                "confidence": value.confidence,
                "evidence": value.evidence,
            }

        return {
            "overall_sli": self.overall_sli,
            "variable_leakage": _safe_score(self.variable_leakage, "variable_leakage"),
            "function_leakage": _safe_score(self.function_leakage, "function_leakage"),
            "intent_leakage": _safe_score(self.intent_leakage, "intent_leakage"),
            "architecture_leakage": _safe_score(self.architecture_leakage, "architecture_leakage"),
            "per_function_scores": self.per_function_scores,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at,
        }
