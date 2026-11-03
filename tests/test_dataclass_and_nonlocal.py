"""Regressions found by the constructs payload (2026-11-03).

Three separate transform bugs, all of the "one authority per name" shape this
project keeps meeting:

* a dataclass with any method lost every field, because the guard only kept
  bare annotations when they were the class's ENTIRE body;
* a dataclass field was renamed in its declaration but not in `self.x`
  accesses, raising AttributeError at runtime;
* a `nonlocal` name was encoded in one place and not the other, raising
  "SyntaxError: no binding for nonlocal 'count' found" at import.
"""
import contextlib
import io

import pytest

from obfuscator.core.sources import apply_ast_mutation

DATACLASS_WITH_METHOD = '''import dataclasses


@dataclasses.dataclass
class P:
    x: int
    y: int

    def total(self):
        return self.x + self.y


print("sum:", P(3, 4).total())
print("field:", P(1, 2).x)
print("OK")
'''

CLOSURE = '''def make_counter():
    count = 0

    def bump():
        nonlocal count
        count += 1
        return count

    return bump


bump = make_counter()
bump()
print("closure:", bump())
print("OK")
'''

GLOBAL = '''counter = 0


def bump():
    global counter
    counter += 1
    return counter


bump()
print("global:", bump())
print("OK")
'''


def _run(code, name):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(code, name, "exec"), {"__name__": "__main__"})
    return buf.getvalue()


EXPECTED_DC = _run(DATACLASS_WITH_METHOD, "<src>")
EXPECTED_CLOSURE = _run(CLOSURE, "<src>")
EXPECTED_GLOBAL = _run(GLOBAL, "<src>")


@pytest.mark.parametrize("level", [0, 1, 3, 5])
def test_dataclass_fields_survive_a_method(level):
    out, _ = apply_ast_mutation(DATACLASS_WITH_METHOD, {"opt_level": level})
    assert "x: int" in out and "y: int" in out, (
        "dataclass fields were deleted; @dataclass will synthesise __init__(self)")
    assert _run(out, "<dc%d>" % level) == EXPECTED_DC


@pytest.mark.parametrize("level", [0, 1, 3, 5])
def test_closure_over_nonlocal_still_binds(level):
    out, _ = apply_ast_mutation(CLOSURE, {"opt_level": level})
    compile(out, "<cl>", "exec")
    assert _run(out, "<cl%d>" % level) == EXPECTED_CLOSURE


@pytest.mark.parametrize("level", [0, 1, 3, 5])
def test_global_declaration_still_binds(level):
    out, _ = apply_ast_mutation(GLOBAL, {"opt_level": level})
    compile(out, "<gl>", "exec")
    assert _run(out, "<gl%d>" % level) == EXPECTED_GLOBAL
