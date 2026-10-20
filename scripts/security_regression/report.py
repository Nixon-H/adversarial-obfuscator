"""
report.py

Purpose:
Defines the GateReport dataclass and provides formatting functions
(text and JSON) for presenting security gate results. The report
includes per-gate pass/fail status, BLOCKER/WARNING counts, and a
human-readable summary.

Architectural Role:
Output formatting for the security regression module. GateReport is
produced by RegressionChecker and written to the build directory as
security_gate_report.json. Text formatting is used for CLI output.

Execution Context:
GateReport is created by RegressionChecker.generate_report() and
RegressionReport.generate_gate_report(). It is serialized to JSON
for persistence and rendered as text for terminal display.

Dependencies:
- gate (GateResult, GateSeverity)
- Standard library (json, os, time, dataclasses, typing)

Security Relevance:
The gate report is the final verdict on build security quality. The
all_passed field determines whether the build pipeline continues or
stops. BLOCKER failures must be investigated before the next build.

Maintenance Notes:
- generate_gate_report() writes the report to the build directory
  and returns the GateReport object.
- format_report_text() produces a table-style output with per-gate
  status suitable for CI/CD pipeline logs.
- GateResult.__post_init__ computes delta_percent and passed status
  automatically; these are not passed as constructor arguments.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List

from .gate import GateResult, GateSeverity


@dataclass
class GateReport:
    timestamp: str = ""
    all_passed: bool = True
    gates: List[GateResult] = field(default_factory=list)
    blockers: List[GateResult] = field(default_factory=list)
    warnings: List[GateResult] = field(default_factory=list)
    summary: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "all_passed": self.all_passed,
            "summary": self.summary,
            "gate_count": len(self.gates),
            "blocker_count": len(self.blockers),
            "warning_count": len(self.warnings),
            "gates": [
                {
                    "gate_name": g.gate_name,
                    "metric_name": g.metric_name,
                    "baseline_value": g.baseline_value,
                    "current_value": g.current_value,
                    "delta_percent": round(g.delta_percent, 4),
                    "threshold_percent": g.threshold_percent,
                    "passed": g.passed,
                    "severity": g.severity.value,
                    "message": g.message,
                }
                for g in self.gates
            ],
        }


def generate_gate_report(results: List[GateResult], build_dir: str) -> GateReport:
    blockers = [r for r in results if r.severity == GateSeverity.BLOCKER]
    warnings = [r for r in results if r.severity == GateSeverity.WARNING]
    all_passed = all(r.passed for r in results if r.severity == GateSeverity.BLOCKER)
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    summary = f"Security Gates: {passed}/{total} passed"
    if not all_passed:
        failed_blockers = [r for r in blockers if not r.passed]
        summary += f", {len(failed_blockers)} BLOCKER(s) failed"

    report = GateReport(
        all_passed=all_passed,
        gates=results,
        blockers=blockers,
        warnings=warnings,
        summary=summary,
    )

    report_path = os.path.join(build_dir, "security_gate_report.json")
    os.makedirs(build_dir, exist_ok=True)
    json_str = format_report_json(report)
    with open(report_path, "w") as f:
        f.write(json_str)
    return report


def format_report_text(report: GateReport) -> str:
    lines: list = []
    lines.append("=" * 60)
    lines.append("  SECURITY GATE REPORT")
    lines.append("=" * 60)
    lines.append(f"  Timestamp: {report.timestamp}")
    lines.append(f"  Result:    {'PASSED' if report.all_passed else 'FAILED'}")
    lines.append(f"  Summary:   {report.summary}")
    lines.append("")
    for g in report.gates:
        status = "PASS" if g.passed else "FAIL"
        sev = g.severity.value.upper()
        lines.append(f"  [{sev:7s}] [{status:4s}] {g.gate_name:25s} "
                     f"baseline={g.baseline_value:.4f} current={g.current_value:.4f} "
                     f"delta={g.delta_percent * 100:+.2f}% threshold={g.threshold_percent * 100:.0f}%")
    lines.append("")
    if report.blockers:
        failed = [r for r in report.blockers if not r.passed]
        if failed:
            lines.append(f"  BLOCKERS FAILED: {len(failed)}")
            for r in failed:
                lines.append(f"    - {r.gate_name} ({r.message})")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_report_json(report: GateReport) -> str:
    return json.dumps(report.to_dict(), indent=2)
