"""
resilience.py

Purpose:
Quantitative obfuscation resilience metrics. Measures how well protected code
resists static analysis, symbolic execution, and reverse engineering across
six orthogonal dimensions: CFG entropy, cyclomatic complexity, instruction
diversity, dead-code injection, symbolic-execution resistance (Z3), and
static-analyser confusion.

Architectural Role:
One of three metric families (resilience, context_saturation, prompt_resistance).
Provides both standalone computation functions (compute_*) and the
ResilienceMetrics class that orchestrates a full measurement run.

Execution Context:
Called by build.py when --metrics or --min-resilience flags are set.
Also used by evaluation scripts (cost model, survivability index).

Dependencies:
- ast: Python AST parsing/walking
- z3: SMT solver for symbolic-resistance measurement
- json, math, os, subprocess, tempfile, time, collections: standard library
"""
import ast
import json
import math
import os
import subprocess
import logging
import sys
import tempfile
import time
from collections import defaultdict, Counter

import z3

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _count_blocks_and_edges(tree):
    """
    _count_blocks_and_edges

    Purpose:
    Walk an AST and count basic blocks, control-flow edges, and edge-type
    frequencies. Used as input to CFG entropy computation.

    Inputs:
    - tree (ast.AST): parsed Python AST

    Outputs:
    - tuple (block_count, edges_list, edge_type_counter)
    """
    blocks = []
    edges = []
    edge_types = Counter()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            blocks.append(node)
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.If):
                    blocks.append(child)
                    edges.append(("branch",))
                    edge_types["branch"] += 1
                elif isinstance(child, (ast.For, ast.While)):
                    blocks.append(child)
                    edges.append(("loop",))
                    edge_types["loop"] += 1
                elif isinstance(child, ast.Try):
                    blocks.append(child)
                    edges.append(("try",))
                    edge_types["try"] += 1
                elif isinstance(child, ast.With):
                    blocks.append(child)
            edges.append(("sequential",))
            edge_types["sequential"] += 1

    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            edges.append(("return",))
            edge_types["return"] += 1
        if isinstance(node, ast.Raise):
            edges.append(("raise",))
            edge_types["raise"] += 1
        if isinstance(node, ast.Call):
            edges.append(("call",))
            edge_types["call"] += 1

    return len(blocks), edges, edge_types


