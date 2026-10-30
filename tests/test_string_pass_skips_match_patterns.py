"""String obfuscation must not rewrite match patterns.

A constant pattern matches a value. Replacing the constant with an encoded
lookup turns it into a CAPTURE pattern, which binds a name — and two
alternatives then bind different names, which CPython rejects:

    case 'normal' | 'gauss':   ->   case _n(A) | _n(B):   SyntaxError

Found with cpython's statistics.py, which dispatches on string patterns. The
failure is a compile error in the OUTPUT, so it is invisible to any test that
only compiles the input.
"""

import ast
import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.transforms import StringLiteralObfuscator  # noqa: E402

MATCH_SRC = '''def f(v):
    match v:
        case 'normal' | 'gauss':
            return 1
        case 'rectangular' | 'uniform':
            return 2
        case _:
            return 0
'''


def test_match_patterns_stay_literals():
    out = ast.unparse(StringLiteralObfuscator().visit(ast.parse(MATCH_SRC)))
    assert "'normal'" in out or '"normal"' in out, (
        "the string pattern was rewritten; a constant pattern becomes a capture "
        "and CPython rejects alternative patterns binding different names"
    )


def test_obfuscated_match_module_compiles():
    out = ast.unparse(StringLiteralObfuscator().visit(ast.parse(MATCH_SRC)))
    compile(out, "<generated>", "exec")     # SyntaxError means the regression


def test_ordinary_strings_are_still_obfuscated():
    src = "def f():\n    return 'a string long enough to encode'\n"
    out = ast.unparse(StringLiteralObfuscator().visit(ast.parse(src)))
    assert "a string long enough to encode" not in out, (
        "excluding match patterns must not disable string obfuscation entirely"
    )
