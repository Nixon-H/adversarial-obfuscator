"""
report.py

Purpose:
Generates HTML and text-format benchmark reports from AIBenchmark results.
Produces a self-contained HTML page with score cards, metric tables, a
radar chart (rendered via inline Canvas JavaScript), and optional LLM
evaluation scores.

Architectural Role:
Presentation layer for the benchmarking subsystem. Consumes the results
dict produced by AIBenchmark.evaluate() and formats it for human
consumption. The HTML report is suitable for CI artifact publishing.

Dependencies:
json, os, html.escape

Security Relevance:
Enables visual comparison of protection effectiveness across builds.
The radar chart and score breakdown help identify which protection
dimensions need strengthening.
"""

import json
import os
from html import escape


RADAR_CHART_JS = """
function drawRadar(id, metrics, values) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    const cx = w/2, cy = h/2, radius = Math.min(cx, cy) - 60;
    const n = metrics.length;
    const angleStep = (2 * Math.PI) / n;

    ctx.clearRect(0, 0, w, h);

    function toCoords(i, r) {
        const angle = -Math.PI/2 + i * angleStep;
        return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
    }

    // Grid
    for (let ring = 1; ring <= 5; ring++) {
        const r = (radius * ring) / 5;
        ctx.beginPath();
        for (let i = 0; i <= n; i++) {
            const [x, y] = toCoords(i % n, r);
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.strokeStyle = '#e0e0e0';
        ctx.stroke();
    }

    // Axes
    for (let i = 0; i < n; i++) {
        const [x, y] = toCoords(i, radius);
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(x, y);
        ctx.strokeStyle = '#d0d0d0';
        ctx.stroke();
        const [lx, ly] = toCoords(i, radius + 15);
        ctx.fillStyle = '#333';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(metrics[i], lx, ly);
    }

    // Data
    const colors = ['#2563eb', '#dc2626', '#16a34a', '#9333ea'];
    values.forEach((data, di) => {
        ctx.beginPath();
        for (let i = 0; i <= n; i++) {
            const idx = i % n;
            const v = Math.max(0, Math.min(1, data.values[idx]));
            const [x, y] = toCoords(idx, v * radius);
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.fillStyle = colors[di % colors.length] + '33';
        ctx.fill();
        ctx.strokeStyle = colors[di % colors.length];
        ctx.lineWidth = 2;
        ctx.stroke();
    });
}
"""


def _score_bar(value: float) -> str:
    """Render an inline HTML/CSS progress bar for a score value."""
    pct = max(0, min(100, int(value * 100)))
    color = "#16a34a" if value >= 0.7 else ("#ca8a04" if value >= 0.4 else "#dc2626")
    return f"""<div style="background:#e5e7eb;border-radius:4px;height:20px;width:200px;">
<div style="background:{color};width:{pct}%;height:20px;border-radius:4px;text-align:center;color:white;font-size:11px;line-height:20px;">{pct}%</div>
</div>"""


