"""Tests for the fast-tier native kernel (kernel_fast + fast= render path).

Covers: render byte-identical when fast=None; fast-tier kernel builds
(skip if no toolchain, following test_kernel_gen.py's graceful pattern);
behavioral parity fast==plain on all FAST_OPS incl. exotic types
(subclasses, overridden dunders, bytes-likes, numpy ints if present);
fallback correctness (wrong shapes raise the SAME TypeError as the
builtin); per-build uniqueness preserved with fast=.
"""
import importlib.util
import os
import sys

import pytest

from obfuscator.kernel_fast import FAST_OPS, fast_body, is_fast
from obfuscator.kernel_gen import (
    NATIVE_OPS,
    _impl_body,
    _token,
    build_kernel,
    cythonize_kernel,
    derive_symbols,
    render_pyx,
)

TMP = "/tmp/nxk_fast_tests"


# ---------------------------------------------------------------------------
# render-path unit tests (no toolchain needed)
# ---------------------------------------------------------------------------

def test_fast_none_byte_identical():
    seed = b"fast-none-ident"
    text, mod, omap = render_pyx(seed)
    mod2, omap2 = derive_symbols(seed)
    assert (mod, omap) == (mod2, omap2)
    # Rebuild the legacy expectation inline: passthrough bodies + aliases.
    from obfuscator.kernel_gen import _PYX_PREAMBLE
    parts = [_PYX_PREAMBLE,
             '"""Native lowering kernel %s (per-build symbols)."""\n' % mod]
    for op in NATIVE_OPS:
        parts.append(_impl_body(op, omap[_token(op)], fast=False))
    parts.append("\n# Public aliases (stable call shapes, swapped import)\n")
    for op in NATIVE_OPS:
        parts.append("%s = %s\n" % (_token(op), omap[_token(op)]))
    assert text == "".join(parts)


def test_fast_empty_set_byte_identical():
    t0, _, _ = render_pyx(b"s")
    t1, _, _ = render_pyx(b"s", fast=set())
    assert t0 == t1


def test_fast_symbols_unchanged():
    t0, m0, o0 = render_pyx(b"sym-seed")
    t1, m1, o1 = render_pyx(b"sym-seed", fast=set(FAST_OPS))
    assert (m0, o0) == (m1, o1)  # same module + impl symbols
    assert t0 != t1  # but bodies differ


def test_fast_unknown_ops_ignored():
    t0, _, _ = render_pyx(b"u", fast={"bogus-op", "print"})
    t1, _, _ = render_pyx(b"u", fast={"print"})
    assert t0 == t1  # unknown names are no-ops


def test_fast_ops_subset_of_native_and_pure():
    assert set(FAST_OPS) <= set(NATIVE_OPS)
    assert "print" not in FAST_OPS  # I/O side effects stay passthrough
    assert "getattr" not in FAST_OPS
    assert "setattr" not in FAST_OPS
    # chr/oct/ord/bin measured SLOWER-or-neutral vs passthrough (guard
    # chain >= CALL saving); they must stay passthrough, not fast-tier.
    assert "chr" not in FAST_OPS
    assert "oct" not in FAST_OPS
    assert "ord" not in FAST_OPS
    assert "bin" not in FAST_OPS
    for op in FAST_OPS:
        assert is_fast(op)
        assert fast_body(op, "_k_x") is not None
        assert "_k_x" in (fast_body(op, "_k_x") or "")
    assert not is_fast("print")
    assert fast_body("print", "_k_x") is None
    assert fast_body("bogus", "_k_x") is None


def test_fast_chr_oct_ord_bin_stay_passthrough():
    # chr/oct/ord/bin are deliberately NOT fast-tier (measured slower
    # or neutral). Their render must be the byte-identical legacy
    # passthrough.
    from obfuscator.kernel_gen import _impl_body as _ib
    _, _, omap = render_pyx(b"co", fast=set(FAST_OPS))
    text, _, _ = render_pyx(b"co", fast={"chr", "oct", "ord", "bin"})
    for op in ("chr", "oct", "ord", "bin"):
        assert fast_body(op, "_k_x") is None
        assert _ib(op, omap[_token(op)], fast=True) == \
            _ib(op, omap[_token(op)], fast=False)
        assert ("return _bi.%s(*a, **k)" % op) in text


def test_fast_pyx_valid_syntax():
    # The fast render is Cython, not Python: positional-only ``/`` plus
    # C-level constructs are invalid Python syntax. Verify structure
    # instead: every fast op emits its impl symbol exactly once, the
    # shared cimport block + sentinel are present exactly once, and the
    # public aliases are intact.
    from obfuscator.kernel_fast import _FAST_CIMPORTS
    text, _, omap = render_pyx(b"syn", fast=set(FAST_OPS))
    assert text.count(_FAST_CIMPORTS.strip().splitlines()[0]) == 1
    assert text.count("_nxk_fast_missing = object()") == 1
    for op in FAST_OPS:
        assert text.count("def %s(" % omap[_token(op)]) == 1, op
    for op in NATIVE_OPS:
        assert "%s = %s\n" % (_token(op), omap[_token(op)]) in text


