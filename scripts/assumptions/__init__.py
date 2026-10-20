"""
assumptions — Assumption Tracker (F171)

Purpose:
    Tracks and checks runtime assumptions that each protection feature depends
    on (OS features, hardware capabilities, software packages, configuration).
    Produces an AssumptionReport listing satisfied, unsatisfied, and unknown
    assumptions.

Architectural Role:
    Pre-flight validation layer. Called before pipeline execution to verify
    the runtime environment meets all feature prerequisites.

Security Relevance:
    A feature whose assumptions are not met will silently fail or behave
    incorrectly. Explicit assumption tracking prevents runtime surprises.
"""

from .tracker import Assumption, AssumptionReport, AssumptionTracker
from .registry import FEATURE_ASSUMPTIONS, register_all


def build_assumption_report(runtime_caps: dict | None = None) -> AssumptionReport:
    """Build an assumption report by registering all known assumptions and checking them against runtime capabilities."""
    tracker = AssumptionTracker()
    register_all(tracker)
    if runtime_caps is not None:
        tracker.check_assumptions(runtime_caps)
    return tracker.build_report()


def check_assumptions(runtime_caps: dict) -> AssumptionReport:
    """Alias for build_assumption_report; checks all assumptions against provided runtime capabilities."""
    return build_assumption_report(runtime_caps)

# Re-exported names: listed explicitly so the intent is
# unambiguous and the unused-import check does not flag them.
__all__ = [
    "Assumption",
    "AssumptionReport",
    "AssumptionTracker",
    "FEATURE_ASSUMPTIONS",
    "register_all",
]
