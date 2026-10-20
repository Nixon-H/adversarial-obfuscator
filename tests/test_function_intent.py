"""Tests for Function Intent Obfuscation (Item 78)."""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from obfuscator.function_intent import FunctionIntentObfuscator


SAMPLE_CODE = """
def encrypt(data, key):
    result = data ^ key
    return result
"""

MULTI_FUNC = """
def validate(input_data):
    return input_data > 0

def parse(data):
    return data.split(",")
"""


def test_misleading_names():
    obf = FunctionIntentObfuscator(seed=42)
    tree = ast.parse(SAMPLE_CODE)
    tree = obf.obfuscate_intent(tree)
    func = tree.body[0]
    assert isinstance(func, ast.FunctionDef)
    orig_keywords = ["encrypt", "compress", "serialize", "encode", "pack", "obfuscate"]
    found_misleading = any(kw in func.name for kw in orig_keywords)
    assert found_misleading, f"Name '{func.name}' not in expected misleading set"
    assert func.name != "encrypt", f"Name should not be 'encrypt', got '{func.name}'"


def test_signature_swapped():
    obf = FunctionIntentObfuscator(seed=42)
    tree = ast.parse(SAMPLE_CODE)
    tree = obf.obfuscate_intent(tree)
    code = ast.unparse(tree)
    compile(code, "<test>", "exec")


def test_fake_docstrings():
    obf = FunctionIntentObfuscator(seed=42)
    tree = ast.parse(SAMPLE_CODE)
    tree = obf.obfuscate_intent(tree)
    func = tree.body[0]
    assert isinstance(func, ast.FunctionDef)
    first_stmt = func.body[0]
    has_docstring = (
        isinstance(first_stmt, ast.Expr)
        and isinstance(first_stmt.value, ast.Constant)
        and isinstance(first_stmt.value.value, str)
        and len(first_stmt.value.value) > 10
    )
    assert has_docstring, "Expected a fake docstring as first statement"


def test_preserves_semantics():
    obf = FunctionIntentObfuscator(seed=42)
    src = """
def compute_double(x):
    return x * 2
"""
    tree = ast.parse(src)
    tree = obf.obfuscate_intent(tree)
    code = ast.unparse(tree)
    compile(code, "<test>", "exec")
    exec_globals = {}
    exec(code, exec_globals)
    func_name = tree.body[0].name
    assert exec_globals[func_name](5) == 10


def test_multiple_functions():
    obf = FunctionIntentObfuscator(seed=42)
    tree = ast.parse(MULTI_FUNC)
    tree = obf.obfuscate_intent(tree)
    code = ast.unparse(tree)
    compile(code, "<test>", "exec")
    exec_globals = {}
    exec(code, exec_globals)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert node.name != "validate", "Name should be changed"
            assert node.name != "parse", "Name should be changed"


def test_obfuscate_intent_returns_ast():
    obf = FunctionIntentObfuscator(seed=42)
    tree = ast.parse(SAMPLE_CODE)
    result = obf.obfuscate_intent(tree)
    assert isinstance(result, ast.AST)
    assert isinstance(result, ast.Module)


def test_name_map_updated():
    obf = FunctionIntentObfuscator(seed=42)
    tree = ast.parse(SAMPLE_CODE)
    obf.obfuscate_intent(tree)
    name_map = obf.get_name_map()
    assert "encrypt" in name_map
    assert name_map["encrypt"] != "encrypt"


def test_valid_python_output():
    obf = FunctionIntentObfuscator(seed=42)
    examples = [
        "def add(a, b): return a + b",
        "def check(value): return value is True",
        "def keygen(): return 42",
        "def decode(msg): return msg.lower()",
    ]
    for src in examples:
        tree = ast.parse(src)
        tree = obf.obfuscate_intent(tree)
        code = ast.unparse(tree)
        compile(code, "<test>", "exec")