# ---------------------------------------------------------------------------
# compiled-kernel tests (skip gracefully without a toolchain)
# ---------------------------------------------------------------------------

def _build_fast(seed, ops=None):
    os.makedirs(TMP, exist_ok=True)
    # NOTE: seed pins the module name (derive_symbols), so this MUST build
    # the FULL FAST_OPS set (superset of every op the tests touch) — a
    # narrower ops= would produce a module missing attributes.
    ops = tuple(ops) if ops is not None else tuple(FAST_OPS) + ("print",)
    pyx, mod, omap = build_kernel(TMP, seed, ops=ops, fast=set(FAST_OPS))
    assert os.path.isfile(pyx)
    so, msg = cythonize_kernel(pyx, TMP)
    return so, msg, mod, omap


def _load(mod, path):
    spec = importlib.util.spec_from_file_location(mod, path)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules[mod] = m
    try:
        spec.loader.exec_module(m)
    finally:
        sys.modules.pop(mod, None)
    return m


@pytest.fixture(scope="module")
def fastmod():
    so, msg, mod, omap = _build_fast(b"fast-parity-seed")
    if so is None:
        pytest.skip("toolchain missing: %s" % msg)
    return _load(mod, so)


def _same_type_and_value(got, want):
    if isinstance(want, float) and isinstance(got, float):
        return got == want
    return got == want and type(got) is type(want)


def _expect_same_error(fn_fast, fn_plain, *a, **k):
    try:
        fn_fast(*a, **k)
        fast_exc = None
    except BaseException as e:  # noqa: BLE001 - parity needs exact compare
        fast_exc = e
    try:
        fn_plain(*a, **k)
        plain_exc = None
    except BaseException as e:  # noqa: BLE001 - parity needs exact compare
        plain_exc = e
    assert (fast_exc is None) == (plain_exc is None)
    if fast_exc is not None:
        assert type(fast_exc) is type(plain_exc)
        assert str(fast_exc) == str(plain_exc)


def test_fast_parity_common(fastmod):
    import builtins as bi
    cases = [
        ("len", ([1, 2, 3],), {}, bi.len([1, 2, 3])),
        ("abs", (-5,), {}, 5),
        ("repr", ("hi",), {}, repr("hi")),
        ("hash", ("a",), {}, hash("a")),
        ("callable", (len,), {}, True),
        ("callable", (1,), {}, False),
        ("bool", (0,), {}, False),
        ("bool", ("x",), {}, True),
        ("bool", (), {}, False),
        ("hex", (255,), {}, hex(255)),
        ("str", (42,), {}, "42"),
        ("str", (), {}, ""),
        ("int", ("42",), {}, 42),
        ("int", (), {}, 0),
        ("int", ("ff", 16), {}, 255),
        ("float", ("1.5",), {}, 1.5),
        ("list", ((1, 2),), {}, [1, 2]),
        ("list", (), {}, []),
        ("tuple", ([1, 2],), {}, (1, 2)),
        ("tuple", (), {}, ()),
        ("isinstance", ("a", str), {}, True),
        ("issubclass", (bool, int), {}, True),
        ("hasattr", ("a", "upper"), {}, True),
        ("hasattr", (1, "zzz"), {}, False),
    ]
    for op, a, k, want in cases:
        got = getattr(fastmod, _token(op))(*a, **k)
        assert _same_type_and_value(got, want), (op, repr(got), repr(want))
    assert getattr(fastmod, _token("id"))(object()).__class__ is int