def _edge_entropy(edge_types):
    """
    _edge_entropy

    Purpose:
    Compute Shannon entropy of the edge-type distribution. Higher entropy
    means more varied control flow, which is harder for static analysis.

    Inputs:
    - edge_types (Counter): edge-type frequencies

    Outputs:
    - float: entropy in bits (0.0 if no edges)
    """
    total = sum(edge_types.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in edge_types.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


def compute_cfg_entropy(original_ast, protected_ast):
    """
    compute_cfg_entropy

    Purpose:
    Compare CFG edge-entropy between original and protected ASTs. A ratio > 1
    indicates the protected version has more varied control flow.

    Inputs:
    - original_ast (ast.AST): parsed original source
    - protected_ast (ast.AST): parsed obfuscated source

    Outputs:
    - dict: original/protected entropy values, ratio, block counts, edge types
    """
    orig_blocks, _, orig_edge_types = _count_blocks_and_edges(original_ast)
    prot_blocks, _, prot_edge_types = _count_blocks_and_edges(protected_ast)
    orig_entropy = _edge_entropy(orig_edge_types)
    prot_entropy = _edge_entropy(prot_edge_types)
    ratio = prot_entropy / orig_entropy if orig_entropy > 0 else 1.0
    return {
        "original_entropy": round(orig_entropy, 4),
        "protected_entropy": round(prot_entropy, 4),
        "entropy_ratio": round(ratio, 4),
        "original_blocks": orig_blocks,
        "protected_blocks": prot_blocks,
        "original_edge_types": dict(orig_edge_types),
        "protected_edge_types": dict(prot_edge_types),
    }


def _cfg_edges_nodes(tree):
    """
    _cfg_edges_nodes

    Purpose:
    Count edges and nodes in the CFG for cyclomatic complexity calculation.

    Inputs:
    - tree (ast.AST): parsed AST

    Outputs:
    - tuple (edge_count, node_count)
    """
    blocks = set()
    edges = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            blocks.add(id(node))
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                    blocks.add(id(child))
                    edges += 1
            edges += 1

    for node in ast.walk(tree):
        if isinstance(node, (ast.Return, ast.Raise, ast.Call)):
            edges += 1
        if isinstance(node, ast.Break):
            edges += 1
        if isinstance(node, ast.Continue):
            edges += 1

    return edges, len(blocks)


def compute_cyclomatic(original_ast, protected_ast):
    """
    compute_cyclomatic

    Purpose:
    Compute McCabe cyclomatic complexity for original and protected ASTs.
    The ratio shows how much control-flow complexity was added by obfuscation.

    Inputs:
    - original_ast (ast.AST): parsed original source
    - protected_ast (ast.AST): parsed obfuscated source

    Outputs:
    - dict: original/protected complexity, ratio
    """
    orig_edges, orig_nodes = _cfg_edges_nodes(original_ast)
    prot_edges, prot_nodes = _cfg_edges_nodes(protected_ast)

    orig_funcs = sum(1 for _ in ast.walk(original_ast) if isinstance(_, ast.FunctionDef))
    prot_funcs = sum(1 for _ in ast.walk(protected_ast) if isinstance(_, ast.FunctionDef))

    orig_m = orig_edges - orig_nodes + 2 * max(orig_funcs, 1)
    prot_m = prot_edges - prot_nodes + 2 * max(prot_funcs, 1)
    ratio = prot_m / orig_m if orig_m > 0 else 1.0

    return {
        "original_complexity": orig_m,
        "protected_complexity": prot_m,
        "complexity_ratio": round(ratio, 4),
    }


def compute_instruction_diversity(original_ast, protected_ast):
    """
    compute_instruction_diversity

    Purpose:
    Count distinct AST node types as a proxy for instruction-set diversity.
    Higher diversity suggests the obfuscator introduced varied constructs.

    Inputs:
    - original_ast (ast.AST): parsed original source
    - protected_ast (ast.AST): parsed obfuscated source

    Outputs:
    - dict: original/protected diversity, ratio, top-20 type distributions
    """
    def count_types(node):
        types = Counter()
        for n in ast.walk(node):
            types[type(n).__name__] += 1
        return types

    orig_types = count_types(original_ast)
    prot_types = count_types(protected_ast)

    return {
        "original_diversity": len(orig_types),
        "protected_diversity": len(prot_types),
        "diversity_ratio": round(len(prot_types) / max(len(orig_types), 1), 4),
        "original_types": dict(orig_types.most_common(20)),
        "protected_types": dict(prot_types.most_common(20)),
    }


def _find_honey_functions(tree):
    """
    _find_honey_functions

    Purpose:
    Count functions whose names match known honey/dead/fake function prefixes.
    These are deliberately injected to mislead reverse engineers.

    Inputs:
    - tree (ast.AST): parsed AST

    Outputs:
    - int: count of honey functions
    """
    honey_count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            name_lower = node.name.lower()
            if any(kw in name_lower for kw in ("honey", "dead", "fake", "decoy", "junk", "nx_")):
                honey_count += 1
    return honey_count


def _count_unreachable_blocks(tree):
    """
    _count_unreachable_blocks

    Purpose:
    Identify obviously unreachable blocks — constant-false if conditions and
    opaque predicates that always evaluate to False.

    Inputs:
    - tree (ast.AST): parsed AST

    Outputs:
    - int: count of unreachable blocks
    """
    unreachable = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            if isinstance(node.test, ast.Compare):
                try:
                    if isinstance(node.test.left, ast.Constant) and isinstance(node.test.comparators[0], ast.Constant):
                        if isinstance(node.test.left.value, (int, bool)) and isinstance(node.test.comparators[0].value, (int, bool)):
                            if node.test.left.value != node.test.comparators[0].value:
                                unreachable += 1
                except (IndexError, AttributeError):
                    pass
            if isinstance(node.test, ast.Constant) and not node.test.value:
                unreachable += 1
    return unreachable


def compute_dead_code(original_ast, protected_ast):
    """
    compute_dead_code

    Purpose:
    Measure dead-code injection: honey functions, unreachable blocks, and
    overall dead-code percentage before and after obfuscation.

    Inputs:
    - original_ast (ast.AST): parsed original source
    - protected_ast (ast.AST): parsed obfuscated source

    Outputs:
    - dict: dead-code percentages, honey function counts, deltas
    """
    orig_honey = _find_honey_functions(original_ast)
    prot_honey = _find_honey_functions(protected_ast)

    orig_unreachable = _count_unreachable_blocks(original_ast)
    prot_unreachable = _count_unreachable_blocks(protected_ast)

    orig_total_stmts = sum(1 for _ in ast.walk(original_ast))
    prot_total_stmts = sum(1 for _ in ast.walk(protected_ast))

    orig_dead_pct = round((orig_unreachable / max(orig_total_stmts, 1)) * 100, 2)
    prot_dead_pct = round((prot_unreachable / max(prot_total_stmts, 1)) * 100, 2)

    return {
        "original_dead_code_pct": orig_dead_pct,
        "protected_dead_code_pct": prot_dead_pct,
        "dead_code_increase_pct": round(prot_dead_pct - orig_dead_pct, 2),
        "original_honey_function_count": orig_honey,
        "protected_honey_function_count": prot_honey,
        "honey_function_increase": prot_honey - orig_honey,
    }


def _indirect_call_count(tree):
    """
    _indirect_call_count

    Purpose:
    Count calls via non-name expressions (attributes, subscripts, etc.),
    which are harder for static analysis to resolve.

    Inputs:
    - tree (ast.AST): parsed AST

    Outputs:
    - int: count of indirect calls
    """
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                count += 1
    return count


def _opaque_predicate_count(tree):
    """
    _opaque_predicate_count

    Purpose:
    Count if-statements whose test expressions have high nesting depth,
    a heuristic for opaque predicates.

    Inputs:
    - tree (ast.AST): parsed AST

    Outputs:
    - int: count of high-depth predicates
    """
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            depth = _expr_depth(node.test)
            if depth > 5:
                count += 1
    return count


def _expr_depth(node, depth=0):
    """
    _expr_depth

    Purpose:
    Recursively compute maximum nesting depth of an AST expression node.

    Inputs:
    - node (ast.AST): expression node
    - depth (int): current recursion depth

    Outputs:
    - int: maximum depth of this expression subtree
    """
    if depth > 50:
        return depth
    max_child = 0
    for child in ast.iter_child_nodes(node):
        child_depth = _expr_depth(child, depth + 1)
        max_child = max(max_child, child_depth)
    return depth + max_child


def _mba_depth(tree):
    """
    _mba_depth

    Purpose:
    Find the maximum expression depth among all BinaryOp nodes,
    approximating the complexity of MBA (Mixed Boolean-Arithmetic) substitutions.

    Inputs:
    - tree (ast.AST): parsed AST

    Outputs:
    - int: maximum BinOp expression depth
    """
    max_depth = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp):
            d = _expr_depth(node)
            max_depth = max(max_depth, d)
    return max_depth


