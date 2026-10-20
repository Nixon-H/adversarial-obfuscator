"""Differential semantic tests for the renamer (G2 follow-up).

Every case: transform source with the rename pipeline, execute both
original and transformed, assert identical observable behavior.
Covers: for-targets, tuple/list unpacking, comprehensions, nested
scopes, closures, global/nonlocal, exception targets, imports,
class bodies, pattern matching, augassign, decorators, kwargs,
while/with, del, AnnAssign, starred unpacking, walrus.

Top-level def/class names are positionally mapped (original order ->
variant order) since renaming changes names but must preserve count
and order. A count mismatch fails loudly.

These lock the renamer repair: any case failing here is a
semantic-preservation defect, not an obfuscation trade-off.
"""
import ast as _ast
import os
import sys
import textwrap


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.diversity.generator import generate_variant

PASSES = ["rename"]


def _top_defs(source):
    tree = _ast.parse(source)
    return [n.name for n in tree.body
            if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef))]


def run_both(source, probe, seed=7):
    """Transform + exec original and variant; return (want, got, code)."""
    ns_want = {}
    exec(compile(source, "<orig>", "exec"), ns_want)
    want_names = _top_defs(source)
    code = generate_variant(source, 0, {"master_seed": seed, "pass_sets": [PASSES]})
    ns_got = {}
    exec(compile(code, "<variant>", "exec"), ns_got)
    got_names = _top_defs(code)
    assert len(got_names) == len(want_names), (
        "top-level def count changed: %s -> %s" % (want_names, got_names))
    mapping = dict(zip(want_names, got_names))
    want = probe(ns_want, {n: n for n in want_names})
    got = probe(ns_got, mapping)
    return want, got, code


def check(source, probe, seed=7):
    want, got, _ = run_both(source, probe, seed)
    assert got == want, "want %r got %r" % (want, got)


def test_for_target():
    src = textwrap.dedent("""\
        def total(xs):
            s = 0
            for v in xs:
                s = s + v
            return s
        """)
    check(src, lambda ns, m: ns[m["total"]]([1, 2, 3, 4]))


def test_tuple_unpack_loop():
    src = textwrap.dedent("""\
        def fib(n):
            a, b = 0, 1
            for _ in range(n):
                a, b = b, a + b
            return a
        """)
    check(src, lambda ns, m: ns[m["fib"]](10))


def test_list_unpack():
    src = textwrap.dedent("""\
        def first(pair):
            [x, y] = pair
            return x - y
        """)
    check(src, lambda ns, m: ns[m["first"]]([9, 4]))


def test_comprehension():
    src = textwrap.dedent("""\
        def squares(n):
            return [i * i for i in range(n)]
        def total(m):
            return sum(v for v in m.values())
        """)
    check(src, lambda ns, m: (ns[m["squares"]](5), ns[m["total"]]({"a": 1, "b": 2})))


def test_nested_scope():
    src = textwrap.dedent("""\
        def outer(x):
            y = x + 1
            def inner(z):
                return y + z
            return inner(10)
        """)
    check(src, lambda ns, m: ns[m["outer"]](5))


def test_closure():
    src = textwrap.dedent("""\
        def counter():
            n = 0
            def bump():
                nonlocal n
                n = n + 1
                return n
            return bump
        """)

    def probe(ns, m):
        b = ns[m["counter"]]()
        return (b(), b(), b())

    check(src, probe)


def test_global():
    src = textwrap.dedent("""\
        COUNT = 0
        def tick():
            global COUNT
            COUNT = COUNT + 1
            return COUNT
        """)

    def probe(ns, m):
        ns[m["tick"]]()
        return ns[m["tick"]]()

    check(src, probe)


def test_except_target():
    src = textwrap.dedent("""\
        def risky(flag):
            try:
                if flag:
                    raise ValueError("boom")
                return "ok"
            except ValueError as err:
                return "caught:" + str(err)
        """)
    check(src, lambda ns, m: (ns[m["risky"]](True), ns[m["risky"]](False)))


def test_imports():
    src = textwrap.dedent("""\
        import math as m
        from collections import Counter as C
        def hyp(a, b):
            return m.hypot(a, b)
        def freq(xs):
            return dict(C(xs))
        """)
    check(src, lambda ns, m: (ns[m["hyp"]](3, 4), ns[m["freq"]]("aab")))


def test_class_body():
    src = textwrap.dedent("""\
        class Box:
            kind = "box"
            def __init__(self, v):
                self.v = v
            def get(self):
                return (self.kind, self.v)
        """)
    check(src, lambda ns, m: ns[m["Box"]](7).get())


