"""
phase_assumptions.py

Purpose:
Builds an assumption report — enumerates all assumptions made by the
pipeline (e.g., z3 is installed, angr is available, platform is x86_64)
and checks each one against the runtime environment.  Identifies critical
unsatisfied assumptions.

Architectural Role:
Pre-flight validation phase — ensures the environment meets pipeline
requirements.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, platform, sys, ..assumptions, ..common

Security Relevance:
Unsatisfied assumptions can silently disable protections; this phase
surfaces them before the pipeline proceeds.
"""

from __future__ import annotations

import json
import os
import platform
import sys

from ..assumptions import AssumptionTracker, AssumptionReport
from ..assumptions.registry import register_all
from ..common import BUILD_DIR, log


def _get_runtime_caps() -> dict:
    """
    Probe the runtime environment for available capabilities.

    Returns:
        dict mapping capability names (z3, numpy, angr, etc.) to booleans
    """
    caps = {
        "os": {
            "system": platform.system().lower(),
            "machine": platform.machine().lower(),
            "release": platform.release(),
        },
        "python3": True,
        "hashlib": True,
        "z3": False,
        "numpy": False,
        "angr": False,
    }

    try:
        import z3  # noqa: F401
        caps["z3"] = True
    except ImportError:
        pass

    try:
        import numpy  # noqa: F401
        caps["numpy"] = True
    except ImportError:
        pass

    try:
        import angr  # noqa: F401
        caps["angr"] = True
    except ImportError:
        pass

    caps["x86_64"] = platform.machine().lower() in ("x86_64", "amd64")
    caps["linux"] = platform.system().lower() == "linux"

    try:
        import hashlib  # noqa: F401
        caps["hashlib"] = True
    except ImportError:
        caps["hashlib"] = False

    return caps


def phase_assumptions(args) -> AssumptionReport:
    """
    Build and print the assumption report for the build environment.

    Args:
        args: argparse.Namespace

    Returns:
        AssumptionReport with satisfaction status per assumption
    """
    log("ASSUMPTIONS", "Building assumption report...")

    tracker = AssumptionTracker()
    register_all(tracker)

    runtime_caps = _get_runtime_caps()
    tracker.check_assumptions(runtime_caps)

    report = tracker.build_report()

    report_path = os.path.join(BUILD_DIR, "assumption_report.json")
    os.makedirs(BUILD_DIR, exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report.to_json())

    log("ASSUMPTIONS", f"Report written to {report_path}")
    log("ASSUMPTIONS", f"Total: {report.total_count}, Satisfied: {report.satisfied_count}, "
                       f"Unsatisfied: {report.unsatisfied_count}, Unknown: {report.unknown_count}")

    critical = report.critical_unsatisfied
    if critical:
        log("ASSUMPTIONS", f"CRITICAL unsatisfied assumptions: {len(critical)}")
        for a in critical:
            log("ASSUMPTIONS", f"  [{a.feature}] {a.assumption} ({a.assumption_type})")

    print()
    print(f"  {'='*60}")
    print(f"  ASSUMPTION REPORT")
    print(f"  {'='*60}")
    print(f"  Total assumptions:    {report.total_count}")
    print(f"  Satisfied:            {report.satisfied_count}")
    print(f"  Unsatisfied:          {report.unsatisfied_count}")
    print(f"  Unknown:              {report.unknown_count}")
    print(f"  Critical unsatisfied: {len(critical)}")
    if critical:
        print(f"  {'─'*40}")
        for a in critical:
            print(f"  !!! {a.feature}: {a.assumption} ({a.assumption_type})")
    print(f"  {'='*60}")
    print()

    return report