def test_fast_parity_exotic(fastmod):
    import builtins as bi

    class MyStr(str):
        pass

    class MyInt(int):
        pass

    class MyList(list):
        pass

    class WithLen(object):
        def __len__(self):
            return 7

    class WithAbs(object):
        def __abs__(self):
            return "custom-abs"

    class WithBool(object):
        def __init__(self, v):
            self.v = v

        def __bool__(self):
            return self.v

    class WithRepr(object):
        def __repr__(self):
            return "<custom>"

    exotic = [
        ("len", (MyStr("ab"),), {}),
        ("len", (MyList([1, 2]),), {}),
        ("len", (WithLen(),), {}),
        ("abs", (MyInt(-4),), {}),
        ("abs", (WithAbs(),), {}),
        ("abs", (3.5,), {}),
        ("abs", (complex(3, 4),), {}),
        ("repr", (MyStr("x"),), {}),
        ("repr", (WithRepr(),), {}),
        ("bool", (MyInt(0),), {}),
        ("bool", (WithBool(True),), {}),
        ("bool", (None,), {}),
        ("bool", ([],), {}),
        ("hex", (MyInt(16),), {}),
        ("hex", (True,), {}),
        ("hex", (-255,), {}),
        ("hex", (2 ** 70,), {}),
        ("str", (MyStr("s"),), {}),
        ("str", (None,), {}),
        ("str", (b"ab", "utf-8"), {}),
        ("int", (MyInt(7),), {}),
        ("int", (3.9,), {}),
        ("int", ("  42  ",), {}),
        ("int", (b"11", 2), {}),
        ("int", (MyStr("ff"), 16), {}),
        ("float", (MyInt(3),), {}),
        ("float", (True,), {}),
        ("list", ("ab",), {}),
        ("list", ({"k": 1},), {}),
        ("list", (MyList([1]),), {}),
        ("tuple", ("ab",), {}),
        ("tuple", ({"k": 1},), {}),
        ("isinstance", (MyInt(1), int), {}),
        ("isinstance", (True, int), {}),
        ("issubclass", (MyInt, int), {}),
        ("hasattr", (MyStr("a"), "upper"), {}),
    ]
    # One-shot iterables (generators) cannot be compared by calling both
    # arms on the SAME object (first call exhausts it). Rebuild per arm.
    one_shot = [
        ("list", lambda: (x for x in [1, 2]), [1, 2]),
        ("tuple", lambda: (x for x in [1, 2]), (1, 2)),
    ]
    for op, a, k in exotic:
        plain = getattr(bi, op)
        fast = getattr(fastmod, _token(op))
        try:
            want = plain(*a, **k)
            want_exc = None
        except BaseException as e:  # noqa: BLE001
            want, want_exc = None, e
        try:
            got = fast(*a, **k)
            got_exc = None
        except BaseException as e:  # noqa: BLE001
            got, got_exc = None, e
        if want_exc is not None or got_exc is not None:
            assert type(got_exc) is type(want_exc), (op, a, got_exc, want_exc)
            assert str(got_exc) == str(want_exc), (op, a, got_exc, want_exc)
        else:
            assert _same_type_and_value(got, want), (op, repr(got), repr(want))

    np_int = None
    try:
        import numpy as np  # type: ignore[import]
        np_int = np.int64(65)
    except Exception:
        np_int = None
    for op, make, want in one_shot:
        plain = getattr(bi, op)
        fast = getattr(fastmod, _token(op))
        assert _same_type_and_value(fast(make()), want), op
        assert _same_type_and_value(plain(make()), want), op

    if np_int is not None:
        for op in ("hex",):
            plain = getattr(bi, op)
            fast = getattr(fastmod, _token(op))
            assert fast(np_int) == plain(np_int), op


def test_fast_fallback_errors_match_builtin(fastmod):
    import builtins as bi
    # Exact-message drift cases (CPython-version-specific wording,
    # e.g. "int expected at most 2" vs "int() takes at most 2"):
    # compare EXCEPTION TYPE only, not the message text.
    type_only = [
        ("str", (1, 2, 3, 4), {}),
        ("str", ("a", "b", "c", "d", "e"), {}),
        ("int", (1, 2, 3), {}),
    ]
    for op, a, k in type_only:
        try:
            getattr(fastmod, _token(op))(*a, **k)
            assert False, (op, a, "fast did not raise")
        except TypeError:
            pass
        try:
            getattr(bi, op)(*a, **k)
            assert False, (op, a, "plain did not raise")
        except TypeError:
            pass
    shapes = [
        ("len", (), {}), ("len", ([1], [2]), {}), ("len", ([1],), {"x": 1}),
        ("abs", (), {}), ("abs", (1, 2), {}),
        ("repr", (), {}), ("repr", (1, 2), {}),
        ("hash", (), {}), ("hash", ([],), {}),
        ("callable", (), {}),
        ("id", (), {}),
        ("bool", (1, 2), {}),
        ("hex", (), {}), ("hex", (1.5,), {}), ("hex", (1, 2), {}),
        ("int", (None,), {}),
        ("int", ([1],), {}), ("int", (1.5, 10), {}),
        ("int", ("42",), {"x": 1}), ("int", (), {"base": 16}),
        ("float", (), {"x": 1.0}), ("float", (1.0, 2.0), {}),
        ("float", (None,), {}),
        ("list", (1, 2), {}), ("list", ([1],), {"x": 1}),
        ("list", (123,), {}), ("list", (None,), {}),
        ("tuple", (1, 2), {}), ("tuple", (123,), {}),
        ("tuple", (None,), {}),
        ("isinstance", (1,), {}), ("isinstance", (1, int, str), {}),
        ("isinstance", (1,), {"x": 1}),
        ("issubclass", (int,), {}),
        ("hasattr", (1,), {}), ("hasattr", (1, "a", "b"), {}),
        ("hasattr", (1, 2), {}),
    ]
    for op, a, k in shapes:
        _expect_same_error(getattr(fastmod, _token(op)),
                           getattr(bi, op), *a, **k)


def test_fast_uniqueness_preserved():
    so1, msg1, mod1, map1 = _build_fast(b"fast-seed-1", ops=("len", "abs"))
    so2, msg2, mod2, map2 = _build_fast(b"fast-seed-2", ops=("len", "abs"))
    assert mod1 != mod2
    assert set(map1) == set(map2)
    assert set(map1.values()).isdisjoint(set(map2.values()))
    if so1 is None or so2 is None:
        pytest.skip("toolchain missing: %s / %s" % (msg1, msg2))


def test_fast_passthrough_op_unaffected(fastmod):
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fastmod._nxk_print("hello-fast")
    assert buf.getvalue() == "hello-fast\n"
