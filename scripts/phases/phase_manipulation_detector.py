"""
phase_manipulation_detector.py

Purpose:
Detects metric manipulation — scans for evidence that security metrics
have been tampered with or gamed (e.g., cherry-picked benchmarks,
selective reporting, adversarial mutations).

Architectural Role:
Integrity verification phase — prevents metrics fraud.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.manipulation_detector.*

Security Relevance:
Metrics are only useful if they can be trusted; manipulation detection
preserves the integrity of all downstream decision-making.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.manipulation_detector.detector import detect_metric_manipulation



def phase_manipulation_detector(args: Any) -> dict | None:
    """
    Scan for metric manipulation in the codebase.

    Args:
        args: argparse.Namespace

    Returns:
        dict with manipulation_score and findings, or None if disabled
    """
    enabled = getattr(args, "manipulation_detector", False)
    if not enabled:
        log("MANIPULATION", "Manipulation detector disabled (use --manipulation-detector)")
        return None
    log("MANIPULATION", "Scanning for metric manipulation...")
    result = detect_metric_manipulation()
    os.makedirs(BUILD_DIR, exist_ok=True)
    atomic_write(os.path.join(BUILD_DIR, "manipulation_detection.json"), json.dumps(result, indent=2))
    print("\n" + "=" * 60 + "\n  METRIC MANIPULATION DETECTOR\n" + "=" * 60)
    print(f"  Manipulation Score: {result.get('manipulation_score', 0):.1f}/100")
    print(f"  Total Findings:     {result.get('total_findings', 0)}")
    print(f"  Adversarial Mutations: {result.get('total_mutations', 0)}")
    print(f"  Files w/ findings:  {len(result.get('findings_per_file', {}))}")
    print("=" * 60)
    return result
