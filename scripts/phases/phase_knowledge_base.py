"""
phase_knowledge_base.py

Purpose:
Builds a security knowledge base — compiles all security-relevant
information (threats, protections, proofs, metrics) into a structured
database with category coverage statistics.

Architectural Role:
Knowledge management phase — centralizes security information.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.knowledge_base.*

Security Relevance:
A structured knowledge base enables automated reasoning about
security posture and supports downstream analysis phases.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.knowledge_base.database import build_knowledge_base



def phase_knowledge_base(args: Any) -> dict:
    """
    Build a structured security knowledge base.

    Args:
        args: argparse.Namespace

    Returns:
        dict with total_entries, by_category, and knowledge_coverage
    """
    log("KNOWLEDGE_BASE", "Building security knowledge base...")
    root = getattr(args, "root", _ROOT)
    result = build_knowledge_base(root)

    print()
    print("=" * 60)
    print("  SECURITY KNOWLEDGE BASE")
    print("=" * 60)
    print(f"  Total entries: {result['total_entries']}")
    print("  By category:")
    for cat, count in sorted(result["by_category"].items()):
        print(f"    {cat:30s} {count}")
    kc = result["knowledge_coverage"]
    print(f"  Knowledge coverage: {kc['coverage_pct']:.1f}% "
          f"({kc['covered_categories']}/{kc['total_categories']} categories)")
    print("=" * 60)
    print()

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "knowledge_base_report.json")
    atomic_write(report_path, json.dumps(result, indent=2, default=str))
    log("KNOWLEDGE_BASE", f"Report saved to {report_path}")

    return result
