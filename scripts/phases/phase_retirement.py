"""
phase_retirement.py

Purpose:
Analyzes features for retirement — evaluates each protection feature
on effectiveness, overhead, and survivability scores to recommend
whether to DEPRECATE, MONITOR, KEEP, or OPTIMIZE.

Architectural Role:
Lifecycle management phase — prevents protection bloat.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.feature_retirement.*

Security Relevance:
Retirement analysis removes protections that are no longer effective
or are outweighed by their costs, reducing attack surface.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.feature_retirement.analyzer import (
    RetirementAnalyzer,
    RetirementReport,
    RetirementStatus,
)


def phase_retirement(args: Any) -> Optional[RetirementReport]:
    """
    Analyze features for potential retirement based on effectiveness and cost.

    Args:
        args: argparse.Namespace

    Returns:
        RetirementReport with recommendations, or None
    """
    log("RETIREMENT", "Running feature retirement analysis...")

    analyzer = RetirementAnalyzer()
    report = analyzer.generate_report()

    report_path = os.path.join(BUILD_DIR, "retirement_report.json")
    os.makedirs(BUILD_DIR, exist_ok=True)
    atomic_write(report_path, json.dumps(report.to_dict(), indent=2))
    log("RETIREMENT", f"Report saved to {report_path}")

    summary_path = os.path.join(BUILD_DIR, "retirement_summary.txt")
    lines = [
        "=" * 60,
        "  FEATURE RETIREMENT REPORT",
        "=" * 60,
        f"  Total features:           {report.total_features}",
        f"  DEPRECATE (retire):       {report.deprecate_count}",
        f"  MONITOR:                  {report.monitor_count}",
        f"  KEEP:                     {report.keep_count}",
        f"  OPTIMIZE:                 {report.optimize_count}",
        "=" * 60,
        "",
        "  DETAIL:",
    ]
    for name, a in sorted(report.assessments.items()):
        status_str = a.recommendation.value
        lines.append(
            f"  [{status_str:>12s}] {name:45s} "
            f"eff={a.effectiveness_score:.2f} ovr={a.overhead_score:.2f} "
            f"sur={a.survivability_score:.2f}  {a.reason}"
        )

    lines.append("=" * 60)
    summary_text = "\n".join(lines)
    atomic_write(summary_path, summary_text)
    log("RETIREMENT", f"Summary saved to {summary_path}")

    print()
    for line in lines:
        print(line)
    print()

    return report
