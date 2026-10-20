"""
phase_reachability.py

Purpose:
Analyzes reachability of all pipeline features — determines which
features are REACHABLE, PARTIALLY reachable, or UNREACHABLE from the
current build configuration.

Architectural Role:
Audit phase — identifies protection features that are configured but
never actually executed.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.reachability.*

Security Relevance:
Unreachable protections are useless — reachability analysis ensures
that configured protections can actually be triggered.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.reachability.analyzer import ReachabilityAnalyzer, ReachabilityReport


def phase_reachability(args: Any) -> Optional[ReachabilityReport]:
    """
    Analyze reachability of all pipeline features.

    Args:
        args: argparse.Namespace

    Returns:
        ReachabilityReport or None
    """
    log("REACHABILITY", "Running reachability analysis on all features...")

    analyzer = ReachabilityAnalyzer()
    report = analyzer.generate_report()

    report_path = os.path.join(BUILD_DIR, "reachability_report.json")
    os.makedirs(BUILD_DIR, exist_ok=True)
    atomic_write(report_path, json.dumps(report.to_dict(), indent=2))
    log("REACHABILITY", f"Report saved to {report_path}")

    summary_path = os.path.join(BUILD_DIR, "reachability_summary.txt")
    lines = [
        "=" * 60,
        "  REACHABILITY COVERAGE REPORT",
        "=" * 60,
        f"  Total features:   {report.total_features}",
        f"  REACHABLE:        {report.reachable_count}",
        f"  PARTIALLY:        {report.partially_reachable_count}",
        f"  UNREACHABLE:      {report.unreachable_count}",
        "=" * 60,
        "",
        "  DETAIL:",
    ]
    for name, fr in sorted(report.features.items()):
        status_str = fr.status.value
        missing = ", ".join(fr.missing_links) if fr.missing_links else "none"
        lines.append(f"  [{status_str:>22s}] {name:40s} missing: {missing}")

    lines.append("=" * 60)
    summary_text = "\n".join(lines)
    atomic_write(summary_path, summary_text)
    log("REACHABILITY", f"Summary saved to {summary_path}")

    print()
    for line in lines:
        print(line)
    print()

    return report
