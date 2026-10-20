"""
ai_eval.py

Purpose:
Implements static proxy metrics for measuring obfuscation effectiveness.
Provides AIBenchmark, the main evaluation harness that scores naming
recovery, semantic leakage, static analysis resistance, decompilation
resistance, complexity impact, and information entropy.

Architectural Role:
Core measurement module for the benchmarking subsystem. Each metric
function compares original vs. protected source code and produces a
normalized score (0.0 = weak protection, 1.0 = strong protection).
The overall protection score is a weighted combination of all metrics.

Dependencies:
ast, math, subprocess, tempfile, collections.Counter

Security Relevance:
Quantifies protection strength across multiple dimensions. Used to
drive adaptive rewriting: if a metric score is low, the pipeline
applies additional protection passes targeting that weakness.
"""

import ast
import math
import os
import subprocess
import sys
import tempfile
from collections import Counter

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _shannon_entropy(data: str) -> float:
    """
    Compute the Shannon entropy of a string.

    Higher entropy indicates more randomness/unpredictability.
    Used by measure_information_entropy to assess whether the
    protected output looks noise-like to an analyst.
    """
    if not data:
        return 0.0
    entropy = 0.0
    length = len(data)
    counts = Counter(data)
    for count in counts.values():
        p = count / length
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


def _hellinger(p: Counter, q: Counter) -> float:
    """
    Compute the Hellinger distance between two frequency distributions.

    Returns a value in [0, 1] where 0 = identical distributions and
    1 = completely disjoint. Used by measure_semantic_leakage to
    quantify how much the AST node-type distribution changes after
    protection.
    """
    all_keys = set(p) | set(q)
    total_p = sum(p.values())
    total_q = sum(q.values())
    if total_p == 0 or total_q == 0:
        return 1.0
    distance_sq = 0.0
    for k in all_keys:
        pp = p.get(k, 0) / total_p
        qq = q.get(k, 0) / total_q
        distance_sq += (math.sqrt(pp) - math.sqrt(qq)) ** 2
    return math.sqrt(distance_sq) / math.sqrt(2)


