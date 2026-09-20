"""
analyzers.py

Purpose:
Four hierarchical leakage analyzers (Variable, Function, Intent,
Architecture) that compute LeakageScore instances by comparing
original and obfuscated IR modules.

Architectural Role:
Analysis layer of the semantic leakage metric. Each analyzer
focuses on one taxonomy level and combines multiple sub-metrics
into a single score. The scores are aggregated by compute_sli().

Execution Context:
Each analyzer's analyze() method is called by scorer.compute_sli()
with original and obfuscated IR modules. The results are weighted
and combined into the overall SLI.

Dependencies:
- taxonomy (LeakageLevel, LeakageScore)
- metrics (compute_cfg_similarity, compute_opcode_histogram, etc.)
- Standard library (typing, collections.Counter)

Security Relevance:
Each analyzer detects a different class of obfuscation failure:
- Variable: renaming and type-hiding failures
- Function: boundary-hiding and signature-preservation failures
- Intent: algorithm recovery from opcode/CFG patterns
- Architecture: call-graph and module-structure recovery

Maintenance Notes:
- The VariableLeakageAnalyzer maps functions by name (obf_funcs[fname]).
  If function names are obfuscated, the mapping will be incomplete
  and the leakage score will be artificially lower.
- The _build_cfg method in IntentLeakageAnalyzer uses a simplified
  CFG model that may miss indirect jumps and computed branches.
"""

from __future__ import annotations
from typing import Any
from collections import Counter

from .taxonomy import LeakageLevel, LeakageScore
from .metrics import (
    compute_cfg_similarity,
    compute_opcode_histogram,
    compute_entropy,
    compute_name_preservation,
    compute_call_graph_similarity,
)


class VariableLeakageAnalyzer:
    """
    Measures variable-level semantic leakage.

    Compares name preservation, parameter name preservation, and
    type preservation between original and obfuscated IR. High
    scores indicate that the renaming and type-hiding obfuscation
    is insufficient.
    """

    def analyze(self, original_ir: Any, obfuscated_ir: Any) -> LeakageScore:
        if not hasattr(original_ir, 'functions') or not hasattr(obfuscated_ir, 'functions'):
            return LeakageScore(
                level=LeakageLevel.VARIABLE,
                score=0.0,
                method="static_analysis",
                confidence=0.0,
                evidence={"error": "IR missing .functions attribute", "inconclusive": True},
            )
        name_preservation = compute_name_preservation(original_ir, obfuscated_ir)
        orig_funcs = {f.name: f for f in original_ir.functions}
        obf_funcs = {f.name: f for f in obfuscated_ir.functions}
        param_preserved = 0
        param_total = 0
        type_preserved = 0
        type_total = 0
        for fname, ofunc in obf_funcs.items():
            if fname in orig_funcs:
                ofunc_orig = orig_funcs[fname]
                for (oname, otype), (pname, ptype) in zip(ofunc_orig.params, ofunc.params):
                    param_total += 1
                    if oname == pname:
                        param_preserved += 1
                    type_total += 1
                    if otype.kind == ptype.kind and otype.size == ptype.size:
                        type_preserved += 1
        param_leakage = (param_preserved / max(param_total, 1)) * 100.0
        type_leakage = (type_preserved / max(type_total, 1)) * 100.0
        score = name_preservation * 0.5 + param_leakage * 0.3 + type_leakage * 0.2
        return LeakageScore(
            level=LeakageLevel.VARIABLE,
            score=round(score, 2),
            method="static_analysis",
            confidence=0.9 if param_total > 0 else 0.5,
            evidence={
                "name_preservation": round(name_preservation, 2),
                "param_name_preservation": round(param_leakage, 2),
                "type_preservation": round(type_leakage, 2),
                "param_count": param_total,
                "type_count": type_total,
            },
        )


