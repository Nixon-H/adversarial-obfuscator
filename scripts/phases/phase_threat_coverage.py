"""
phase_threat_coverage.py

Purpose:
Maps formal threat coverage — evaluates each known threat against the
pipeline's features, metrics, and verifications to determine coverage
status.  Identifies uncovered threats requiring new protections.

Architectural Role:
Threat modeling/coverage analysis phase.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.threat_coverage.*

Security Relevance:
Threat coverage maps close the gap between known threats and actual
protections, ensuring no threat category is left unaddressed.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.threat_coverage.mapper import map_threat_coverage



def phase_threat_coverage(args: Any) -> dict:
    """
    Map formal threat coverage across the security posture.

    Args:
        args: argparse.Namespace

    Returns:
        dict with coverage_score, uncovered_threats, and threat_map
    """
    log("THREAT_COVERAGE", "Mapping formal threat coverage...")
    root = getattr(args, "root", _ROOT)
    result = map_threat_coverage(root)

    print()
    print("=" * 60)
    print("  FORMAL THREAT COVERAGE REPORT")
    print("=" * 60)
    print(f"  Coverage score: {result['coverage_score']:.1f}%")
    print(f"  Uncovered threats: {len(result['uncovered_threats'])}")
    print(f"  {'─' * 40}")

    for ut in result["uncovered_threats"]:
        print(f"    ⚠ {ut['threat']}: missing {', '.join(ut['missing'])}")

    print(f"  {'─' * 40}")
    print(f"  Per-threat breakdown:")
    for entry in result["threat_map"]:
        status = "COVERED" if (
            entry["features"] and entry["metrics"] and entry["verifications"]
        ) else "UNCOVERED"
        print(
            f"    {entry['threat']:30s} [{status:10s}]  "
            f"F:{len(entry['features'])} M:{len(entry['metrics'])} V:{len(entry['verifications'])}"
        )
    print("=" * 60)
    print()

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "threat_coverage_report.json")
    atomic_write(report_path, json.dumps(result, indent=2, default=str))
    log("THREAT_COVERAGE", f"Report saved to {report_path}")

    return result
