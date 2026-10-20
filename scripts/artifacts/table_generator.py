"""
table_generator.py

Purpose:
Generates formatted tables (Markdown + HTML) for build artifacts:
benchmark results, metric comparisons, threat models, and coverage
matrices.

Architectural Role:
Tabular output layer of the artifacts module. Each function accepts
structured data and returns a string with both Markdown and HTML
representations of the table.

Execution Context:
Called by ArtifactBuilder._generate_tables() during artifact
generation. Tables are written to build/artifacts/tables/.

Dependencies:
- Standard library only (json, os)

Security Relevance:
Tables provide structured, machine-readable views of security metrics.
The coverage table shows per-function protection status at a glance.
The comparison table quantifies metric changes between builds.

Maintenance Notes:
- Both Markdown and HTML versions are produced for each table.
  Markdown renders in plain-text/terminal; HTML renders in browsers.
- The _fmt_num helper uses scientific notation for very small
  values (< 0.0001).
- The generate_coverage_table function uses a hardcoded fallback
  protection list when per_protection_stats is empty.
"""

from __future__ import annotations

import json  # noqa: F401 (this line binds a name used by an embedded template)
import os


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _html_table(headers: list[str], rows: list[list[str]], cls: str = "data-table") -> str:
    parts = [f'<table class="{cls}">']
    parts.append("  <thead><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead>")
    parts.append("  <tbody>")
    for row in rows:
        parts.append("    <tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
    parts.append("  </tbody>")
    parts.append("</table>")
    return "\n".join(parts)


def generate_benchmark_table(
    benchmark_data: dict, output_path: str | None = None
) -> str:
    headers = ["Benchmark", "Mean", "Min", "Max", "StdDev", "OPS"]

    rows = []
    for bench_name, data in sorted(benchmark_data.items()):
        if not isinstance(data, dict):
            continue
        mean = _fmt_num(data.get("mean", 0))
        minv = _fmt_num(data.get("min", 0))
        maxv = _fmt_num(data.get("max", 0))
        std = _fmt_num(data.get("stddev", data.get("std", 0)))
        ops = _fmt_num(data.get("ops", data.get("operations_per_second", 0)))
        rows.append([str(bench_name), mean, minv, maxv, std, ops])

    md = _markdown_table(headers, rows)
    html = _html_table(headers, rows, cls="benchmark-table")

    result = f"<!-- Benchmark Table (Markdown) -->\n\n{md}\n\n<!-- HTML -->\n{html}\n"

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(result)

    return result


def _fmt_num(val) -> str:
    try:
        v = float(val)
        if abs(v) < 0.0001 and v != 0:
            return f"{v:.6e}"
        if v == int(v):
            return str(int(v))
        return f"{v:.4f}"
    except (TypeError, ValueError):
        return str(val)


def generate_comparison_table(
    baseline: dict, current: dict, output_path: str | None = None
) -> str:
    headers = ["Metric", "Baseline", "Current", "Delta", "Pass?"]
    rows = []

    all_keys = sorted(set(baseline.keys()) | set(current.keys()))
    for key in all_keys:
        bv = baseline.get(key, "N/A")
        cv = current.get(key, "N/A")
        try:
            bf = float(bv) if bv != "N/A" else None
            cf = float(cv) if cv != "N/A" else None
        except (TypeError, ValueError):
            bf = None
            cf = None

        if bf is not None and cf is not None:
            delta = cf - bf
            delta_str = f"{delta:+.4f}" if abs(delta) >= 0.0001 else "0"
            passed = "✓" if delta >= 0 else "✗"
            if key in ("execution_time", "binary_size", "instruction_count"):
                passed = "✓" if delta <= 0 else "✗"
        else:
            delta_str = "N/A"
            passed = "—"

        rows.append([
            str(key),
            str(bv),
            str(cv),
            delta_str,
            passed,
        ])

    md = _markdown_table(headers, rows)
    html = _html_table(headers, rows, cls="comparison-table")

    result = f"<!-- Comparison Table (Markdown) -->\n\n{md}\n\n<!-- HTML -->\n{html}\n"

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(result)

    return result


def generate_threat_model_table(
    threats: list[dict], output_path: str | None = None
) -> str:
    headers = ["Threat", "Severity", "Mitigation", "Status"]
    rows = []

    for threat in threats:
        name = threat.get("name", threat.get("threat", "Unknown"))
        severity = threat.get("severity", "unknown")
        mitigation = threat.get("mitigation", threat.get("mitigations", "None"))
        status = threat.get("status", "unmitigated")
        if isinstance(mitigation, list):
            mitigation = "; ".join(mitigation)
        rows.append([str(name), str(severity), str(mitigation), str(status)])

    if not rows:
        rows.append(["No threats defined", "—", "—", "—"])

    md = _markdown_table(headers, rows)
    html = _html_table(headers, rows, cls="threat-model-table")

    result = f"<!-- Threat Model Table (Markdown) -->\n\n{md}\n\n<!-- HTML -->\n{html}\n"

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(result)

    return result


def generate_coverage_table(
    coverage_map: dict, output_path: str | None = None
) -> str:
    functions = coverage_map.get("functions", {})
    per_prot = coverage_map.get("per_protection_stats", {})

    all_protections = sorted(per_prot.keys()) if per_prot else ["VM", "ROP", "FHE",
        "Watermark", "Attestation", "Fragment", "ZK", "CryptoBinding",
        "Diversity", "CFG", "SSA"]

    headers = ["Function"] + all_protections + ["Covered", "Total", "%"]
    rows = []

    for fname, fdata in sorted(functions.items()):
        prot = fdata.get("protections", {})
        row = [str(fname)]
        covered = 0
        total = len(all_protections)
        for p in all_protections:
            val = prot.get(p, False)
            if val:
                row.append("✓")
                covered += 1
            else:
                row.append("—")
        pct = f"{covered / max(total, 1) * 100:.0f}%"
        row.extend([str(covered), str(total), pct])
        rows.append(row)

    if not rows:
        summary = coverage_map.get("summary", {})
        total_funcs = summary.get("total_functions", 0)
        if total_funcs:
            for i in range(total_funcs):
                fname = f"func_{i}"
                row = [fname] + ["—"] * len(all_protections) + ["0", str(len(all_protections)), "0%"]
                rows.append(row)
        else:
            rows.append(["No functions"] + ["—"] * len(all_protections) + ["0", "0", "0%"])

    md = _markdown_table(headers, rows)
    html = _html_table(headers, rows, cls="coverage-table")

    result = f"<!-- Coverage Table (Markdown) -->\n\n{md}\n\n<!-- HTML -->\n{html}\n"

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(result)

    return result
