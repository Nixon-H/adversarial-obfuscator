"""
LLM Fingerprinting — embed detectable signatures unique to each AI model.

LLMFingerprinter embeds subtle AST patterns that are invisible to humans
but detectable programmatically, allowing identification of which AI tool
produced or analyzed a given code fragment.
"""

import ast
import hashlib
import random
import secrets


_MODEL_SIGNATURES = {
    "gpt": {
        "guard_var": "_nx_fp_a",
        "opaque_constant": 0xDEADBEEF,
        "sentinel_value": "a1b2c3d4",
    },
    "claude": {
        "guard_var": "_nx_fp_b",
        "opaque_constant": 0xCAFEBABE,
        "sentinel_value": "e5f6g7h8",
    },
    "gemini": {
        "guard_var": "_nx_fp_c",
        "opaque_constant": 0xBA5EBA11,
        "sentinel_value": "i9j0k1l2",
    },
    "deepseek": {
        "guard_var": "_nx_fp_d",
        "opaque_constant": 0xD15EA5E5,
        "sentinel_value": "m3n4o5p6",
    },
    "copilot": {
        "guard_var": "_nx_fp_e",
        "opaque_constant": 0xC0DEBABE,
        "sentinel_value": "q7r8s9t0",
    },
}

_MODEL_BY_CONSTANT = {sig["opaque_constant"]: name for name, sig in _MODEL_SIGNATURES.items()}
_MODEL_BY_SENTINEL = {sig["sentinel_value"]: name for name, sig in _MODEL_SIGNATURES.items()}


class LLMFingerprinter:
    """Embeds and detects model-specific fingerprints in ASTs."""

    def __init__(self, seed: int | None = None):
        self._rng = secrets.SystemRandom() if seed is None else random.Random(seed)

    def embed_fingerprint(self, tree: ast.AST, model_name: str) -> ast.AST:
        """Embed a model-specific fingerprint into an AST."""
        sig = _MODEL_SIGNATURES.get(model_name.lower())
        if sig is None:
            raise ValueError(f"Unknown model: {model_name}. Choose from: {list(_MODEL_SIGNATURES.keys())}")

        tag = self._rng.randint(0, 2**32)
        guard_name = f"{sig['guard_var']}_{tag:x}"
        sentinel_name = f"_nx_fp_s_{tag:x}"

        fp_assign = ast.Assign(
            targets=[ast.Name(id=guard_name, ctx=ast.Store())],
            value=ast.Constant(value=sig["opaque_constant"]),
        )

        fp_check = ast.If(
            test=ast.Compare(
                left=ast.Name(id=guard_name, ctx=ast.Load()),
                ops=[ast.Eq()],
                comparators=[ast.Constant(value=sig["opaque_constant"])],
            ),
            body=[ast.Pass()],
            orelse=[],
        )

        sentinel_marker = int(hashlib.sha256(sig["sentinel_value"].encode()).hexdigest()[:8], 16)
        sentinel_assign = ast.Assign(
            targets=[ast.Name(id=sentinel_name, ctx=ast.Store())],
            value=ast.Constant(value=sentinel_marker),
        )

        if isinstance(tree, ast.Module):
            import_idx = 0
            for i, stmt in enumerate(tree.body):
                if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                    import_idx = i + 1
            if import_idx < len(tree.body):
                tree.body.insert(import_idx, fp_assign)
                tree.body.insert(import_idx + 1, sentinel_assign)
                tree.body.insert(import_idx + 2, fp_check)
            else:
                tree.body.append(fp_assign)
                tree.body.append(sentinel_assign)
                tree.body.append(fp_check)
        else:
            if hasattr(tree, "body") and isinstance(tree.body, list):
                tree.body.insert(0, fp_check)
                tree.body.insert(0, sentinel_assign)
                tree.body.insert(0, fp_assign)

        ast.fix_missing_locations(tree)
        return tree

    def detect_fingerprint(self, code: str) -> str:
        """Detect which model's fingerprint is present in source code."""
        tree = ast.parse(code)

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                if isinstance(node.targets[0], ast.Name) and node.targets[0].id.startswith("_nx_fp_"):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, int):
                        if node.value.value in _MODEL_BY_CONSTANT:
                            return _MODEL_BY_CONSTANT[node.value.value]

        return "unknown"

    def supported_models(self) -> list[str]:
        return list(_MODEL_SIGNATURES.keys())
