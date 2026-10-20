"""
coverage_map.py

Purpose:
Builds and serializes protection coverage maps that track which
protections (VM, ROP, Fragmentation, Watermark, etc.) are applied
to each function in an IR module.

Architectural Role:
Central aggregation point for protection status. Reads pipeline
state and IR scan data, produces CoverageMap dataclasses with
per-function and per-protection statistics. Supports JSON, HTML,
and text output formats for reporting.

Execution Context:
Called after all protection passes complete. The CoverageMap is
consumed by the knowledge graph builder, artifact generator,
security regression gates, and the CLI reporting commands.

Dependencies:
- ir_scanner (scan_ir_module) for per-function IR metadata
- dataclasses for structured data
- datetime for generation timestamps

Security Relevance:
A protection coverage map is the canonical answer to the question
"what is protecting function X?". The per-protection stats identify
weak spots in the protection surface, and the heatmap view makes
it easy to spot functions that are dangerously under-protected.

Maintenance Notes:
- When adding a new protection, add its name to PROTECTION_NAMES
  and add a corresponding flag_map entry in _check_protection_applied.
- The flag_map must mirror the CLI option names exactly.
- HTML output uses inline styles with no CSS dependencies.
"""

from __future__ import annotations
import datetime
import logging

from dataclasses import dataclass, field
from typing import Dict, List

from .ir_scanner import scan_ir_module

PROTECTION_NAMES = [
    "VM",
    "ROP",
    "Fragmentation",
    "Watermark",
    "Attestation",
    "Proof",
    "FHE",
    "ZK",
    "Kernel",
    "IO_Research",
    "MicroJIT",
    "DataObfuscation",
    "EntropyFlatten",
    "CryptoBinding",
    "FlowEntangle",
    "ChallengeResponse",
    "Diversity",
    "DistributedProtection",
]


@dataclass
class FunctionCoverage:
    """
    Per-function protection coverage data.

    Stores which protections are present/absent for a single function,
    plus detailed metadata about each protection and any uncovered
    code paths that explain why a protection was skipped.
    """

    function_name: str
    ir_block_count: int
    protections: Dict[str, bool] = field(default_factory=dict)
    protection_details: Dict[str, Dict] = field(default_factory=dict)
    uncovered_paths: List[str] = field(default_factory=list)

    def coverage_count(self) -> int:
        """
        Count how many protections are actively applied to this function.
        """
        return sum(1 for v in self.protections.values() if v)

    def protection_percent(self) -> float:
        """
        Return the percentage of known protections applied to this function.
        """
        if not self.protections:
            return 0.0
        return (self.coverage_count() / len(self.protections)) * 100.0


@dataclass
class CoverageMap:
    """
    Aggregate protection coverage for an entire IR module.

    Combines per-function coverage data into module-level statistics:
    total/covered function counts, a coverage percentage, per-protection
    coverage ratios, and a generation timestamp.
    """

    module_name: str
    total_functions: int
    covered_functions: int
    coverage_percent: float
    functions: Dict[str, FunctionCoverage] = field(default_factory=dict)
    per_protection_stats: Dict[str, dict] = field(default_factory=dict)
    generated_at: str = ""


def _check_protection_applied(opts, protection_name: str, func_name: str, pipeline_state=None) -> bool:
    """
    Check whether a specific protection is applied to a function.

    Queries pipeline options for the relevant flag (e.g., opts.rop,
    opts.fragment, opts.watermark). Supports per-function overrides
    via pipeline_state.function_overrides.
    Returns True if the protection's flag is active.
    """
    overrides = {}
    if pipeline_state is not None:
        if isinstance(pipeline_state, dict):
            overrides = pipeline_state.get("function_overrides", {}).get(func_name, {})
        else:
            overrides = getattr(pipeline_state, "function_overrides", {}).get(func_name, {})
    if overrides and protection_name in overrides:
        return overrides[protection_name]
    flag_map = {
        "VM": lambda: bool((hasattr(opts, "state_isa") and getattr(opts, "state_isa", False)) or (hasattr(opts, "ephemeral_isa") and getattr(opts, "ephemeral_isa", False)) or (hasattr(opts, "simd_vm") and getattr(opts, "simd_vm", False))),
        "ROP": lambda: bool(getattr(opts, "rop", False)),
        "Fragmentation": lambda: bool(getattr(opts, "fragment", False) or getattr(opts, "micro_fragment", False)),
        "Watermark": lambda: bool(getattr(opts, "watermark", None) is not None),
        "Attestation": lambda: bool(getattr(opts, "attestation", False)),
        "Proof": lambda: bool(getattr(opts, "proof_carrying", False) or getattr(opts, "embed_proof", False) or getattr(opts, "verify_preservation_formal", False)),
        "FHE": lambda: bool(getattr(opts, "fhe_vm", False)),
        "ZK": lambda: bool(getattr(opts, "zk_state", False)),
        "Kernel": lambda: bool(getattr(opts, "kernel_assist", False)),
        "IO_Research": lambda: bool(getattr(opts, "io_research", False)),
        "MicroJIT": lambda: bool(getattr(opts, "microjit", False)),
        "DataObfuscation": lambda: bool(getattr(opts, "data_obfuscation", False)),
        "EntropyFlatten": lambda: bool(getattr(opts, "hw_entropy", False) or getattr(opts, "entropy_flatten", False)),
        "CryptoBinding": lambda: bool(getattr(opts, "crypto_binding", False)),
        "FlowEntangle": lambda: bool(getattr(opts, "flow_entangle", False)),
        "ChallengeResponse": lambda: bool(getattr(opts, "challenge_response", False)),
        "Diversity": lambda: bool(getattr(opts, "diversity", None) is not None and getattr(opts, "diversity", 0) > 0),
        "DistributedProtection": lambda: bool(getattr(opts, "multi_binary", False) or getattr(opts, "cross_process", False) or getattr(opts, "distributed_vm", False) or getattr(opts, "dist_attestation", False)),
    }
    checker = flag_map.get(protection_name)
    if checker is None:
        return False
    return checker()