def _recursion_depth(tree):
    """
    _recursion_depth

    Purpose:
    Estimate the maximum recursion depth of self-recursive functions.
    Used as a proxy for symbolic-execution path explosion difficulty.

    Inputs:
    - tree (ast.AST): parsed AST

    Outputs:
    - int: estimated recursion depth
    """
    max_depth = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            calls_self = any(
                isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == node.name
                for c in ast.walk(node)
            )
            if calls_self:
                d = 0
                for c in ast.walk(node):
                    if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == node.name:
                        parent = c
                        while hasattr(parent, 'parent'):
                            parent = parent.parent
                            d += 1
                max_depth = max(max_depth, d + 1)
    return max_depth


def _loop_bound_estimate(tree):
    """
    _loop_bound_estimate

    Purpose:
    Estimate a coarse upper bound on loop iterations across the AST.
    Used as one factor in symbolic-resistance scoring.

    Inputs:
    - tree (ast.AST): parsed AST

    Outputs:
    - int: total estimated loop iterations
    """
    total_bound = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name):
                if node.iter.func.id == "range":
                    if node.iter.args:
                        arg = node.iter.args[0]
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                            total_bound += arg.value
                        else:
                            total_bound += 10
                    else:
                        total_bound += 10
        elif isinstance(node, ast.While):
            total_bound += 100
    return total_bound


