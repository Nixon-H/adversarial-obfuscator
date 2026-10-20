"""
phase_reality.py

Purpose:
Computes Reality Scores — measures the gap between claimed protections
and actual implemented/reachable/executed protections.  Each feature
receives scores for implementation, reachability, runtime execution,
and attack impact.  Critical gaps (score < 25) are highlighted.

Architectural Role:
Audit/truth phase — provides a reality check against protection claims.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.reality

Security Relevance:
Reality scoring prevents security theater by quantifying whether
claimed protections are actually effective in practice.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.reality import compute_reality_scores, RealityReport, score_to_grade


def _build_pipeline_state(args: Any) -> dict:
    build_py_path = os.path.join(_ROOT, "scripts", "build.py")
    build_py_source = ""
    if os.path.isfile(build_py_path):
        with open(build_py_path) as f:
            build_py_source = f.read()

    manifest = {}
    manifest_path = os.path.join(BUILD_DIR, "manifest.json")
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    metrics_report = {}
    metrics_path = os.path.join(BUILD_DIR, "metrics_report.json")
    if os.path.isfile(metrics_path):
        try:
            with open(metrics_path) as f:
                metrics_report = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    redteam_report = {}
    rt_path = os.path.join(BUILD_DIR, "redteam", "attack_report.json")
    if os.path.isfile(rt_path):
        try:
            with open(rt_path) as f:
                redteam_report = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    benchmark_report = {}
    bm_path = os.path.join(BUILD_DIR, "benchmark_report.json")
    if os.path.isfile(bm_path):
        try:
            with open(bm_path) as f:
                benchmark_report = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    security_gate_report = {}
    sg_path = os.path.join(BUILD_DIR, "security_gate_report.json")
    if os.path.isfile(sg_path):
        try:
            with open(sg_path) as f:
                security_gate_report = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "build_py_source": build_py_source,
        "manifest": manifest,
        "metrics_report": metrics_report,
        "redteam_report": redteam_report,
        "benchmark_report": benchmark_report,
        "security_gate_report": security_gate_report,
    }


def phase_reality(args: Any) -> Optional[RealityReport]:
    """
    Compute reality scores for all protection features.

    Args:
        args: argparse.Namespace

    Returns:
        RealityReport or None if disabled
    """
    enabled = getattr(args, "reality_score", False)
    if not enabled:
        log("REALITY", "Reality score disabled (use --reality-score to enable)")
        return None

    log("REALITY", "Computing reality scores for all protection features...")

    pipeline_state = _build_pipeline_state(args)
    report = compute_reality_scores(pipeline_state)

    report_path = os.path.join(BUILD_DIR, "reality_report.json")

    report_dict = {
        "overall_reality_score": report.overall_reality_score,
        "grade": report.grade,
        "timestamp": report.timestamp,
        "critical_gaps": report.critical_gaps,
        "feature_scores": {
            name: {
                "implemented_score": fr.implemented_score,
                "reachability_score": fr.reachability_score,
                "runtime_execution_score": fr.runtime_execution_score,
                "attack_impact_score": fr.attack_impact_score,
                "reality_score": fr.reality_score,
                "evidence_count": fr.evidence_count,
                "missing_evidence": fr.missing_evidence,
            }
            for name, fr in sorted(report.feature_scores.items())
        },
    }

    atomic_write(report_path, json.dumps(report_dict, indent=2))
    log("REALITY", f"Report saved to {report_path}")

    print()
    print("=" * 60)
    print("  REALITY SCORE REPORT")
    print("=" * 60)
    print(f"  Overall Reality Score: {report.overall_reality_score:.1f} / 100")
    print(f"  Grade:                 {report.grade}")
    print(f"  Features evaluated:    {len(report.feature_scores)}")
    print(f"  Critical gaps:         {len(report.critical_gaps)}")
    print(f"  Timestamp:             {report.timestamp}")
    print("=" * 60)
    print()

    if report.critical_gaps:
        print("  CRITICAL GAPS (score < 25):")
        for gap in report.critical_gaps:
            print(f"    - {gap}")
        print()

    print("  Feature Reality Scores:")
    print(f"  {'Feature':40s} {'Impl':6s} {'Reach':6s} {'Runtime':8s} {'Attack':7s} {'Total':6s} {'Grade':5s}")
    print(f"  {'─' * 78}")
    for name in sorted(report.feature_scores.keys()):
        fr = report.feature_scores[name]
        grade = score_to_grade(fr.reality_score)
        print(f"  {name:40s} {fr.implemented_score:5.1f} {fr.reachability_score:5.1f} "
              f"{fr.runtime_execution_score:6.1f} {fr.attack_impact_score:6.1f} "
              f"{fr.reality_score:5.1f} {grade:5s}")
    print(f"  {'─' * 78}")
    print()

    log("REALITY", f"Overall: {report.overall_reality_score:.1f}/100 ({report.grade})")

    return report
