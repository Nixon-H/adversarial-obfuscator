"""Tests for Reasoning-Loop Traps (Item 75)."""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from obfuscator.reasoning_traps import ReasoningLoopInjector


SAMPLE_CODE = """
def compute(x):
    return x + 1
"""


def test_loop_creates_circular_call_graph():
    injector = ReasoningLoopInjector(seed=42)
    tree = ast.parse(SAMPLE_CODE)
    tree = injector.inject_loop(tree, depth=3)
    func_names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert "compute" in func_names
    trap_funcs = [n for n in func_names if n.startswith("_nx_trap_")]
    assert len(trap_funcs) >= 1, f"Expected trap functions, got {func_names}"
    code = ast.unparse(tree)
    assert "compute(" in code
    assert "_nx_trap_" in code


def test_loop_terminates_at_runtime():
    injector = ReasoningLoopInjector(seed=42)
    tree = ast.parse(SAMPLE_CODE)
    tree = injector.inject_loop(tree, depth=3)
    code = ast.unparse(tree)
    exec_globals = {}
    exec(code, exec_globals)
    result = exec_globals["compute"](5)
    assert result == 6


def test_loop_depth_configurable():
    injector = ReasoningLoopInjector(seed=42)
    for depth in [2, 3, 5]:
        tree = ast.parse(SAMPLE_CODE)
        tree = injector.inject_loop(tree, depth=depth)
        code = ast.unparse(tree)
        compile(code, "<test>", "exec")
        exec_globals = {}
        exec(code, exec_globals)
        assert exec_globals["compute"](5) == 6
        trap_count = code.count("_nx_trap_")
        if depth <= 2:
            assert trap_count >= 1, f"depth={depth}"
        else:
            assert trap_count >= depth - 1


def test_loop_preserves_semantics():
    injector = ReasoningLoopInjector(seed=42)
    src = """
def multiply(a, b):
    return a * b
"""
    tree = ast.parse(src)
    tree = injector.inject_loop(tree, depth=4)
    code = ast.unparse(tree)
    compile(code, "<test>", "exec")
    exec_globals = {}
    exec(code, exec_globals)
    assert exec_globals["multiply"](3, 7) == 21
    assert exec_globals["multiply"](0, 100) == 0


def test_loop_with_multiple_functions():
    injector = ReasoningLoopInjector(seed=42)
    src = """
def add(a, b):
    return a + b

def sub(a, b):
    return a - b
"""
    tree = ast.parse(src)
    tree = injector.inject_loop(tree, depth=3)
    code = ast.unparse(tree)
    compile(code, "<test>", "exec")
    exec_globals = {}
    exec(code, exec_globals)
    assert exec_globals["add"](5, 3) == 8
    assert exec_globals["sub"](5, 3) == 2


def test_loop_valid_python():
    injector = ReasoningLoopInjector(seed=42)
    tree = ast.parse(SAMPLE_CODE)
    tree = injector.inject_loop(tree, depth=10)
    code = ast.unparse(tree)
    compile(code, "<test>", "exec")


def test_no_functions_no_injection():
    injector = ReasoningLoopInjector(seed=42)
    tree = ast.parse("x = 5")
    result = injector.inject_loop(tree, depth=5)
    assert isinstance(result, ast.Module)
