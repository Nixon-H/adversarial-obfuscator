"""
phase_conflicts.py

Purpose:
Checks the requested CLI flags against known protection feature conflicts
before the pipeline begins.  Prevents incompatible protection combinations
from silently producing broken output.

Architectural Role:
Pre-flight validation phase — runs first in the pipeline.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
argparse, json, os, scripts.common, scripts.conflicts

Security Relevance:
Conflict detection prevents silently broken or weakened protection
from incompatible feature combinations.
"""

from __future__ import annotations

import argparse
import json
import os

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.conflicts import (
    KNOWN_CONFLICTS,
    ConflictDetector,
)


def phase_check_conflicts(args: argparse.Namespace) -> bool:
    """Check CLI args against known protection conflicts.

    Returns True if no blocking conflicts found, False otherwise.
    """
    if getattr(args, "skip_conflict_check", False):
        log("CONFLICT", "Conflict check bypassed (--skip-conflict-check)")
        return True

    detector = ConflictDetector(KNOWN_CONFLICTS)
    conflicts = detector.check_cli_args(args)

    if not conflicts:
        log("CONFLICT", "No protection conflicts detected")
        return True

    report = detector.generate_report(conflicts)
    print(report)

    report_path = os.path.join(BUILD_DIR, "conflict_report.json")
    os.makedirs(BUILD_DIR, exist_ok=True)
    atomic_write(
        report_path,
        json.dumps(
            [
                {
                    "flag_a": c.flag_a,
                    "flag_b": c.flag_b,
                    "type": c.conflict_type.value,
                    "severity": c.severity.value,
                    "description": c.description,
                    "resolution": c.resolution,
                }
                for c in conflicts
            ],
            indent=2,
        ),
    )
    log("CONFLICT", f"Report written to {report_path}")

    if detector.has_errors(conflicts):
        log("CONFLICT", "Blocking conflicts found — aborting pipeline")
        return False

    return True
