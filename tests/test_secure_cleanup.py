"""Tests for scripts.secure_cleanup."""

import os

from scripts.secure_cleanup import secure_cleanup_tree


def test_files_removed(tmp_path):
    d = tmp_path / "tree"
    d.mkdir()
    (d / "a.txt").write_bytes(b"secret-1")
    (d / "b.bin").write_bytes(b"secret-2" * 100)
    result = secure_cleanup_tree(str(d), passes=1)
    assert result["files"] == 2
    assert not d.exists()


def test_nested_dirs_removed(tmp_path):
    d = tmp_path / "nested"
    (d / "sub1" / "sub2").mkdir(parents=True)
    (d / "sub1" / "f.txt").write_bytes(b"x")
    (d / "sub1" / "sub2" / "g.txt").write_bytes(b"y")
    result = secure_cleanup_tree(str(d), passes=1)
    assert result["files"] == 2
    assert result["dirs"] >= 3  # sub2, sub1, root
    assert not d.exists()


def test_symlinks_skipped_not_followed(tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"do-not-delete")
    d = tmp_path / "tree"
    d.mkdir()
    (d / "real.txt").write_bytes(b"wipe-me")
    os.symlink(str(outside), str(d / "link.txt"))
    os.symlink(str(tmp_path), str(d / "linkdir"))
    result = secure_cleanup_tree(str(d), passes=1)
    # Outside target must survive; symlinks recorded as skipped.
    assert outside.exists()
    assert outside.read_bytes() == b"do-not-delete"
    assert any("symlink" in e for e in result["errors"])
    # real file was wiped
    assert not (d / "real.txt").exists()


def test_missing_dir_returns_errors_entry(tmp_path):
    missing = str(tmp_path / "no-such-dir")
    result = secure_cleanup_tree(missing)
    assert result["files"] == 0
    assert result["dirs"] == 0
    assert len(result["errors"]) >= 1
