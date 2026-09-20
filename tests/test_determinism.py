"""Determinism test: same seed must give same transform output.

The reproducible-builds doc tells auditors to set SEED/--randomization-seed.
This test makes that claim real for the seed-sensitive AST passes: with
random.seed fixed, two fresh transformer instances must produce identical
output. (Covers SymbolRenamer, OpaquePredicateInjector, EnhancedJunkInserter
— the passes that draw from the global `random` module.)
"""
import ast
import random

from obfuscator.core.transforms import (
    EnhancedJunkInserter,
    OpaquePredicateInjector,
    SymbolRenamer,
)

SOURCE = """
def compute(a, b):
    total = a + b
    if total > 10:
        return total * 2
    return total

x = compute(3, 4)
"""


def _run_all(seed):
    random.seed(seed)
    tree = ast.parse(SOURCE)
    tree = SymbolRenamer().visit(tree)
    tree = OpaquePredicateInjector().visit(tree)
    tree = EnhancedJunkInserter().visit(tree)
    return ast.dump(tree)


def test_same_seed_same_output():
    assert _run_all(42) == _run_all(42)


def test_different_seed_usually_differs():
    assert _run_all(42) != _run_all(999)
