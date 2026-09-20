"""
phase_security_gates.py

Purpose:
Runs security regression gates — collects metrics about the current
build and checks them against configured thresholds.  BLOCKER-level
failures cause the build to exit with error.

Architectural Role:
Quality-gate phase — enforces minimum security standards before
a build can proceed or be released.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.security_regression

Security Relevance:
Security gates prevent the pipeline from producing builds that fail
to meet minimum security metrics.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.security_regression import (
    RegressionChecker,
    MetricsCollector,
    GateSeverity,
    generate_gate_report,
    format_report_text,
    update_baseline,
)


def phase_security_gates(args: Any) -> bool:
    """
    Run security regression gates against current metrics.

    Args:
        args: argparse.Namespace

    Returns:
        True if all gates pass, False if blockers found
    """
    log("SECURITY_GATES", "Running security regression gates...")

    collector = MetricsCollector()
    if hasattr(args, "build_dir") and getattr(args, "build_dir"):
        collector.build_dir = args.build_dir

    current_metrics = collector.collect_with_fallback(args)

    checker = RegressionChecker()

    gate_threshold = getattr(args, "gate_threshold", None)
    if gate_threshold is not None:
        for gate in checker.gates:
            gate.threshold_percent = max(0.0, min(1.0, gate_threshold))

    results = checker.check_all_gates(current_metrics)
    report = generate_gate_report(results, BUILD_DIR)

    text = format_report_text(report)
    print()
    print(text)
    print()

    log("SECURITY_GATES", report.summary)

    report_json = json.dumps(report.to_dict(), indent=2)
    report_path = os.path.join(BUILD_DIR, "security_gate_report.json")
    atomic_write(report_path, report_json)
    log("SECURITY_GATES", f"Gate report saved to {report_path}")

    if getattr(args, "update_baseline", False):
        baseline_path = os.path.join(_ROOT, "config", "baseline_report.json")
        update_baseline(baseline_path, current_metrics)
        log("SECURITY_GATES", f"Baseline updated at {baseline_path}")

    if checker.has_blockers(results):
        failed_blockers = [r for r in results if r.severity == GateSeverity.BLOCKER and not r.passed]
        for fb in failed_blockers:
            log("SECURITY_GATES", f"BLOCKER FAILED: {fb.gate_name} — {fb.message}")
        log("SECURITY_GATES", "BLOCKER gates failed — build will exit with error")
        return False

    return True
