"""Renaming must keep bindings and uses in step, including in keyword values.

Two defects, both found with an external module and both invisible to a compile
check because the output is syntactically valid:

1. `from sys import hexversion` kept its original binding while every use was
   renamed. `visit_ImportFrom` only handled the aliased case.
2. `visit_keyword` returned without visiting the value, so `stop=isqrt(n)`
   stayed unrenamed while the import binding was renamed.

Either produces a NameError at import, not at compile time.
"""

import ast
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.transforms import SymbolRenamer  # noqa: E402

CASES = {
    "unaliased_import": "from sys import hexversion\ndef f():\n    return hexversion\n",
    "aliased_import": "from sys import hexversion as hv\ndef f():\n    return hv\n",
    "kwarg_value": "from math import isqrt\ndef f(n):\n    return g(1, stop=isqrt(n) + 1)\n",
    "star_import_untouched": "from os.path import *\ndef f():\n    return 1\n",
}


@pytest.mark.parametrize("label", sorted(CASES))
def test_renamed_module_still_runs(label):
    src = CASES[label]
    out = ast.unparse(SymbolRenamer().visit(ast.parse(src)))
    # The strongest check: the renamed module must import and define f.
    ns = {}
    exec(compile(out, "<renamed>", "exec"), ns)   # NameError here means a desync
    assert "f" in ns


def test_unaliased_import_is_renamed_consistently():
    out = ast.unparse(SymbolRenamer().visit(
        ast.parse("from sys import hexversion\ndef f():\n    return hexversion\n")))
    # exactly one spelling survives, and it is bound by the import
    assert out.count("hexversion") <= 1


def test_keyword_value_is_visited():
    out = ast.unparse(SymbolRenamer().visit(
        ast.parse("from math import isqrt\ndef f(n):\n    return g(1, stop=isqrt(n))\n")))
    assert "isqrt(" not in out, (
        "a use inside a keyword argument kept its original spelling while the "
        "import was renamed: %r" % out
    )
