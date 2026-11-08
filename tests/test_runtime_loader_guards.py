"""Structural guards for the loader/runtime fixes from the 2026-11-08 audit.

These pin the code SHAPES that carry the fixes, the same way
test_item_fixes.py pins the JIT hooks: if a refactor removes the payload's
exit-code propagation, the loader runtime bound, the SIMD-VM fail-loud
behaviour, or the UPX archive pin, these tests fail even though nothing
else in the suite can see it.
"""
import os
import sys
import tarfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _utils_source():
    with open(os.path.join(REPO, "obfuscator", "core", "utils.py"),
              encoding="utf-8") as f:
        return f.read()


def _window(src, needle, span=300):
    i = src.index(needle)
    return src[i:i + span]


# ── Emitted loaders: payload exit codes and runtime are no longer swallowed ──

def test_universal_loader_propagates_payload_status():
    """The loader used to subprocess.call() and fall off the end: rc always 0,
    no runtime bound, every failure silent."""
    src = _utils_source()
    block = _window(src, "_rc = subprocess.call([path] + sys.argv[1:], timeout=3600)")
    assert "sys.exit(_rc)" in block, "payload exit code is still swallowed"
    assert "except SystemExit" in src, "a propagating exit must not be re-caught"
    assert 'sys.stderr.write("[loader] failed:' in src, (
        "loader failures are silent again")


def test_tar_loader_propagates_payload_status(tmp_path):
    from obfuscator.core.utils import generate_tar_loader_script
    tar_path = tmp_path / "payload.tar.xz"
    with tarfile.open(tar_path, "w:xz") as tar:
        payload = tmp_path / "inner.bin"
        payload.write_bytes(b"0" * 16)
        tar.add(str(payload), arcname="inner.bin")
    script = generate_tar_loader_script(str(tar_path))[0]
    assert "timeout=3600" in script, "tar loader runs the payload unbounded"
    assert "sys.exit(_rc)" in script, "tar loader swallows the payload's status"
    assert "except SystemExit" in script, "SystemExit must not be re-caught"
    assert "os.remove(tmp_path)" in script, (
        "the loader's temp archive copy is left behind")


def test_both_loader_sites_are_guarded():
    """Both emitted loaders carry the fix, not just one of them."""
    src = _utils_source()
    assert src.count("subprocess.call([tmp_path] + sys.argv[1:], timeout=3600)")
    assert src.count("subprocess.call([path] + sys.argv[1:], timeout=3600)")


# ── build.py: a broken native VM fails the build instead of shipping green ──

def test_simd_vm_build_fails_loud_and_bounds_its_test_run():
    with open(os.path.join(REPO, "scripts", "build.py"), encoding="utf-8") as f:
        src = f.read()
    for marker in ("SIMD-VM tests FAILED", "SIMD-VM compilation failed"):
        block = _window(src, marker)
        assert "sys.exit(1)" in block, (
            "%s logged without failing the build" % marker)
    assert "timeout=120" in src, "SIMD-VM test binary runs unbounded"


# ── UPX download: the archive is hash-checked before it becomes code ────────

_UPX_BODY = b"not really upx"


def _plant_upx_archive(monkeypatch, pin):
    import hashlib
    import shutil
    import urllib.request
    import obfuscator.core.utils as utils
    # A machine with a system upx would return before ever reaching the
    # download branch; force the branch these tests exist for.
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None)
    tools = os.path.join(os.path.dirname(utils.__file__), ".tools")
    os.makedirs(tools, exist_ok=True)
    archive = os.path.join(tools, "upx-4.2.2-amd64_linux.tar.xz")
    with open(archive, "wb") as f:
        f.write(_UPX_BODY)
    digest = hashlib.sha256(_UPX_BODY).hexdigest()
    monkeypatch.setenv("NIXON_UPX_SHA256", pin)
    monkeypatch.setattr(urllib.request, "urlretrieve", lambda url, path: None)
    return archive, digest


def test_upx_pin_mismatch_refuses_the_archive(monkeypatch):
    import obfuscator.core.utils as utils
    archive, _ = _plant_upx_archive(monkeypatch, pin="0" * 64)
    try:
        assert utils.ensure_upx_installed() is False
        assert not os.path.exists(archive), "refused archive was kept"
    finally:
        if os.path.exists(archive):
            os.remove(archive)


def test_upx_without_a_pin_prints_the_hash(monkeypatch, capsys):
    import obfuscator.core.utils as utils
    archive, digest = _plant_upx_archive(monkeypatch, pin="")
    try:
        utils.ensure_upx_installed()   # dummy archive: extraction fails, rc False
        out = capsys.readouterr().out
        assert digest in out, "unpinned download must print its hash to pin later"
    finally:
        if os.path.exists(archive):
            os.remove(archive)


def test_upx_pin_match_passes_the_hash_gate(monkeypatch, capsys):
    import hashlib
    import obfuscator.core.utils as utils
    digest = hashlib.sha256(_UPX_BODY).hexdigest()
    archive, _ = _plant_upx_archive(monkeypatch, pin=digest)
    try:
        rc = utils.ensure_upx_installed()
        out = capsys.readouterr().out
        assert "refusing it" not in out, "a matching pin was rejected"
        assert rc is False, (
            "the dummy archive cannot yield a real upx binary; downstream "
            "extraction must fail, not the hash gate")
    finally:
        if os.path.exists(archive):
            os.remove(archive)
