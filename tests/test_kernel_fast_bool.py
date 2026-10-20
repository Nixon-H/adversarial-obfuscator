"""Bool-parity tests for kernel_fast hot returns (audit item 16).

C-API predicates (PyCallable_Check, PyObject_IsTrue, PyObject_IsInstance,
PyObject_IsSubclass, PyObject_HasAttr) return C int, not Python bool.
The hot branches must wrap them in bool() so ``type(x) is bool`` and
``is True/False`` parity hold against the builtins.
"""
from obfuscator.kernel_fast import _FAST_BODIES, fast_body

_BOOL_OPS = ("callable", "bool", "isinstance", "issubclass", "hasattr")


def test_hot_returns_wrapped_in_bool():
    for op in _BOOL_OPS:
        body = fast_body(op, "_k_impl")
        assert body is not None
        assert "bool(Py" in body, op


def test_no_bare_c_int_return():
    for op in _BOOL_OPS:
        for line in _FAST_BODIES[op].splitlines():
            s = line.strip()
            if s.startswith("return Py"):
                raise AssertionError(f"{op}: bare C-int return: {s!r}")


def test_runtime_bool_parity():
    try:
        from tests.test_kernel_fast import _build_fast, _load, _token
    except ImportError:
        import pytest
        pytest.skip("test helper unavailable")
        return
    import pytest as _pt
    so, msg, mod, omap = _build_fast(b"fast-bool-seed")
    if so is None:
        _pt.skip("toolchain missing: %s" % msg)
    m = _load(mod, so)
    assert m.__dict__[_token("callable")](len) is True
    assert m.__dict__[_token("callable")](1) is False
    assert m.__dict__[_token("bool")](1) is True
    assert type(m.__dict__[_token("bool")](0)) is bool
    assert m.__dict__[_token("isinstance")]("a", str) is True
    assert m.__dict__[_token("issubclass")](bool, int) is True
    assert m.__dict__[_token("hasattr")]("a", "upper") is True
    assert m.__dict__[_token("hasattr")](1, "zzz") is False
