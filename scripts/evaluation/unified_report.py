"""Unified evaluation report — collects all 9 metrics into a single JSON report."""
import json
import os
import sys
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _read_source(path: str) -> Optional[str]:
    if path and os.path.exists(path):
        try:
            with open(path) as f:
                return f.read()
        except Exception:
            return None
    return None


def collect_cfg_entropy(obfuscated_path: str, original_path: Optional[str] = None) -> Dict:
    """Collect CFG entropy metrics."""
    from scripts.metrics.resilience import compute_cfg_entropy
    obf_source = _read_source(obfuscated_path)
    orig_source = _read_source(original_path) if original_path else None
    if obf_source and orig_source:
        try:
            import ast
            obf_tree = ast.parse(obf_source)
            orig_tree = ast.parse(orig_source)
            entropy_result = compute_cfg_entropy(orig_tree, obf_tree)
            return {"cfg_entropy": entropy_result, "status": "measured"}
        except Exception as e:
            return {"cfg_entropy": {"error": str(e)}, "status": "error"}
    return {"cfg_entropy": None, "status": "skipped"}


def collect_cyclomatic_complexity(obfuscated_path: str, original_path: Optional[str] = None) -> Dict:
    """Collect cyclomatic complexity metrics."""
    from scripts.metrics.resilience import compute_cyclomatic
    obf_source = _read_source(obfuscated_path)
    orig_source = _read_source(original_path) if original_path else None
    if obf_source and orig_source:
        try:
            import ast
            obf_tree = ast.parse(obf_source)
            orig_tree = ast.parse(orig_source)
            result = compute_cyclomatic(orig_tree, obf_tree)
            return {"cyclomatic_complexity": result, "status": "measured"}
        except Exception as e:
            return {"cyclomatic_complexity": {"error": str(e)}, "status": "error"}
    return {"cyclomatic_complexity": None, "status": "skipped"}


def collect_symbolic_resistance(obfuscated_path: str, original_path: Optional[str] = None) -> Dict:
    """Collect symbolic execution resistance metrics."""
    from scripts.metrics.resilience import compute_symbolic_resistance
    obf_source = _read_source(obfuscated_path)
    orig_source = _read_source(original_path) if original_path else None
    if obf_source and orig_source:
        try:
            import ast
            obf_tree = ast.parse(obf_source)
            orig_tree = ast.parse(orig_source)
            result = compute_symbolic_resistance(orig_tree, obf_tree)
            return {"symbolic_resistance": result, "status": "measured"}
        except Exception as e:
            return {"symbolic_resistance": {"error": str(e)}, "status": "error"}
    return {"symbolic_resistance": None, "status": "skipped"}


def collect_decompiler_resistance(source_path: str) -> Dict:
    """Collect decompiler resistance metrics."""
    from scripts.benchmark.ai_eval import measure_decompilation_resistance
    source = _read_source(source_path)
    if source:
        try:
            result = measure_decompilation_resistance(source)
            return {"decompiler_resistance": result, "status": "measured"}
        except Exception as e:
            return {"decompiler_resistance": {"error": str(e)}, "status": "error"}
    return {"decompiler_resistance": None, "status": "skipped"}


def collect_ai_resistance(obfuscated_path: str, original_path: Optional[str] = None) -> Dict:
    """Collect AI-assisted analysis resistance metrics."""
    from scripts.benchmark.ai_eval import (
        measure_naming_recovery, measure_semantic_leakage,
        measure_static_analysis_resistance,
    )
    obf_source = _read_source(obfuscated_path)
    orig_source = _read_source(original_path) if original_path else None
    if obf_source and orig_source:
        try:
            naming = measure_naming_recovery(orig_source, obf_source)
            leakage = measure_semantic_leakage(orig_source, obf_source)
            static = measure_static_analysis_resistance(obf_source)
            naming_score = naming.get("score", 0)
            leakage_score = leakage.get("score", 0)
            static_score = static.get("score", 0)
            return {
                "ai_resistance": {
                    "naming_recovery_score": naming_score,
                    "semantic_leakage_score": leakage_score,
                    "static_analysis_resistance": static_score,
                    "composite": (naming_score + leakage_score + static_score) / 3,
                },
                "status": "measured",
            }
        except Exception as e:
            return {"ai_resistance": {"error": str(e)}, "status": "error"}
    return {"ai_resistance": None, "status": "skipped"}