class FunctionLeakageAnalyzer:
    """
    Measures function-level semantic leakage.

    Compares function count, name overlap (Jaccard), and return-type
    signature preservation. High scores indicate that function
    boundaries and signatures are too easily recovered.
    """

    def analyze(self, original_ir: Any, obfuscated_ir: Any) -> LeakageScore:
        if not hasattr(original_ir, 'functions') or not hasattr(obfuscated_ir, 'functions'):
            return LeakageScore(
                level=LeakageLevel.FUNCTION,
                score=0.0,
                method="static_analysis",
                confidence=0.0,
                evidence={"error": "IR missing .functions attribute", "inconclusive": True},
            )
        orig_funcs = {f.name: f for f in original_ir.functions}
        obf_funcs = {f.name: f for f in obfuscated_ir.functions}
        orig_set = set(orig_funcs.keys())
        obf_set = set(obf_funcs.keys())
        intersection = orig_set & obf_set
        name_jaccard = len(intersection) / max(len(orig_set | obf_set), 1)
        count_match = 1.0 - abs(len(orig_funcs) - len(obf_funcs)) / max(len(orig_funcs), 1)
        sig_match = 0.0
        sig_total = 0
        for fname in intersection:
            of = orig_funcs[fname]
            nf = obf_funcs[fname]
            sig_total += 1
            if of.return_type.kind == nf.return_type.kind:
                sig_match += 1.0
            else:
                sig_match += 0.0
        signature_score = sig_match / max(sig_total, 1) if sig_total > 0 else 0.0
        similarity = count_match * 0.3 + name_jaccard * 0.4 + signature_score * 0.3
        leakage = similarity * 100.0
        return LeakageScore(
            level=LeakageLevel.FUNCTION,
            score=round(leakage, 2),
            method="structural",
            confidence=0.85 if sig_total > 0 else 0.4,
            evidence={
                "function_count_original": len(orig_funcs),
                "function_count_obfuscated": len(obf_funcs),
                "matched_functions": len(intersection),
                "name_jaccard": round(name_jaccard, 4),
                "count_match": round(count_match, 4),
                "signature_score": round(signature_score, 4),
            },
        )


class IntentLeakageAnalyzer:
    """
    Measures intent-level semantic leakage.

    Compares opcode histogram similarity, CFG similarity, and
    entropy difference between original and obfuscated IR. High
    scores suggest an attacker can infer the original algorithm
    despite obfuscation.
    """

    def analyze(self, original_ir: Any, obfuscated_ir: Any) -> LeakageScore:
        if not hasattr(original_ir, 'functions') or not hasattr(obfuscated_ir, 'functions'):
            return LeakageScore(
                level=LeakageLevel.INTENT,
                score=0.0,
                method="static_analysis",
                confidence=0.0,
                evidence={"error": "IR missing .functions attribute", "inconclusive": True},
            )
        orig_hist = compute_opcode_histogram(original_ir)
        obf_hist = compute_opcode_histogram(obfuscated_ir)
        all_ops = set(orig_hist.keys()) | set(obf_hist.keys())
        if not all_ops:
            return LeakageScore(
                level=LeakageLevel.INTENT,
                score=0.0,
                method="static_analysis",
                confidence=0.2,
                evidence={"opcode_histogram_similarity": 0, "cfg_similarity": 0, "entropy_diff": 0},
            )
        hist_diff = 0.0
        for op in all_ops:
            a = orig_hist.get(op, 0.0)
            b = obf_hist.get(op, 0.0)
            hist_diff += abs(a - b)
        hist_similarity = max(0.0, 1.0 - hist_diff / 2.0)
        cfg_a = self._build_cfg(original_ir)
        cfg_b = self._build_cfg(obfuscated_ir)
        cfg_sim = compute_cfg_similarity(cfg_a, cfg_b) / 100.0
        orig_ent = compute_entropy(original_ir)
        obf_ent = compute_entropy(obfuscated_ir)
        max_ent = max(orig_ent, obf_ent, 1)
        ent_similarity = max(0.0, 1.0 - abs(orig_ent - obf_ent) / max_ent)
        similarity = hist_similarity * 0.4 + cfg_sim * 0.35 + ent_similarity * 0.25
        leakage = similarity * 100.0
        return LeakageScore(
            level=LeakageLevel.INTENT,
            score=round(leakage, 2),
            method="structural",
            confidence=0.75,
            evidence={
                "opcode_histogram_similarity": round(hist_similarity, 4),
                "cfg_similarity": round(cfg_sim, 4),
                "entropy_similarity": round(ent_similarity, 4),
                "original_entropy": round(orig_ent, 4),
                "obfuscated_entropy": round(obf_ent, 4),
            },
        )

    def _build_cfg(self, ir_module: Any) -> dict[str, list[str]]:
        """
        Build a simplified CFG from an IR module for comparison.

        Maps each basic block (qualified as function::label) to its
        successor blocks based on terminator opcodes (jmp, br).
        """
        cfg: dict[str, list[str]] = {}
        for func in ir_module.functions:
            for block in func.blocks:
                qualified = f"{func.name}::{block.label}"
                if block.terminator:
                    op = block.terminator.opcode
                    if op == "jmp" and block.terminator.operands:
                        target = f"{func.name}::{block.terminator.operands[0]}"
                        cfg.setdefault(qualified, []).append(target)
                    elif op == "br" and len(block.terminator.operands or []) >= 3:
                        t1 = f"{func.name}::{block.terminator.operands[1]}"
                        t2 = f"{func.name}::{block.terminator.operands[2]}"
                        cfg.setdefault(qualified, []).append(t1)
                        cfg.setdefault(qualified, []).append(t2)
                cfg.setdefault(qualified, [])
        return cfg


