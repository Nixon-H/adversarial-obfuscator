"""
phase_audit_drift.py

Purpose:
Detects audit drift — measures how far the current codebase has drifted
from the last security audit baseline.  Reports staleness scores and
identifies files changed since last audit.

Architectural Role:
Maintenance/oversight phase — prevents audit decay over time.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.audit_drift.*

Security Relevance:
Audit drift means the security posture has changed since the last audit;
undetected drift can introduce vulnerabilities without review.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.audit_drift.detector import detect_audit_drift



def phase_audit_drift(args: Any) -> dict | None:
    """
    Detect audit drift between current code and last audit baseline.

    Args:
        args: argparse.Namespace

    Returns:
        dict with staleness_score and drifted files, or None if disabled
    """
    enabled = getattr(args, "audit_drift", False)
    if not enabled:
        log("DRIFT", "Audit drift detector disabled (use --audit-drift)")
        return None
    log("DRIFT", "Detecting audit drift...")
    result = detect_audit_drift()
    os.makedirs(BUILD_DIR, exist_ok=True)
    atomic_write(os.path.join(BUILD_DIR, "audit_drift.json"), json.dumps(result, indent=2))
    print("\n" + "=" * 60 + "\n  AUDIT DRIFT DETECTION\n" + "=" * 60)
    print(f"  Staleness Score:    {result.get('staleness_score', 0):.1f}/100")
    print(f"  Source Files:       {result.get('total_source_files', 0)}")
    print(f"  Reports:            {result.get('total_reports', 0)}")
    print(f"  Drifted Files:      {result.get('total_drifted', 0)}")
    print("=" * 60)
    return result
