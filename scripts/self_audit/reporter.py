"""
self_audit/reporter.py — Self-audit report formatting and output (F180)

Purpose:
    Formats a SelfAudit AuditReport as human-readable Markdown and as JSON,
    and writes both to an output directory.

Architectural Role:
    Presentation layer. Converts the structured AuditReport into deliverables
    suitable for CI/CD logs, dashboards, and archival.

Security Relevance:
    Ensures that audit results are accessible to both humans (Markdown) and
    machines (JSON), enabling automated gating and historical tracking.
"""

from __future__ import annotations

import json
import os

from scripts.common import atomic_write, log
from scripts.self_audit import AuditReport


def _format_timestamp(ts: str) -> str:
    """Normalize an ISO-8601 timestamp to a human-readable 'YYYY-MM-DD HH:MM:SS UTC' format."""
    if "T" not in ts:
        return ts
    ts = ts.replace("Z", "").replace("+00:00", "")
    parts = ts.split("T")
    return f"{parts[0]} {parts[1][:8]} UTC"


def generate_markdown_report(report: AuditReport) -> str:
    """Format the audit report as monospace Markdown suitable for CI/CD logs."""
    lines: list[str] = []
    ts = _format_timestamp(report.timestamp)

    lines.append("=" * 72)
    lines.append("  SECURITY SELF-AUDIT REPORT")
    lines.append("=" * 72)
    lines.append(f"  Timestamp:       {ts}")
    lines.append(f"  Overall Score:   {report.overall_score:.1f} / 100")
    lines.append(f"  Overall Grade:   {report.overall_grade}")
    lines.append(f"  Total Findings:  {report.total_findings}")
    lines.append(f"  Critical:        {report.critical_findings}")
    lines.append(f"  Major:           {report.major_findings}")
    lines.append(f"  Minor:           {report.minor_findings}")
    lines.append("=" * 72)
    lines.append("")

    cat_order = ["source", "tests", "reachability", "proofs", "benchmarks",
                  "claims", "metrics", "debt", "assumptions", "reality"]
    for name in cat_order:
        cat = report.categories.get(name)
        if cat is None:
            continue
        status = "PASS" if cat.passed else "FAIL"
        lines.append(f"  [{status}] {name.upper():20s}  {cat.score:.1f}/{cat.max_score}  ({cat.percentage:.1f}%)")
        lines.append(f"  {'─' * 72}")
        if cat.findings:
            for f in cat.findings:
                sev_tag = f"[{f.severity.upper():8s}]"
                lines.append(f"  {sev_tag} {f.title}")
                lines.append(f"  {' ' * 12} {f.description}")
                lines.append(f"  {' ' * 12} Recommendation: {f.recommendation}")
                if f.file:
                    lines.append(f"  {' ' * 12} File: {f.file}")
                if f.metric_name is not None:
                    lines.append(f"  {' ' * 12} Metric: {f.metric_name} = {f.metric_value}  (threshold: {f.threshold})")
                lines.append("")
        else:
            lines.append("  (no findings)")
            lines.append("")
        lines.append("")

    lines.append("=" * 72)
    lines.append("  END OF SELF-AUDIT REPORT")
    lines.append("=" * 72)

    return "\n".join(lines)


def generate_json_report(report: AuditReport) -> dict:
    """Serialize the audit report to a plain dict for JSON output."""
    return report.to_dict()


def write_reports(report: AuditReport, output_dir: str) -> None:
    """Write both Markdown and JSON versions of the audit report to output_dir."""
    os.makedirs(output_dir, exist_ok=True)

    md_path = os.path.join(output_dir, "security_audit.md")
    md_content = generate_markdown_report(report)
    atomic_write(md_path, md_content)
    log("SELF_AUDIT", f"Markdown report written to {md_path}")

    json_path = os.path.join(output_dir, "security_audit.json")
    json_content = generate_json_report(report)
    atomic_write(json_path, json.dumps(json_content, indent=2))
    log("SELF_AUDIT", f"JSON report written to {json_path}")
