"""AUDIT GAP #71: runtime watermark refuse-to-run gate.

Build with a watermark -> the emitted loader carries an HMAC-bound gate
that refuses (non-zero exit) when the watermark is stripped or tampered.
No watermark configured -> DISABLED gate, artifact runs unchanged.
"""
import marshal
import os
import re
import subprocess
import sys
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import generate_hybrid_loader_script
from obfuscator.core.utils import fast_xor_bytes
from obfuscator.watermark_gate import (
    build_watermark_context,
    check_watermark,
    compute_tag,
    emit_watermark_snippet,
    verify_tag,
)

_BLANKS = {"windows": "", "linux": "", "darwin": ""}
_RAW_KEY = bytes(range(32))


def test_tag_verifies_same_message():
    key = b"k" * 32
    tag = compute_tag(key, "owner-71")
    assert verify_tag(key, "owner-71", tag) is True


def test_tag_fails_wrong_message_or_key():
    key = b"k" * 32
    tag = compute_tag(key, "owner-71")
    assert verify_tag(key, "other", tag) is False
    assert verify_tag(b"j" * 32, "owner-71", tag) is False
    assert verify_tag(key, "owner-71", "0" * 64) is False


def test_check_missing_marker():
    key = b"k" * 32
    tag = compute_tag(key, "owner-71")
    assert check_watermark(key, "owner-71", tag, marker_present=True) == "ok"
    assert check_watermark(key, "owner-71", tag, marker_present=False) == "missing"
    assert check_watermark(key, "tampered-msg", tag, marker_present=True) == "tampered"


def test_snippet_compiles_and_runs():
    ctx = build_watermark_context("owner-71", build_key=b"k" * 32)
    src = emit_watermark_snippet(str(ctx["message"]), str(ctx["tag"]),
                                 bytes(ctx["build_key"]).hex(),
                                 str(ctx["marker"]))
    compile(src, "<wm_snippet>", "exec")
    ns = {"__name__": "wm_snippet"}
    exec(compile(src, "<wm_snippet>", "exec"), ns)
    ns["_NX_WATERMARK_MARKER"] = ctx["marker"]
    assert ns["_nx_watermark_gate"]() == "ok"
    # Wrong key -> tampered.
    ns["_nx_watermark_gate"].__globals__  # sanity: plain function
    bad_ctx = build_watermark_context("owner-71", build_key=b"j" * 32)
    assert bad_ctx["tag"] != ctx["tag"]


def test_loader_no_watermark_disabled():
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANKS), b"", _RAW_KEY.hex(), build_id="wm-dis-01")
    compile(src, "<wm_dis>", "exec")
    assert '_NX_WATERMARK_GATE = "DISABLED"' in src
    assert "def _nx_watermark_gate" not in src


def test_loader_with_watermark_has_gate(tmp_path):
    enc = fast_xor_bytes(
        zlib.compress(marshal.dumps(
            compile("WM_E2E = 6 * 7\n", "<wm_e2e>", "exec"))),
        _RAW_KEY)
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(),
        watermark="owner-71", watermark_key=b"k" * 32,
        build_id="wm-on-01")
    compile(src, "<wm_on>", "exec")
    assert "def _nx_watermark_gate" in src
    assert "_NX_WATERMARK_TAG" in src
    assert "_NX_WATERMARK_MARKER" in src
    m = re.search(r"_NX_WATERMARK_TAG = '([0-9a-f]{64})'", src)
    assert m, "tag literal missing"
    ns = {"__name__": "wm_on_loader"}
    exec(compile(src, "<wm_on_loader>", "exec"), ns)
    assert ns.get("_NX_WATERMARK_GATE") == "ok"
    ns["_exec_fallback"]()
    assert ns.get("WM_E2E") == 42


def _write_and_run_loader(src, workdir, name):
    target = os.path.join(str(workdir), name)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(src)
    env = dict(os.environ)
    env.pop("NIXON_VERIFY_SKIP_VERSION_CHECK", None)
    env.pop("NIXON_CI", None)
    env.pop("NIXON_ALLOW_SKIP", None)
    proc = subprocess.run([sys.executable, target],
                          capture_output=True, text=True, timeout=60,
                          cwd=str(workdir), env=env)
    return proc


