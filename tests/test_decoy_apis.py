"""Tests for Semantic Decoy APIs (Item 72)."""
import ast
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.decoy_apis import SemanticDecoyApiInjector
from obfuscator.algo_templates import _REAL_ALGO_SOURCES


SIMPLE_SCRIPT = """
def greet(name):
    msg = "hello " + name
    return msg

def main():
    result = greet("world")
    print(result)

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


class TestSemanticDecoyApiInjector:
    """
    TestSemanticDecoyApiInjector
    
    Positive test cases for semanticdecoyapiinjector.
    """
    def test_decoy_api_signatures(self):
        injector = SemanticDecoyApiInjector(count=5)
        tree = ast.parse(SIMPLE_SCRIPT)
        tree = injector.inject(tree)
        decoy_funcs = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name.startswith("_nx_decoy_")
        ]
        assert len(decoy_funcs) >= 3, f"Expected >=3 decoy funcs, got {len(decoy_funcs)}"
        for func in decoy_funcs:
            assert len(func.args.args) > 0, f"{func.name} has no params"
            # Check for docstring
            assert func.body and isinstance(func.body[0], ast.Expr) and isinstance(func.body[0].value, ast.Constant)

    def test_decoy_apis_never_called(self):
        injector = SemanticDecoyApiInjector(count=5)
        tree = ast.parse(SIMPLE_SCRIPT)
        tree = injector.inject(tree)
        code = ast.unparse(tree)
        decoy_funcs = [
            n.name for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name.startswith("_nx_decoy_")
        ]
        for func_name in decoy_funcs:
            call_count = code.count(func_name + "(")
            assert call_count <= 1, f"{func_name} has {call_count} references (should be 0 actual calls)"

    def test_decoy_apis_compile(self):
        injector = SemanticDecoyApiInjector(count=5)
        tree = ast.parse(SIMPLE_SCRIPT)
        tree = injector.inject(tree)
        code = ast.unparse(tree)
        try:
            compile(code, "<test>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Compilation failed: {e}")

    def test_decoy_apis_semantics_preserved(self):
        original_stdout = _execute(SIMPLE_SCRIPT)
        injector = SemanticDecoyApiInjector(count=5)
        tree = ast.parse(SIMPLE_SCRIPT)
        tree = injector.inject(tree)
        code = ast.unparse(tree)
        obfuscated_stdout = _execute(code)
        assert original_stdout == obfuscated_stdout

    def test_decoy_api_collision_avoidance(self):
        src = """
def validate_license():
    return "real"

def main():
    return validate_license()
"""
        injector = SemanticDecoyApiInjector(count=3)
        tree = ast.parse(src)
        tree = injector.inject(tree)
        func_names = [
            n.name for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef)
        ]
        real_count = func_names.count("validate_license")
        assert real_count == 1, f"validate_license should appear exactly once (real), got {real_count}"

    def test_inject_with_varying_counts(self):
        for count in [1, 3, 8]:
            injector = SemanticDecoyApiInjector(count=count)
            tree = ast.parse(SIMPLE_SCRIPT)
            tree = injector.inject(tree)
            decoy_funcs = [
                n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name.startswith("_nx_decoy_")
            ]
            assert len(decoy_funcs) >= min(count, 8)

    def test_inject_twice_no_collision(self):
        injector = SemanticDecoyApiInjector(count=3)
        tree = ast.parse(SIMPLE_SCRIPT)
        tree = injector.inject(tree)
        code1 = ast.unparse(tree)
        tree = injector.inject(tree)
        code2 = ast.unparse(tree)
        assert code2.count("_nx_decoy_") > code1.count("_nx_decoy_")

    def test_algo_templates_exist(self):
        assert "base64_decode" in _REAL_ALGO_SOURCES
        assert "crc32" in _REAL_ALGO_SOURCES
        assert "xor_block" in _REAL_ALGO_SOURCES
        assert "json_parse" in _REAL_ALGO_SOURCES

    def test_decoy_bodies_have_no_unescaped_braces(self):
        # The templates carry str.format escapes ({{ -> {) but are filled
        # with str.replace, so the escapes must be undone.  Leaving them
        # emits `return {{...}}`, which parses as a set containing a dict.
        injector = SemanticDecoyApiInjector(count=8)
        tree = ast.parse(SIMPLE_SCRIPT)
        tree = injector.inject(tree)
        code = ast.unparse(tree)
        assert "{{" not in code, "unescaped '{{' left in a decoy body"
        assert "}}" not in code, "unescaped '}}' left in a decoy body"

    def test_dict_returning_decoys_return_dicts(self):
        # A `return {{...}}` body parses but raises TypeError
        # (unhashable dict) when the decoy is actually called.
        injector = SemanticDecoyApiInjector(count=8)
        tree = ast.parse(SIMPLE_SCRIPT)
        tree = injector.inject(tree)
        checked = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if not node.name.startswith("_nx_decoy_"):
                continue
            src = ast.unparse(node)
            if "license_key" in src:
                args = ("abc", b"12345678")
            elif "activation_code" in src:
                args = ("ac", b"m" * 8)
            elif "subscription_id" in src:
                args = ("sub", b"m" * 8)
            elif "customer_id" in src:
                args = ("cust", b"m" * 8)
            else:
                continue
            namespace = {}
            exec(compile(src, "<decoy>", "exec"), namespace)
            result = namespace[node.name](*args)
            assert isinstance(result, dict), (
                "%s returned %r, expected dict"
                % (node.name, type(result)))
            checked += 1
        assert checked >= 1, "no dict-returning decoy was exercised"
