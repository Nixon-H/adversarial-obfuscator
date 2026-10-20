import ast
import z3

from scripts.validation.ast_to_smt import ASTToSMT
from scripts.validation.equivalence import EquivalenceChecker
from scripts.validation.smt_validator import SMTValidator


def _translate_pair(code_a, code_b):
    ta = ASTToSMT()
    tb = ASTToSMT()
    fa = ta.translate(ast.parse(code_a))
    fb = tb.translate(ast.parse(code_b))
    return ta, tb, fa, fb


def test_ast_smt_simple_add():
    code = """
def f(x, y):
    return x + y
"""
    tree = ast.parse(code)
    translator = ASTToSMT()
    formula = translator.translate(tree)
    solver = z3.Solver()
    solver.add(formula)
    result = solver.check()
    assert result == z3.sat


def test_ast_smt_commutative_add():
    code_a = """
def f(x, y):
    return x + y
"""
    code_b = """
def f(x, y):
    return y + x
"""
    ta, tb, fa, fb = _translate_pair(code_a, code_b)
    x = z3.BitVec("x", 64)
    y = z3.BitVec("y", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [x, y], fa, fb)
    assert result.equivalent


def test_ast_smt_mul_vs_shift():
    code_mul = """
def f(x):
    return x * 2
"""
    code_shift = """
def f(x):
    return x << 1
"""
    ta, tb, fa, fb = _translate_pair(code_mul, code_shift)
    x = z3.BitVec("x", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [x], fa, fb)
    assert result.equivalent


def test_if_else_vs_ternary():
    code_if = """
def f(c, x, y):
    if c:
        return x
    else:
        return y
"""
    code_tern = """
def f(c, x, y):
    return x if c else y
"""
    ta, tb, fa, fb = _translate_pair(code_if, code_tern)
    c = z3.BitVec("c", 64)
    x = z3.BitVec("x", 64)
    y = z3.BitVec("y", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [c, x, y], fa, fb)
    assert result.equivalent


def test_mba_substitution_equivalence():
    code_original = """
def f(a, b):
    return a + b
"""
    code_mba = """
def f(a, b):
    return (a ^ b) + (2 * (a & b))
"""
    ta, tb, fa, fb = _translate_pair(code_original, code_mba)
    a = z3.BitVec("a", 64)
    b = z3.BitVec("b", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [a, b], fa, fb)
    assert result.equivalent


def test_mba_xor_identity():
    code_a = """
def f(a, b):
    return a ^ b
"""
    code_b = """
def f(a, b):
    return (a | b) - (a & b)
"""
    ta, tb, fa, fb = _translate_pair(code_a, code_b)
    a = z3.BitVec("a", 64)
    b = z3.BitVec("b", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [a, b], fa, fb)
    assert result.equivalent


def test_detect_semantic_diff():
    code_a = """
def f(x):
    return x + 1
"""
    code_b = """
def f(x):
    return x + 2
"""
    ta, tb, fa, fb = _translate_pair(code_a, code_b)
    x = z3.BitVec("x", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [x], fa, fb)
    assert not result.equivalent
    assert result.counterexample is not None


def test_detect_sub_vs_add_diff():
    code_a = """
def f(a, b):
    return a - b
"""
    code_b = """
def f(a, b):
    return a + b
"""
    ta, tb, fa, fb = _translate_pair(code_a, code_b)
    a = z3.BitVec("a", 64)
    b = z3.BitVec("b", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [a, b], fa, fb)
    assert not result.equivalent


def test_if_exp_equivalence():
    code_if = """
def f(c, x, y):
    return x if c else y
"""
    code_ifelse = """
def f(c, x, y):
    if c:
        return x
    else:
        return y
"""
    ta, tb, fa, fb = _translate_pair(code_if, code_ifelse)
    c = z3.BitVec("c", 64)
    x = z3.BitVec("x", 64)
    y = z3.BitVec("y", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [c, x, y], fa, fb)
    assert result.equivalent


def test_constant_folding_equivalence():
    code_orig = """
def f():
    return 42
"""
    code_folded = """
def f():
    return 21 + 21
"""
    ta, tb, fa, fb = _translate_pair(code_orig, code_folded)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [], fa, fb)
    assert result.equivalent


def test_smt_validator_ok():
    source = """
def f(x):
    return x * 2
"""
    from irgen.compile import compile_py_to_ir as py2ir
    ir_module = py2ir(source)
    validator = SMTValidator()
    result = validator.validate_source_vs_ir(source, ir_module)
    assert result.equivalent, f"Validator failed: {result.check_result.counterexample if result.check_result else result.error}"


def test_or_commutative():
    code_a = """
def f(a, b):
    return a | b
"""
    code_b = """
def f(a, b):
    return b | a
"""
    ta, tb, fa, fb = _translate_pair(code_a, code_b)
    a = z3.BitVec("a", 64)
    b = z3.BitVec("b", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [a, b], fa, fb)
    assert result.equivalent


def test_assignment_equivalence():
    code_a = """
def f(x):
    y = x + 1
    return y
"""
    code_b = """
def f(x):
    return x + 1
"""
    ta, tb, fa, fb = _translate_pair(code_a, code_b)
    x = z3.BitVec("x", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [x], fa, fb)
    assert result.equivalent


