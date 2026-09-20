import ast
import pytest

from scripts.validation.mba_validator import MBAValidator


def test_valid_identity_accepts():
    validator = MBAValidator()
    code_a = """
def f(a, b):
    return a + b
"""
    code_b = """
def f(a, b):
    return (a ^ b) + (2 * (a & b))
"""
    tree_a = ast.parse(code_a)
    tree_b = ast.parse(code_b)
    func_a = tree_a.body[0]
    func_b = tree_b.body[0]
    assert validator.validate(func_a, func_b)


def test_invalid_identity_rejects():
    validator = MBAValidator()
    code_a = """
def f(a, b):
    return a + b
"""
    code_b = """
def f(a, b):
    return a - b
"""
    tree_a = ast.parse(code_a)
    tree_b = ast.parse(code_b)
    func_a = tree_a.body[0]
    func_b = tree_b.body[0]
    assert not validator.validate(func_a, func_b)


def test_stats_tracking():
    validator = MBAValidator()
    valid_a = """
def f(a, b):
    return a + b
"""
    valid_b = """
def f(a, b):
    return (a ^ b) + (2 * (a & b))
"""
    invalid_b = """
def f(a, b):
    return a - b
"""
    ta = ast.parse(valid_a)
    va = ast.parse(valid_b)
    ia = ast.parse(invalid_b)
    fa = ta.body[0]
    vf = va.body[0]
    invf = ia.body[0]
    validator.validate(fa, vf)
    validator.validate(fa, invf)
    assert validator.stats["attempted"] == 2
    assert validator.stats["passed"] == 1
    assert validator.stats["failed"] == 1
    assert validator.stats["total_time_ms"] > 0


def test_mba_pipeline_integration():
    from obfuscator.core.transforms import InstructionSubstitutor
    validator = MBAValidator()
    substitutor = InstructionSubstitutor(mba_validator=validator)
    code = """
def f():
    x = 3 + 5
    return x
"""
    tree = ast.parse(code)
    result = substitutor.visit(tree)
    result_code = ast.unparse(result)
    assert "x" in result_code


def test_mba_fallback():
    validator = MBAValidator()
    code_a = """
def f(a, b):
    return a + b
"""
    code_non_eq = """
def f(a, b):
    return a * b
"""
    ta = ast.parse(code_a)
    tn = ast.parse(code_non_eq)
    fa = ta.body[0]
    fn = tn.body[0]
    assert not validator.validate(fa, fn)


def test_validate_expressions_negative():
    validator = MBAValidator()
    import ast as py_ast
    expr_a = py_ast.parse("a + b", mode="eval").body
    expr_b = py_ast.parse("a - b", mode="eval").body
    assert not validator.validate_expressions(expr_a, expr_b)


def test_validate_expressions_custom_vars():
    validator = MBAValidator()
    import ast as py_ast
    expr_a = py_ast.parse("x + y", mode="eval").body
    expr_b = py_ast.parse("(x ^ y) + (2 * (x & y))", mode="eval").body
    assert validator.validate_expressions(expr_a, expr_b)


def test_validate_expressions_custom_vars_negative():
    validator = MBAValidator()
    import ast as py_ast
    expr_a = py_ast.parse("x + y", mode="eval").body
    expr_b = py_ast.parse("x * y", mode="eval").body
    assert not validator.validate_expressions(expr_a, expr_b)
