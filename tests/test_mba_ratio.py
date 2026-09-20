"""Batch-4: MBA ratio check — level3 output size >= level1 (close INVESTIGATE).

The transformer (InstructionSubstitutor) takes no seed argument; it uses the
global ``random`` module, so tests set ``random.seed`` for determinism.
"""

import ast
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.transforms import InstructionSubstitutor

SRC = """def f(a, b):
    x = 3 + 5
    y = 10 - 4
    z = x * 2
    w = 7 + 8
    v = 20 - 6
    return x + y + z + w + v
"""


def _transform(src, level, seed):
    random.seed(seed)
    tree = ast.parse(src)
    sub = InstructionSubstitutor(level=level)
    out = sub.visit(tree)
    ast.fix_missing_locations(out)
    return ast.unparse(out)


def test_level3_size_gte_level1_fixed_seed():
    c1 = _transform(SRC, level=1, seed=1234)
    c3 = _transform(SRC, level=3, seed=1234)
    compile(c1, "<t>", "exec")
    compile(c3, "<t>", "exec")
    assert len(c3) >= len(c1), (len(c1), len(c3))


def test_level3_size_gte_level1_aggregate():
    tot1 = tot3 = 0
    for seed in range(3):
        tot1 += len(_transform(SRC, level=1, seed=seed))
        tot3 += len(_transform(SRC, level=3, seed=seed))
    assert tot3 >= tot1, (tot1, tot3)
