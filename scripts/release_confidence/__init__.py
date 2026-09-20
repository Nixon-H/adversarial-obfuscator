"""
release_confidence/__init__.py

Purpose:
Exports ReleaseConfidenceScorer and compute_release_confidence for use by
the meta-assurance pipeline.

Architectural Role:
Package init for the Release Confidence Score feature (F197).

Security Relevance:
The release confidence score aggregates all other meta-assurance metrics into
a single go/no-go decision input.
"""
from __future__ import annotations

from .scorer import ReleaseConfidenceScorer, compute_release_confidence

__all__ = [
    "ReleaseConfidenceScorer",
    "compute_release_confidence",
]
