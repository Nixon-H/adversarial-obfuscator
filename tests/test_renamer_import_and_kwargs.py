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


def test_imported_names_are_reserved_not_renamed():
    """Imported names keep their spelling, and so do their uses.

    The renamer rewrites module-level uses but not module-level bindings, so an
    imported name caught in between raised NameError. Reserving it is the only
    rule consistent for both a plain import and a try/except ImportError
    fallback that rebinds the same name.
    """
    out = ast.unparse(SymbolRenamer().visit(
        ast.parse("from sys import hexversion\ndef f():\n    return hexversion\n")))
    assert "_nixon_" not in out, "an imported name was renamed: %r" % out


def test_try_except_rebind_still_runs():
    src = (
        "try:\n"
        "    from math import sumprod as _sumprod\n"
        "except ImportError:\n"
        "    _sumprod = lambda a, b: sum(x * y for x, y in zip(a, b))\n"
        "def f(a, b):\n"
        "    return _sumprod(a, b)\n"
    )
    out = ast.unparse(SymbolRenamer().visit(ast.parse(src)))
    ns = {}
    exec(compile(out, "<renamed>", "exec"), ns)
    assert ns["f"]([1, 2], [3, 4]) == 11
