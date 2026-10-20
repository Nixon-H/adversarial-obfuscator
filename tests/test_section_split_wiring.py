"""Section split: the payload travels as independently sealed sections.

``obfuscator/section_split.py`` was implemented and unit-tested but was
never called by any build, pipeline or loader path -- a repo-wide search
found references only in its own two test files, while
``THREAT_MODEL.md`` presented "per-section fresh nonce" as an active
control.  The module is not redundant: it is the only place in the tree
that seals a payload in independently verifiable sections, so it is now
wired into the hybrid loader as an opt-in feature.

These tests drive the real builder: they emit a loader, run it, and
tamper with it.
"""
import base64
import json
import marshal
import os
import re
import subprocess
import sys
import zlib


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import generate_hybrid_loader_script
from obfuscator.core.utils import fast_xor_bytes

RAW_KEY = bytes(range(32))
_BLANKS = {"windows": "", "linux": "", "darwin": ""}


def _emit(tmp_path, **kwargs):
    """Emit a hybrid loader carrying a tiny payload."""
    payload = "print('SECTIONED-OK')\n"
    blob = zlib.compress(marshal.dumps(compile(payload, "<p>", "exec")))
    enc = fast_xor_bytes(blob, RAW_KEY)
    src, _, _ = generate_hybrid_loader_script(
        _BLANKS, bytes(enc), RAW_KEY.hex(), **kwargs)
    src += "\n_ci_probe_out = _exec_fallback()\n"
    path = os.path.join(str(tmp_path), "artifact.py")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src)
    return path, src


def _pack_match(src):
    """Find the emitted section pack (the loader quotes it either way)."""
    return re.search(r"_NX_SECTION_PACK = '([^']*)'", src) or \
        re.search(r'_NX_SECTION_PACK = "([^"]*)"', src)


def _run(path):
    env = dict(os.environ)
    env["NIXON_LOG_REDIRECT"] = "0"
    return subprocess.run([sys.executable, path], capture_output=True,
                          text=True, timeout=60, env=env)


def test_default_path_is_unchanged(tmp_path):
    """Without the flag the loader carries the single blob, as before."""
    path, src = _emit(tmp_path)
    assert 'FALLBACK_BLOB = "SECTIONED"' not in src
    # The join helper is only emitted when the feature is armed; the call
    # site stays in the template but its branch is guarded by an empty pack.
    assert "def _nx_section_join(" not in src
    assert re.search(r"_NX_SECTION_PACK = (''|\"\")", src)
    proc = _run(path)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "SECTIONED-OK" in proc.stdout


def test_sectioned_loader_runs(tmp_path):
    path, src = _emit(tmp_path, section_split=True, section_count=4)
    assert 'FALLBACK_BLOB = "SECTIONED"' in src
    assert "_nx_section_join" in src
    proc = _run(path)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "SECTIONED-OK" in proc.stdout


def test_sections_are_individually_sealed(tmp_path):
    """The pack holds N sections, each with its own nonce and tag."""
    _, src = _emit(tmp_path, section_split=True, section_count=4)
    match = _pack_match(src)
    assert match, "no section pack in the loader"
    pack = json.loads(base64.b85decode(match.group(1)).decode("utf-8"))
    assert pack["count"] == 4
    assert len(pack["sections"]) == 4
    nonces = {s["nonce"] for s in pack["sections"]}
    assert len(nonces) == 4, "sections must not share a nonce"
    for sec in pack["sections"]:
        assert sec["data"], "empty section"
        assert sec["i"] == pack["sections"].index(sec)


def test_tampered_section_fails_closed(tmp_path):
    """A flipped bit in one section must kill the artifact, not run it."""
    _, src = _emit(tmp_path, section_split=True, section_count=4)
    match = _pack_match(src)
    pack = json.loads(base64.b85decode(match.group(1)).decode("utf-8"))
    data = bytearray(bytes.fromhex(pack["sections"][1]["data"]))
    data[5] ^= 0xFF
    pack["sections"][1]["data"] = data.hex()
    tampered = base64.b85encode(
        json.dumps(pack, sort_keys=True).encode()).decode()
    path = os.path.join(str(tmp_path), "tampered.py")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src.replace(match.group(1), tampered))
    proc = _run(path)
    assert proc.returncode != 0, "tampered artifact still ran"
    assert "SECTIONED-OK" not in proc.stdout
    # The kill ladder: silent, exit 137, nothing on stdout/stderr.
    assert proc.returncode == 137, proc.returncode
    assert proc.stdout == "" and proc.stderr == ""


def test_truncated_pack_fails_closed(tmp_path):
    """Dropping a section must not yield a partial payload."""
    _, src = _emit(tmp_path, section_split=True, section_count=4)
    match = _pack_match(src)
    pack = json.loads(base64.b85decode(match.group(1)).decode("utf-8"))
    pack["sections"] = pack["sections"][:-1]
    truncated = base64.b85encode(
        json.dumps(pack, sort_keys=True).encode()).decode()
    path = os.path.join(str(tmp_path), "truncated.py")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src.replace(match.group(1), truncated))
    proc = _run(path)
    assert proc.returncode != 0
    assert "SECTIONED-OK" not in proc.stdout


def test_loader_snippet_is_stdlib_only_and_self_contained():
    from obfuscator.section_split import emit_loader_snippet
    src = emit_loader_snippet()
    assert "def _nx_section_join(" in src
    compile(src, "<snippet>", "exec")
    # No third-party imports: the loader is stdlib-only.
    for banned in ("import requests", "import numpy", "import cryptography",
                   "from Cython"):
        assert banned not in src
