"""
confidence/interval.py — Confidence interval computation for security metrics (F179)

Purpose:
    Computes confidence intervals for security metric samples using normal
    approximation or Student's t-distribution based on sample size. Provides
    the SecurityConfidenceInterval data class and formatting utilities.

Architectural Role:
    Statistical engine. Consumed by any module that reports numeric security
    scores (metrics, reality, reproducibility) to add statistical rigour.

Security Relevance:
    Without confidence intervals, security metrics can be cherry-picked or
    misinterpreted. F179 enforces honest reporting of uncertainty.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class SecurityConfidenceInterval:
    """A confidence interval for a security metric estimate.

    Attributes:
        mean: Sample mean.
        margin: Half-width of the confidence interval.
        lower: Lower bound (mean - margin).
        upper: Upper bound (mean + margin).
        confidence_level: Requested confidence level (e.g. 0.95).
        sample_size: Number of samples.
        distribution: "normal" (n ≥ 30) or "t-distribution" (n < 30).
    """
    mean: float
    margin: float
    lower: float
    upper: float
    confidence_level: float
    sample_size: int
    distribution: str

    def __str__(self) -> str:
        """Human-readable representation: "mean ± margin"."""
        return f"{self.mean:.0f} ± {self.margin:.0f}"

    def to_tuple(self) -> Tuple[float, float]:
        """Return (lower, upper) as a tuple."""
        return (self.lower, self.upper)

    def to_dict(self) -> Dict:
        """Serialize the interval to a dict with rounded values."""
        return {
            "mean": round(self.mean, 4),
            "margin": round(self.margin, 4),
            "lower": round(self.lower, 4),
            "upper": round(self.upper, 4),
            "confidence_level": self.confidence_level,
            "sample_size": self.sample_size,
            "distribution": self.distribution,
        }


def _norm_ppf(p: float) -> float:
    """Approximate the standard normal quantile function (inverse CDF) using the Hastings formula.

    Used as a fallback when scipy.stats is not available.
    """
    if p <= 0.0 or p >= 1.0:
        return 0.0
    if abs(p - 0.5) < 1e-15:
        return 0.0
    q = 1.0 - p if p > 0.5 else p
    t = math.sqrt(-2.0 * math.log(q if q > 1e-100 else 1e-100))
    c0 = 2.515517
    c1 = 0.802853
    c2 = 0.010328
    d1 = 1.432788
    d2 = 0.189269
    d3 = 0.001308
    z = t - (c0 + c1 * t + c2 * t * t) / (1.0 + d1 * t + d2 * t * t + d3 * t * t * t)
    return z if p > 0.5 else -z


def _normal_critical(alpha: float) -> float:
    """Compute the critical z-value for a given alpha (two-tailed normal)."""
    return _norm_ppf(1.0 - alpha / 2.0)


def _t_critical(alpha: float, dof: int) -> float:
    """Approximate the critical t-value using a normal approximation with Cornish-Fisher expansion.

    For dof ≥ 100, falls back to the normal approximation.
    """
    if dof <= 0:
        return _normal_critical(alpha)
    if dof >= 100:
        z = _normal_critical(alpha)
        return z + (z ** 3 + z) / (4.0 * dof)
    z = _normal_critical(alpha)
    g = ((z ** 3 + z) / 4.0)
    g2 = ((5 * z ** 5 + 16 * z ** 3 + 3 * z) / 96.0)
    g3 = ((3 * z ** 7 + 19 * z ** 5 + 17 * z ** 3 - 15 * z) / 384.0)
    return z + g / dof + g2 / (dof ** 2) + g3 / (dof ** 3)


def compute_confidence_interval(
    samples: List[float],
    confidence_level: float = 0.95,
) -> SecurityConfidenceInterval:
    """Compute a confidence interval for the given security metric samples.

    Handles edge cases: empty list → zero interval, single sample → degenerate
    interval. Uses normal critical values for n ≥ 30, t-distribution otherwise.
    """
    n = len(samples)
    if n == 0:
        return SecurityConfidenceInterval(
            mean=0.0, margin=0.0, lower=0.0, upper=0.0,
            confidence_level=confidence_level, sample_size=0,
            distribution="none",
        )
    if n == 1:
        return SecurityConfidenceInterval(
            mean=samples[0], margin=0.0,
            lower=samples[0], upper=samples[0],
            confidence_level=confidence_level, sample_size=1,
            distribution="degenerate",
        )

    mean = sum(samples) / n
    variance = sum((x - mean) ** 2 for x in samples) / (n - 1)
    std_dev = math.sqrt(variance)
    alpha = 1.0 - confidence_level
    std_err = std_dev / math.sqrt(n)

    if n >= 30:
        critical = _normal_critical(alpha)
        distribution = "normal"
    else:
        critical = _t_critical(alpha, n - 1)
        distribution = "t-distribution"

    margin = critical * std_err
    lower = mean - margin
    upper = mean + margin

    return SecurityConfidenceInterval(
        mean=mean,
        margin=margin,
        lower=lower,
        upper=upper,
        confidence_level=confidence_level,
        sample_size=n,
        distribution=distribution,
    )


def format_confidence_interval(
    score_label: str,
    samples: List[float],
    confidence_level: float = 0.95,
) -> str:
    """Format a confidence interval as a human-readable monospace report string."""
    ci = compute_confidence_interval(samples, confidence_level)
    lines = []
    lines.append("-" * 60)
    lines.append(f"  {score_label}")
    lines.append("-" * 60)
    lines.append(f"  Score: {ci.mean:.0f}/100")
    lines.append(f"  Confidence Interval: {ci}")
    lines.append(f"  Range: [{ci.lower:.1f}, {ci.upper:.1f}]")
    lines.append(f"  Level: {confidence_level * 100:.0f}%")
    lines.append(f"  Samples: {ci.sample_size}")
    lines.append(f"  Distribution: {ci.distribution}")
    lines.append(f"  Margin: {ci.margin:.1f}")
    lines.append("-" * 60)
    return "\n".join(lines)
