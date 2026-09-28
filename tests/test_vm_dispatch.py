"""Differential tests for VM-A / VM-B dispatchers (G2-H3/H4 families).

Every eligible program: original vs VM-A vs VM-B across seeds must
agree exactly (values AND exception types/messages). Ineligible
programs pass through untouched. Encodings/layouts differ per seed.
Error behavior (ZeroDivisionError, unpack ValueError, range
TypeError/ValueError) is asserted exactly — a protection that changes
semantics is a broken compiler.
"""
import os
import sys
import textwrap

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.vm_dispatch import (
    _eligible,
    _encoding,
    compile_function,
    virtualize_source,
)
import ast


def run_all(source, *argsets, seeds=(7, 8), families=("a", "b")):
    """Returns {(family, seed, argset): outcome} where outcome is a value
    or 'ExcType:msg' string. Original outcome computed the same way."""
    results = {}
    ns0 = {}
    exec(compile(source, "<orig>", "exec"), ns0)
    fn0 = [v for v in ns0.values() if callable(v)][0]

    def outcome(fn, args):
        try:
            return ("ok", fn(*args))
        except Exception as e:
            return ("exc", "%s:%s" % (type(e).__name__, str(e)[:60]))

    for idx, args in enumerate(argsets):
        results[("orig", None, idx)] = outcome(fn0, args)
    for fam in families:
        for s in seeds:
            code, stats = virtualize_source(source, seed=s, family=fam)
            ns = {}
            exec(compile(code, "<vm>", "exec"), ns)
            fns = [v for v in ns.values() if callable(v)]
            assert len(fns) == 1
            for idx, args in enumerate(argsets):
                results[(fam, s, idx)] = outcome(fns[0], args)
    return results


def assert_agree(source, *argsets, seeds=(7, 8)):
    r = run_all(source, *argsets, seeds=seeds)
    for (fam, s, idx), v in r.items():
        if fam == "orig":
            continue
        want = r[("orig", None, idx)]
        if isinstance(want[1], float) and isinstance(v[1], float):
            assert v[0] == "ok" and want[1] == v[1]
        else:
            assert v == want, "%s %s args=%r: %r != %r" % (fam, s, argsets[idx], v, want)


def test_fib_gcd_fact():
    assert_agree(
        "def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n"
        "        a, b = b, a + b\n    return a\n", (0,), (1,), (10,), (20,))
    assert_agree(
        "def gcd(a, b):\n    while b:\n        a, b = b, a % b\n    return a\n",
        (48, 18), (7, 7), (0, 5))
    assert_agree(
        "def fact(n):\n    r = 1\n    for i in range(1, n + 1):\n"
        "        r = r * i\n    return r\n", (0,), (1,), (6,))


def test_branches_loops_nested():
    assert_agree(
        "def sgn(x):\n    if x > 0:\n        return 1\n"
        "    elif x < 0:\n        return -1\n    else:\n        return 0\n",
        (-5,), (0,), (9,))
    assert_agree(
        "def f(n):\n    t = 0\n    for i in range(n):\n"
        "        for j in range(i):\n            t = t + 1\n    return t\n",
        (0,), (1,), (5,))
    assert_agree(
        "def f(n):\n    t = []\n    for i in range(n, 0, -1):\n"
        "        t = t + [i]\n    return t\n", (0,), (4,))


def test_operators_and_errors():
    assert_agree(
        "def f(a, b):\n    return (a + b, a - b, a * b, a % b, a == b, a != b, a < b, a >= b, a is b, a is not b, not a, -a)\n",
        (7, 3), (0, 0))
    # Error parity: exact exception type propagation.
    assert_agree(
        "def f(a, b):\n    return a / b\n", (1, 0))
    assert_agree(
        "def f(v):\n    a, b = v\n    return a\n", ((1, 2, 3),), ((),))
    assert_agree(
        "def f(n):\n    t = 0\n    for i in range(n):\n        t = t + i\n    return t\n",
        ("x",), ([1],))


def test_range_edge_cases():
    assert_agree(
        "def f(a, b, c):\n    t = 0\n    for i in range(a, b, c):\n"
        "        t = t + 1\n    return t\n",
        (0, 5, 2), (5, 0, -2), (0, 5, 0), (0, 5, 0.5), (0, 0, 1))
    assert_agree(
        "def f(n):\n    t = (1, 2)\n    u = [3]\n    return (t, u, None, True)\n",
        (0,))


