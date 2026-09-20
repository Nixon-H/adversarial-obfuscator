"""Tests for Attention Poisoning Graphs (Item 70)."""
import ast
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.attention_poison import AttentionPoisonInjector


SIMPLE_3STMT = """
def process(a, b):
    x = a + b
    y = x * 2
    return y
"""

EMPTY_FUNC = """
def empty():
    pass
"""

SINGLE_STMT = """
def single():
    return 42
"""

RETURN_FUNC = """
def compute(n):
    if n > 0:
        return n * 2
    return 0
"""

SEMANTIC_SRC = """
def add(a, b):
    result = a + b
    return result

def main():
    x = add(3, 4)
    print(x)

main()
"""


def _count_ast_nodes(code: str) -> int:
    tree = ast.parse(code)
    return sum(1 for _ in ast.walk(tree))


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


class TestAttentionPoisonInjector:
    """
    TestAttentionPoisonInjector
    
    Positive test cases for attentionpoisoninjector.
    """
    def test_expands_simple_cfg(self):
        tree = ast.parse(SIMPLE_3STMT)
        orig_nodes = _count_ast_nodes(SIMPLE_3STMT)
        injector = AttentionPoisonInjector(fan_out=10)
        injector.visit(tree)
        code = ast.unparse(tree)
        new_nodes = _count_ast_nodes(code)
        assert new_nodes >= 3 * orig_nodes, (
            f"Expected >= {3*orig_nodes} nodes, got {new_nodes}"
        )

    def test_preserves_semantics(self):
        original_stdout = _execute(SEMANTIC_SRC)
        injector = AttentionPoisonInjector(fan_out=5)
        tree = ast.parse(SEMANTIC_SRC)
        injector.visit(tree)
        obfuscated = ast.unparse(tree)
        obfuscated_stdout = _execute(obfuscated)
        assert original_stdout == obfuscated_stdout

    def test_token_explosion_ratio(self):
        injector = AttentionPoisonInjector(fan_out=10)
        tree = ast.parse(SIMPLE_3STMT)
        injector.visit(tree)
        ratio = injector.explosion_ratio()
        assert ratio >= 10.0, f"Expected ratio >= 10x, got {ratio:.2f}x"

    def test_handles_empty_function(self):
        injector = AttentionPoisonInjector(fan_out=10)
        tree = ast.parse(EMPTY_FUNC)
        injector.visit(tree)
        code = ast.unparse(tree)
        ast.parse(code)

    def test_handles_return(self):
        injector = AttentionPoisonInjector(fan_out=10)
        tree = ast.parse(RETURN_FUNC)
        injector.visit(tree)
        code = ast.unparse(tree)
        ast.parse(code)
        assert "return" in code

    def test_valid_python(self):
        injector = AttentionPoisonInjector(fan_out=10)
        tree = ast.parse(SIMPLE_3STMT)
        injector.visit(tree)
        code = ast.unparse(tree)
        try:
            ast.parse(code)
        except SyntaxError as e:
            pytest.fail(f"Invalid Python generated: {e}")

    def test_fan_out_zero(self):
        injector = AttentionPoisonInjector(fan_out=0)
        tree = ast.parse(SIMPLE_3STMT)
        injector.visit(tree)
        code = ast.unparse(tree)
        ast.parse(code)

    def test_multiple_functions(self):
        src = """
def foo():
    a = 1
    b = 2
    return a + b

def bar():
    x = 10
    y = 20
    return x * y
"""
        injector = AttentionPoisonInjector(fan_out=5)
        tree = ast.parse(src)
        injector.visit(tree)
        code = ast.unparse(tree)
        ast.parse(code)
        assert "def foo" in code
        assert "def bar" in code
