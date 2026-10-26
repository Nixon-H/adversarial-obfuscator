"""V10 bugfix regression tests — each guards a bug class Nyami fixed in V10.

Every test runs the input through our own pipeline (obfuscation passes)
and asserts the semantics survive. If any of these fail, we have the same
bug Nyami had:

1. kwargs binding (V10: renamed internals broke f(1, c=2), dict(a=1),
   keyword-only args, **kwargs)
2. exception-table integrity (V10: LE-vs-BE read silently reverted a
   decompiler-breaker layer) — our NYSER1 must preserve co_exceptiontable
3. zero-arg super() (V10: per-method compilation stripped __class__)
4. constant negative indexing / min-max type discipline (V10: PYTOC
   adjacent-memory read, wrong min/max type on mixed int/float) — our
   ConstantUnfolder + MBA must preserve index/type semantics
"""
import ast
import types

from obfuscator.core.transforms import (
    ConstantUnfolder,
    InstructionSubstitutor,
    SymbolRenamer,
)


def _exec(src):
    ns: dict = {}
    exec(compile(src, "<t>", "exec"), ns)
    return ns


def _roundtrip(src):
    """Run representative passes; return transformed source."""
    tree = ast.parse(src)
    tree = SymbolRenamer().visit(tree)
    tree = InstructionSubstitutor().visit(tree)
    tree = ConstantUnfolder().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def test_kwargs_binding_survives():
    src = (
        "def f(a, b=2, *args, c, d=4, **kw):\n"
        "    return (a, b, args, c, d, kw)\n"
        "r1 = f(1, c=2)\n"
        "r2 = f(1, 2, 3, c=4, d=5, e=6)\n"
        "d = dict(a=1)\n"
    )
    out = _roundtrip(src)
    ns = _exec(out)
    # NOTE: module-level result names (r1/r2/d) ARE renamed by design —
    # resolve them positionally: user code reads them via the rename log
    # in production; here we compare binding tuples, not names.
    vals = [v for k, v in ns.items() if isinstance(v, tuple) and len(v) == 6]
    dicts = [v for k, v in ns.items() if v == {"a": 1}]
    assert (1, 2, (), 2, 4, {}) in vals
    assert (1, 2, (3,), 4, 5, {"e": 6}) in vals
    assert dicts, "dict(a=1) binding lost"


def test_exception_table_preserved_by_nyser():
    """NYSER1 round-trip must preserve co_exceptiontable byte-for-byte."""
    from obfuscator.nyser import dumps, loads, roundtrip_supported
    import pytest
    if not roundtrip_supported():
        pytest.skip("NYSER1 unsupported here")
    src = (
        "def f(x):\n"
        "    try:\n"
        "        return 10 // x\n"
        "    except ZeroDivisionError:\n"
        "        return -1\n"
        "    finally:\n"
        "        y = 1\n"
    )
    co = compile(src, "<t>", "exec")
    # Module-level co_exceptiontable is empty (handlers live in child
    # code objects) — assert on the child function instead.
    kids = [c for c in co.co_consts if isinstance(c, types.CodeType)]
    assert kids, "expected nested code objects"
    # co_exceptiontable is 3.11+ (zero-cost exceptions).  On 3.10 the
    # metadata that must survive the round-trip is the line table; the
    # test used to require the 3.11 field on every interpreter and died
    # with "expected nested code objects" there.
    has_exc = hasattr(kids[0], "co_exceptiontable")
    if has_exc:
        assert any(k.co_exceptiontable for k in kids), "expected non-empty table"
    co2 = loads(dumps(co))
    kids2 = [c for c in co2.co_consts if isinstance(c, types.CodeType)]
    assert len(kids2) == len(kids)
    for a, b in zip(kids, kids2):
        if has_exc:
            assert b.co_exceptiontable == a.co_exceptiontable, "table mismatch"
        assert b.co_linetable == a.co_linetable, "linetable mismatch"


def _renamed(ns, values):
    """Find namespace values by VALUE (module-level names get renamed)."""
    found = []
    for v in ns.values():
        try:
            if v in values:
                found.append(v)
        except TypeError:
            continue
    return found


def test_zero_arg_super_survives():
    src = (
        "class A:\n"
        "    def who(self):\n"
        "        return 'A'\n"
        "class B(A):\n"
        "    def who(self):\n"
        "        return super().who() + 'B'\n"
        "r = B().who()\n"
    )
    out = _roundtrip(src)
    # __class__ cell must survive renaming (zero-arg super needs it)
    assert "__class__" in out or "super()" in out
    ns = _exec(out)
    assert _renamed(ns, ["AB"]) == ["AB"]


def test_negative_index_semantics():
    src = (
        "xs = [1, 2, 3, 4]\n"
        "a = xs[-1]\n"
        "b = xs[-4]\n"
        "c = 'hello'[-2]\n"
    )
    out = _roundtrip(src)
    ns = _exec(out)
    got = {}
    for want in (4, 1, "l"):
        got[want] = got.get(want, 0) + sum(1 for v in ns.values() if v == want)
    assert got.get(4, 0) >= 1 and got.get(1, 0) >= 1 and got.get("l", 0) >= 1


def test_min_max_mixed_types():
    src = (
        "a = min(1, 2.5)\n"
        "b = max(1, 2.5)\n"
        "c = min([3, 1, 2])\n"
        "ta = type(a).__name__\n"
        "tb = type(b).__name__\n"
    )
    out = _roundtrip(src)
    ns = _exec(out)
    vals = list(ns.values())
    assert 1 in vals and 2.5 in vals
    assert "int" in vals and "float" in vals


def test_dis_no_adjacent_memory_read():
    """Transformed constant indexing must stay in-bounds (no adjacent read).

    Static check: every Subscript index in the transformed tree must be a
    constant within a sane range or a Name (dynamic) — never a folded
    constant that escaped its container length. We verify semantically:
    indexing results equal the originals for a battery of containers.
    """
    src = (
        "t = (10, 20, 30)\n"
        "s = 'abcdef'\n"
        "r = [t[-1], t[0], s[-1], s[2], t[-3]]\n"
    )
    out = _roundtrip(src)
    ns = _exec(out)
    assert _renamed(ns, [[30, 10, "f", "c", 10]]) == [[30, 10, "f", "c", 10]]