def collect_watermark_survivability(source_path: str) -> Dict:
    """Collect watermark survivability metrics."""
    from scripts.evaluation.survivability_probes import probe_watermark
    source = _read_source(source_path)
    if source:
        try:
            score = probe_watermark(source)
            return {"watermark_survivability": {"survival_score": score}, "status": "measured"}
        except Exception as e:
            return {"watermark_survivability": {"error": str(e)}, "status": "error"}
    return {"watermark_survivability": None, "status": "skipped"}


def collect_protection_survivability(source_path: str) -> Dict:
    """Collect protection survivability metrics."""
    from scripts.evaluation.survivability_probes import probe_vm_opcodes, probe_cfg, probe_fragments
    source = _read_source(source_path)
    if source:
        try:
            vm = probe_vm_opcodes(source)
            cfg = probe_cfg(source)
            frag = probe_fragments(source)
            composite = (vm + cfg + frag) / 3
            return {
                "protection_survivability": {
                    "vm_opcode_recovery_resistance": vm,
                    "cfg_reconstruction_resistance": cfg,
                    "fragment_isolation_resistance": frag,
                    "composite": composite,
                },
                "status": "measured",
            }
        except Exception as e:
            return {"protection_survivability": {"error": str(e)}, "status": "error"}
    return {"protection_survivability": None, "status": "skipped"}


def collect_runtime_overhead(unprotected_path: Optional[str], protected_path: Optional[str]) -> Dict:
    """Collect runtime overhead metrics."""
    from scripts.evaluation.runtime_overhead import measure_runtime_overhead
    if unprotected_path and protected_path and os.path.exists(unprotected_path) and os.path.exists(protected_path):
        try:
            result = measure_runtime_overhead(unprotected_path, protected_path, iterations=3)
            return {"runtime_overhead": result, "status": "measured"}
        except Exception as e:
            return {"runtime_overhead": {"error": str(e)}, "status": "error"}
    return {"runtime_overhead": None, "status": "skipped"}


def collect_binary_size_overhead(unprotected_path: Optional[str], protected_path: Optional[str]) -> Dict:
    """Collect binary size overhead metrics."""
    from scripts.evaluation.binary_size import measure_size_overhead
    if unprotected_path and protected_path:
        try:
            result = measure_size_overhead(unprotected_path, protected_path)
            return {"binary_size_overhead": result, "status": "measured"}
        except Exception as e:
            return {"binary_size_overhead": {"error": str(e)}, "status": "error"}
    return {"binary_size_overhead": None, "status": "skipped"}


def generate_evaluation_report(
    obfuscated_source_path: str,
    original_source_path: Optional[str] = None,
    unprotected_binary_path: Optional[str] = None,
    protected_binary_path: Optional[str] = None,
    output_path: str = "build/evaluation_report.json",
) -> Dict:
    """Generate a unified evaluation report with all 9 metrics."""
    report = {
        "report_version": "2.0",
        "metrics": {},
    }

    report["metrics"]["cfg_entropy"] = collect_cfg_entropy(obfuscated_source_path, original_source_path)
    report["metrics"]["cyclomatic_complexity"] = collect_cyclomatic_complexity(obfuscated_source_path, original_source_path)
    report["metrics"]["symbolic_resistance"] = collect_symbolic_resistance(obfuscated_source_path, original_source_path)
    report["metrics"]["decompiler_resistance"] = collect_decompiler_resistance(obfuscated_source_path)
    report["metrics"]["ai_resistance"] = collect_ai_resistance(obfuscated_source_path, original_source_path)
    report["metrics"]["watermark_survivability"] = collect_watermark_survivability(obfuscated_source_path)
    report["metrics"]["protection_survivability"] = collect_protection_survivability(obfuscated_source_path)
    report["metrics"]["runtime_overhead"] = collect_runtime_overhead(unprotected_binary_path, protected_binary_path)
    report["metrics"]["binary_size_overhead"] = collect_binary_size_overhead(unprotected_binary_path, protected_binary_path)

    report["summary"] = {
        "total_metrics": len(report["metrics"]),
        "measured": sum(1 for m in report["metrics"].values() if m.get("status") == "measured"),
        "skipped": sum(1 for m in report["metrics"].values() if m.get("status") == "skipped"),
        "errors": sum(1 for m in report["metrics"].values() if m.get("status") == "error"),
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    return report