def test_pattern_matching():
    src = textwrap.dedent("""\
        def describe(cmd):
            match cmd:
                case ["go", dest]:
                    return "go:" + dest
                case ["stop"]:
                    return "stop"
                case _:
                    return "unknown"
        """)
    check(src, lambda ns, m: (ns[m["describe"]](["go", "x"]), ns[m["describe"]](["stop"]), ns[m["describe"]]([1])))


def test_augassign():
    src = textwrap.dedent("""\
        def acc(xs):
            t = 0
            for v in xs:
                t += v
            t *= 2
            return t
        """)
    check(src, lambda ns, m: ns[m["acc"]]([1, 2, 3]))


def test_decorator():
    src = textwrap.dedent("""\
        def tag(fn):
            fn.tagged = True
            return fn
        @tag
        def work(x):
            return x * 3
        """)
    check(src, lambda ns, m: (ns[m["work"]](4), ns[m["work"]].tagged))


def test_kwargs_call():
    src = textwrap.dedent("""\
        def f(a, b=2, *args, **kwargs):
            return (a, b, args, sorted(kwargs.items()))
        """)
    check(src, lambda ns, m: ns[m["f"]](1, b=5, x=9))


def test_while_with():
    src = textwrap.dedent("""\
        import io
        def drain(n):
            out = []
            while n > 0:
                out.append(n)
                n = n - 1
            return out
        def read_text():
            buf = io.StringIO("hi")
            with buf as fh:
                return fh.read()
        """)
    check(src, lambda ns, m: (ns[m["drain"]](3), ns[m["read_text"]]()))


def test_del_annassign():
    src = textwrap.dedent("""\
        def cleanup(d):
            x: int = d.pop("k")
            if "gone" in d:
                del d["gone"]
            return x
        """)
    check(src, lambda ns, m: ns[m["cleanup"]]({"k": 42}))


def test_starred_walrus():
    src = textwrap.dedent("""\
        def head(xs):
            first, *rest = xs
            return (first, len(rest))
        def twice(x):
            return (y := x * 2, y + 1)
        """)
    check(src, lambda ns, m: (ns[m["head"]]([1, 2, 3]), ns[m["twice"]](5)))


def test_lambda_params():
    """Lambda-bound names must agree between def and use sites."""
    src = textwrap.dedent("""\
        def apply_twice(f, x):
            g = lambda v: v * 2
            return g(x) + 1
        def with_default(n, f=lambda v: v + 1):
            return f(n)
        """)
    check(src, lambda ns, m: (ns[m["apply_twice"]](None, 21), ns[m["with_default"]](10)))


def test_module_order_preserved():
    """Definition-before-use at module level must survive (G2 bug 1)."""
    src = textwrap.dedent("""\
        def fib(n):
            a, b = 0, 1
            for _ in range(n):
                a, b = b, a + b
            return a
        RESULT = fib(10)
        """)
    ns = {}
    exec(compile(src, "<orig>", "exec"), ns)
    assert ns["RESULT"] == 55
    code = generate_variant(src, 0, {"master_seed": 7, "pass_sets": [PASSES]})
    ns2 = {}
    exec(compile(code, "<variant>", "exec"), ns2)  # NameError here = reorder bug
    assert 55 in ns2.values()


def test_module_binding_use_agreement():
    # Regression (5th binding/use desync): the sandbox-check template
    # `import uuid, sys, multiprocessing` kept its spelling (visit_Import
    # only renames asnames) while use sites renamed uuid/multiprocessing
    # (absent from reserved) -> NameError at runtime (masked by
    # try/except) and Cython compile error (broke the Ghidra arm).
    # Fix: uuid/multiprocessing reserved in both renamers. Every Load of
    # a plain-imported module must agree with its binding.
    import ast as _ast
    from scripts.diversity.generator import generate_variant
    src = "import sys\n\ndef f(x):\n    return x + 1\nprint(f(1))\n"
    seen_template = False
    for seed in range(1, 31):
        code = generate_variant(
            src, 0,
            {"master_seed": seed,
             "pass_sets": [["rename", "dead_code", "mba", "cfg_flatten", "vm"]]})
        tree = _ast.parse(code)
        bound = set()
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Import):
                for a in node.names:
                    bound.add((a.asname or a.name).split(".")[0])
            elif isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef,
                                   _ast.ClassDef)):
                bound.add(node.name)
        if "uuid" in bound:
            seen_template = True
            # uuid/multiprocessing uses must keep their spelling.
            assert "uuid.getnode" in code, seed
            loads = {n.id for n in _ast.walk(tree)
                     if isinstance(n, _ast.Name) and isinstance(n.ctx, _ast.Load)}
            for mod in ("uuid", "multiprocessing"):
                if mod in loads:
                    assert mod in bound, (seed, mod)
    assert seen_template, "sandbox template never injected in 30 seeds"
