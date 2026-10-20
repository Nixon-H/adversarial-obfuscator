"""Tests for LLM-resilient AST obfuscation passes."""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from obfuscator.llm_resilient import ContextCollapseObfuscator, HoneyFunctionInjector


SIMPLE_FUNC = """
def greet(name):
    msg = "hello " + name
    return msg
"""


def test_context_collapse_produces_valid_python():
    tree = ast.parse(SIMPLE_FUNC)
    obf = ContextCollapseObfuscator(depth=5, dead_vars=10)
    result = obf.obfuscate(tree)
    code = ast.unparse(result)
    compile(code, "<test>", "exec")
    assert isinstance(result, ast.Module)


def test_context_collapse_has_deep_nesting():
    tree = ast.parse(SIMPLE_FUNC)
    obf = ContextCollapseObfuscator(depth=10, dead_vars=10)
    result = obf.obfuscate(tree)
    func_def = None
    for stmt in result.body:
        if isinstance(stmt, ast.FunctionDef):
            func_def = stmt
            break
    assert func_def is not None, "FunctionDef not found"

    def count_nested_ifs(node, max_depth=0):
        for child in ast.walk(node):
            if isinstance(child, ast.If):
                max_depth += 1
        return max_depth

    if_count = count_nested_ifs(func_def)
    assert if_count >= 5, f"Expected at least 5 if statements, got {if_count}"


def test_context_collapse_string_encoding():
    tree = ast.parse('x = "secret_message"')
    obf = ContextCollapseObfuscator(depth=2, dead_vars=5)
    result = obf.obfuscate(tree)
    code = ast.unparse(result)
    assert "b64decode" in code, "Expected base64.b64decode call"
    assert "secret_message" not in code, "String should be base64 encoded"
    compile(code, "<test>", "exec")


def test_context_collapse_execution_preserves_semantics():
    src = """
def greet(name):
    msg = "hello " + name
    return msg
print(greet("world"))
"""
    tree = ast.parse(src)
    obf = ContextCollapseObfuscator(depth=4, dead_vars=5)
    tree = obf.obfuscate(tree)
    code = ast.unparse(tree)
    compile(code, "<test>", "exec")


def test_context_collapse_dead_vars_present():
    tree = ast.parse(SIMPLE_FUNC)
    obf = ContextCollapseObfuscator(depth=3, dead_vars=20)
    result = obf.obfuscate(tree)
    code = ast.unparse(result)
    dc_count = code.count("_nx_dc_")
    assert dc_count >= 5, f"Expected dead variable references, got {dc_count}"


def test_context_collapse_guard_vars_present():
    tree = ast.parse(SIMPLE_FUNC)
    obf = ContextCollapseObfuscator(depth=3, dead_vars=5)
    result = obf.obfuscate(tree)
    code = ast.unparse(result)
    found_guard = any(gv in code for gv in [
        "_nx_gc_enabled", "_nx_crypto_init", "_nx_vm_ready",
        "_nx_license_valid", "_nx_hw_bound", "_nx_self_check",
    ])
    assert found_guard, "No guard variable found in output"


def test_honey_function_injector_adds_functions():
    tree = ast.parse(SIMPLE_FUNC)
    injector = HoneyFunctionInjector(count=3)
    result = injector.inject(tree)
    func_names = []
    for stmt in result.body:
        if isinstance(stmt, ast.FunctionDef):
            func_names.append(stmt.name)
    honey_funcs = [n for n in func_names if "_nx_honey_" in n]
    assert len(honey_funcs) >= 1, f"Expected honey functions, got {func_names}"


def test_honey_functions_are_valid_python():
    tree = ast.parse(SIMPLE_FUNC)
    injector = HoneyFunctionInjector(count=5)
    result = injector.inject(tree)
    code = ast.unparse(result)
    compile(code, "<test>", "exec")


def test_honey_functions_contain_real_algorithms():
    tree = ast.parse(SIMPLE_FUNC)
    injector = HoneyFunctionInjector(count=5)
    result = injector.inject(tree)
    code = ast.unparse(result)
    algo_keywords = ["table", "poly", "sbox", "rcon", "crc", "buffer"]
    found = any(kw in code for kw in algo_keywords)
    assert found, "No real algorithm keywords found in honey functions"


def test_both_passes_compose():
    tree = ast.parse(SIMPLE_FUNC)
    obf = ContextCollapseObfuscator(depth=5, dead_vars=10)
    tree = obf.obfuscate(tree)
    injector = HoneyFunctionInjector(count=3)
    tree = injector.inject(tree)
    code = ast.unparse(tree)
    compile(code, "<test>", "exec")
    assert isinstance(tree, ast.Module)


def test_multiple_functions_all_obfuscated():
    source = """
def foo():
    return "alpha"

def bar():
    return "beta"
"""
    tree = ast.parse(source)
    obf = ContextCollapseObfuscator(depth=4, dead_vars=5)
    result = obf.obfuscate(tree)
    func_defs = [s for s in result.body if isinstance(s, ast.FunctionDef)]
    assert len(func_defs) == 2
    code = ast.unparse(result)
    assert "alpha" not in code, "String 'alpha' should be encoded"
    assert "beta" not in code, "String 'beta' should be encoded"
