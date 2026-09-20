"""
phase_feature_effectiveness.py

Purpose:
Computes feature effectiveness scores — evaluates each protection feature
based on impact metrics, before/after comparisons, and resistance benchmark
results.  Identifies low-impact features that waste resources.

Architectural Role:
Optimization/ROI measurement phase.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.feature_effectiveness.*

Security Relevance:
Effectiveness measurement prevents continued investment in protections
that do not actually improve security posture.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, ROOT, atomic_write, log
from scripts.feature_effectiveness.scorer import FeatureEffectivenessScorer



def phase_feature_effectiveness(args: Any) -> Optional[dict]:
    """
    Compute feature effectiveness scores across all protections.

    Args:
        args: argparse.Namespace

    Returns:
        dict with overall_score and per_feature_scores, or None if disabled
    """
    enabled = getattr(args, "feature_effectiveness", False)
    if not enabled:
        log("FEATURE_EFFECTIVENESS", "Feature effectiveness scorer disabled (use --feature-effectiveness)")
        return None

    log("FEATURE_EFFECTIVENESS", "Computing feature effectiveness scores...")

    scripts_dir = os.path.join(ROOT, "scripts")
    tests_dir = os.path.join(ROOT, "tests")
    scorer = FeatureEffectivenessScorer(scripts_dir=scripts_dir, tests_dir=tests_dir)
    result = scorer.compute_feature_effectiveness()

    print()
    print("=" * 60)
    print("  FEATURE EFFECTIVENESS REPORT")
    print("=" * 60)
    print(f"  Total features:                {result['total_features']}")
    print(f"  Overall effectiveness score:   {result['overall_score']:.2f}/100")
    print(f"  Low-impact features (< 30):    {len(result['low_impact_features'])}")
    print()

    if result["low_impact_features"]:
        print("  Low-impact features:")
        for name in result["low_impact_features"][:20]:
            print(f"    - {name}")
        print()

    print("  Top features by score:")
    sorted_scores = sorted(
        result["per_feature_scores"],
        key=lambda x: x["overall_score"],
        reverse=True,
    )
    for s in sorted_scores[:10]:
        print(f"    {s['feature_name']:40s} score: {s['overall_score']:5.2f}  "
              f"[impact={s['has_impact_metric']}, "
              f"before_after={s['has_before_after_comparison']}, "
              f"resistance={s['has_resistance_benchmark']}]")
    print()

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "feature_effectiveness_report.json")
    atomic_write(report_path, json.dumps(result, indent=2))
    log("FEATURE_EFFECTIVENESS", f"Report saved to {report_path}")

    return result
