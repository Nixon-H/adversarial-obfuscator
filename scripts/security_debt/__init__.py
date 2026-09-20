"""
security_debt — Security Debt Index (F170)

Purpose:
    Tracks and scores security debt: known gaps where protection is missing,
    weak, outdated, or vulnerable. Produces a normalized Security Debt Index
    (0-100) with category and severity breakdowns.

Architectural Role:
    Technical-debt measurement layer. Consumed by the Self-Audit Agent (F180)
    to flag accumulation of security debt across sprints.

Security Relevance:
    Quantifies the gap between current protection posture and ideal state.
    A rising debt index indicates eroding security that must be addressed.
"""

from .tracker import SecurityDebtItem, SecurityDebtTracker
from .scorer import SecurityDebtScorer, SecurityDebtReport

__all__ = [
    "SecurityDebtItem",
    "SecurityDebtTracker",
    "SecurityDebtScorer",
    "SecurityDebtReport",
]
