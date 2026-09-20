"""
phase_reproducibility.py

Purpose:
Performs reproducibility analysis — scores each build artifact on how
reproducibly it can be rebuilt.  Detects non-reproducible artifacts
and provides recommendations for improvement.

Architectural Role:
Quality assurance phase — ensures build outputs are deterministic.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, time, typing, scripts.common, scripts.reproducibility.*

Security Relevance:
Reproducibility is essential for verifiable builds — non-reproducible
artifacts cannot be independently confirmed.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sys
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.reproducibility.scorer import compute_reproducibility
from scripts.reproducibility.checker import check_result_reproducibility
from scripts.reproducibility.environment import snapshot_environment


def phase_reproducibility(args: Any) -> dict:
    """
    Analyze reproducibility of all build artifacts.

    Args:
        args: argparse.Namespace

    Returns:
        dict with overall_score and report
    """
    log("REPRODUCIBILITY", "Starting reproducibility analysis...")

    build_dir = getattr(args, "build_dir", BUILD_DIR)
    os.makedirs(build_dir, exist_ok=True)

    report = compute_reproducibility(build_dir)

    overall_score = report.overall_score
    total_artifacts = len(report.results)
    non_repro_count = len(report.non_reproducible_artifacts)

    print()
    print("=" * 60)
    print("  REPRODUCIBILITY SCORE REPORT")
    print("=" * 60)
    print(f"  Overall reproducibility score:  {overall_score:.1f}/100")
    print(f"  Total artifacts scanned:       {total_artifacts}")
    print(f"  Non-reproducible artifacts:    {non_repro_count}")
    if report.non_reproducible_artifacts:
        print(f"  {'─' * 40}")
        for art in report.non_reproducible_artifacts:
            print(f"    ✗ {art}")
    print(f"  {'─' * 40}")
    for rec in report.recommendations:
        print(f"  → {rec}")
    print("=" * 60)
    print()

    if total_artifacts > 0:
        print("  Per-artifact breakdown:")
        print(f"  {'Type':<15s} {'Score':>7s}  {'Artifact'}")
        print(f"  {'─' * 50}")
        for r in sorted(report.results, key=lambda x: x.reproducibility_score):
            rel_path = r.artifact_path
            if len(rel_path) > 40:
                rel_path = "..." + rel_path[-37:]
            bar = "█" * max(1, int(r.reproducibility_score / 10))
            print(f"  {r.artifact_type:<15s} {r.reproducibility_score:>5.1f}/100 {bar}  {rel_path}")
        print()

    report_path = os.path.join(build_dir, "reproducibility_report.json")
    atomic_write(report_path, report.to_json(indent=2))
    log("REPRODUCIBILITY", f"Report saved to {report_path}")

    return {
        "overall_score": overall_score,
        "total_artifacts": total_artifacts,
        "non_reproducible": non_repro_count,
        "report_path": report_path,
        "report": report.to_dict(),
    }
