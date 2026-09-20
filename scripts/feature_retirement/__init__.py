"""
feature_retirement — Feature Retirement (F176)

Purpose:
    Assesses each protection feature for retirement eligibility based on
    effectiveness, overhead, survivability, and integration health. Produces
    recommendations: KEEP, MONITOR, OPTIMIZE, or DEPRECATE.

Architectural Role:
    Lifecycle management layer. Helps identify features that have become
    obsolete, too costly, or ineffective, enabling informed removal decisions.

Security Relevance:
    Retaining obsolete or ineffective features increases attack surface and
    maintenance burden. Systematic retirement analysis keeps the protection
    surface lean and effective.
"""

from .analyzer import (
    RetirementAnalyzer,
    RetirementAssessment,
    RetirementReport,
    RetirementStatus,
)


def analyze_feature_retirement(feature_name: str) -> dict:
    """Convenience: assess a single feature's retirement eligibility; return dict summary."""
    analyzer = RetirementAnalyzer()
    a = analyzer.assess_feature(feature_name)
    return {
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


def generate_retirement_report() -> RetirementReport:
    """Convenience: run a full retirement analysis and return the report object."""
    analyzer = RetirementAnalyzer()
    return analyzer.generate_report()


__all__ = [
    "RetirementAnalyzer",
    "RetirementAssessment",
    "RetirementReport",
    "RetirementStatus",
    "analyze_feature_retirement",
    "generate_retirement_report",
]