def test_comparison_chain():
    code = """
def f(x, y):
    return 1 if x == y else 0
"""
    tree = ast.parse(code)
    translator = ASTToSMT()
    translator.translate(tree)
    x = z3.BitVec("x", 64)
    y = z3.BitVec("y", 64)
    solver = z3.Solver()
    solver.add(translator.get_output_var() == z3.If(x == y, z3.BitVecVal(1, 64), z3.BitVecVal(0, 64)))
    assert solver.check() == z3.sat


def test_compare_lt():
    code_a = """
def f(x, y):
    return 1 if x < y else 0
"""
    code_b = """
def f(x, y):
    if x < y:
        return 1
    else:
        return 0
"""
    ta, tb, fa, fb = _translate_pair(code_a, code_b)
    x = z3.BitVec("x", 64)
    y = z3.BitVec("y", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [x, y], fa, fb)
    assert result.equivalent


def test_mba_xor_alt():
    code_a = """
def f(a, b):
    return a ^ b
"""
    code_b = """
def f(a, b):
    return (a | b) & (~a | ~b)
"""
    ta, tb, fa, fb = _translate_pair(code_a, code_b)
    a = z3.BitVec("a", 64)
    b = z3.BitVec("b", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [a, b], fa, fb)
    assert result.equivalent


def test_mba_add_via_or_and():
    code_a = """
def f(a, b):
    return a + b
"""
    code_b = """
def f(a, b):
    return (a | b) + (a & b)
"""
    ta, tb, fa, fb = _translate_pair(code_a, code_b)
    a = z3.BitVec("a", 64)
    b = z3.BitVec("b", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [a, b], fa, fb)
    assert result.equivalent


def test_obfuscated_equals_original_smt():
    """Real SMT check: verify obfuscation preserves semantics."""
    original = """
def f(x, y):
    return (x + y) * 2
"""
    obfuscated = """
def f(x, y):
    return (x << 1) + (y << 1)
"""
    ta, tb, fa, fb = _translate_pair(original, obfuscated)
    x = z3.BitVec("x", 64)
    y = z3.BitVec("y", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [x, y], fa, fb)
    assert result.equivalent, f"Obfuscated should be semantically equivalent: {result.counterexample}"


def test_smt_validator_rejects_broken():
    """SMT validator should detect semantic differences."""
    original = """
def f(x):
    return x * 2
"""
    broken = """
def f(x):
    return x * 3
"""
    ta, tb, fa, fb = _translate_pair(original, broken)
    x = z3.BitVec("x", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [x], fa, fb)
    assert not result.equivalent
    assert result.counterexample is not None


def test_mba_add_mba_sub():
    """MBA identity: a + b = (a ^ b) + 2*(a & b)"""
    code_a = """
def f(a, b):
    return a + b
"""
    code_b = """
def f(a, b):
    return (a ^ b) + 2 * (a & b)
"""
    ta, tb, fa, fb = _translate_pair(code_a, code_b)
    a = z3.BitVec("a", 64)
    b = z3.BitVec("b", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [a, b], fa, fb)
    assert result.equivalent


def test_mba_not_equivalent():
    """Verify that non-equivalent MBA patterns are rejected."""
    code_a = """
def f(a, b):
    return a + b
"""
    code_b = """
def f(a, b):
    return a - b
"""
    ta, tb, fa, fb = _translate_pair(code_a, code_b)
    a = z3.BitVec("a", 64)
    b = z3.BitVec("b", 64)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [a, b], fa, fb)
    assert not result.equivalent


def test_constant_folding_correctness():
    """Verify that constant folding is semantically neutral."""
    code_a = """
def f():
    return 42
"""
    code_b = """
def f():
    return 21 + 21
"""
    ta, tb, fa, fb = _translate_pair(code_a, code_b)
    checker = EquivalenceChecker()
    result = checker.check(ta.get_output_var(), tb.get_output_var(), [], fa, fb)
    assert result.equivalent


def test_smt_validator_wired():
    """End-to-end: SMTValidator correctly validates source vs IR."""
    from scripts.validation.smt_validator import SMTValidator
    from irgen.compile import compile_py_to_ir
    source = """
def f(x, y):
    return x ^ y
"""
    ir_module = compile_py_to_ir(source)
    validator = SMTValidator(timeout_ms=30000)
    result = validator.validate_source_vs_ir(source, ir_module)
    assert result.equivalent, f"Source vs IR should be equivalent: {result.error}"


def test_mba_validator_function():
    """MBAValidator should detect equivalent and non-equivalent functions."""
    from scripts.validation.mba_validator import MBAValidator
    import ast
    orig = "def f(a, b): return a + b"
    equiv = "def f(a, b): return (a ^ b) + 2 * (a & b)"
    nonequiv = "def f(a, b): return a - b"
    validator = MBAValidator()
    r1 = validator.validate(ast.parse(orig).body[0], ast.parse(equiv).body[0])
    assert r1, "MBA add should be equivalent"
    r2 = validator.validate(ast.parse(orig).body[0], ast.parse(nonequiv).body[0])
    assert not r2, "add vs sub should not be equivalent"