def _z3_solver_time(tree, timeout_ms=5000):
    """
    _z3_solver_time

    Purpose:
    Encode an AST as an SMT formula and measure Z3 solver time + constraint
    count. This is a direct proxy for symbolic-execution difficulty.

    Inputs:
    - tree (ast.AST): parsed AST
    - timeout_ms (int): Z3 solver timeout in ms

    Outputs:
    - dict: solver_time_ms, solver_result, constraint_count, num_vars
    """
    try:
        from scripts.validation.ast_to_smt import ASTToSMT, ast_to_smt_formula
        source = ast.unparse(tree)
        formula, translator = ast_to_smt_formula(source)
        output = translator.get_output_var()

        solver = z3.Solver()
        solver.set("timeout", timeout_ms)
        if formula is not None:
            solver.add(formula)

        start = time.time()
        result = solver.check()
        elapsed = (time.time() - start) * 1000

        constraint_count = len(solver.assertions()) if hasattr(solver, 'assertions') else 0
        return {
            "solver_time_ms": round(elapsed, 2),
            "solver_result": str(result),
            "constraint_count": constraint_count,
            "num_vars": len(translator.get_input_vars()) if hasattr(translator, 'get_input_vars') else 0,
        }
    except Exception as e:
        return {
            "solver_time_ms": 0.0,
            "solver_result": "error",
            "constraint_count": 0,
            "num_vars": 0,
            "error": str(e),
        }


def compute_symbolic_resistance(original_ast, protected_ast):
    """
    compute_symbolic_resistance

    Purpose:
    Compute a blended symbolic-execution resistance score from heuristic
    metrics (indirect jumps, opaque predicates, MBA depth, recursion, loop
    bounds) and Z3 solver timing. The blended score ranges 0.0–1.0.

    Inputs:
    - original_ast (ast.AST): parsed original source
    - protected_ast (ast.AST): parsed obfuscated source

    Outputs:
    - dict: various sub-metrics plus resistance_score, z3_resistance_score,
      blended_resistance_score
    """
    orig_indirect = _indirect_call_count(original_ast)
    prot_indirect = _indirect_call_count(protected_ast)

    orig_opaque = _opaque_predicate_count(original_ast)
    prot_opaque = _opaque_predicate_count(protected_ast)

    orig_mba = _mba_depth(original_ast)
    prot_mba = _mba_depth(protected_ast)

    orig_recursion = _recursion_depth(original_ast)
    prot_recursion = _recursion_depth(protected_ast)

    orig_loop_bound = _loop_bound_estimate(original_ast)
    prot_loop_bound = _loop_bound_estimate(protected_ast)

    prot_feasible_paths = (
        prot_indirect * 3 +
        prot_opaque * 5 +
        prot_mba * 2 +
        prot_recursion * 10 +
        min(prot_loop_bound, 1000)
    )
    orig_feasible_paths = max(
        orig_indirect * 3 +
        orig_opaque * 5 +
        orig_mba * 2 +
        orig_recursion * 10 +
        min(orig_loop_bound, 1000),
        1,
    )

    resistance_score = min(1.0, prot_feasible_paths / (prot_feasible_paths + orig_feasible_paths))

    orig_z3 = _z3_solver_time(original_ast)
    prot_z3 = _z3_solver_time(protected_ast)

    z3_resistance = 0.0
    if prot_z3["solver_time_ms"] > 0 and orig_z3["solver_time_ms"] >= 0:
        z3_resistance = min(1.0, prot_z3["solver_time_ms"] / max(prot_z3["solver_time_ms"] + orig_z3["solver_time_ms"], 1))

    if "error" not in orig_z3 and "error" not in prot_z3:
        blended_score = (resistance_score * 0.4) + (z3_resistance * 0.6)
    else:
        blended_score = resistance_score

    return {
        "original_indirect_jumps": orig_indirect,
        "protected_indirect_jumps": prot_indirect,
        "original_opaque_predicates": orig_opaque,
        "protected_opaque_predicates": prot_opaque,
        "original_mba_depth": orig_mba,
        "protected_mba_depth": prot_mba,
        "original_recursion_depth": orig_recursion,
        "protected_recursion_depth": prot_recursion,
        "original_loop_bound_estimate": orig_loop_bound,
        "protected_loop_bound_estimate": prot_loop_bound,
        "original_feasible_paths": orig_feasible_paths,
        "protected_feasible_paths": prot_feasible_paths,
        "resistance_score": round(resistance_score, 4),
        "z3_original_solver_time_ms": orig_z3["solver_time_ms"],
        "z3_protected_solver_time_ms": prot_z3["solver_time_ms"],
        "z3_original_constraints": orig_z3["constraint_count"],
        "z3_protected_constraints": prot_z3["constraint_count"],
        "z3_resistance_score": round(z3_resistance, 4),
        "blended_resistance_score": round(blended_score, 4),
    }


