"""Tests for the native lowering kernel (V10 Phase 2).

Covers: symbol derivation (deterministic + unique), .pyx render, real
Cython build + import + behavioral parity with the shim, per-build
uniqueness, fusion dispatch, and graceful skip paths.
"""
import importlib.util
import os
import sys

import pytest

from obfuscator.kernel_gen import build_kernel, cythonize_kernel, derive_symbols, emit_native_import, render_pyx

TMP = "/tmp/nxk_tests"


def test_derive_deterministic_and_unique():
    m1, o1 = derive_symbols(b"seed-A")
    m2, o2 = derive_symbols(b"seed-A")
    m3, o3 = derive_symbols(b"seed-B")
    assert (m1, o1) == (m2, o2)
    assert m1 != m3 and o1 != o3
    assert m1.startswith("_nxk_") and len(m1) == 5 + 12
    assert len(set(o1.values())) == len(o1)


def test_render_covers_shim():
    # Every public _nxk_* name in the shim must have a kernel op behind it
    # (else the import swap would break lowered output).
    import obfuscator.lowering_shim as shim
    text, mod, omap = render_pyx(b"seed")
    shim_names = {n for n in dir(shim) if n.startswith("_nxk_")}
    assert shim_names <= set(omap), sorted(shim_names - set(omap))
    for token in shim_names:
        assert f"{token} = " in text  # public alias present
    compile(text, "<kernel.pyx>", "exec")  # sanity: valid Python syntax


def test_emit_native_import():
    line = emit_native_import("_nxk_abc123", ["_nxk_len", "_nxk_len", "_nxk_print"])
    assert line == "from _nxk_abc123 import _nxk_len, _nxk_print\n"
    assert emit_native_import("_nxk_x", []) == ""


def _build(mod_seed, ops=("len", "sorted", "print", "fuse")):
    os.makedirs(TMP, exist_ok=True)
    pyx, mod, omap = build_kernel(TMP, mod_seed, ops=ops)
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


def test_build_import_parity():
    so, msg, mod, omap = _build(b"parity-seed")
    if so is None:
        pytest.skip(f"toolchain missing: {msg}")
    m = _load(mod, so)
    import obfuscator.lowering_shim as shim
    # Same call shapes, same results as the shim.
    assert m._nxk_len([1, 2, 3]) == shim._nxk_len([1, 2, 3]) == 3
    assert m._nxk_sorted([3, 1, 2]) == shim._nxk_sorted([3, 1, 2]) == [1, 2, 3]


def test_per_build_uniqueness():
    so1, msg1, mod1, map1 = _build(b"seed-1")
    so2, msg2, mod2, map2 = _build(b"seed-2")
    if so1 is None or so2 is None:
        pytest.skip(f"toolchain missing: {msg1} / {msg2}")
    # Different module names AND different impl symbols, same public names.
    assert mod1 != mod2
    assert set(map1) == set(map2)  # same public call shapes
    assert set(map1.values()).isdisjoint(set(map2.values()))


def test_fusion_native():
    so, msg, mod, omap = _build(b"fusion-seed", ops=("fuse", "len"))
    if so is None:
        pytest.skip(f"toolchain missing: {msg}")
    m = _load(mod, so)
    calls = []
    out = m._nxk_fuse(lambda: calls.append(1), lambda: calls.append(2))
    assert calls == [1, 2] and out is None


def test_graceful_skip_missing_source():
    so, msg = cythonize_kernel("/nonexistent_kernel_xyz.pyx", TMP)
    assert so is None and "missing" in msg