class BenchmarkReport:
    """
    Generates HTML and text-format benchmark reports.

    The HTML report includes:
      - Overall protection score card (color-coded green/yellow/red)
      - Per-metric score table with inline progress bars
      - Canvas-based radar chart of all six metric dimensions
      - Optional LLM evaluation results table

    The text summary is suitable for CLI display or log files.
    """

    def generate_html(self, results: dict, title: str = "AI Obfuscation Benchmark Report") -> str:
        """
        Generate a self-contained HTML report from benchmark results.

        Inlines all CSS and JavaScript (including the radar chart
        rendering). No external dependencies required.
        """
        overall = results.get("overall", 0)
        metrics_order = ["naming_recovery", "semantic_leakage", "static_confusion",
                         "decompilation_resistance", "complexity_impact", "entropy"]
        metric_labels = ["Naming Recovery", "Semantic Leakage", "Static Confusion",
                         "Decomp. Resistance", "Complexity Impact", "Entropy"]
        metric_scores = [results.get(m, {}).get("score", 0) for m in metrics_order]

        llm_results = results.get("_llm_results", {})

        rows = ""
        for label, key in zip(metric_labels, metrics_order):
            data = results.get(key, {})
            score = data.get("score", 0)
            detail = self._metric_detail(key, data)
            rows += f"""<tr>
<td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:500;">{label}</td>
<td style="padding:8px;border-bottom:1px solid #e5e7eb;">{_score_bar(score)}</td>
<td style="padding:8px;border-bottom:1px solid #e5e7eb;font-size:13px;color:#666;">{escape(detail)}</td>
</tr>"""

        llm_rows = ""
        for model, scores in llm_results.items():
            avg = sum(scores.values()) / max(len(scores), 1)
            llm_rows += f"""<tr>
<td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:500;">{escape(model)}</td>
<td style="padding:8px;border-bottom:1px solid #e5e7eb;">{_score_bar(avg)}</td>
<td style="padding:8px;border-bottom:1px solid #e5e7eb;font-size:13px;">
{', '.join(f'{k}: {v:.2f}' for k, v in sorted(scores.items()))}
</td>
</tr>"""

        radar_data = json.dumps([{"label": "Protected", "values": metric_scores}])

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(title)}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; color: #333; }}
.container {{ max-width: 1000px; margin: 0 auto; }}
.header {{ text-align: center; padding: 20px 0; }}
.header h1 {{ margin: 0; font-size: 28px; }}
.score-card {{ background: white; border-radius: 12px; padding: 30px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin: 20px 0; }}
.score-card .big-score {{ font-size: 64px; font-weight: 700; }}
.score-card .label {{ font-size: 14px; color: #666; }}
table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin: 20px 0; }}
th {{ text-align: left; padding: 12px 8px; background: #f3f4f6; border-bottom: 2px solid #e5e7eb; }}
canvas {{ display: block; margin: 20px auto; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>{escape(title)}</h1>
<p style="color:#666;">Generated by AIBenchmark — Static proxy metrics for AI deobfuscation resistance</p>
</div>

<div class="score-card">
<div class="big-score" style="color: {'#16a34a' if overall >= 0.7 else ('#ca8a04' if overall >= 0.4 else '#dc2626')};">{overall:.2f}</div>
<div class="label">Overall Protection Score</div>
</div>

<h2>Metric Scores</h2>
<table>
<tr><th style="width:200px;">Metric</th><th style="width:220px;">Score</th><th>Details</th></tr>
{rows}
</table>

<h2>Radar Chart</h2>
<canvas id="radar" width="500" height="500" style="max-width:500px;"></canvas>

<h2>LLM Evaluation</h2>
<table>
<tr><th style="width:200px;">Model</th><th style="width:220px;">Avg. Score</th><th>Per-Metric</th></tr>
{llm_rows if llm_rows else '<tr><td colspan="3" style="padding:12px;text-align:center;color:#999;">No LLM evaluation data (run with --benchmark-model to enable)</td></tr>'}
</table>

<p style="text-align:center;color:#999;font-size:12px;margin-top:30px;">
Protected: {escape(results.get('_protected_path', 'N/A'))}<br>
Original: {escape(results.get('_original_path', 'N/A'))}
</p>
</div>

<script>
{RADAR_CHART_JS}
const radarMetrics = {json.dumps(metric_labels)};
const radarData = {radar_data};
radarData.forEach(d => drawRadar('radar', radarMetrics, [d.values]));
</script>
</body>
</html>"""
        return html

    def generate_text_summary(self, results: dict) -> str:
        """
        Generate a plain-text benchmark summary for CLI/log output.

        Includes overall score, per-metric scores, and optional LLM
        evaluation data in a fixed-width table format.
        """
        lines = []
        lines.append("=" * 60)
        lines.append("  AI OBFUSCATION BENCHMARK SUMMARY")
        lines.append("=" * 60)

        overall = results.get("overall", 0)
        lines.append(f"  Overall Protection Score: {overall:.4f}")
        lines.append("")

        metrics_order = [
            ("naming_recovery", "Named Entity Recovery"),
            ("semantic_leakage", "Semantic Leakage"),
            ("static_confusion", "Static Analysis Confusion"),
            ("decompilation_resistance", "Decompilation Resistance"),
            ("complexity_impact", "Complexity Impact"),
            ("entropy", "Information Entropy"),
        ]
        for key, label in metrics_order:
            data = results.get(key, {})
            score = data.get("score", 0)
            lines.append(f"  {label:30s}: {score:.4f}")

        llm_results = results.get("_llm_results", {})
        if llm_results:
            lines.append("")
            lines.append(f"  {'--- LLM Evaluation ---':^60s}")
            for model, scores in llm_results.items():
                avg = sum(scores.values()) / max(len(scores), 1)
                lines.append(f"  {model:30s}: avg={avg:.4f}  {scores}")

        lines.append("=" * 60)
        return "\n".join(lines)

    @staticmethod
    def _metric_detail(key: str, data: dict) -> str:
        """Extract a human-readable detail string for a given metric."""
        if key == "naming_recovery":
            return f"Recovery rate: {data.get('recovery_rate', 0):.2%}"
        if key == "semantic_leakage":
            return f"Hellinger distance: {data.get('hellinger_distance', 0):.4f}"
        if key == "static_confusion":
            return f"Tool warnings: {data.get('total_warnings', 0)}"
        if key == "decompilation_resistance":
            c = data.get("constructs", {})
            return f"exec/eval: {c.get('exec_eval', 0)}, decorators: {c.get('nested_decorators', 0)}, except-flow: {c.get('exception_control_flow', 0)}"
        if key == "complexity_impact":
            return f"Ratio: {data.get('complexity_ratio', 0):.2f}x"
        if key == "entropy":
            return f"Shannon: {data.get('shannon_entropy', 0):.2f}"
        return ""
