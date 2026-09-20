"""
context_saturation.py

Purpose:
Context Window Saturation Metrics — quantify how obfuscation degrades LLM
understanding by consuming context-window capacity with noise, confusing
attention mechanisms, and collapsing meaningful patterns into repetitive
or dead constructs.

Architectural Role:
One of three metric families (resilience, context_saturation, prompt_resistance).
Provides the ContextSaturationMetrics class with three measurement dimensions
and a composite 0–100 score.

Execution Context:
Called by build.py when --context-saturation flag is set, after the obfuscated
output is written.

Dependencies:
- ast: Python AST parsing/walking
- math, collections.Counter: standard library
"""

import ast
import math
from collections import Counter

_NOISE_PREFIXES = ("_nx_", "_gpt_", "_claude_", "_gemini_", "_nx_fp_", "_nx_trap_", "_nx_gc_", "_nx_sentinel_")


class ContextSaturationMetrics:
    """
    ContextSaturationMetrics

    Purpose:
    Quantify context-window saturation effects of obfuscation across three
    dimensions: token utilisation (noise ratio), attention degradation
    (depth variance / branch density / ID repetition), and context collapse
    (repetitive line patterns / dead variable density).

    Lifecycle:
    Instantiated on demand; each measure_* method runs independently.

    State:
    Stateless — all state is local to each method call.
    """

    def measure_token_utilization(self, code: str) -> float:
        """
        measure_token_utilization

        Purpose:
        What percentage of the AST nodes are noise-like (dead assignments,
        opaque predicates, empty exception handlers, prefixed identifiers)
        versus semantically meaningful code.

        Inputs:
        - code (str): source code to analyse

        Outputs:
        - float: 0.0 (all meaningful) to 1.0 (all noise)

        Security:
        Higher noise ratios make it harder for LLMs to extract the real
        program logic from obfuscated code.
        """
        if not code.strip():
            return 0.0
        tree = ast.parse(code)
        total_nodes = sum(1 for _ in ast.walk(tree))

        noise_nodes = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.startswith(_NOISE_PREFIXES):
                        noise_nodes += 1
                        break
                else:
                    continue
            elif isinstance(node, ast.Pass):
                noise_nodes += 1
            elif isinstance(node, ast.If):
                if self._is_opaque_predicate(node.test):
                    noise_nodes += 1
            elif isinstance(node, ast.Try):
                if all(isinstance(h, ast.ExceptHandler) and len(h.body) == 1 and isinstance(h.body[0], ast.Pass) for h in node.handlers):
                    noise_nodes += 1
            elif isinstance(node, ast.Name) and node.id.startswith(_NOISE_PREFIXES):
                noise_nodes += 1

        noise_ratio = noise_nodes / max(total_nodes, 1)
        return min(1.0, noise_ratio)

    def _is_opaque_predicate(self, test: ast.expr) -> bool:
        """
        _is_opaque_predicate

        Purpose:
        Heuristic to detect opaque predicates: constant comparisons,
        underscore-prefixed variables, negations, and certain bool-ops.

        Inputs:
        - test (ast.expr): the test expression from an if-statement

        Outputs:
        - bool: True if the predicate looks opaque
        """
        if isinstance(test, ast.Compare):
            if isinstance(test.left, ast.BinOp) and isinstance(test.left.left, ast.Constant) and isinstance(test.left.right, ast.Constant):
                return True
            if isinstance(test.left, ast.Attribute) or (isinstance(test.left, ast.Name) and test.left.id.startswith("_")):
                return True
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            return True
        if isinstance(test, ast.BoolOp):
            return self._is_opaque_predicate(test.values[0]) if test.values else False
        return False

    def measure_attention_degradation(self, code: str) -> float:
        """
        measure_attention_degradation

        Purpose:
        Estimate how much transformer attention mechanisms are confused by
        obfuscated code. Uses nesting depth variance, branch density, and
        identifier repetition as proxy signals.

        Inputs:
        - code (str): source code to analyse

        Outputs:
        - float: 0.0 (no degradation) to 1.0 (severe degradation)
        """
        if not code.strip():
            return 0.0
        tree = ast.parse(code)

        nesting_depths = []
        id_repetitions: Counter[str] = Counter()
        branch_count = 0

        def walk_depth(node: ast.AST, depth: int = 0) -> None:
            nonlocal branch_count
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                    nesting_depths.append(depth + 1)
                    branch_count += 1
                    walk_depth(child, depth + 1)
                elif isinstance(child, ast.FunctionDef):
                    nesting_depths.append(depth)
                    walk_depth(child, depth)
                else:
                    walk_depth(child, depth)

            if isinstance(node, ast.Name):
                id_repetitions[node.id] += 1

        walk_depth(tree)

        avg_nesting = sum(nesting_depths) / max(len(nesting_depths), 1)
        depth_variance = sum((d - avg_nesting) ** 2 for d in nesting_depths) / max(len(nesting_depths), 1) if nesting_depths else 0

        total_ids = sum(id_repetitions.values())
        repeated = sum(c for c in id_repetitions.values() if c > 3)
        repetition_ratio = repeated / max(total_ids, 1)

        depth_score = min(1.0, depth_variance / 25.0)
        branch_score = min(1.0, branch_count / 50.0)
        rep_score = min(1.0, repetition_ratio * 2)

        combined = 0.4 * depth_score + 0.3 * branch_score + 0.3 * rep_score
        return min(1.0, combined)

    def measure_context_collapse(self, code: str) -> float:
        """
        measure_context_collapse

        Purpose:
        How much context is wasted on repetitive patterns — duplicate line
        structures, deeply nested if-chains, and dead variable assignments.

        Inputs:
        - code (str): source code to analyse

        Outputs:
        - float: 0.0 (no collapse) to 1.0 (severe collapse)
        """
        if not code.strip():
            return 0.0
        tree = ast.parse(code)

        lines = code.split("\n")
        line_patterns: Counter[str] = Counter()
        for line in lines:
            stripped = line.strip()
            if len(stripped) > 3:
                pattern = stripped[:40]
                line_patterns[pattern] += 1

        repetitive_lines = sum(c - 1 for c in line_patterns.values() if c > 2)
        collapse_ratio = repetitive_lines / max(len(lines), 1)

        if_nest_count = sum(1 for n in ast.walk(tree) if isinstance(n, ast.If))

        dead_var_count = sum(
            1 for n in ast.walk(tree)
            if isinstance(n, ast.Assign)
            for t in n.targets
            if isinstance(t, ast.Name) and t.id.startswith(("_nx_", "_gpt_", "_claude_", "_nx_fp_"))
        )

        pattern_score = min(1.0, collapse_ratio * 5)
        nest_score = min(1.0, if_nest_count / 100.0)
        dead_score = min(1.0, dead_var_count / 200.0)

        combined = 0.35 * pattern_score + 0.35 * nest_score + 0.30 * dead_score
        return min(1.0, combined)

    def compute_saturation_score(self, code: str) -> float:
        """
        compute_saturation_score

        Purpose:
        Composite 0–100 score combining token utilisation, attention
        degradation, and context collapse with fixed weights.

        Inputs:
        - code (str): source code to analyse

        Outputs:
        - float: 0 (no saturation) to 100 (fully saturated)
        """
        token_util = self.measure_token_utilization(code)
        attention_degrad = self.measure_attention_degradation(code)
        context_coll = self.measure_context_collapse(code)

        raw = 0.35 * token_util + 0.35 * attention_degrad + 0.30 * context_coll
        return min(100.0, round(raw * 100, 2))
