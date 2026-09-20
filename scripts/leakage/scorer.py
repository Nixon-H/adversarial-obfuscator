"""
scorer.py

Purpose:
Computes the Semantic Leakage Index (SLI) — a weighted aggregate
of all four taxonomy level scores (variable, function, intent,
architecture). Produces a LeakageReport with per-function breakdowns
and remediation recommendations.

Architectural Role:
Top-level entry point for the semantic leakage metric. compute_sli()
is the primary function called by the build pipeline. It orchestrates
all four analyzers and combines their scores using preset weights.

Execution Context:
Called by the build pipeline after both original and obfuscated IR
modules are available. The returned LeakageReport is serialized to
build/leakage/leakage_report.json and consumed by the security
regression gates.

Dependencies:
- taxonomy (LeakageReport)
- analyzers (Variable/Function/Intent/Architecture LeakageAnalyzer)
- metrics (compute_opcode_histogram)

Security Relevance:
The SLI is a key gating metric used by security regression gates.
A high SLI indicates that the obfuscation leaks semantic information,
making the code understandable despite protection. The per-function
breakdown identifies which functions are leaking the most.

Maintenance Notes:
- The SLI weights (variable=0.2, function=0.3, intent=0.3,
  architecture=0.2) are empirically chosen. They should be reviewed
  as new obfuscation techniques are added.
- Per-function scores in _compute_per_function_scores use simple
  metrics (block count diff, return type match, param count match).
  These are coarse proxies for true per-function leakage.
"""

from __future__ import annotations
import logging
from typing import Any

from .taxonomy import LeakageReport
from .analyzers import (
    VariableLeakageAnalyzer,
    FunctionLeakageAnalyzer,
    IntentLeakageAnalyzer,
    ArchitectureLeakageAnalyzer,
)
from .metrics import compute_opcode_histogram

logger = logging.getLogger(__name__)


def compute_sli(original_ir: Any, obfuscated_ir: Any) -> LeakageReport:
    var_analyzer = VariableLeakageAnalyzer()
    func_analyzer = FunctionLeakageAnalyzer()
    intent_analyzer = IntentLeakageAnalyzer()
    arch_analyzer = ArchitectureLeakageAnalyzer()

    var_score = var_analyzer.analyze(original_ir, obfuscated_ir)
    func_score = func_analyzer.analyze(original_ir, obfuscated_ir)
    intent_score = intent_analyzer.analyze(original_ir, obfuscated_ir)
    arch_score = arch_analyzer.analyze(original_ir, obfuscated_ir)

    weights = {
        "variable": 0.2,
        "function": 0.3,
        "intent": 0.3,
        "architecture": 0.2,
    }

    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > 0.001:
        import logging as _lg
        _lg.warning(f"SLI weights sum to {weight_sum}, not 1.0. Normalizing.")
        weights = {k: v / weight_sum for k, v in weights.items()}

    overall_sli = (
        var_score.score * weights["variable"]
        + func_score.score * weights["function"]
        + intent_score.score * weights["intent"]
        + arch_score.score * weights["architecture"]
    )

    per_function_scores = _compute_per_function_scores(original_ir, obfuscated_ir)

    recommendations = _generate_recommendations(
        var_score.score,
        func_score.score,
        intent_score.score,
        arch_score.score,
    )

    return LeakageReport(
        overall_sli=round(overall_sli, 2),
        variable_leakage=var_score,
        function_leakage=func_score,
        intent_leakage=intent_score,
        architecture_leakage=arch_score,
        per_function_scores=per_function_scores,
        recommendations=recommendations,
    )


