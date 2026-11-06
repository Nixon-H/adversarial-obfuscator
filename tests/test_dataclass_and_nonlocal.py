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


def test_nested_function_coverage_follows_actual_capture():
    """Nested functions are eligible unless they really do capture.

    The JIT transform replays a function's source in a fresh namespace built from
    dict(globals()), which provides module globals but not an enclosing function's
    locals. Excluding every nested function for that reason discarded the whole
    population, including the ones that capture nothing and replay perfectly well.

    The gate is now the actual condition: does the body load a name bound by an
    enclosing function scope?
    """
    import ast
    from obfuscator.core.transforms import _bound_names, _captures_enclosing

    src = (
        "def outer():\n"
        "    fn = 1\n"
        "    def closes_over_fn():\n"
        "        return fn\n"
        "    def standalone():\n"
        "        y = 2\n"
        "        return y\n"
    )
    outer = ast.parse(src).body[0]
    stack = [_bound_names(outer)]
    by_name = {n.name: n for n in outer.body if isinstance(n, ast.FunctionDef)}

    assert _captures_enclosing(by_name["closes_over_fn"], stack) is True
    assert _captures_enclosing(by_name["standalone"], stack) is False, (
        "a nested function that captures nothing must remain eligible")


def test_a_capturing_closure_is_transformed_only_when_its_free_names_are_injectable():
    """Closures that READ their free variables are transformable now.

    The wrapper is emitted in the same scope as the original def, so each free
    name is resolvable there and can be placed in the exec namespace before the
    template runs. Reading a cell is the same as reading its current value, so
    semantics are preserved.

    `nonlocal` stays excluded: the replayed copy would rebind a local instead of
    the cell, which the injection cannot reproduce.
    """
    import ast
    import random
    from obfuscator.core.transforms import DynamicCodeGenerator

    read_only = (
        "def cached(fn):\n"
        "    store = {}\n"
        "    def wrapper(*args):\n"
        "        if args not in store:\n"
        "            store[args] = fn(*args)\n"
        "        return store[args]\n"
        "    return wrapper\n"
        "@cached\n"
        "def sq(n):\n"
        "    return n * n\n"
        "RESULT = sq(3)\n"
    )
    random.seed(1)
    out = ast.unparse(DynamicCodeGenerator().visit(ast.parse(read_only)))
    ns = {}
    exec(compile(out, "<closure-jit>", "exec"), ns)
    assert ns["RESULT"] == 9, "the transformed closure must still compute correctly"
    assert "sq(3)" not in out or "_ns[" in out, "the closure should have been wrapped"

    writes_nonlocal = (
        "def make_counter():\n"
        "    count = 0\n"
        "    def bump():\n"
        "        nonlocal count\n"
        "        count += 1\n"
        "        return count\n"
        "    return bump\n"
        "C = make_counter()\n"
        "RESULT = [C(), C()]\n"
    )
    random.seed(1)
    out2 = ast.unparse(DynamicCodeGenerator().visit(ast.parse(writes_nonlocal)))
    ns2 = {}
    exec(compile(out2, "<nonlocal-jit>", "exec"), ns2)
    assert ns2["RESULT"] == [1, 2]
