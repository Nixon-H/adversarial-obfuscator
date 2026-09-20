import builtins
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.hostguard import emit_hostguard_snippet


def _load():
    src = emit_hostguard_snippet()
    compile(src, "<t>", "exec")
    ns = {"__name__": "hostguard_test"}
    exec(compile(src, "<t>", "exec"), ns)
    return ns


def test_snippet_compiles_and_exports():
    ns = _load()
    for name in ("bind_host", "check_host", "verify_builtin", "isolated_exec"):
        assert callable(ns[name])
    assert "_NX_HOST" in ns


def test_bind_check_same_ns_passes():
    ns = _load()
    host = {"__name__": "__main__", "x": 1}
    ns["bind_host"](host)
    assert ns["check_host"](host) is True


def test_different_ns_raises():
    ns = _load()
    host = {"a": 1}
    ns["bind_host"](host)
    with pytest.raises(RuntimeError):
        ns["check_host"]({"a": 1})
    with pytest.raises(RuntimeError):
        ns["check_host"]({"a": 1, "extra": 2})


def test_tampered_keys_raise():
    ns = _load()
    host = {"a": 1, "b": 2}
    ns["bind_host"](host)
    host["c"] = 3  # same object, new key -> digest mismatch
    with pytest.raises(RuntimeError):
        ns["check_host"](host)


def test_unbound_raises():
    ns = _load()
    with pytest.raises(RuntimeError):
        ns["check_host"]({})


def test_verify_builtin_true_then_false_after_patch():
    ns = _load()
    assert ns["verify_builtin"]("len") is True
    orig = builtins.len
    try:
        builtins.len = lambda x: 0  # noqa: E731
        assert ns["verify_builtin"]("len") is False
        # Explicit ref comparison still works.
        assert ns["verify_builtin"]("len", ref=builtins.len) is True
        assert ns["verify_builtin"]("len", ref=orig) is False
    finally:
        builtins.len = orig
    assert ns["verify_builtin"]("len") is True


def test_verify_builtin_missing_name_false():
    ns = _load()
    assert ns["verify_builtin"]("no_such_builtin_xyz") is False


def test_isolated_exec_runs_code():
    ns = _load()
    host = {}
    ns["bind_host"](host)
    code = compile("result = 40 + 2", "<iso>", "exec")
    h = ns["host_hash"](code)
    ns["isolated_exec"](code, host, h)
    assert host["result"] == 42


def test_isolated_exec_hash_mismatch_raises():
    ns = _load()
    host = {}
    ns["bind_host"](host)
    code = compile("result = 1", "<iso>", "exec")
    with pytest.raises(RuntimeError):
        ns["isolated_exec"](code, host, "0" * 64)


def test_isolated_exec_wrong_host_raises():
    ns = _load()
    host = {}
    ns["bind_host"](host)
    code = compile("result = 1", "<iso>", "exec")
    h = ns["host_hash"](code)
    with pytest.raises(RuntimeError):
        ns["isolated_exec"](code, {}, h)