def _compute_per_function_scores(original_ir: Any, obfuscated_ir: Any) -> dict[str, dict[str, float]]:
    scores: dict[str, dict[str, float]] = {}

    if not hasattr(original_ir, "functions") or not hasattr(obfuscated_ir, "functions"):
        logger.warning(
            "original_ir or obfuscated_ir missing 'functions' attribute — "
            "returning empty per-function scores"
        )
        return scores

    orig_funcs = {f.name: f for f in original_ir.functions if hasattr(f, "name")}
    obf_funcs = {f.name: f for f in obfuscated_ir.functions if hasattr(f, "name")}
    all_names = set(orig_funcs.keys()) | set(obf_funcs.keys())
    for fname in all_names:
        fn_scores: dict[str, float] = {}
        if fname in orig_funcs and fname in obf_funcs:
            of = orig_funcs[fname]
            nf = obf_funcs[fname]

            if hasattr(of, "blocks") and hasattr(nf, "blocks"):
                fn_scores["block_count_diff"] = abs(len(of.blocks) - len(nf.blocks))
                fn_scores["block_match"] = 100.0 - fn_scores["block_count_diff"] / max(len(of.blocks), 1) * 100.0
            else:
                fn_scores["block_count_diff"] = 0.0
                fn_scores["block_match"] = 100.0
                logger.warning("Function '%s' missing 'blocks' attribute — defaulting block scores", fname)

            if hasattr(of, "return_type") and hasattr(nf, "return_type") and hasattr(of.return_type, "kind") and hasattr(nf.return_type, "kind"):
                fn_scores["return_type_match"] = 100.0 if of.return_type.kind == nf.return_type.kind else 0.0
            else:
                fn_scores["return_type_match"] = 100.0
                logger.warning("Function '%s' missing return_type or return_type.kind — defaulting return_type_match to 100", fname)

            if hasattr(of, "params") and hasattr(nf, "params"):
                fn_scores["param_count_match"] = 100.0 if len(of.params) == len(nf.params) else 0.0
            else:
                fn_scores["param_count_match"] = 100.0
                logger.warning("Function '%s' missing 'params' attribute — defaulting param_count_match to 100", fname)

        elif fname in orig_funcs:
            of = orig_funcs[fname]
            fn_scores["block_count_diff"] = len(of.blocks) if hasattr(of, "blocks") else 0
            fn_scores["block_match"] = 0.0
            fn_scores["return_type_match"] = 0.0
            fn_scores["param_count_match"] = 0.0
        else:
            nf = obf_funcs[fname]
            fn_scores["block_count_diff"] = len(nf.blocks) if hasattr(nf, "blocks") else 0
            fn_scores["block_match"] = 0.0
            fn_scores["return_type_match"] = 0.0
            fn_scores["param_count_match"] = 0.0
        scores[fname] = fn_scores
    return scores


def _generate_recommendations(
    var_leakage: float,
    func_leakage: float,
    intent_leakage: float,
    arch_leakage: float,
) -> list[str]:
    recs: list[str] = []
    if var_leakage > 50:
        recs.append("HIGH variable leakage: rename variables with opaque identifiers and strip type annotations")
        recs.append("Use `--unicode-ids` to enable Unicode variable renaming")
        recs.append("Consider MBA substitution to break type inference")
    if func_leakage > 50:
        recs.append("HIGH function leakage: merge trivial functions, split complex ones, add opaque dispatchers")
        recs.append("Enable `--function-intent` to obfuscate function boundaries")
        recs.append("Consider CFG flattening to break function boundary recovery")
    if intent_leakage > 50:
        recs.append("HIGH intent leakage: apply CFG flattening, opaque predicates, and bogus control flow")
        recs.append("Use `--cfg-flatten` to flatten control flow")
        recs.append("Enable `--bogus-exceptions` to insert misleading paths")
    if arch_leakage > 50:
        recs.append("HIGH architecture leakage: inject decoy functions, restructure call graph")
        recs.append("Use `--honey-functions` to inject decoy functions")
        recs.append("Enable `--adversarial-injection` for misleading call graphs")
    if not recs:
        recs.append("Low semantic leakage across all levels. Current obfuscation is effective.")
    return recs
