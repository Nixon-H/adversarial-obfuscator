"""Batch-2: MBA levels — L1 single-identity, L2 current default, L3 deep.

L1 = chain depth exactly 1 + compare rewrites OFF.
L2 = chain depth 1..3 + compare rewrites at 50% (pre-existing default).
L3 = chain depth 3..5 + compare rewrites always ON.
"""

import ast
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from obfuscator.core.transforms import InstructionSubstitutor

SRC = """def f(a, b):
    x = 3 + 5
    y = 10 - 4
    z = x * 2
    w = 7 + 8
    v = 20 - 6
    return x + y + z + w + v
"""


def _exec(src):
    ns = {}
    exec(compile(src, "<t>", "exec"), ns)
    return ns


def _transform(src, level, seed):
    random.seed(seed)
    tree = ast.parse(src)
    sub = InstructionSubstitutor(level=level)
    out = sub.visit(tree)
    ast.fix_missing_locations(out)
    return ast.unparse(out), sub


def test_default_is_level2():
    sub = InstructionSubstitutor()
    assert sub.level == 2


def test_invalid_level_raises():
    with pytest.raises(ValueError):
        InstructionSubstitutor(level=0)
    with pytest.raises(ValueError):
        InstructionSubstitutor(level=9)
    with pytest.raises(ValueError):
        InstructionSubstitutor(level=True)


def test_level1_output_parses_and_preserves_semantics():
    for seed in (1, 2, 3):
        code, _ = _transform(SRC, level=1, seed=seed)
        compile(code, "<t>", "exec")  # parses
        ns_orig = _exec(SRC)
        ns_new = _exec(code)
        assert ns_orig["f"](3, 4) == ns_new["f"](3, 4)
        assert ns_orig["f"](0, 0) == ns_new["f"](0, 0)


def test_level3_output_parses_and_preserves_semantics():
    for seed in (1, 2, 3):
        code, _ = _transform(SRC, level=3, seed=seed)
        compile(code, "<t>", "exec")
        ns_orig = _exec(SRC)
        ns_new = _exec(code)
        assert ns_orig["f"](3, 4) == ns_new["f"](3, 4)


def test_level3_injects_at_least_level1():
    # Same seeds, aggregate over several runs: L3 (depth 3-5 + always-on
    # compares) must produce >= output growth vs L1 (depth 1, compares off).
    tot1 = tot3 = 0
    for seed in range(10):
        c1, _ = _transform(SRC, level=1, seed=seed)
        c3, _ = _transform(SRC, level=3, seed=seed)
        tot1 += len(c1)
        tot3 += len(c3)
    assert tot3 >= tot1, (tot1, tot3)


def test_levels_wired_from_options():
    from obfuscator.core.sources import apply_ast_mutation

    src = "def f():\n    x = 3 + 5\n    return x\n"
    for level in (1, 2, 3):
        out, _ = apply_ast_mutation(
            src, {"mba_subs": True, "mba_level": level, "break_decompiler": False})
        compile(out, "<t>", "exec")
    with pytest.raises(ValueError):
        apply_ast_mutation(src, {"mba_subs": True, "mba_level": 9})
