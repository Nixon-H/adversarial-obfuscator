"""
phase_runtime_truth.py

Purpose:
Records runtime truth — compares intended pipeline execution (what phases
are expected to run) against actual evidence collected.  Identifies gaps
where phases were expected to run but produced no evidence.

Architectural Role:
Verification phase — closes the loop between planning and execution.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.runtime_truth.*

Security Relevance:
Runtime truth surfaces the gap between intended and actual execution;
phases that silently fail produce no evidence but may appear to run.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, ROOT, atomic_write, log
from scripts.runtime_truth.monitor import RuntimeTruthMonitor



def phase_runtime_truth(args: Any) -> Optional[dict]:
    """
    Record and compare intended vs actual pipeline execution.

    Args:
        args: argparse.Namespace

    Returns:
        dict with truth_score, gaps, and evidence, or None if disabled
    """
    enabled = getattr(args, "runtime_truth", False)
    if not enabled:
        log("RUNTIME_TRUTH", "Runtime truth monitor disabled (use --runtime-truth)")
        return None

    log("RUNTIME_TRUTH", "Recording runtime truth...")

    scripts_dir = os.path.join(ROOT, "scripts")
    monitor = RuntimeTruthMonitor(scripts_dir=scripts_dir)
    result = monitor.record_runtime_truth(build_dir=BUILD_DIR)

    print()
    print("=" * 60)
    print("  RUNTIME TRUTH REPORT")
    print("=" * 60)
    print(f"  Intended phases:              {len(result['intended_execution'])}")
    print(f"  Actual evidence collected:    {len(result['actual_evidence'])}")
    print(f"  Gaps detected:                {len(result['gaps'])}")
    print(f"  Truth score:                  {result['truth_score']:.2f}/100")
    print()

    if result["gaps"]:
        print("  Gaps:")
        for gap in result["gaps"]:
            print(f"    - {gap['phase_name']}: {gap['gap_type']} — {gap['description']}")
        print()

    print("  Intended execution path:")
    for i, intent in enumerate(result["intended_execution"], 1):
        flag_info = f" [{intent['enabled_by_flag']}]" if intent["enabled_by_flag"] else ""
        print(f"    {i}. {intent['phase_name']} at line {intent['line_number']}{flag_info}")
    print()

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "runtime_truth_report.json")
    atomic_write(report_path, json.dumps(result, indent=2))
    log("RUNTIME_TRUTH", f"Report saved to {report_path}")

    return result