def compute_static_confusion(original_ast, protected_ast):
    """
    compute_static_confusion

    Purpose:
    Run static analysers (pyflakes, pylint, mypy) on the protected code and
    count false-positive warnings. A higher warning count means the obfuscated
    code confuses static analysis tools more effectively.

    Inputs:
    - original_ast (ast.AST): parsed original source (unused directly, kept
      for API consistency)
    - protected_ast (ast.AST): parsed obfuscated source

    Outputs:
    - dict: false_positives, warnings, analysis_confusion_score (0.0–1.0)
    """
    false_positives = 0
    warnings = 0

    for tool in ("pyflakes", "pylint", "mypy"):
        if shutil_which(tool):
            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                    f.write(ast.unparse(protected_ast))
                    tmp_path = f.name

                if tool == "pyflakes":
                    result = subprocess.run(
                        [sys.executable, "-m", "pyflakes", tmp_path],
                        capture_output=True, text=True, timeout=30,
                    )
                    stderr_lines = result.stderr.strip().split("\n") if result.stderr.strip() else []
                    stdout_lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
                    all_lines = [l for l in stderr_lines + stdout_lines if l.strip()]
                    warnings += len(all_lines)
                elif tool == "pylint":
                    result = subprocess.run(
                        [sys.executable, "-m", "pylint", "--score=n", tmp_path],
                        capture_output=True, text=True, timeout=30,
                    )
                    for line in result.stdout.split("\n"):
                        if "warning" in line.lower() or "error" in line.lower():
                            warnings += 1
                elif tool == "mypy":
                    result = subprocess.run(
                        [sys.executable, "-m", "mypy", tmp_path],
                        capture_output=True, text=True, timeout=30,
                    )
                    for line in result.stdout.split("\n"):
                        if "error" in line.lower():
                            warnings += 1

                os.unlink(tmp_path)
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
                logging.warning(f"Static analysis tool {tool} failed: {e}")

    analysis_confusion_score = min(1.0, warnings / 20.0) if warnings else 0.0

    return {
        "false_positives": false_positives,
        "warnings": warnings,
        "analysis_confusion_score": round(analysis_confusion_score, 4),
    }


def shutil_which(cmd):
    """
    shutil_which

    Purpose:
    Thin wrapper around shutil.which to avoid import shadowing in the
    _z3_solver_time closure.

    Inputs:
    - cmd (str): command name to locate

    Outputs:
    - str | None: full path or None
    """
    import shutil
    return shutil.which(cmd)


