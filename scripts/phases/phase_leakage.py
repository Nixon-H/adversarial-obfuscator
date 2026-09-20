"""
phase_leakage.py

Purpose:
Computes the Semantic Leakage Index (SLI) between original and obfuscated
IR — measuring how much semantic information (variable intent, function
purpose, architecture hints) leaks through the obfuscation.

Architectural Role:
Measurement/audit phase — quantifies the effectiveness of obfuscation
at the semantic level.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, time, typing, ..common, ..leakage.*

Security Relevance:
Semantic leakage is a more meaningful metric than decompilation resistance —
it measures whether a human analyst could understand what the code does.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from ..common import log, BUILD_DIR
from ..leakage.taxonomy import LeakageReport
from ..leakage.scorer import compute_sli


def phase_leakage(args, original_ir: Any, obfuscated_ir: Any) -> LeakageReport | None:
    """Compute Semantic Leakage Index between original and obfuscated IR.

    Args:
        args: argparse namespace with .semantic_leakage flag
        original_ir: IrModule from compile_py_to_ir on original source
        obfuscated_ir: IrModule from compile_py_to_ir on obfuscated source

    Returns:
        LeakageReport with SLI and per-level scores, or None if disabled.
    """
    if not getattr(args, "semantic_leakage", False):
        return None

    log("LEAKAGE", "Computing Semantic Leakage Index...")

    start = time.time()
    report = compute_sli(original_ir, obfuscated_ir)
    elapsed = time.time() - start

    log("LEAKAGE", f"  SLI: {report.overall_sli:.2f}/100")
    log("LEAKAGE", f"  Variable Leakage:   {report.variable_leakage.score:.2f}")
    log("LEAKAGE", f"  Function Leakage:   {report.function_leakage.score:.2f}")
    log("LEAKAGE", f"  Intent Leakage:     {report.intent_leakage.score:.2f}")
    log("LEAKAGE", f"  Architecture Leakage: {report.architecture_leakage.score:.2f}")
    log("LEAKAGE", f"  Computed in {elapsed*1000:.1f}ms")

    leakage_dir = os.path.join(BUILD_DIR, "leakage")
    os.makedirs(leakage_dir, exist_ok=True)

    report_path = os.path.join(leakage_dir, "leakage_report.json")
    with open(report_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2)
    log("LEAKAGE", f"Report written to {report_path}")

    per_func_path = os.path.join(leakage_dir, "per_function_leakage.json")
    with open(per_func_path, "w") as f:
        json.dump(report.per_function_scores, f, indent=2)
    log("LEAKAGE", f"Per-function breakdown written to {per_func_path}")

    for rec in report.recommendations:
        log("LEAKAGE", f"  Recommendation: {rec}")

    return report
