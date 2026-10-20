"""
phase_attack_corpus.py

Purpose:
Builds an attack corpus — collects all known attack techniques relevant
to the pipeline, categorized by type and severity.  Used as a reference
for threat modeling and coverage analysis.

Architectural Role:
Knowledge base phase — maintains the threat catalog.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.attack_corpus.*

Security Relevance:
A comprehensive attack corpus ensures threat modeling covers all
relevant attack vectors, not just the most common ones.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.attack_corpus.corpus import build_attack_corpus



def phase_attack_corpus(args: Any) -> dict:
    """
    Build an attack corpus from known threat data.

    Args:
        args: argparse.Namespace

    Returns:
        dict with total_attacks, categories, and severity_distribution
    """
    log("ATTACK_CORPUS", "Building attack corpus...")
    root = getattr(args, "root", _ROOT)
    corpus = build_attack_corpus(root)

    print()
    print("=" * 60)
    print("  ATTACK CORPUS REPORT")
    print("=" * 60)
    print(f"  Total attack entries: {corpus['total_attacks']}")
    print("  Categories:")
    for cat, count in sorted(corpus["categories"].items()):
        print(f"    {cat:25s} {count}")
    print("  Severity distribution:")
    for sev, count in sorted(corpus["severity_distribution"].items()):
        print(f"    {sev:25s} {count}")
    print("=" * 60)
    print()

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "attack_corpus_report.json")
    atomic_write(report_path, json.dumps(corpus, indent=2, default=str))
    log("ATTACK_CORPUS", f"Report saved to {report_path}")

    return corpus
