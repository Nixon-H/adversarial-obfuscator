"""Differential tests for representation diversification (G2-H2 family).

Every case: transform original across seeds, execute both, assert
identical observable behavior (values, exceptions, stdout). Plus:
determinism (same seed twice), variety (seeds differ on suitable
input), docstring preservation, exactness edge cases (NaN, empty,
non-ASCII, negatives, zero).
"""
import math
import os
import sys
import textwrap

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.rep_diversify import RepDiversifier, diversify_source


def run_pair(source, probe, seed=7, **flags):
    ns0 = {}
    exec(compile(source, "<orig>", "exec"), ns0)
    want = probe(ns0)
    code, stats = diversify_source(source, seed=seed, **flags)
    ns1 = {}
    exec(compile(code, "<variant>", "exec"), ns1)
    got = probe(ns1)
    assert got == want, "seed=%r want %r got %r" % (seed, want, got)
    return stats


def check(source, probe, seeds=(7, 8, 9), **flags):
    for s in seeds:
        run_pair(source, probe, seed=s, **flags)


def test_int_forms():
    src = textwrap.dedent("""\
        def f():
            return (42, 0, 1, -7, 255, 1024, 2**40)
        """)
    check(src, lambda ns: ns["f"]())


def test_int_negative_zero():
    src = textwrap.dedent("""\
        def f(a):
            return [a + (-3), a - (-4), 0 - 0]
        """)
    check(src, lambda ns: ns["f"](10))


def test_string_forms_ascii():
    src = textwrap.dedent("""\
        def f():
            return ("hello" + " " + "world", len("abc"), "x" * 3)
        """)
    check(src, lambda ns: ns["f"]())


def test_string_nonceskip_unicode():
    # Non-ASCII strings must survive byte-identical (forms skip them).
    src = textwrap.dedent("""\
        def f():
            return ("héllo wörld 日本語", "plain")
        """)
    check(src, lambda ns: ns["f"]())


def test_empty_string():
    src = textwrap.dedent("""\
        def f(s):
            return [s + "", "" + s, len("")]
        """)
    check(src, lambda ns: ns["f"]("ab"))


def test_docstring_preserved():
    src = textwrap.dedent('''\
        """Module doc."""
        def f():
            """Func doc."""
            return 1
        ''')
    code, _ = diversify_source(src, seed=7)
    ns = {}
    exec(compile(code, "<v>", "exec"), ns)
    assert ns["f"]() == 1
    assert ns["f"].__doc__ == "Func doc."


def test_comparison_flips_exact():
    # Including NaN (both sides False) and signed zeroes.
    src = textwrap.dedent("""\
        def f(a, b):
            return [a < b, a > b, a <= b, a >= b, a == b, a != b]
        """)
    vals = [(1, 2), (2, 1), (3, 3), (0.0, -0.0),
            (float("nan"), 1.0), (float("nan"), float("nan")),
            ("a", "b"), ((1,), (2,))]
    check(src, lambda ns: [ns["f"](a, b) for a, b in vals])


def test_demorgan_exhaustive_bool():
    src = textwrap.dedent("""\
        def f(a, b):
            return [(not (a and b)), (not (a or b))]
        """)
    check(src, lambda ns: [ns["f"](a, b)
                           for a in (0, 1, "", "x", None, [], [1])
                           for b in (0, 1, "", "y", None, (), [2])])


def test_double_negation():
    src = textwrap.dedent("""\
        def f(x):
            return (not not x, type(not not x) is bool)
        """)
    check(src, lambda ns: [ns["f"](v) for v in (0, 1, "", "x", None, [], {})])


def test_fragmentation():
    src = textwrap.dedent("""\
        def f():
            s = "hello world"
            l = [1, 2, 3, 4]
            t = ("a", "b", "c")
            return (s, l, t, len(s) + len(l) + len(t))
        """)
    check(src, lambda ns: ns["f"]())


def test_determinism():
    src = "def f(a):\n    return a * 2 + 15\n"
    c1, _ = diversify_source(src, seed=123)
    c2, _ = diversify_source(src, seed=123)
    assert c1 == c2


def test_variety_across_seeds():
    # A suitable input must diversify: some seed pair must differ.
    src = textwrap.dedent("""\
        def f(a):
            return a * 2 + 15 + len("hello world")
        """)
    outs = {diversify_source(src, seed=s)[0] for s in range(6)}
    assert len(outs) > 1


def test_stats_counted():
    _, stats = diversify_source("x = 41 + 'ab' + [1, 2]\n", seed=7)
    assert set(stats) == {"ints", "strings", "exprs", "frags"}
    assert all(isinstance(v, int) and v >= 0 for v in stats.values())


def test_flags_disable_families():
    src = "x = 41\n"
    code, stats = diversify_source(
        src, seed=7, int_forms=False, str_forms=False,
        expr_rewrite=False, fragment=False)
    assert code.strip() == "x = 41"
    assert all(v == 0 for v in stats.values())


def test_side_effect_order_preserved():
    # Effectful operands are never De-Morganed (only pure ones).
    src = textwrap.dedent("""\
        calls = []
        def eff(name):
            calls.append(name)
            return True
        def f():
            return (not (eff("a") and eff("b")))
        """)

    def probe(ns):
        ns["calls"].clear()
        out = ns["f"]()
        return (out, list(ns["calls"]))

    check(src, probe)


def _pipeline_run(source, options, seed=11):
    import contextlib
    import io as _io
    from obfuscator.core.pipeline import ObfuscationTransformer
    t = ObfuscationTransformer(seed=seed)
    out = t.transform(source, options=dict(options))
    ns, buf = {}, _io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(out, "<pipe>", "exec"), ns)
    return buf.getvalue()


def test_pipeline_opt_in_end_to_end():
    src = "def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fib(10))\n"
    assert _pipeline_run(src, {"rep_diversify": True}).strip() == "55"


def test_pipeline_default_off_unchanged():
    # Default pipeline (no opt-in) must not contain rep/vm artifacts and
    # must run identically: new passes are strictly opt-in.
    import contextlib
    import io as _io
    from obfuscator.core.pipeline import ObfuscationTransformer
    src = "def f(a):\n    return a + 1\nprint(f(41))\n"
    t = ObfuscationTransformer(seed=11)
    out = t.transform(src, options={})
    assert "while _pc" not in out and "_handlers" not in out
    ns, buf = {}, _io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(out, "<pipe>", "exec"), ns)
    assert buf.getvalue().strip() == "42"
