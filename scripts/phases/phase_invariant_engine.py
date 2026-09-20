"""
phase_invariant_engine.py

Purpose:
Verifies security invariants across the entire codebase — checks that
properties like "all file writes are encrypted" or "no plaintext keys
in memory" hold by analyzing code patterns.

Architectural Role:
Automated verification phase — enforces security properties as code.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.invariant_engine.*

Security Relevance:
Invariant violations are security bugs waiting to happen; automated
invariant checking catches them before they reach production.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.invariant_engine.engine import SecurityInvariantEngine



def phase_invariant_engine(args: Any) -> dict:
    """
    Verify all security invariants across the codebase.

    Args:
        args: argparse.Namespace

    Returns:
        dict with invariant_score, violations_found, per-invariant results
    """
    log("INVARIANT_ENGINE", "Verifying security invariants across codebase...")

    engine = SecurityInvariantEngine()
    result = engine.verify_invariants()

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "invariant_engine_report.json")
    atomic_write(report_path, json.dumps(result, indent=2))
    log("INVARIANT_ENGINE", f"Report saved to {report_path}")

    print()
    print("=" * 60)
    print("  SECURITY INVARIANT ENGINE")
    print("=" * 60)
    print(f"  Invariant score: {result['invariant_score']:.1f}/100")
    print(f"  Violations found: {result['violations_found']}")
    print("=" * 60)
    print()

    for inv_name, inv_result in result["invariant_results"].items():
        status = "PASS" if inv_result["passed"] else "FAIL"
        print(f"  [{status}] {inv_name} ({len(inv_result['violations'])} violations)")
        for v in inv_result["violations"][:3]:
            print(f"         [{v['severity']}] {v['file_path']}:{v['line_number']} - {v['description']}")
    print()
    print("=" * 60)
    print()

    return result
