"""Storage virtualization must rewrite every read of a virtualized name.

Regression for the 2026-11-15 bench finding. ``DataProtector._virtualize_storage``
moved a local binding into a shuffled slot list::

    bump = make_counter()   ->   _vs_1[_vmap_1[0]] = make_counter()

but the hand-written expression rewriter only covered ``Name``, ``BinOp``,
``UnaryOp``, ``Subscript``, call *arguments* and ``Compare``. A read in any
other position kept the original spelling, so the very next statement --
``bump()`` -- raised ``NameError`` at import and the whole payload died.

The same hole covered attribute receivers, boolops, f-strings, comprehensions,
``for`` targets, ``with ... as`` bindings, ``except ... as`` bindings, walrus
targets and ``del``. Two of those are *write* paths, which cannot be rewritten
into a slot at all, so those names are now excluded from virtualization
instead: ``total = 0; for total in range(4): pass; return total`` used to
return 0.

These tests pin both halves: reads are rewritten, and names with a second
write path are left alone.
"""
import ast
import contextlib
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.data_obfuscation.data_protector import DataProtector


def _protect(source):
    tree = DataProtector(level=3).protect(ast.parse(source))
    return ast.unparse(ast.fix_missing_locations(tree))


def _run(source):
    code = _protect(source)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(code, "<do>", "exec"), {"__name__": "__main__"})
    return buf.getvalue().strip(), code


def test_bare_call_target_is_rewritten():
    out, code = _run(
        "def make_counter():\n"
        "    count = 0\n"
        "    def bump():\n"
        "        nonlocal count\n"
        "        count += 1\n"
        "        return count\n"
        "    return bump\n"
        "def main():\n"
        "    bump = make_counter()\n"
        "    bump(); bump()\n"
        "    print(bump())\n"
        "main()\n"
    )
    assert out == "3"
    assert "_vs_" in code and "_vmap_" in code


def test_attribute_receiver_is_rewritten():
    out, _ = _run(
        "class Box:\n"
        "    def __init__(self):\n"
        "        self.v = 5\n"
        "def f():\n"
        "    b = Box()\n"
        "    return b.v\n"
        "print(f())\n"
    )
    assert out == "5"


def test_boolop_and_fstring_reads_are_rewritten():
    out, _ = _run(
        "def f():\n"
        "    a = 1\n"
        "    b = 2\n"
        '    return f"{a and b}-{a or b}"\n'
        "print(f())\n"
    )
    assert out == "2-1"


def test_comprehension_read_is_rewritten():
    out, _ = _run(
        "def f():\n"
        "    base = 3\n"
        "    return [base + i for i in range(3)]\n"
        "print(f())\n"
    )
    assert out == "[3, 4, 5]"


def test_augassign_is_rewritten():
    out, _ = _run(
        "def f():\n"
        "    n = 1\n"
        "    n += 4\n"
        "    n *= 2\n"
        "    return n\n"
        "print(f())\n"
    )
    assert out == "10"


def test_assignment_inside_if_body_is_rewritten():
    out, _ = _run(
        "def f(flag):\n"
        "    x = 0\n"
        "    if flag:\n"
        "        x = 9\n"
        "    return x\n"
        "print(f(True), f(False))\n"
    )
    assert out == "9 0"


def test_for_target_is_not_virtualized():
    out, _ = _run(
        "def f():\n"
        "    total = 0\n"
        "    for total in range(4):\n"
        "        pass\n"
        "    return total\n"
        "print(f())\n"
    )
    assert out == "3"


def test_with_as_target_is_not_virtualized():
    out, _ = _run(
        "def f():\n"
        "    h = None\n"
        '    with open("/etc/hostname") as h:\n'
        "        pass\n"
        "    return h is not None\n"
        "print(f())\n"
    )
    assert out == "True"


def test_walrus_target_is_not_virtualized():
    out, _ = _run(
        "def f():\n"
        "    n = 0\n"
        "    if (n := 5):\n"
        "        pass\n"
        "    return n\n"
        "print(f())\n"
    )
    assert out == "5"


def test_except_as_target_is_not_virtualized():
    # `except E as e` binds `e` through a plain string, not a Name node, so
    # the Store scan cannot see it. Virtualizing `e` left the handler reading
    # the stale slot value instead of the exception.
    out, _ = _run(
        "def f():\n"
        "    e = 'sentinel'\n"
        "    try:\n"
        "        raise ValueError('boom')\n"
        "    except ValueError as e:\n"
        "        caught = str(e)\n"
        "    return caught\n"
        "print(f())\n"
    )
    assert out == "boom"


def test_nested_closure_read_is_not_virtualized():
    out, _ = _run(
        "def f():\n"
        "    base = 3\n"
        "    def inner():\n"
        "        return base * 2\n"
        "    return inner()\n"
        "print(f())\n"
    )
    assert out == "6"


def test_nonlocal_binding_is_not_virtualized():
    out, _ = _run(
        "def make():\n"
        "    count = 0\n"
        "    def bump():\n"
        "        nonlocal count\n"
        "        count += 1\n"
        "        return count\n"
        "    return bump\n"
        "b = make()\n"
        "b(); b()\n"
        "print(b())\n"
    )
    assert out == "3"