def generate_coverage_map(ir_module, pipeline_state=None):
    """
    Build a CoverageMap from an IR module and optional pipeline state.

    Scans each function's IR for structural metadata, checks every
    known protection against the pipeline options, and merges in
    runtime tracking data if a PipelineTracker is available.
    Returns a fully populated CoverageMap with per-function and
    per-protection statistics.
    """
    opts = getattr(pipeline_state, "opts", None) if pipeline_state else None
    if opts is None:
        import logging as _lg
        _lg.warning("No pipeline opts available for coverage map; coverage may be incomplete")
        opts = _dummy_opts()
    func_scan = scan_ir_module(ir_module)
    module_name = getattr(ir_module, "name", "unknown")
    functions: Dict[str, FunctionCoverage] = {}
    for func in ir_module.functions:
        name = func.name
        scan_info = func_scan.get(name, {})
        fn_cov = FunctionCoverage(
            function_name=name,
            ir_block_count=len(func.blocks),
        )
        for pname in PROTECTION_NAMES:
            applied = _check_protection_applied(opts, pname, name, pipeline_state)
            fn_cov.protections[pname] = applied
        fn_cov.protection_details["ir_scan"] = scan_info
        if pipeline_state is not None:
            if isinstance(pipeline_state, dict):
                globals_dict = pipeline_state.get("globals", {})
            else:
                globals_dict = getattr(pipeline_state, "globals", {})
            tracker = globals_dict.get("tracker") if isinstance(globals_dict, dict) else None
            if tracker:
                fn_tracker_state = tracker.get_function_state(name)
                for pname in PROTECTION_NAMES:
                    if pname in fn_tracker_state.get("applied", []):
                        fn_cov.protections[pname] = True
                        fn_cov.protection_details[pname] = fn_tracker_state.get("details", {}).get(pname, {})
                    if pname in fn_tracker_state.get("skipped", []):
                        fn_cov.uncovered_paths.append(f"{pname}: {fn_tracker_state['skipped'][pname]}")
        fn_cov.uncovered_paths = _find_uncovered(fn_cov)
        functions[name] = fn_cov
    total = len(functions)
    covered = sum(1 for f in functions.values() if f.coverage_count() > 0)
    coverage_pct = (covered / total * 100.0) if total > 0 else 0.0
    per_protection_stats: Dict[str, dict] = {}
    for pname in PROTECTION_NAMES:
        count = sum(1 for f in functions.values() if f.protections.get(pname, False))
        per_protection_stats[pname] = {
            "functions_covered": count,
            "total_functions": total,
            "coverage_ratio": count / total if total > 0 else 0.0,
        }
    return CoverageMap(
        module_name=module_name,
        total_functions=total,
        covered_functions=covered,
        coverage_percent=coverage_pct,
        functions=functions,
        per_protection_stats=per_protection_stats,
        generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )


def _find_uncovered(fn_cov: FunctionCoverage) -> List[str]:
    """
    Generate a list of explanatory strings for absent protections.
    """
    uncovered = []
    for pname, applied in fn_cov.protections.items():
        if not applied:
            uncovered.append(f"No {pname} protection applied")
    return uncovered


def _dummy_opts():
    """
    Create a dummy options object with no flags set.

    Used as fallback when no pipeline state is available, ensuring
    all protection checks return False (conservative default).
    """
    class _Opts:
        pass
    return _Opts()


