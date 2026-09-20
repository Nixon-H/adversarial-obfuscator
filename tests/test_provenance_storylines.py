"""Tests for Multi-Agent Deception Storylines (Item 71)."""
import ast
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.provenance.poisoner import ProvenancePoisoner
from scripts.provenance.metrics import ProvenanceMetrics
from scripts.provenance.storylines import get_all_storylines, STORYLINES


SIMPLE_SCRIPT = """
def greet(name):
    msg = "hello " + name
    return msg

def main():
    print(greet("world"))

main()
"""


def _execute(code: str) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp = f.name
    try:
        result = subprocess.run(
            [sys.executable, tmp], capture_output=True, text=True, timeout=10
        )
        return result.stdout
    finally:
        os.unlink(tmp)


class TestStorylineInjection:
    """
    TestStorylineInjection
    
    Positive test cases for storylineinjection.
    """
    def test_storyline_injection(self):
        tree = ast.parse(SIMPLE_SCRIPT)
        poisoner = ProvenancePoisoner(seed=42)
        tree = poisoner.poison_with_storylines(tree)
        code = ast.unparse(tree)
        for sl in STORYLINES:
            for func_name, _ in sl["functions"]:
                assert func_name in code, f"Expected {func_name} in code from {sl['name']}"

    def test_storyline_independence(self):
        tree = ast.parse(SIMPLE_SCRIPT)
        poisoner = ProvenancePoisoner(seed=42)
        tree = poisoner.poison_with_storylines(tree)
        # Build a mapping: storyline name -> set of function names
        sl_funcs: dict[str, set[str]] = {}
        for sl in STORYLINES:
            sl_funcs[sl["name"]] = {fn for fn, _ in sl["functions"]}
        # Check every call site: if a function from storyline A calls a target
        # that belongs to a different storyline, that's a cross-reference violation.
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name):
                continue
            caller_sl = None
            # find enclosing function and its storyline
            for n in ast.walk(tree):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for child in ast.walk(n):
                        if child is node:
                            caller_sl = next(
                                (s for s, funcs in sl_funcs.items() if n.name in funcs),
                                None,
                            )
                            break
                    if caller_sl is not None:
                        break
            if caller_sl is None:
                continue
            target = node.func.id
            for other_sl, other_funcs in sl_funcs.items():
                if other_sl == caller_sl:
                    continue
                assert target not in other_funcs, \
                    f"{target} from {other_sl} called inside {caller_sl}"

    def test_storyline_metrics(self):
        tree = ast.parse(SIMPLE_SCRIPT)
        poisoner = ProvenancePoisoner(seed=42)
        tree = poisoner.poison_with_storylines(tree)
        metrics = ProvenanceMetrics()
        result = metrics.measure_storyline_confusion(tree)
        assert result["distinct_narratives"] >= 1
        assert result["narrative_entropy"] > 0

    def test_storyline_preserves_semantics(self):
        original_stdout = _execute(SIMPLE_SCRIPT)
        tree = ast.parse(SIMPLE_SCRIPT)
        poisoner = ProvenancePoisoner(seed=42)
        tree = poisoner.poison_with_storylines(tree)
        code = ast.unparse(tree)
        obfuscated_stdout = _execute(code)
        assert original_stdout == obfuscated_stdout

    def test_storylines_valid_python(self):
        tree = ast.parse(SIMPLE_SCRIPT)
        poisoner = ProvenancePoisoner(seed=42)
        tree = poisoner.poison_with_storylines(tree)
        code = ast.unparse(tree)
        try:
            ast.parse(code)
        except SyntaxError as e:
            pytest.fail(f"Invalid Python: {e}")

    def test_get_all_storylines(self):
        storylines = get_all_storylines()
        assert len(storylines) == 3
        names = [s["name"] for s in storylines]
        assert "crypto" in names
        assert "license" in names
        assert "telemetry" in names

    def test_storyline_add_storyline_direct(self):
        tree = ast.parse(SIMPLE_SCRIPT)
        poisoner = ProvenancePoisoner(seed=42)
        from scripts.provenance.storylines import get_storyline
        crypto = get_storyline("crypto")
        assert crypto is not None
        tree = poisoner.add_storyline(tree, crypto)
        code = ast.unparse(tree)
        assert "_nx_init_secure_enclave" in code
        assert "HSM not available" in code
