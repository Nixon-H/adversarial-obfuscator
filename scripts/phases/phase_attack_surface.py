"""
phase_attack_surface.py

Purpose:
Enumerates all attack surfaces in the codebase — identifies entry points,
assigns risk levels, and categorizes them for prioritization.

Architectural Role:
Security audit phase — produces an attack surface map.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.attack_surface.*

Security Relevance:
Attack surface enumeration is the foundation for threat modeling;
unknown attack surfaces cannot be defended.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.attack_surface.enumerator import AttackSurfaceEnumerator

def phase_attack_surface(args: Any) -> dict:
    """
    Enumerate all attack surfaces in the codebase.

    Args:
        args: argparse.Namespace

    Returns:
        dict with entry points, risk summary, and per-category results
    """
    log("ATTACK_SURFACE", "Enumerating all attack surfaces...")

    enumerator = AttackSurfaceEnumerator()
    result = enumerator.enumerate_attack_surfaces()

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "attack_surface_report.json")
    atomic_write(report_path, json.dumps(result, indent=2))
    log("ATTACK_SURFACE", f"Report saved to {report_path}")

    print()
    print("=" * 60)
    print("  ATTACK SURFACE ENUMERATION")
    print("=" * 60)
    print(f"  Total entry points: {result['total_entry_points']}")
    print(f"  Risk summary:")
    for level, count in sorted(result["risk_summary"].items()):
        print(f"    {level:>10s}: {count}")
    print("=" * 60)
    print()

    for category, entries in result["per_category_results"].items():
        if entries:
            risks = set(e["risk_level"] for e in entries)
            print(f"  [{category}] {len(entries)} entry points | risks: {', '.join(sorted(risks))}")

    print()
    print("=" * 60)
    print()

    return result
