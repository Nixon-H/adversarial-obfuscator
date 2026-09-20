"""
phase_protection_roi.py

Purpose:
Computes protection Return on Investment (ROI) — compares the security
gain of each protection feature against its implementation and runtime
costs.  Identifies net-negative features where cost exceeds benefit.

Architectural Role:
Economic analysis phase — optimizes protection portfolio.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.protection_roi.*

Security Relevance:
ROI analysis ensures protection resources are allocated where they
provide the most security benefit per unit cost.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, ROOT, atomic_write, log
from scripts.protection_roi.engine import ProtectionROIEngine



def phase_protection_roi(args: Any) -> Optional[dict]:
    """
    Compute protection Return on Investment for all features.

    Args:
        args: argparse.Namespace

    Returns:
        dict with overall_roi and per-feature analysis, or None if disabled
    """
    enabled = getattr(args, "protection_roi", False)
    if not enabled:
        log("PROTECTION_ROI", "Protection ROI engine disabled (use --protection-roi)")
        return None

    log("PROTECTION_ROI", "Computing protection ROI...")

    scripts_dir = os.path.join(ROOT, "scripts")
    tests_dir = os.path.join(ROOT, "tests")
    engine = ProtectionROIEngine(scripts_dir=scripts_dir, tests_dir=tests_dir)
    result = engine.compute_protection_roi()

    print()
    print("=" * 60)
    print("  PROTECTION ROI REPORT")
    print("=" * 60)
    print(f"  Total features:                {result['total_features']}")
    print(f"  Overall ROI:                   {result['overall_roi']:.2f}")
    print(f"  Net negative features:         {len(result['net_negative_features'])}")
    print()

    if result["net_negative_features"]:
        print("  Net Negative Features (ROI < 50):")
        for name in result["net_negative_features"][:20]:
            print(f"    - {name}")
        print()

    print("  Top ROI Features:")
    for t in result["top_roi_features"]:
        print(f"    {t['feature_name']:40s} ROI={t['roi']:.2f}  "
              f"gain={t['security_gain']:.2f}  cost={t['total_cost']:.2f}")
    print()

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "protection_roi_report.json")
    atomic_write(report_path, json.dumps(result, indent=2))
    log("PROTECTION_ROI", f"Report saved to {report_path}")

    return result