class ArchitectureLeakageAnalyzer:
    """
    Measures architecture-level semantic leakage.

    Compares call graph similarity, module structure (function count,
    block counts, return types), and data dependency patterns. High
    scores indicate the high-level program architecture is recoverable.
    """

    def analyze(self, original_ir: Any, obfuscated_ir: Any) -> LeakageScore:
        if not hasattr(original_ir, 'functions') or not hasattr(obfuscated_ir, 'functions'):
            return LeakageScore(
                level=LeakageLevel.ARCHITECTURE,
                score=0.0,
                method="static_analysis",
                confidence=0.0,
                evidence={"error": "IR missing .functions attribute", "inconclusive": True},
            )
        calls_a = self._extract_call_graph(original_ir)
        calls_b = self._extract_call_graph(obfuscated_ir)
        call_sim = compute_call_graph_similarity(calls_a, calls_b) / 100.0
        mod_a = self._module_structure(original_ir)
        mod_b = self._module_structure(obfuscated_ir)
        struct_sim = self._structure_similarity(mod_a, mod_b)
        data_sim = self._data_dependency_similarity(original_ir, obfuscated_ir)
        similarity = call_sim * 0.4 + struct_sim * 0.35 + data_sim * 0.25
        leakage = similarity * 100.0
        return LeakageScore(
            level=LeakageLevel.ARCHITECTURE,
            score=round(leakage, 2),
            method="structural",
            confidence=0.7,
            evidence={
                "call_graph_similarity": round(call_sim, 4),
                "structure_similarity": round(struct_sim, 4),
                "data_dependency_similarity": round(data_sim, 4),
            },
        )

    def _extract_call_graph(self, ir_module: Any) -> dict[str, list[str]]:
        """Extract a function -> [called_functions] map from IR."""
        calls: dict[str, list[str]] = {}
        for func in ir_module.functions:
            targets = []
            for block in func.blocks:
                for inst in block.instructions:
                    if inst.opcode == "call" and inst.func_name:
                        targets.append(inst.func_name)
                if block.terminator and block.terminator.opcode == "call" and block.terminator.func_name:
                    targets.append(block.terminator.func_name)
            calls[func.name] = targets
        return calls

    def _module_structure(self, ir_module: Any) -> dict[str, Any]:
        return {
            "function_count": len(ir_module.functions),
            "block_counts": {f.name: len(f.blocks) for f in ir_module.functions},
            "return_types": {f.name: f.return_type.kind for f in ir_module.functions},
        }

    def _structure_similarity(self, a: dict[str, Any], b: dict[str, Any]) -> float:
        if a["function_count"] == 0 and b["function_count"] == 0:
            return 1.0
        count_sim = 1.0 - abs(a["function_count"] - b["function_count"]) / max(a["function_count"], b["function_count"], 1)
        all_funcs = set(a["block_counts"].keys()) | set(b["block_counts"].keys())
        if not all_funcs:
            return count_sim
        block_sim = 0.0
        type_sim = 0.0
        total = 0
        for fname in all_funcs:
            bc_a = a["block_counts"].get(fname, 0)
            bc_b = b["block_counts"].get(fname, 0)
            max_bc = max(bc_a, bc_b, 1)
            block_sim += 1.0 - abs(bc_a - bc_b) / max_bc
            rt_a = a["return_types"].get(fname, "void")
            rt_b = b["return_types"].get(fname, "void")
            type_sim += 1.0 if rt_a == rt_b else 0.0
            total += 1
        block_sim /= max(total, 1)
        type_sim /= max(total, 1)
        return count_sim * 0.2 + block_sim * 0.4 + type_sim * 0.4

    def _data_dependency_similarity(self, original_ir: Any, obfuscated_ir: Any) -> float:
        def extract_stores(ir: Any) -> set[str]:
            deps: set[str] = set()
            for func in ir.functions:
                for block in func.blocks:
                    for inst in block.instructions:
                        if inst.opcode in ("store", "load") and inst.operands:
                            for op in inst.operands:
                                if hasattr(op, "name") and op.name.startswith("%"):
                                    deps.add(op.name)
            return deps
        stores_a = extract_stores(original_ir)
        stores_b = extract_stores(obfuscated_ir)
        if not stores_a and not stores_b:
            return 1.0
        intersection = stores_a & stores_b
        return len(intersection) / max(len(stores_a | stores_b), 1)
