"""
attack_corpus/__init__.py

Purpose:
Exports AttackCorpus and build_attack_corpus for use by the meta-assurance pipeline.

Architectural Role:
Package init for the Attack Corpus feature (F196).

Security Relevance:
The attack corpus catalogs known attack vectors and their coverage status.
"""
from __future__ import annotations

from .corpus import AttackCorpus, build_attack_corpus

__all__ = [
    "AttackCorpus",
    "build_attack_corpus",
]