def merge_coverage_maps(maps):
    """
    Merge multiple CoverageMap objects into a single aggregate map.

    Unions the function sets, ORs the protection flags (a function
    is considered covered if any map reports coverage), and
    recalculates statistics. Useful when protections are applied
    across multiple pipeline stages or binaries.
    """
    if not maps:
        return CoverageMap(module_name="empty", total_functions=0, covered_functions=0, coverage_percent=0.0, generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    merged_name = " + ".join(m.module_name for m in maps)
    merged_fns: Dict[str, FunctionCoverage] = {}
    protection_true: Dict[str, Dict[str, bool]] = {}
    protection_false: Dict[str, Dict[str, bool]] = {}
    for m in maps:
        for fname, fc in m.functions.items():
            if fname not in merged_fns:
                merged_fns[fname] = FunctionCoverage(
                    function_name=fc.function_name,
                    ir_block_count=fc.ir_block_count,
                )
            for pname in fc.protections:
                merged_fns[fname].protections[pname] = merged_fns[fname].protections.get(pname, False) or fc.protections[pname]
                if fc.protections[pname]:
                    protection_true.setdefault(fname, {})[pname] = True
                else:
                    protection_false.setdefault(fname, {})[pname] = True
            for pname, details in fc.protection_details.items():
                if pname not in merged_fns[fname].protection_details:
                    merged_fns[fname].protection_details[pname] = details
            merged_fns[fname].uncovered_paths.extend(fc.uncovered_paths)
    for fname in merged_fns:
        for pname in set(protection_true.get(fname, {})) & set(protection_false.get(fname, {})):
            logging.warning(
                f"Inconsistent coverage for {fname}: protection '{pname}' is applied in some maps but not all"
            )
    total = len(merged_fns)
    covered = sum(1 for f in merged_fns.values() if f.coverage_count() > 0)
    coverage_pct = (covered / total * 100.0) if total > 0 else 0.0
    per_protection_stats: Dict[str, dict] = {}
    for pname in PROTECTION_NAMES:
        count = sum(1 for f in merged_fns.values() if f.protections.get(pname, False))
        per_protection_stats[pname] = {
            "functions_covered": count,
            "total_functions": total,
            "coverage_ratio": count / total if total > 0 else 0.0,
        }
    return CoverageMap(
        module_name=merged_name,
        total_functions=total,
        covered_functions=covered,
        coverage_percent=coverage_pct,
        functions=merged_fns,
        per_protection_stats=per_protection_stats,
        generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )


def _fc_to_dict(fc: FunctionCoverage) -> dict:
    """
    Serialize a FunctionCoverage to a JSON-compatible dict.
    """
    return {
        "function_name": fc.function_name,
        "ir_block_count": fc.ir_block_count,
        "protections": dict(fc.protections),
        "protection_details": {k: _serialize_details(v) for k, v in fc.protection_details.items()},
        "uncovered_paths": list(fc.uncovered_paths),
        "coverage_count": fc.coverage_count(),
        "protection_percent": fc.protection_percent(),
    }


def _serialize_details(d: Dict) -> Dict:
    """
    Recursively serialize a details dict to JSON-safe types.
    Converts non-primitive values to strings.
    """
    result = {}
    for k, v in d.items():
        if isinstance(v, (str, int, float, bool)):
            result[k] = v
        elif isinstance(v, dict):
            result[k] = _serialize_details(v)
        elif isinstance(v, list):
            result[k] = [str(x) for x in v]
        else:
            result[k] = str(v)
    return result


def coverage_to_json(coverage_map: CoverageMap) -> dict:
    """
    Convert a CoverageMap to a plain JSON-serializable dict.
    """
    return {
        "module_name": coverage_map.module_name,
        "total_functions": coverage_map.total_functions,
        "covered_functions": coverage_map.covered_functions,
        "coverage_percent": coverage_map.coverage_percent,
        "functions": {k: _fc_to_dict(v) for k, v in coverage_map.functions.items()},
        "per_protection_stats": dict(coverage_map.per_protection_stats),
        "generated_at": coverage_map.generated_at,
    }


def coverage_to_html(coverage_map: CoverageMap) -> str:
    """
    Render a CoverageMap as a self-contained HTML page with a
    colour-coded heatmap table and per-protection statistics.
    """
    rows = []
    for fname, fc in sorted(coverage_map.functions.items()):
        pct = fc.protection_percent()
        color = "#4CAF50" if pct >= 80 else ("#FF9800" if pct >= 40 else "#f44336")
        heat_cells = ""
        for pname in PROTECTION_NAMES:
            applied = fc.protections.get(pname, False)
            cell_color = "#4CAF50" if applied else "#f44336"
            symbol = "&#10003;" if applied else "&#10007;"
            heat_cells += f'<td style="background:{cell_color};color:white;text-align:center">{symbol}</td>'
        uncovered = "; ".join(fc.uncovered_paths) if fc.uncovered_paths else "None"
        rows.append(f"""<tr>
            <td>{fname}</td>
            <td>{fc.ir_block_count}</td>
            <td>{fc.coverage_count()}/{len(PROTECTION_NAMES)}</td>
            <td style="background:{color};color:white">{pct:.1f}%</td>
            {heat_cells}
            <td>{uncovered}</td>
        </tr>""")

    prot_headers = "".join(f"<th>{p}</th>" for p in PROTECTION_NAMES)
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Protection Coverage Map - {coverage_map.module_name}</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; background: #1e1e1e; color: #d4d4d4; }}
h1 {{ color: #569cd6; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #3c3c3c; padding: 6px 10px; text-align: left; white-space: nowrap; }}
th {{ background: #2d2d2d; color: #569cd6; position: sticky; top: 0; }}
tr:nth-child(even) {{ background: #252526; }}
tr:hover {{ background: #2a2d2e; }}
.summary {{ margin: 20px 0; padding: 15px; background: #252526; border-radius: 4px; }}
.stat {{ display: inline-block; margin-right: 30px; }}
.label {{ color: #888; }}
.value {{ font-size: 1.4em; font-weight: bold; }}
</style></head><body>
<h1>Protection Coverage Map: {coverage_map.module_name}</h1>
<div class="summary">
<div class="stat"><span class="label">Total Functions</span><br><span class="value">{coverage_map.total_functions}</span></div>
<div class="stat"><span class="label">Covered</span><br><span class="value">{coverage_map.covered_functions}</span></div>
<div class="stat"><span class="label">Coverage</span><br><span class="value">{coverage_map.coverage_percent:.1f}%</span></div>
<div class="stat"><span class="label">Generated</span><br><span class="value">{coverage_map.generated_at}</span></div>
</div>
<h2>Per-Protection Statistics</h2>
<table><tr><th>Protection</th><th>Functions Covered</th><th>Coverage Ratio</th></tr>"""
    for pname in PROTECTION_NAMES:
        stats = coverage_map.per_protection_stats.get(pname, {})
        html += f"<tr><td>{pname}</td><td>{stats.get('functions_covered', 0)}/{stats.get('total_functions', 0)}</td><td>{stats.get('coverage_ratio', 0):.1%}</td></tr>"
    html += "</table><h2>Per-Function Heatmap</h2>"
    html += f"""<table><thead><tr><th>Function</th><th>Blocks</th><th>Covered</th><th>%</th>{prot_headers}<th>Uncovered</th></tr></thead><tbody>"""
    html += "\n".join(rows)
    html += "</tbody></table></body></html>"
    return html


def coverage_to_text(coverage_map: CoverageMap) -> str:
    """
    Render a CoverageMap as a plain-text table for terminal display.
    """
    lines = [f"Protection Coverage Map: {coverage_map.module_name}"]
    lines.append(f"{'=' * 60}")
    lines.append(f"  Total functions:  {coverage_map.total_functions}")
    lines.append(f"  Covered functions: {coverage_map.covered_functions}")
    lines.append(f"  Coverage:         {coverage_map.coverage_percent:.1f}%")
    lines.append(f"  Generated:        {coverage_map.generated_at}")
    lines.append("")
    lines.append("Per-Protection Statistics:")
    lines.append(f"  {'Protection':25s} {'Covered':>10s} {'Ratio':>8s}")
    lines.append(f"  {'-'*25} {'-'*10} {'-'*8}")
    for pname in PROTECTION_NAMES:
        stats = coverage_map.per_protection_stats.get(pname, {})
        count = stats.get("functions_covered", 0)
        ratio = stats.get("coverage_ratio", 0)
        lines.append(f"  {pname:25s} {count:>3d}/{stats.get('total_functions', 0):<3d}  {ratio:>7.1%}")
    lines.append("")
    lines.append("Per-Function Coverage:")
    lines.append(f"  {'Function':30s} {'Blocks':>6s} {'Covered':>8s} {'Percent':>8s}")
    lines.append(f"  {'-'*30} {'-'*6} {'-'*8} {'-'*8}")
    for fname, fc in sorted(coverage_map.functions.items()):
        pct = fc.protection_percent()
        lines.append(f"  {fname:30s} {fc.ir_block_count:>6d} {fc.coverage_count():>3d}/{len(PROTECTION_NAMES):<3d} {pct:>7.1f}%")
    return "\n".join(lines)
