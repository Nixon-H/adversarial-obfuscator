"""Tests for obfuscator.secure_temp."""

import os
import stat
import tempfile
import time

from obfuscator.secure_temp import (
    emit_loader_snippet,
    purge_stale,
    secure_unlink,
    secure_write_temp,
)


def test_write_read_roundtrip():
    data = b"hello-secure-world\x00\xff"
    path = secure_write_temp(data, ".bin")
    try:
        with open(path, "rb") as f:
            assert f.read() == data
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_mode_is_0600():
    path = secure_write_temp(b"x", ".bin")
    try:
        mode = stat.S_IMODE(os.stat(path).st_mode)
        assert mode == 0o600, f"expected 0o600, got {oct(mode)}"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_purge_removes_only_old_matching_prefix():
    tmpdir = tempfile.gettempdir()
    # old matching file -> should be removed
    old_path = secure_write_temp(b"old", ".purge")
    old_name = os.path.basename(old_path)
    assert old_name.startswith("_nx_")
    ancient = time.time() - 7200
    os.utime(old_path, (ancient, ancient))

    # fresh matching file -> must survive
    fresh_path = secure_write_temp(b"fresh", ".purge")
    try:
        # non-matching old file -> must survive
        other = os.path.join(tmpdir, "other_prefix_%d.tmp" % os.getpid())
        with open(other, "w") as f:
            f.write("keep")
        os.utime(other, (ancient, ancient))
        try:
            n = purge_stale(prefix="_nx_", max_age_s=3600)
            assert n >= 1
            assert not os.path.exists(old_path)
            assert os.path.exists(fresh_path)
            assert os.path.exists(other)
        finally:
            if os.path.exists(other):
                os.unlink(other)
    finally:
        if os.path.exists(fresh_path):
            os.unlink(fresh_path)
        if os.path.exists(old_path):
            os.unlink(old_path)


def test_secure_unlink_removes_and_true(tmp_path):
    p = tmp_path / "victim.bin"
    p.write_bytes(b"sensitive-data-123")
    assert secure_unlink(str(p), passes=1) is True
    assert not p.exists()


def test_secure_unlink_missing_returns_false(tmp_path):
    missing = str(tmp_path / "does-not-exist.bin")
    assert secure_unlink(missing) is False


def test_snippet_compiles():
    snippet = emit_loader_snippet()
    assert isinstance(snippet, str) and len(snippet) > 0
    compile(snippet, "<loader_snippet>", "exec")
    assert "O_EXCL" in snippet
    assert "atexit" in snippet
    assert "_nx_" in snippet