def _ast_node_types(source: str) -> Counter:
    """
    Extract the frequency distribution of AST node type names from source.

    Handles SyntaxError gracefully by returning an empty Counter.
    Used by measure_semantic_leakage to build a structural fingerprint.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return Counter()
    return Counter(type(n).__name__ for n in ast.walk(tree))


def _count_named_entities(source: str) -> dict:
    """
    Count function definitions and variable assignments in source code.

    Returns dict with keys 'functions' (list of function names) and
    'variables' (list of assigned variable names). Used by
    measure_naming_recovery to compare original vs. protected names.
    """
    tree = ast.parse(source)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            names.append(("function", node.name))
        elif isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Store):
                names.append(("variable", node.id))
    return {"functions": [n for t, n in names if t == "function"],
            "variables": [n for t, n in names if t == "variable"]}


def measure_naming_recovery(original_source: str, protected_source: str) -> dict:
    """
    Measure how many original function/variable names survive protection.

    A high recovery rate means renaming was ineffective. Score is
    1.0 - recovery_rate, so effective renaming yields a high score.
    """
    orig = _count_named_entities(original_source)
    prot = _count_named_entities(protected_source)
    orig_funcs = set(orig["functions"])
    orig_vars = set(orig["variables"])
    prot_funcs = set(prot["functions"])
    prot_vars = set(prot["variables"])

    recovered_funcs = orig_funcs & prot_funcs
    recovered_vars = orig_vars & prot_vars

    total_orig = len(orig_funcs) + len(orig_vars)
    recovered = len(recovered_funcs) + len(recovered_vars)
    recovery_rate = recovered / max(total_orig, 1)

    score = 1.0 - recovery_rate
    return {
        "original_function_count": len(orig_funcs),
        "original_variable_count": len(orig_vars),
        "recovered_functions": list(recovered_funcs),
        "recovered_variables": list(recovered_vars),
        "recovery_rate": round(recovery_rate, 4),
        "score": round(score, 4),
    }


def measure_semantic_leakage(original_source: str, protected_source: str) -> dict:
    """
    Measure how much AST structure leaks between original and protected code.

    Uses Hellinger distance between AST node-type distributions.
    A low distance means the protected code structurally resembles
    the original, indicating weak semantic hiding. Score = distance.
    """
    orig_types = _ast_node_types(original_source)
    prot_types = _ast_node_types(protected_source)
    distance = _hellinger(orig_types, prot_types)

    return {
        "original_node_types": dict(orig_types.most_common(10)),
        "protected_node_types": dict(prot_types.most_common(10)),
        "hellinger_distance": round(distance, 4),
        "score": round(distance, 4),
    }


def measure_static_analysis_resistance(protected_source: str) -> dict:
    """
    Measure how many warnings/errors static analysis tools produce.

    Runs pyflakes, pylint, mypy, and bandit on the protected source.
    More warnings = higher static confusion = better protection.
    Score is min(1.0, warnings / 30), capped at 1.0 at 30+ warnings.
    """
    warnings = 0
    tool_results = {}

    for tool in ("pyflakes", "pylint", "mypy", "bandit"):
        tool_which = _shutil_which(tool)
        if not tool_which:
            tool_results[tool] = {"available": False, "warnings": 0}
            continue
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(protected_source)
                tmp_path = f.name

            count = 0
            if tool == "pyflakes":
                result = subprocess.run(
                    [sys.executable, "-m", "pyflakes", tmp_path],
                    capture_output=True, text=True, timeout=30,
                )
                lines = [l for l in (result.stderr + result.stdout).split("\n") if l.strip()]
                count = len(lines)
            elif tool == "pylint":
                result = subprocess.run(
                    [sys.executable, "-m", "pylint", "--score=n", tmp_path],
                    capture_output=True, text=True, timeout=30,
                )
                for line in result.stdout.split("\n"):
                    if "warning" in line.lower() or "error" in line.lower():
                        count += 1
            elif tool == "mypy":
                result = subprocess.run(
                    [sys.executable, "-m", "mypy", tmp_path],
                    capture_output=True, text=True, timeout=30,
                )
                for line in result.stdout.split("\n"):
                    if "error" in line.lower():
                        count += 1
            elif tool == "bandit":
                result = subprocess.run(
                    [sys.executable, "-m", "bandit", "-q", "-f", "txt", tmp_path],
                    capture_output=True, text=True, timeout=30,
                )
                for line in result.stdout.split("\n"):
                    if ">> Issue" in line:
                        count += 1

            warnings += count
            tool_results[tool] = {"available": True, "warnings": count}
            os.unlink(tmp_path)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            tool_results[tool] = {"available": False, "warnings": 0, "error": str(sys.exc_info()[1])}

    score = min(1.0, warnings / 30.0)
    return {
        "total_warnings": warnings,
        "tool_results": tool_results,
        "score": round(score, 4),
    }


def measure_decompilation_resistance(protected_source: str) -> dict:
    """
    Measure resistance to Python decompilers (uncompyle6, decompyle3).

    Counts anti-decompilation constructs (exec/eval, nested decorators,
    exception-based control flow). If a decompiler succeeds, the score
    is reduced proportionally to the anti-decompiler construct density.
    """
    constructs_found = {
        "exec_eval": 0,
        "nested_decorators": 0,
        "self_modifying": 0,
        "exception_control_flow": 0,
    }

    try:
        tree = ast.parse(protected_source)
    except SyntaxError:
        return {"score": 1.0, "constructs": constructs_found,
                "decompiler_available": False, "decompiler_success": False,
                "error": "Cannot parse protected source"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("exec", "eval"):
                constructs_found["exec_eval"] += 1
            if isinstance(node.func, ast.Attribute) and node.func.attr in ("exec", "eval"):
                constructs_found["exec_eval"] += 1

        if isinstance(node, ast.FunctionDef):
            decorator_count = len(node.decorator_list)
            if decorator_count > 2:
                constructs_found["nested_decorators"] += decorator_count

    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            if any(isinstance(h, ast.ExceptHandler) and
                   h.name is not None and
                   h.name in ("_", "__", "_nx_ex")
                   for h in node.handlers):
                constructs_found["exception_control_flow"] += 1

    score_sum = (min(constructs_found["exec_eval"], 5) / 5 * 0.25 +
                 min(constructs_found["nested_decorators"], 10) / 10 * 0.25 +
                 min(constructs_found["exception_control_flow"], 10) / 10 * 0.25)

    decompiler_success = False
    decompiler_available = False
    for decompiler in ("uncompyle6", "decompyle3"):
        if _shutil_which(decompiler):
            decompiler_available = True
            try:
                # The decompiler check needs a .pyc of the protected
                # source.  `tempfile_name` never existed: the NameError
                # was swallowed by the except below, so the decompiler
                # probe never ran and the score was never reduced.
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                                 delete=False) as _sf:
                    _sf.write(protected_source)
                    _src_path = _sf.name
                with tempfile.NamedTemporaryFile(mode="w", suffix=".pyc", delete=False) as f:
                    pyc_path = f.name
                import py_compile
                py_compile.compile(_src_path, cfile=pyc_path)
                result = subprocess.run(
                    [decompiler, pyc_path],
                    capture_output=True, text=True, timeout=30,
                )
                decompiler_success = result.returncode == 0
                os.unlink(pyc_path)
                os.unlink(_src_path)
            except Exception:
                pass
            break

    if decompiler_success:
        score = max(0.0, 1.0 - score_sum)
    else:
        score = min(1.0, score_sum + 0.3)

    return {
        "constructs": constructs_found,
        "decompiler_available": decompiler_available,
        "decompiler_success": decompiler_success,
        "score": round(score, 4),
    }


def measure_complexity_impact(original_source: str, protected_source: str) -> dict:
    """
    Measure the increase in cyclomatic complexity after protection.

    Effective obfuscation inflates complexity. Score is
    min(1.0, ratio / 5.0), where ratio = protected / original.
    A 5x increase achieves a perfect score.
    """
    def cyclomatic(source: str) -> int:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return 0
        edges = 0
        nodes = set()
        funcs = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                funcs += 1
                nodes.add(id(node))
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                        nodes.add(id(child))
                        edges += 1
                edges += 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.Return, ast.Raise, ast.Call, ast.Break, ast.Continue)):
                edges += 1
        return edges - len(nodes) + 2 * max(funcs, 1)

    orig_c = cyclomatic(original_source)
    prot_c = cyclomatic(protected_source)
    ratio = prot_c / max(orig_c, 1)

    score = min(1.0, ratio / 5.0)
    return {
        "original_complexity": orig_c,
        "protected_complexity": prot_c,
        "complexity_ratio": round(ratio, 4),
        "score": round(score, 4),
    }


def measure_information_entropy(protected_source: str) -> dict:
    """
    Measure the Shannon entropy of the protected source code.

    Higher entropy means the protected code appears more random,
    making it harder for analysts to spot meaningful patterns.
    Score = normalized entropy capped at 1.0.
    """
    entropy = _shannon_entropy(protected_source)
    max_entropy = math.log2(len(set(protected_source))) if protected_source else 1.0
    normalized = entropy / max_entropy if max_entropy > 0 else 0.0

    score = min(1.0, normalized)
    return {
        "shannon_entropy": round(entropy, 4),
        "max_entropy": round(max_entropy, 4),
        "normalized_entropy": round(normalized, 4),
        "length": len(protected_source),
        "score": round(score, 4),
    }


def compute_protection_score(results: dict) -> float:
    """
    Compute a weighted overall protection score from individual metric scores.

    Weights:
      naming_recovery:         0.20
      semantic_leakage:        0.20
      decompilation_resistance: 0.25
      complexity_impact:       0.15
      entropy:                 0.10
      static_confusion:        0.10
    """
    weights = {
        "naming_recovery": 0.20,
        "semantic_leakage": 0.20,
        "decompilation_resistance": 0.25,
        "complexity_impact": 0.15,
        "entropy": 0.10,
        "static_confusion": 0.10,
    }
    total = 0.0
    for key, weight in weights.items():
        if key in results:
            total += results[key].get("score", 0) * weight
    return round(total, 4)


class AIBenchmark:
    """
    Main benchmark harness that evaluates protection effectiveness.

    Runs six static proxy metrics (naming_recovery, semantic_leakage,
    static_confusion, decompilation_resistance, complexity_impact,
    entropy) by comparing original and protected source files, then
    computes a weighted overall protection score.

    Usage:
        bench = AIBenchmark()
        results = bench.evaluate("original.py", "protected.py")
    """

    METRICS = [
        "naming_recovery",
        "semantic_leakage",
        "static_confusion",
        "decompilation_resistance",
        "complexity_impact",
        "entropy",
    ]

    def evaluate(self, original_path: str, protected_path: str) -> dict:
        """
        Evaluate protection by comparing original vs. protected source.

        Reads both files, runs all six metric functions, computes the
        weighted overall score, and returns the complete results dict
        including per-metric breakdowns.
        """
        with open(original_path, encoding="utf-8") as f:
            original_source = f.read()
        with open(protected_path, encoding="utf-8") as f:
            protected_source = f.read()

        results = {
            "naming_recovery": measure_naming_recovery(original_source, protected_source),
            "semantic_leakage": measure_semantic_leakage(original_source, protected_source),
            "static_confusion": measure_static_analysis_resistance(protected_source),
            "decompilation_resistance": measure_decompilation_resistance(protected_source),
            "complexity_impact": measure_complexity_impact(original_source, protected_source),
            "entropy": measure_information_entropy(protected_source),
        }

        results["overall"] = compute_protection_score(results)
        results["_original_path"] = original_path
        results["_protected_path"] = protected_path
        return results


def _shutil_which(cmd: str):
    """Lazy-loaded shutil.which wrapper for tool discovery."""
    import shutil
    return shutil.which(cmd)
