"""
phase_self_critique.py

Purpose:
Runs the self-critique engine — the pipeline questions its own security
claims, evaluates the evidence for each claim, and produces an honesty
score.  Designed to counteract overconfidence and confirmation bias.

Architectural Role:
Meta-audit phase — the pipeline audits its own reasoning.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.self_critique.*

Security Relevance:
Self-critique is a safeguard against groupthink and overconfidence —
it forces the pipeline to confront its own limitations.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.self_critique.engine import SelfCritiqueEngine



def phase_self_critique(args: Any) -> dict:
    """
    Run the self-critique engine to audit the pipeline's own claims.

    Args:
        args: argparse.Namespace

    Returns:
        dict with honesty_score, critiques, and markdown report
    """
    log("SELF_CRITIQUE", "Running self-critique engine...")
    root = getattr(args, "root", _ROOT)
    engine = SelfCritiqueEngine(root)
    report = engine.generate_report()

    print()
    print("=" * 60)
    print("  SELF-CRITIQUE REPORT")
    print("=" * 60)
    print(f"  Honesty score: {report.honesty_score}")
    print(f"  Evidence summary: {report.evidence_summary}")
    print(f"  {'─' * 40}")
    for c in report.critiques:
        print(f"  [{c.severity.upper():8s}] {c.question}")
        print(f"  {' ':<10s}{c.answer[:80]}...")
        print()
    print("=" * 60)
    print()

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "self_critique_report.json")
    atomic_write(report_path, json.dumps(report.to_dict(), indent=2, default=str))
    log("SELF_CRITIQUE", f"Report saved to {report_path}")

    markdown = engine.generate_markdown()
    md_path = os.path.join(BUILD_DIR, "self_critique.md")
    atomic_write(md_path, markdown)
    log("SELF_CRITIQUE", f"Markdown saved to {md_path}")

    return report.to_dict()