def test_bool_logic():
    assert_agree(
        "def f(a, b):\n    x = a and b\n    y = a or b\n"
        "    z = x if y else not x\n    return (x, y, z)\n",
        (0, 0), (0, 5), (3, 0), ("", None), ([1], [2]))


def test_defaults_posonly_docstring():
    src = textwrap.dedent('''\
        def f(a, b=10, /, c=20):
            """Compute it."""
            return a + b + c
        ''')
    assert_agree(src, (1,), (1, 2), (1, 2, 3))
    for fam in ("a", "b"):
        code, _ = virtualize_source(src, seed=7, family=fam)
        ns = {}
        exec(compile(code, "<v>", "exec"), ns)
        fn = [v for v in ns.values() if callable(v)][0]
        assert fn.__doc__ == "Compute it."
        import inspect
        assert str(inspect.signature(fn)) == "(a, b=10, /, c=20)"


def test_ineligible_untouched():
    cases = [
        "def f(g, x):\n    return g(x)\n",                      # call
        "def f():\n    x = 1\n    def g():\n        return x\n    return g()\n",  # closure
        "def f():\n    global Q\n    Q = 1\n    return Q\n",     # global
        "def f(*a):\n    return a\n",                            # vararg
        "def f(**k):\n    return k\n",                           # kwarg
        "async def f():\n    return 1\n",                        # async
        "def f(x):\n    return x.attr\n",                        # attribute
        "def f(x):\n    return x[0]\n",                          # subscript
        "def f(x):\n    y = yield x\n    return y\n",            # yield
        "def f(x):\n    try:\n        return x\n    except Exception:\n        return 0\n",  # try
        "@deco\ndef f():\n    return 1\n",                       # decorated
        "def f(x):\n    import os\n    return x\n",              # import
        "def f(x):\n    break\n",                                # break (also invalid, but must not crash transform)
    ]
    for src in cases:
        for fam in ("a", "b"):
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            fn = tree.body[0]
            if fn.__class__.__name__ != "FunctionDef":
                continue
            assert not _eligible(fn), "should be ineligible: %r" % src[:40]
            code, stats = virtualize_source(src, seed=7, family=fam)
            assert stats["virtualized"] == 0, src[:40]


def test_determinism_and_variety():
    src = "def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n"
    a1, _ = virtualize_source(src, seed=5, family="a")
    a2, _ = virtualize_source(src, seed=5, family="a")
    assert a1 == a2
    b1, _ = virtualize_source(src, seed=6, family="a")
    assert a1 != b1
    # A and B differ structurally (dispatcher organization).
    va, _ = virtualize_source(src, seed=5, family="a")
    vb, _ = virtualize_source(src, seed=5, family="b")
    assert "elif _op" in va and "_handlers" in vb
    assert va != vb


def test_encoding_differs_per_seed():
    e1 = _encoding("s1", "a")
    e2 = _encoding("s2", "a")
    assert e1 != e2
    assert sorted(e1.values()) == sorted(e2.values())
    assert set(e1) == set(__import__("obfuscator.vm_dispatch", fromlist=["OPS"]).OPS)


def test_probability_zero_untouched():
    from obfuscator.vm_dispatch import virtualize_source as vs
    src = "def f(a):\n    return a + 1\n"
    code, stats = vs(src, seed=7, family="a", probability=0.0)
    assert stats["virtualized"] == 0
    assert "while _pc" not in code and "_handlers" not in code


def test_empty_and_trivial():
    assert_agree("def f():\n    return 42\n", ())
    assert_agree("def f():\n    pass\n", ())
    assert_agree("def f(a):\n    x = a\n    return x\n", (7,))


def test_pipeline_opt_in_end_to_end():
    import contextlib
    import io as _io
    from obfuscator.core.pipeline import ObfuscationTransformer
    src = ("def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n"
           "        a, b = b, a + b\n    return a\nprint(fib(10))\n")
    for fam in ("a", "b"):
        t = ObfuscationTransformer(seed=11)
        out = t.transform(src, options={"vm_dispatch": fam})
        ns, buf = {}, _io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(compile(out, "<pipe>", "exec"), ns)
        assert buf.getvalue().strip() == "55", fam
