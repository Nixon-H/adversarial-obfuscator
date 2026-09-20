"""
self_critique/__init__.py

Purpose:
Exports SelfCritiqueEngine and generate_self_critique for use by the
meta-assurance pipeline.

Architectural Role:
Package init for the Self-Critique Engine feature (F200).

Security Relevance:
Self-critique provides an honest, introspective assessment of the entire
security pipeline, identifying weaknesses that other features may miss.
"""
from __future__ import annotations

from .engine import SelfCritiqueEngine, generate_self_critique

__all__ = [
    "SelfCritiqueEngine",
    "generate_self_critique",
]
