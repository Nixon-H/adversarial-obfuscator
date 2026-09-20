"""
phase_longitudinal_tracking.py

Purpose:
Tracks security metrics over time — compares current build metrics
against a stored baseline, computes deltas and trends, and detects
drift.  Provides an early warning system for security regression.

Architectural Role:
Monitoring/trending phase — provides historical security context.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.longitudinal_tracking.*

Security Relevance:
Longitudinal tracking detects gradual security decay that individual
builds would miss — a key input for release confidence.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, ROOT, atomic_write, log
from scripts.longitudinal_tracking.tracker import LongitudinalTracker



def phase_longitudinal_tracking(args: Any) -> Optional[dict]:
    """
    Track longitudinal security metrics against baseline.

    Args:
        args: argparse.Namespace

    Returns:
        dict with baseline, current, deltas, and trends, or None if disabled
    """
    enabled = getattr(args, "longitudinal_tracking", False)
    if not enabled:
        log("LONGITUDINAL_TRACKING", "Longitudinal security tracking disabled (use --longitudinal-tracking)")
        return None

    log("LONGITUDINAL_TRACKING", "Tracking longitudinal security metrics...")

    config_dir = os.path.join(ROOT, "config")
    tracker = LongitudinalTracker(config_dir=config_dir)
    result = tracker.track_longitudinal_security()

    print()
    print("=" * 60)
    print("  LONGITUDINAL SECURITY TRACKING REPORT")
    print("=" * 60)
    print()
    print("  Baseline:")
    b = result["baseline"]
    print(f"    Tests:            {b['test_count']} (pass rate: {b['test_pass_rate']:.0%})")
    print(f"    CLI flags:        {b['cli_flags']}")
    print(f"    Build success:    {b['build_success']}")
    print()
    print("  Current:")
    c = result["current"]
    print(f"    Tests:            {c['test_count']}")
    print(f"    CLI flags:        {c['cli_flag_count']}")
    print(f"    Build success:    {c['build_success']}")
    print(f"    Phase count:      {c['phase_count']}")
    print()
    print("  Deltas:")
    d = result["deltas"]
    print(f"    Test count:       {d['test_count_delta']:+d} ({d['test_count_pct_change']:+.2f}%)")
    print(f"    Flag count:       {d['flag_count_delta']:+d} ({d['flag_count_pct_change']:+.2f}%)")
    print(f"    Build change:     {'Yes' if d['build_success_change'] else 'No'}")
    print()
    print("  Trends:")
    t = result["trend_analysis"]
    print(f"    Tests:            {t['test_trend']}")
    print(f"    Flags:            {t['flag_trend']}")
    print(f"    Build:            {t['build_trend']}")
    print(f"    Assessment:       {t['assessment']}")
    print()
    print(f"  Drift detected:     {'YES' if result['drift_detected'] else 'No'}")
    print(f"  Trend score:        {result['trend_score']:.2f}/200")
    print()

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "longitudinal_tracking_report.json")
    atomic_write(report_path, json.dumps(result, indent=2))
    log("LONGITUDINAL_TRACKING", f"Report saved to {report_path}")

    return result
