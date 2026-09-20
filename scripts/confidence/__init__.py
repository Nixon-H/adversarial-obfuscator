"""
confidence — Security Confidence Interval (F179)

Purpose:
    Computes statistical confidence intervals for security metrics sampled
    across multiple runs. Uses normal approximation for n ≥ 30 and Student's
    t-distribution for smaller samples.

Architectural Role:
    Statistical-analysis layer. Provides a rigorous mathematical foundation
    for claims about security metric values, replacing point estimates with
    interval estimates.

Security Relevance:
    A single security metric value is meaningless without a confidence interval.
    F179 ensures that reported scores are accompanied by their statistical
    uncertainty, preventing over-interpretation of noisy measurements.
"""

from .interval import compute_confidence_interval, format_confidence_interval, SecurityConfidenceInterval

__all__ = [
    "compute_confidence_interval",
    "format_confidence_interval",
    "SecurityConfidenceInterval",
]
