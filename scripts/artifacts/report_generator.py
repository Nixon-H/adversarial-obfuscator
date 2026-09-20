"""
report_generator.py

Purpose:
Generates human-readable reports (verification, regression, security
summary, executive summary) in Markdown and HTML formats. Each
report function accepts data dicts and optional output paths.

Architectural Role:
Reporting layer of the artifacts module. Consumes verification data,
baseline/current metric comparisons, and all-metrics dictionaries
to produce formatted reports with both Markdown and HTML versions.

Execution Context:
Called by ArtifactBuilder._generate_reports() during artifact
generation. Reports are written to build/artifacts/reports/.

Dependencies:
- Standard library (json, os, time)

Security Relevance:
Reports document the security posture for each build. The verification
report shows test pass/fail status. The regression report shows
metric changes. The security summary provides a dashboard view.

Maintenance Notes:
- Each report function returns a string containing both Markdown and
  HTML sections separated by a horizontal rule.
- HTML styling is inline (no external CSS dependencies) for
  self-contained viewing.
- The _style_html helper wraps body HTML in a complete HTML document
  with a responsive design template.
"""

from __future__ import annotations

import json
import os
import time


def _style_html(body: str, title: str = "Report") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 960px; margin: 2em auto; padding: 0 1em; color: #333; }}
  h1, h2, h3 {{ color: #1a1a2e; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
  th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
  th {{ background: #1a1a2e; color: #fff; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  .pass {{ color: #2ecc71; font-weight: bold; }}
  .fail {{ color: #e74c3c; font-weight: bold; }}
  .warning {{ color: #f39c12; font-weight: bold; }}
  .summary {{ background: #f0f0f0; padding: 1em; border-radius: 6px; margin: 1em 0; }}
  .metric-good {{ background: #d4edda; }}
  .metric-warning {{ background: #fff3cd; }}
  .metric-bad {{ background: #f8d7da; }}
  code {{ background: #eee; padding: 2px 4px; border-radius: 3px; }}
  pre {{ background: #f5f5f5; padding: 1em; border-radius: 6px; overflow-x: auto; }}
</style>
</head>
<body>
{body}
</body>
</html>"""


def _section(title: str, content: str, level: int = 2) -> str:
    prefix = "#" * level
    return f"\n{prefix} {title}\n\n{content}\n"


def generate_verification_report(
    verification_data: dict, output_path: str | None = None
) -> str:
    test_results = verification_data.get("test_results", {})
    benchmark_results = verification_data.get("benchmark_results", {})
    metrics = verification_data.get("metrics", {})

    md_parts = ["# Verification Report", ""]
    md_parts.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    md_parts.append(f"**Status:** {'ALL PASSED' if verification_data.get('passed', True) else 'SOME FAILED'}")
    md_parts.append("")

    ts = test_results
    total = ts.get("total", 0)
    passed = ts.get("passed", 0)
    failed = ts.get("failed", 0)
    skipped = ts.get("skipped", 0)
    md_parts.append("## Test Results")
    md_parts.append("")
    md_parts.append(f"- **Total:** {total}")
    md_parts.append(f"- **Passed:** {passed}")
    md_parts.append(f"- **Failed:** {failed}")
    md_parts.append(f"- **Skipped:** {skipped}")
    md_parts.append("")

    if failed > 0:
        md_parts.append("### Failed Tests")
        for t in ts.get("failed_tests", []):
            name = t.get("name", "unknown")
            error = t.get("error", "unknown error")
            md_parts.append(f"- `{name}`: {error}")
        md_parts.append("")

    bs = benchmark_results
    if bs:
        md_parts.append("## Benchmark Results")
        md_parts.append("")
        md_parts.append("| Benchmark | Mean | Min | Max |")
        md_parts.append("| --- | --- | --- | --- |")
        for bname, bdata in sorted(bs.items()):
            if not isinstance(bdata, dict):
                continue
            mean = bdata.get("mean", "N/A")
            minv = bdata.get("min", "N/A")
            maxv = bdata.get("max", "N/A")
            md_parts.append(f"| {bname} | {mean} | {minv} | {maxv} |")
        md_parts.append("")

    if metrics:
        md_parts.append("## Metrics Summary")
        md_parts.append("")
        md_parts.append("| Metric | Value |")
        md_parts.append("| --- | --- |")
        for k, v in sorted(metrics.items()):
            md_parts.append(f"| {k} | {v} |")
        md_parts.append("")

    md_content = "\n".join(md_parts)

    html_rows = []
    if metrics:
        for k, v in sorted(metrics.items()):
            html_rows.append(f"<tr><td>{k}</td><td>{v}</td></tr>")

    html_body_parts = [
        "<h1>Verification Report</h1>",
        f"<p><strong>Generated:</strong> {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</p>",
        f"<p class=\"{'pass' if verification_data.get('passed', True) else 'fail'}\"><strong>Status:</strong> {'ALL PASSED' if verification_data.get('passed', True) else 'SOME FAILED'}</p>",
        "<h2>Test Results</h2>",
        f"<p>Total: {total} | Passed: <span class='pass'>{passed}</span> | Failed: <span class='fail'>{failed}</span> | Skipped: {skipped}</p>",
    ]
    if failed > 0:
        html_body_parts.append("<h3>Failed Tests</h3><ul>")
        for t in ts.get("failed_tests", []):
            html_body_parts.append(f"<li><code>{t.get('name', 'unknown')}</code>: {t.get('error', 'unknown error')}</li>")
        html_body_parts.append("</ul>")
    if html_rows:
        html_body_parts.append("<h2>Metrics Summary</h2><table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>")
        html_body_parts.extend(html_rows)
        html_body_parts.append("</tbody></table>")

    html_content = _style_html("\n".join(html_body_parts), "Verification Report")

    result = f"{md_content}\n\n-----\n\n{html_content}\n"

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(result)

    return result


def generate_regression_report(
    baseline: dict,
    current: dict,
    gate_results: dict,
    output_path: str | None = None,
) -> str:
    md_parts = ["# Regression Report", ""]
    md_parts.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    md_parts.append("")

    passed_gates = gate_results.get("passed", 0)
    total_gates = gate_results.get("total", 0)
    failed_gates = gate_results.get("failed", 0)
    md_parts.append(f"**Quality Gates:** {passed_gates}/{total_gates} passed ({failed_gates} failed)")
    md_parts.append("")

    md_parts.append("## Metric Comparison")
    md_parts.append("")
    md_parts.append("| Metric | Baseline | Current | Delta | Regressed? |")
    md_parts.append("| --- | --- | --- | --- | --- |")

    all_keys = sorted(set(baseline.keys()) | set(current.keys()))
    regressions = []
    for key in all_keys:
        bv = baseline.get(key, "N/A")
        cv = current.get(key, "N/A")
        try:
            bf = float(bv)
            cf = float(cv)
            delta = cf - bf
            delta_str = f"{delta:+.4f}"
            regressed = delta < 0
        except (TypeError, ValueError):
            delta_str = "N/A"
            regressed = False
        if regressed:
            regressions.append(key)
            md_parts.append(f"| {key} | {bv} | {cv} | {delta_str} | **✗ REGRESSED** |")
        else:
            md_parts.append(f"| {key} | {bv} | {cv} | {delta_str} | ✓ |")

    md_parts.append("")

    if regressions:
        md_parts.append("## ⚠ Regressions Detected")
        md_parts.append("")
        for r in regressions:
            bv = baseline.get(r, "N/A")
            cv = current.get(r, "N/A")
            md_parts.append(f"- **{r}**: {bv} → {cv}")
        md_parts.append("")

    if failed_gates > 0:
        md_parts.append("## Failed Quality Gates")
        md_parts.append("")
        for g in gate_results.get("gates", []):
            if not g.get("passed", True):
                md_parts.append(f"- **{g.get('name', 'Unknown')}**: {g.get('message', '')}")
        md_parts.append("")

    md_content = "\n".join(md_parts)

    html_body_parts = [
        "<h1>Regression Report</h1>",
        f"<p><strong>Generated:</strong> {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</p>",
        f"<p class=\"{'pass' if failed_gates == 0 else 'fail'}\"><strong>Quality Gates:</strong> {passed_gates}/{total_gates} passed</p>",
    ]

    if regressions:
        html_body_parts.append("<h2>Regressions Detected</h2><ul>")
        for r in regressions:
            bv = baseline.get(r, "N/A")
            cv = current.get(r, "N/A")
            html_body_parts.append(f"<li class='fail'><strong>{r}</strong>: {bv} → {cv}</li>")
        html_body_parts.append("</ul>")

    html_content = _style_html("\n".join(html_body_parts), "Regression Report")

    result = f"{md_content}\n\n-----\n\n{html_content}\n"

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(result)

    return result


def generate_security_summary(
    all_metrics: dict, output_path: str | None = None
) -> str:
    md_parts = ["# Security Metrics Summary", ""]
    md_parts.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    md_parts.append("")

    md_parts.append("| Metric | Value | Status |")
    md_parts.append("| --- | --- | --- |")

    html_rows = []
    for key, metric_data in sorted(all_metrics.items()):
        if isinstance(metric_data, dict):
            value = metric_data.get("value", metric_data.get("score", "N/A"))
            status = metric_data.get("status", "unknown")
            threshold_good = metric_data.get("threshold_good")
            threshold_warning = metric_data.get("threshold_warning")
        else:
            value = metric_data
            status = "unknown"

        if status == "good" or (status == "unknown" and isinstance(value, (int, float)) and value >= 0.7):
            status_display = "✓ Good"
            html_cls = "metric-good"
        elif status == "warning" or (isinstance(value, (int, float)) and value >= 0.4):
            status_display = "⚠ Warning"
            html_cls = "metric-warning"
        elif status == "bad":
            status_display = "✗ Bad"
            html_cls = "metric-bad"
        else:
            status_display = str(status)
            html_cls = ""

        md_parts.append(f"| {key} | {value} | {status_display} |")
        html_rows.append(f"<tr class=\"{html_cls}\"><td>{key}</td><td>{value}</td><td>{status_display}</td></tr>")

    md_parts.append("")

    overview = all_metrics.get("__overview__", {})
    if overview:
        g = overview.get("good", 0)
        w = overview.get("warning", 0)
        b = overview.get("bad", 0)
        md_parts.append(f"**Overview:** {g} good, {w} warning, {b} bad")
        md_parts.append("")

    md_content = "\n".join(md_parts)

    html_body_parts = [
        "<h1>Security Metrics Summary</h1>",
        f"<p><strong>Generated:</strong> {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</p>",
        "<h2>Dashboard</h2>",
        "<table><thead><tr><th>Metric</th><th>Value</th><th>Status</th></tr></thead><tbody>",
    ]
    html_body_parts.extend(html_rows)
    html_body_parts.append("</tbody></table>")

    if overview:
        g = overview.get("good", 0)
        w = overview.get("warning", 0)
        b = overview.get("bad", 0)
        html_body_parts.append(f"<div class='summary'><strong>Overview:</strong> {g} good, {w} warning, {b} bad</div>")

    html_content = _style_html("\n".join(html_body_parts), "Security Summary")

    result = f"{md_content}\n\n-----\n\n{html_content}\n"

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(result)

    return result


def generate_executive_summary(
    reports: dict, output_path: str | None = None
) -> str:
    md_parts = ["# Executive Summary", ""]
    md_parts.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    md_parts.append("")

    overview = reports.get("overview", {})
    if overview:
        md_parts.append("## Overview")
        md_parts.append("")
        for k, v in overview.items():
            md_parts.append(f"- **{k}:** {v}")
        md_parts.append("")

    key_metrics = reports.get("key_metrics", {})
    if key_metrics:
        md_parts.append("## Key Metrics")
        md_parts.append("")
        md_parts.append("| Metric | Value |")
        md_parts.append("| --- | --- |")
        for k, v in sorted(key_metrics.items()):
            md_parts.append(f"| {k} | {v} |")
        md_parts.append("")

    protection_summary = reports.get("protection_summary", {})
    if protection_summary:
        md_parts.append("## Protection Summary")
        md_parts.append("")
        layers = protection_summary.get("layers_applied", 0)
        coverage = protection_summary.get("coverage_percent", "N/A")
        resilience = protection_summary.get("resilience_score", "N/A")
        md_parts.append(f"- **Protection layers applied:** {layers}")
        md_parts.append(f"- **Coverage:** {coverage}")
        md_parts.append(f"- **Resilience score:** {resilience}")
        md_parts.append("")

    recommendations = reports.get("recommendations", [])
    if recommendations:
        md_parts.append("## Recommendations")
        md_parts.append("")
        for i, rec in enumerate(recommendations, 1):
            md_parts.append(f"{i}. {rec}")
        md_parts.append("")

    summary_text = reports.get("summary", "")
    if summary_text:
        md_parts.append("## Conclusion")
        md_parts.append("")
        md_parts.append(summary_text)
        md_parts.append("")

    md_content = "\n".join(md_parts)

    html_body_parts = [
        "<h1>Executive Summary</h1>",
        f"<p><strong>Generated:</strong> {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</p>",
    ]

    if key_metrics:
        html_body_parts.append("<h2>Key Metrics</h2><table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>")
        for k, v in sorted(key_metrics.items()):
            html_body_parts.append(f"<tr><td>{k}</td><td>{v}</td></tr>")
        html_body_parts.append("</tbody></table>")

    if recommendations:
        html_body_parts.append("<h2>Recommendations</h2><ul>")
        for rec in recommendations:
            html_body_parts.append(f"<li>{rec}</li>")
        html_body_parts.append("</ul>")

    html_content = _style_html("\n".join(html_body_parts), "Executive Summary")

    result = f"{md_content}\n\n-----\n\n{html_content}\n"

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(result)

    return result
