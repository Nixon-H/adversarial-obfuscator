"""
phase_self_audit.py

Purpose:
Runs a comprehensive self-audit — the pipeline audits its own integrity
by checking protection coverage, evidence quality, and security metrics.
Produces an overall score and grade.

Architectural Role:
Final pipeline integrity check — runs last to validate the entire build.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
os, sys, typing, scripts.common, scripts.self_audit.*

Security Relevance:
Self-audit provides a holistic integrity score that reflects the
trustworthiness of the entire pipeline output.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, log
from scripts.self_audit.auditor import SelfAuditor
from scripts.self_audit.reporter import write_reports


def phase_self_audit(args: Any) -> dict:
    """
    Run the self-audit — final pipeline integrity check.

    Args:
        args: argparse.Namespace

    Returns:
        dict with audit report data
    """
    log("SELF_AUDIT", "Running self-audit — final pipeline integrity check")

    auditor = SelfAuditor(build_dir=BUILD_DIR)

    payload = getattr(args, "payload", None)
    report = auditor.run(payload_path=payload)

    output_dir = BUILD_DIR
    write_reports(report, output_dir)

    print()
    print("=" * 72)
    print("  SELF-AUDIT SUMMARY")
    print("=" * 72)
    print(f"  Overall Score:   {report.overall_score:.1f} / 100")
    print(f"  Overall Grade:   {report.overall_grade}")
    print(f"  Total Findings:  {report.total_findings}")
    print(f"  Critical:        {report.critical_findings}")
    print(f"  Major:           {report.major_findings}")
    print(f"  Minor:           {report.minor_findings}")
    print("=" * 72)

    for name, cat in sorted(report.categories.items()):
        status = "PASS" if cat.passed else "FAIL"
        print(f"  [{status}] {name:20s}  {cat.score:.1f}/{cat.max_score} "
              f"({cat.percentage:.1f}%)  ({len(cat.findings)} findings)")

    print("=" * 72)
    print(f"  Reports: {output_dir}/security_audit.md, {output_dir}/security_audit.json")
    print()

    log("SELF_AUDIT", f"Score: {report.overall_score}/100 ({report.overall_grade}) — "
                      f"{report.total_findings} findings ({report.critical_findings} critical)")

    return report.to_dict()
