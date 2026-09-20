"""
reproducibility — Reproducibility Score (F178)

Purpose:
    Evaluates how reproducible build artefacts are by scoring each file on
    content determinism, metadata stability, and environment sensitivity.
    Produces an overall ReproducibilityReport with recommendations.

Architectural Role:
    Quality-assurance layer. Identifies artefacts that embed non-deterministic
    content (timestamps, random seeds) that would cause bitwise differences
    across rebuilds.

Security Relevance:
    Non-reproducible builds undermine supply-chain security: if two builds
    of the same source produce different artefacts, tampering cannot be
    reliably detected. Reproducibility scoring quantifies this risk.
"""

from __future__ import annotations

from .scorer import ReproducibilityResult, ReproducibilityReport, compute_reproducibility
from .checker import check_result_reproducibility, check_benchmark_reproducibility, check_attack_reproducibility, check_proof_reproducibility, check_test_reproducibility

__all__ = [
    "ReproducibilityScore",
    "ReproducibilityReport",
    "compute_reproducibility",
    "check_result_reproducibility",
    "check_benchmark_reproducibility",
    "check_attack_reproducibility",
    "check_proof_reproducibility",
    "check_test_reproducibility",
    "ReproducibilityResult",
]

ReproducibilityScore = float
