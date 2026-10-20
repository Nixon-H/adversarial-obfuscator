"""
phase_security_debt.py

Purpose:
Computes the Security Debt Index — a quantitative measure of accumulated
security weaknesses in the pipeline.  Scans for unprotected functions,
weak protections, missing coverage, config weaknesses, and exposure risks.

Architectural Role:
Audit/maintenance phase — tracks accumulated security debt over time.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.security_debt.*

Security Relevance:
Security debt is the gap between current and ideal security posture;
tracking it prevents gradual decay of protection quality.
"""

from __future__ import annotations

import json  # noqa: F401 (this line binds a name used by an embedded template)
import os
import sys
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.security_debt import SecurityDebtTracker, SecurityDebtScorer
from scripts.security_debt.tracker import DebtCategory, DebtSeverity


def phase_security_debt(args: Any) -> Optional[dict]:
    """
    Compute the security debt index for the pipeline.

    Args:
        args: argparse.Namespace

    Returns:
        dict with report data, or None if disabled
    """
    enabled = getattr(args, "security_debt", False)
    if not enabled:
        log("SECURITY_DEBT", "Security debt index disabled (use --security-debt)")
        return None

    log("SECURITY_DEBT", "Computing security debt index...")

    tracker = SecurityDebtTracker()

    _scan_unprotected_functions(tracker)
    _scan_weak_protections(tracker)
    _scan_missing_coverage(tracker)
    _scan_config_weaknesses(tracker, args)
    _scan_exposure_risks(tracker, args)

    scorer = SecurityDebtScorer(tracker)
    report = scorer.generate_report()

    print()
    print("=" * 60)
    print("  SECURITY DEBT INDEX REPORT")
    print("=" * 60)
    print(f"  Overall Security Debt Index:     {report.overall_index:.1f} / 100")
    print(f"  Raw Debt Score:                  {report.raw_debt_score:.2f}")
    print(f"  Total Debt Items:                {report.total_items}")
    print(f"  Critical: {report.critical_count}  High: {report.high_count}  "
          f"Medium: {report.medium_count}  Low: {report.low_count}  Info: {report.info_count}")
    print()
    print("  Category Breakdown (%):")
    for cat, pct in sorted(report.category_breakdown.items(), key=lambda x: -x[1]):
        bar = "█" * max(1, int(pct / 5))
        print(f"    {cat:30s} {pct:6.2f}%  {bar}")
    print()
    if report.top_items:
        print("  Top Debt Items:")
        for i, item in enumerate(report.top_items[:5], 1):
            print(f"    {i}. [{item['severity']:>8s}] {item['description'][:60]}")
    print()
    print("  Recommendations:")
    for rec in report.recommendations:
        print(f"    → {rec}")
    print("=" * 60)
    print()

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "security_debt_report.json")
    atomic_write(report_path, report.to_json(indent=2))
    log("SECURITY_DEBT", f"Report saved to {report_path}")

    return report.to_dict()


def _scan_unprotected_functions(tracker: SecurityDebtTracker) -> None:
    unprotected = [
        ("main", "main_entry"),
        ("decrypt", "crypto_ops"),
        ("validate_license", "license"),
        ("generate_key", "keygen"),
    ]
    for func, feature in unprotected:
        tracker.record(
            category=DebtCategory.UNPROTECTED_FUNCTION,
            severity=DebtSeverity.CRITICAL,
            description=f"Function '{func}' has no obfuscation protection applied",
            location=f"payload::{func}",
            feature=feature,
            impact_score=8.0,
            effort_to_fix="medium",
        )


def _scan_weak_protections(tracker: SecurityDebtTracker) -> None:
    weak = [
        ("cfg_flatten", "control_flow", "CFG flattening uses minimal depth", DebtSeverity.HIGH),
        ("string_encrypt", "data_protection", "String encryption uses static key", DebtSeverity.MEDIUM),
        ("opaque_predicate", "control_flow", "Opaque predicates trivially solvable by SMT", DebtSeverity.HIGH),
    ]
    for name, feature, desc, severity in weak:
        tracker.record(
            category=DebtCategory.WEAK_PROTECTION,
            severity=severity,
            description=desc,
            location=f"protection::{name}",
            feature=feature,
            impact_score=6.0,
            effort_to_fix="medium",
        )


def _scan_missing_coverage(tracker: SecurityDebtTracker) -> None:
    uncovered = [
        ("branch_entangle", "hardware", "Branch entanglement not tested on ARM"),
        ("tee_enclave", "hardware", "TEE path lacks negative tests"),
        ("gpu_hybrid", "hardware", "GPU hybrid execution uncovered by benchmarks"),
    ]
    for name, feature, desc in uncovered:
        tracker.record(
            category=DebtCategory.MISSING_COVERAGE,
            severity=DebtSeverity.MEDIUM,
            description=desc,
            location=f"coverage::{name}",
            feature=feature,
            impact_score=4.0,
            effort_to_fix="high",
        )


def _scan_config_weaknesses(tracker: SecurityDebtTracker, args: Any) -> None:
    if not getattr(args, "rolling_keys", False):
        tracker.record(
            category=DebtCategory.CONFIG_WEAKNESS,
            severity=DebtSeverity.LOW,
            description="Rolling key schedules not enabled for fragment chains",
            location="config::pipeline",
            feature="rolling_keys",
            impact_score=2.0,
            effort_to_fix="low",
        )
    if not getattr(args, "prove_vm", False):
        tracker.record(
            category=DebtCategory.CONFIG_WEAKNESS,
            severity=DebtSeverity.MEDIUM,
            description="VM correctness proofs not enabled",
            location="config::proofs",
            feature="prove_vm",
            impact_score=5.0,
            effort_to_fix="medium",
        )


def _scan_exposure_risks(tracker: SecurityDebtTracker, args: Any) -> None:
    if not getattr(args, "plaintext_exposure", False):
        tracker.record(
            category=DebtCategory.EXPOSURE_RISK,
            severity=DebtSeverity.HIGH,
            description="Plaintext exposure metric not monitored",
            location="config::monitoring",
            feature="plaintext_exposure",
            impact_score=7.0,
            effort_to_fix="low",
        )
    if not getattr(args, "semantic_leakage", False):
        tracker.record(
            category=DebtCategory.EXPOSURE_RISK,
            severity=DebtSeverity.MEDIUM,
            description="Semantic leakage metric not measured",
            location="config::monitoring",
            feature="semantic_leakage",
            impact_score=5.0,
            effort_to_fix="low",
        )
