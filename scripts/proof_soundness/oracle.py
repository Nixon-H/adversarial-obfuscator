"""
proof_soundness/oracle.py — Semantic equivalence oracle for transformation testing (F174)

Purpose:
    Provides a ground-truth oracle that checks whether two code snippets are
    semantically equivalent by running them against random inputs and comparing
    outputs. Used to validate that mutations truly change behaviour.

Architectural Role:
    Testing utility consumed by the ProofSoundnessHarness. Provides
    check_semantic_equivalence, is_truly_different, and classify_difference.

Security Relevance:
    The oracle prevents false positives in the soundness harness by ensuring
    that mutations actually change semantics before testing proof rejection.
"""

from __future__ import annotations

import ast
import random
from typing import Any, Dict, List, Tuple


class TransformationOracle:
    """Checks semantic equivalence of two code snippets via random-input execution.

    Parses the source, extracts function parameters, generates random inputs,
    executes both original and modified code, and compares all outputs.
    """
    def __init__(self, random_inputs: int = 100, seed: int = 42):
        self.random_inputs = random_inputs
        self.rng = random.Random(seed)

    def check_semantic_equivalence(
        self, original: str, modified: str
    ) -> bool:
        """Return True if original and modified produce the same outputs for random inputs within tolerance."""
        inputs = self._generate_inputs(original)
        try:
            orig_vals = self._run_with_inputs(original, inputs)
            mod_vals = self._run_with_inputs(modified, inputs)
        except Exception:
            return False

        if len(orig_vals) != len(mod_vals):
            return False

        for ov, mv in zip(orig_vals, mod_vals):
            try:
                if abs(ov - mv) > 1e-9:
                    return False
            except (TypeError, ValueError):
                if ov != mv:
                    return False
        return True

    def is_truly_different(self, original: str, modified: str) -> bool:
        """Inverse of check_semantic_equivalence: True if snippets differ."""
        return not self.check_semantic_equivalence(original, modified)

    def classify_difference(
        self, original: str, modified: str
    ) -> Dict[str, Any]:
        """Classify the type and magnitude of difference between two code snippets.

        Returns a dict with is_different, difference_type (equivalent /
        completely_different / mostly_different / partially_different /
        execution_error / output_count_mismatch), divergence_count, match_rate.
        """
        result: Dict[str, Any] = {
            "is_different": False,
            "difference_type": "none",
            "divergence_count": 0,
            "match_rate": 1.0,
            "sample_size": 0,
        }

        inputs = self._generate_inputs(original)
        try:
            orig_vals = self._run_with_inputs(original, inputs)
            mod_vals = self._run_with_inputs(modified, inputs)
        except Exception:
            result["is_different"] = True
            result["difference_type"] = "execution_error"
            return result

        if len(orig_vals) != len(mod_vals):
            result["is_different"] = True
            result["difference_type"] = "output_count_mismatch"
            return result

        divergences = 0
        for ov, mv in zip(orig_vals, mod_vals):
            try:
                if abs(ov - mv) > 1e-9:
                    divergences += 1
            except (TypeError, ValueError):
                if ov != mv:
                    divergences += 1

        total = len(orig_vals)
        result["sample_size"] = total
        result["divergence_count"] = divergences
        result["match_rate"] = (total - divergences) / total if total > 0 else 1.0
        result["is_different"] = divergences > 0

        if divergences == total:
            result["difference_type"] = "completely_different"
        elif divergences > total * 0.5:
            result["difference_type"] = "mostly_different"
        elif divergences > 0:
            result["difference_type"] = "partially_different"
        else:
            result["difference_type"] = "equivalent"

        return result

    def _generate_inputs(self, source: str) -> List[Dict[str, int]]:
        """Parse source to extract function parameters, then generate random int inputs for each."""
        tree = ast.parse(source, mode="exec")
        params: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                params = [arg.arg for arg in node.args.args]
                break

        if not params:
            return [{}]

        inputs: List[Dict[str, int]] = []
        for _ in range(self.random_inputs):
            inp = {p: self.rng.randint(-100, 100) for p in params}
            inputs.append(inp)
        return inputs

    def _run_with_inputs(
        self, source: str, inputs: List[Dict[str, int]]
    ) -> List[Any]:
        """Execute the function defined in source with each input dict; return list of results."""
        tree = ast.parse(source, mode="exec")
        func_name = None
        params: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                params = [arg.arg for arg in node.args.args]
                break

        if func_name is None:
            return []

        results: List[Any] = []
        for inp in inputs:
            call_args = ", ".join(str(inp[p]) for p in params)
            call_code = f"{func_name}({call_args})"
            val = self._eval_call(source, call_code)
            results.append(val)

        return results

    def _eval_call(self, source: str, call_expr: str) -> Any:
        """Compile source in a fresh namespace, then eval call_expr; returns None on error."""
        ns: Dict[str, Any] = {"__builtins__": __builtins__}
        try:
            exec(compile(source, "<oracle>", "exec"), ns)
            return eval(call_expr, ns)
        except Exception:
            return None
