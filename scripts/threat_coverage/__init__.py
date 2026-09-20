"""
threat_coverage/__init__.py

Purpose:
Exports ThreatCoverageMapper and map_threat_coverage for use by the
meta-assurance pipeline.

Architectural Role:
Package init for the Formal Threat Coverage feature (F198).

Security Relevance:
Threat coverage maps protections to known threat categories, revealing gaps.
"""
from __future__ import annotations

from .mapper import ThreatCoverageMapper, map_threat_coverage

__all__ = [
    "ThreatCoverageMapper",
    "map_threat_coverage",
]
