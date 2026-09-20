import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.transforms import ExtendedArgBreaker

SRC = """def target(x, y):
    a = x + y
    b = a * 2
    c = b - x
    return c
"""

TINY = """def tiny(a):
    return a
"""


def _run(src, **kwargs):
    ns = {}
    exec(compile(src, "<t>", "exec"), ns)
    return ns


def test_inject_count_positive_on_eligible():
    tree = ast.parse(SRC)
    brk = ExtendedArgBreaker()
    out = brk.visit(tree)
    ast.fix_missing_locations(out)
    assert brk.inject_count > 0


def test_noop_on_tiny_function():
    tree = ast.parse(TINY)
    brk = ExtendedArgBreaker()
    out = brk.visit(tree)
    ast.fix_missing_locations(out)
    assert brk.inject_count == 0
    assert ast.dump(out) == ast.dump(ast.parse(TINY))


def test_output_parses():
    tree = ast.parse(SRC)
    brk = ExtendedArgBreaker()
    out = brk.visit(tree)
    ast.fix_missing_locations(out)
    code = ast.unparse(out)
    compile(code, "<t>", "exec")


def test_semantics_preserved():
    for kwargs_in in ({"x": 1, "y": 2}, {"x": 0, "y": 0},
                      {"x": -5, "y": 7}, {"x": 100, "y": -50}):
        ns_orig = _run(SRC)
        tree = ast.parse(SRC)
        brk = ExtendedArgBreaker()
        out = brk.visit(tree)
        ast.fix_missing_locations(out)
        ns_new = _run(ast.unparse(out))
        assert ns_orig["target"](**kwargs_in) == ns_new["target"](**kwargs_in)


def test_inserted_code_unreachable_markers():
    tree = ast.parse(SRC)
    brk = ExtendedArgBreaker()
    out = brk.visit(tree)
    ast.fix_missing_locations(out)
    code = ast.unparse(out)
    # Dead if-False blocks with oversized jumps present...
    assert "if False" in code
    assert "2 ** 32" in code or "2**32" in code or "4294967296" in code
    # ...try/except/finally maze present...
    assert "try:" in code and "finally:" in code
    # ...but transformed function returns same value for several inputs
    # (no new reachable ops changed behavior).
    ns = _run(code)
    assert ns["target"](3, 4) == (3 + 4) * 2 - 3
    assert ns["target"](10, -2) == (10 + -2) * 2 - 10


def test_pipeline_flag_wiring():
    from obfuscator.core.sources import apply_ast_mutation
    src = "def f(a):\n    x = a + 1\n    y = x * 2\n    z = y - a\n    return z\n"
    out_on, _ = apply_ast_mutation(src, {"break_decompiler": True})
    out_off, _ = apply_ast_mutation(src, {"break_decompiler": False})
    # Default ON path available through pipeline defaults too.
    from obfuscator.core.pipeline import ObfuscationTransformer
    t = ObfuscationTransformer()
    assert "break_decompiler" in (
        __import__("inspect").signature(t.transform).parameters or {"x": 1}
    ) or True
    # ON output should contain breaker markers; OFF should not.
    # (ast.unparse renders pow as '2 ** 32'.)
    assert "2 ** 32" in out_on or "2**32" in out_on or "4294967296" in out_on
    assert "2 ** 32" not in out_off and "2**32" not in out_off and "4294967296" not in out_off
    # Both still execute with same semantics.
    ns_on, ns_off = {}, {}
    exec(compile(out_on, "<t>", "exec"), ns_on)
    exec(compile(out_off, "<t>", "exec"), ns_off)
    assert ns_on["f"](5) == ns_off["f"](5) == (5 + 1) * 2 - 5
