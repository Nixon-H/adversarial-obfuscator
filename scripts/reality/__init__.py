"""
reality — Reality Score (F167)

Purpose:
    Computes a reality score per feature, measuring how grounded each security
    feature is in actual implementation, reachability, runtime execution, and
    attack-impact evidence.

Architectural Role:
    Aggregation layer: reads pipeline artefacts (manifest, metrics, red-team
    reports, benchmark reports, security-gate reports) and produces a weighted
    reality report.

Security Relevance:
    Prevents overclaiming by quantifying the gap between intended and actual
    protection. A low reality score flags features that exist only on paper.
"""

from .scorer import (
    RealityReport,
    FeatureReality,
    compute_reality_scores,
    compute_feature_reality,
    score_to_grade,
    aggregate_reality_score,
    load_from_build,
    FEATURE_REGISTRY,
)

# Re-exported names: listed explicitly so the intent is
# unambiguous and the unused-import check does not flag them.
__all__ = [
    "FEATURE_REGISTRY",
    "FeatureReality",
    "RealityReport",
    "aggregate_reality_score",
    "compute_feature_reality",
    "compute_reality_scores",
    "load_from_build",
    "score_to_grade",
]
