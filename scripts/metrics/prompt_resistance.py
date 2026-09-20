"""
prompt_resistance.py

Purpose:
Prompt Reconstruction Resistance — measure the difficulty of recovering
original developer intent from obfuscated code using LLM-based prompt
analysis. Quantifies how well obfuscation hides semantics across name
overlap, AST type similarity, function name overlap, naming clarity,
docstring informativeness, and structural simplicity.

Architectural Role:
One of three metric families (resilience, context_saturation, prompt_resistance).
Provides the PromptResistanceMetrics class measuring intent obscurity and
semantic recoverability, combined into a composite 0–100 score.

Execution Context:
Called by build.py when --prompt-resistance flag is set, comparing the
original payload against the obfuscated output.

Dependencies:
- ast: Python AST parsing/walking
- math, collections.Counter: standard library
"""

import ast
import math
from collections import Counter


class PromptResistanceMetrics:
    """
    PromptResistanceMetrics

    Purpose:
    Measure how well obfuscation hides original developer intent from
    prompt-based reconstruction. Two sub-scores feed into a composite:
    intent obscurity (structural divergence) and semantic recoverability
    (remaining readability).

    Lifecycle:
    Instantiated on demand; methods are independent and can be called
    separately or combined via compute_prompt_resistance_score().

    State:
    Stateless — all state is local to each method call.
    """

    def measure_intent_obscurity(self, original: str, obfuscated: str) -> float:
        """
        measure_intent_obscurity

        Purpose:
        Compute how structurally different the obfuscated AST is from the
        original. Factors: name overlap, AST node-type similarity, function
        name overlap. Returns 0.0 (fully exposed) to 1.0 (fully hidden).

        Inputs:
        - original (str): original source code
        - obfuscated (str): obfuscated source code

        Outputs:
        - float: 0.0–1.0 obscurity score
        """
        orig_tree = ast.parse(original)
        obf_tree = ast.parse(obfuscated)

        orig_names = set()
        for node in ast.walk(orig_tree):
            if isinstance(node, ast.Name):
                orig_names.add(node.id)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                orig_names.add(node.name)

        obf_names = set()
        for node in ast.walk(obf_tree):
            if isinstance(node, ast.Name):
                obf_names.add(node.id)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                obf_names.add(node.name)

        intersecting_names = orig_names & obf_names
        total_names = len(orig_names) | len(obf_names)
        name_overlap = len(intersecting_names) / max(total_names, 1)

        orig_types = Counter(type(n).__name__ for n in ast.walk(orig_tree))
        obf_types = Counter(type(n).__name__ for n in ast.walk(obf_tree))

        all_types = set(orig_types.keys()) | set(obf_types.keys())
        if not all_types:
            return 0.0

        type_sim = 0.0
        for t in all_types:
            o = orig_types.get(t, 0)
            b = obf_types.get(t, 0)
            type_sim += min(o, b) / max(o, b, 1)
        type_sim /= len(all_types)

        orig_func_names = [
            n.name for n in ast.walk(orig_tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        obf_func_names = [
            n.name for n in ast.walk(obf_tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        func_overlap = len(set(orig_func_names) & set(obf_func_names))
        func_total = max(len(set(orig_func_names) | set(obf_func_names)), 1)
        func_sim = func_overlap / func_total

        obscurity = 1.0 - (0.4 * name_overlap + 0.3 * type_sim + 0.3 * func_sim)
        return max(0.0, min(1.0, obscurity))

    def measure_semantic_recoverability(self, code: str) -> float:
        """
        measure_semantic_recoverability

        Purpose:
        Estimate how easily original semantics can be inferred from the
        obfuscated code alone. Uses naming clarity (meaningful vs obfuscated
        names), docstring frequency, and structural simplicity (nesting
        depth variance).

        Inputs:
        - code (str): obfuscated source code

        Outputs:
        - float: 0.0 (hard to recover) to 1.0 (easy to recover)
        """
        tree = ast.parse(code)

        meaningful_names = 0
        total_names = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                total_names += 1
                if len(node.id) >= 3 and not node.id.startswith("_"):
                    meaningful_names += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total_names += 1
                if len(node.name) >= 3 and not node.name.startswith("_"):
                    meaningful_names += 1

        name_clarity = meaningful_names / max(total_names, 1)

        docstrings = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                    if isinstance(node.body[0].value.value, str):
                        docstrings += 1

        total_defs = sum(
            1 for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        doc_ratio = docstrings / max(total_defs, 1)

        depth_variance = 0.0
        depths = []

        def measure_depth(node: ast.AST, d: int = 0) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                    depths.append(d + 1)
                    measure_depth(child, d + 1)
                elif isinstance(child, ast.FunctionDef):
                    measure_depth(child, d)
                else:
                    measure_depth(child, d)

        measure_depth(tree)
        if depths:
            avg_d = sum(depths) / len(depths)
            depth_variance = sum((d - avg_d) ** 2 for d in depths) / len(depths)
        simplicity = 1.0 - min(1.0, depth_variance / 30.0)

        recoverability = 0.5 * name_clarity + 0.3 * doc_ratio + 0.2 * simplicity
        return max(0.0, min(1.0, recoverability))

    def compute_prompt_resistance_score(self, original: str, protected: str) -> float:
        """
        compute_prompt_resistance_score

        Purpose:
        Composite 0–100 score combining intent obscurity (weighted 0.6) and
        the inverse of semantic recoverability (weighted 0.4). Higher scores
        mean better resistance to prompt-based reconstruction.

        Inputs:
        - original (str): original source code
        - protected (str): obfuscated source code

        Outputs:
        - float: 0 (easily reconstructed) to 100 (fully resistant)
        """
        obscurity = self.measure_intent_obscurity(original, protected)
        recoverability = self.measure_semantic_recoverability(protected)

        raw = 0.6 * obscurity + 0.4 * (1.0 - recoverability)
        return min(100.0, round(raw * 100, 2))
