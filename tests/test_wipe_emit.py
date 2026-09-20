"""Batch-3 C-WIPE: emitted _nx_wipe helper in the hybrid loader template.

The emitted ``_exec_fallback`` holds decrypted buffers as ``bytearray``
(mutable) and zeroes the live buffers via ``ctypes.memset`` after
``exec()`` — buffers must not be left to Python GC. Follows the fragment
pattern from tests/test_hybrid_loader.py.
"""
import marshal
import os
import re
import sys
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import generate_hybrid_loader_script
from obfuscator.core.utils import fast_xor_bytes


def _template_src():
    src = open("obfuscator/core/pipeline.py").read()
    m = re.search(r"loader_template = r'''(.*?)'''", src, re.DOTALL)
    assert m, "loader_template not found"
    return m.group(1)


def _exec_namespace(src, build_id="wipe-test-01"):
    """Exec the generated loader far enough to expose helpers (no blob run)."""
    blanks = {"windows": "", "linux": "", "darwin": ""}
    full, _, _ = generate_hybrid_loader_script(
        blanks, b"", "00" * 32, build_id=build_id)
    ns = {"__name__": "wipe_test"}
    exec(compile(full, "<wipe_loader>", "exec"), ns)
    return ns


def test_wipe_helper_present_in_template():
    tpl = _template_src()
    assert "def _nx_wipe(obj)" in tpl
    assert "ctypes.memset" in tpl or "_ct_loader.memset" in tpl


def test_exec_fallback_wipes_buffers():
    tpl = _template_src()
    start = tpl.find("def _exec_fallback")
    body = tpl[start:tpl.find("def _load_native", start)]
    assert "_nx_wipe(encrypted)" in body
    assert "_nx_wipe(compressed)" in body
    assert "_nx_wipe(raw)" in body
    # bytearray buffers (mutable), not immutable bytes holders
    assert "bytearray(base64.b85decode(FALLBACK_BLOB))" in body


def test_nx_wipe_zeroes_bytearray():
    ns = _exec_namespace("unused")
    buf = bytearray(b"SECRET-DATA-1234")
    assert ns["_nx_wipe"](buf) is None
    assert bytes(buf) == b"\x00" * len(buf)


def test_nx_wipe_bytes_path_does_not_crash():
    ns = _exec_namespace("unused")
    # bytes are immutable: cannot wipe in place -> del-only, must not raise
    assert ns["_nx_wipe"](b"immutable") is None
    assert ns["_nx_wipe"](None) is None
    assert ns["_nx_wipe"](bytearray()) is None


def test_fallback_end_to_end_with_wipe():
    """Full decrypt+exec path works with bytearray buffers + wipe calls."""
    payload_src = "WIPE_E2E = 6 * 7\n"
    marshalled = marshal.dumps(compile(payload_src, "<wipe_e2e>", "exec"))
    raw_key = bytes(range(32))
    enc = fast_xor_bytes(zlib.compress(marshalled), raw_key)
    blanks = {"windows": "", "linux": "", "darwin": ""}
    src, _, _ = generate_hybrid_loader_script(
        blanks, enc, raw_key.hex(), build_id="wipe-e2e-01")
    compile(src, "<wipe_e2e_loader>", "exec")  # must be valid syntax
    ns = {"__name__": "wipe_e2e_loader"}
    exec(compile(src, "<wipe_e2e_loader>", "exec"), ns)
    ns["_exec_fallback"]()
    assert ns.get("WIPE_E2E") == 42