class ResilienceMetrics:
    """
    ResilienceMetrics

    Purpose:
    Orchestrates a full resilience measurement run: reads original and
    protected source, parses both ASTs, runs all six metric computations,
    and produces a weighted overall resilience score.

    Lifecycle:
    Created on demand in build.py when --metrics or --min-resilience is set.
    One-shot: call measure() then read .metrics dict or call to_json().

    State:
    - metrics (dict): latest measurement results, populated by measure()

    Security:
    The overall score is a configurable weighted sum; flag --min-resilience
    can trigger re-obfuscation loops to raise it.
    """
    def __init__(self):
        self.metrics = {}

    def measure(self, original_path, protected_path):
        """
        measure

        Purpose:
        Run all six resilience metrics on a pair of source files.

        Inputs:
        - original_path (str): path to original (unobfuscated) source
        - protected_path (str): path to obfuscated source

        Outputs:
        - dict: complete metrics dictionary including "overall" score
        """
        with open(original_path, encoding="utf-8") as f:
            original_source = f.read()
        with open(protected_path, encoding="utf-8") as f:
            protected_source = f.read()

        original_ast = ast.parse(original_source)
        protected_ast = ast.parse(protected_source)

        results = {
            "cfg_entropy": compute_cfg_entropy(original_ast, protected_ast),
            "cyclomatic_complexity": compute_cyclomatic(original_ast, protected_ast),
            "instruction_diversity": compute_instruction_diversity(original_ast, protected_ast),
            "dead_code": compute_dead_code(original_ast, protected_ast),
            "symbolic_resistance": compute_symbolic_resistance(original_ast, protected_ast),
            "static_confusion": compute_static_confusion(original_ast, protected_ast),
        }

        results["overall"] = self._compute_overall(results)
        self.metrics = results
        return results

    def _compute_overall(self, results):
        """
        _compute_overall

        Purpose:
        Weighted sum of the six metric sub-scores into a single 0.0–1.0
        overall resilience score.

        Inputs:
        - results (dict): per-metric dictionaries

        Outputs:
        - float: overall score
        """
        scores = [
            results["cfg_entropy"]["entropy_ratio"] * 0.20,
            min(results["cyclomatic_complexity"]["complexity_ratio"] / 5, 1.0) * 0.15,
            results["instruction_diversity"]["diversity_ratio"] * 0.15,
            min(results["dead_code"]["dead_code_increase_pct"] / 50, 1.0) * 0.15,
            results["symbolic_resistance"]["resistance_score"] * 0.20,
            results["static_confusion"]["analysis_confusion_score"] * 0.15,
        ]
        return round(sum(scores), 4)

    def to_json(self, path=None):
        """
        to_json

        Purpose:
        Serialise metrics to JSON string, optionally writing to a file.

        Inputs:
        - path (str | None): optional file path

        Outputs:
        - str: JSON representation of metrics
        """
        if path:
            with open(path, "w") as f:
                json.dump(self.metrics, f, indent=2)
        return json.dumps(self.metrics, indent=2)

    def print_summary(self):
        """
        print_summary

        Purpose:
        Print a human-readable summary of the last measurement to stdout.
        """
        m = self.metrics
        print("\n" + "=" * 60)
        print("  RESILIENCE METRICS REPORT")
        print("=" * 60)

        ce = m["cfg_entropy"]
        print(f"  CFG Entropy:")
        print(f"    Original:    {ce['original_entropy']}")
        print(f"    Protected:   {ce['protected_entropy']}")
        print(f"    Ratio:       {ce['entropy_ratio']}")

        cc = m["cyclomatic_complexity"]
        print(f"  Cyclomatic Complexity:")
        print(f"    Original:    {cc['original_complexity']}")
        print(f"    Protected:   {cc['protected_complexity']}")
        print(f"    Ratio:       {cc['complexity_ratio']}")

        idv = m["instruction_diversity"]
        print(f"  Instruction Diversity:")
        print(f"    Original:    {idv['original_diversity']}")
        print(f"    Protected:   {idv['protected_diversity']}")
        print(f"    Ratio:       {idv['diversity_ratio']}")

        dc = m["dead_code"]
        print(f"  Dead Code:")
        print(f"    Dead Code %: {dc['protected_dead_code_pct']}%")
        print(f"    Honey Funcs: {dc['protected_honey_function_count']}")

        sr = m["symbolic_resistance"]
        print(f"  Symbolic Resistance:")
        print(f"    Score:       {sr['resistance_score']}")

        sc = m["static_confusion"]
        print(f"  Static Confusion:")
        print(f"    Warnings:    {sc['warnings']}")
        print(f"    Score:       {sc['analysis_confusion_score']}")

        print(f"\n  OVERALL RESILIENCE SCORE: {m['overall']}")
        print("=" * 60 + "\n")