def test_e2e_marked_artifact_runs(tmp_path):
    enc = fast_xor_bytes(
        zlib.compress(marshal.dumps(
            compile("print('WM_OK_MARKER')\n", "<wm_ok>", "exec"))),
        _RAW_KEY)
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(),
        watermark="owner-71", watermark_key=b"k" * 32,
        build_id="wm-e2e-ok")
    src += "\n_ns_wm_out = _exec_fallback()\n"
    proc = _write_and_run_loader(src, tmp_path, "wm_artifact.py")
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "WM_OK_MARKER" in proc.stdout


def test_e2e_stripped_watermark_refuses(tmp_path):
    enc = fast_xor_bytes(
        zlib.compress(marshal.dumps(
            compile("print('SHOULD_NOT_PRINT')\n", "<wm_strip>", "exec"))),
        _RAW_KEY)
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(),
        watermark="owner-71", watermark_key=b"k" * 32,
        build_id="wm-e2e-strip")
    # Strip the marker literal (simulate removal of the watermark block).
    m = re.search(r"_NX_WATERMARK_MARKER = '([^']+)'", src)
    assert m
    src = src.replace(m.group(0), "_NX_WATERMARK_MARKER = 'STRIPPED'", 1)
    src += "\n_ns_wm_out = _exec_fallback()\n"
    proc = _write_and_run_loader(src, tmp_path, "wm_stripped.py")
    # Kill ladder: stripped watermark funnels through _nx_kill (silent,
    # exit 137, no output) — same shape as the migrated audit-hook and
    # driver gates.
    assert proc.returncode == 137, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert "SHOULD_NOT_PRINT" not in proc.stdout


def test_e2e_tampered_watermark_refuses(tmp_path):
    enc = fast_xor_bytes(
        zlib.compress(marshal.dumps(
            compile("print('SHOULD_NOT_PRINT')\n", "<wm_tamp>", "exec"))),
        _RAW_KEY)
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(),
        watermark="owner-71", watermark_key=b"k" * 32,
        build_id="wm-e2e-tamp")
    # Edit the message without the key -> tag mismatch.
    m = re.search(r"_NX_WATERMARK_MSG = '([^']+)'", src)
    assert m
    src = src.replace(m.group(0), "_NX_WATERMARK_MSG = 'attacker-msg'", 1)
    src = src.replace("_wm_msg = %r" % (m.group(1),),
                      "_wm_msg = 'attacker-msg'", 1)
    src += "\n_ns_wm_out = _exec_fallback()\n"
    proc = _write_and_run_loader(src, tmp_path, "wm_tampered.py")
    # Kill ladder: tampered watermark funnels through _nx_kill (silent,
    # exit 137, no output).
    assert proc.returncode == 137, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert "SHOULD_NOT_PRINT" not in proc.stdout


def test_e2e_unmarked_artifact_unaffected(tmp_path):
    enc = fast_xor_bytes(
        zlib.compress(marshal.dumps(
            compile("print('NOWM_OK_MARKER')\n", "<wm_nowm>", "exec"))),
        _RAW_KEY)
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(), build_id="wm-e2e-nowm")
    src += "\n_ns_wm_out = _exec_fallback()\n"
    proc = _write_and_run_loader(src, tmp_path, "wm_nowm.py")
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "NOWM_OK_MARKER" in proc.stdout


def test_e2e_wrong_key_refuses(tmp_path):
    enc = fast_xor_bytes(
        zlib.compress(marshal.dumps(
            compile("print('SHOULD_NOT_PRINT')\n", "<wm_key>", "exec"))),
        _RAW_KEY)
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(),
        watermark="owner-71", watermark_key=b"k" * 32,
        build_id="wm-e2e-key")
    # Swap the embedded key for a wrong one -> tag mismatch.
    m = re.search(r"_NX_WATERMARK_KEY = '([0-9a-f]+)'", src)
    assert m
    wrong = (b"j" * 32).hex()
    src = src.replace(m.group(0), "_NX_WATERMARK_KEY = '%s'" % (wrong,), 1)
    src = src.replace("_wm_key = bytes.fromhex(%r)" % (m.group(1),),
                      "_wm_key = bytes.fromhex(%r)" % (wrong,), 1)
    src += "\n_ns_wm_out = _exec_fallback()\n"
    proc = _write_and_run_loader(src, tmp_path, "wm_wrongkey.py")
    # Kill ladder: wrong-key watermark funnels through _nx_kill (silent,
    # exit 137, no output).
    assert proc.returncode == 137, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert "SHOULD_NOT_PRINT" not in proc.stdout
