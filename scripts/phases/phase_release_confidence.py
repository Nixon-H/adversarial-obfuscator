"""
phase_release_confidence.py

Purpose:
Computes the release confidence score — a weighted composite of multiple
security factors (test results, gate status, evidence coverage, trend
analysis) that determines whether a build is ready for release.

Architectural Role:
Release gating phase — final go/no-go decision support.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.release_confidence.*

Security Relevance:
Release confidence is the ultimate synthesis metric — it determines
whether all other phases collectively indicate a secure release.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.release_confidence.scorer import compute_release_confidence



def phase_release_confidence(args: Any) -> dict:
    """
    Compute the release confidence score from all available metrics.

    Args:
        args: argparse.Namespace

    Returns:
        dict with confidence_score, interval, grade, and factor breakdown
    """
    log("RELEASE_CONFIDENCE", "Computing release confidence score...")
    build_dir = getattr(args, "build_dir", BUILD_DIR)
    result = compute_release_confidence(build_dir)

    print()
    print("=" * 60)
    print("  RELEASE CONFIDENCE SCORE")
    print("=" * 60)
    print(f"  Confidence:        {result['confidence_score']:.1f}")
    print(f"  Interval:          {result['confidence_interval']}")
    print(f"  Grade:             {result['confidence_grade']}")
    print(f"  {'─' * 40}")
    print(f"  Factor breakdown:")
    for factor in result["per_factor_scores"]:
        print(
            f"    {factor['factor_name']:25s} {factor['raw_score']:.4f} × {factor['weight']:.2f} = {factor['weighted_score']:.4f}"
        )
    print("=" * 60)
    print()

    os.makedirs(build_dir, exist_ok=True)
    report_path = os.path.join(build_dir, "release_confidence_report.json")
    atomic_write(report_path, json.dumps(result, indent=2, default=str))
    log("RELEASE_CONFIDENCE", f"Report saved to {report_path}")

    return result
