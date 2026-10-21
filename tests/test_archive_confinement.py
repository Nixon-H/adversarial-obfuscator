"""No archive this project extracts may write outside its directory.

A zip (or tar) member named ``../x`` would otherwise write outside the
extraction directory -- ZipSlip / tar traversal.  The build had it
inconsistently: the older build-farm path checked, the Nuitka path did
not, and the tool-download path did not.  All three now go through one
helper, so the check cannot drift apart again.

The check is on the RESOLVED destination, so neither a ``..`` component
nor a symlinked member can escape.
"""
import io
import os
import sys
import tarfile
import zipfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from obfuscator.core import utils as nutils  # noqa: E402


def _zip_with_member(path, member_name, content=b"pwned"):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(member_name, content)
    return path


def test_zip_member_cannot_escape_the_output_dir(tmp_path):
    zip_path = _zip_with_member(str(tmp_path / "evil.zip"), "../escaped.txt")
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(ValueError) as exc:
        nutils._extract_zip_confined(zip_path, str(out))
    assert "escaping output dir" in str(exc.value)
    assert not (tmp_path / "escaped.txt").exists()


def test_zip_member_cannot_escape_by_absolute_path(tmp_path):
    target = tmp_path / "elsewhere.txt"
    zip_path = _zip_with_member(str(tmp_path / "abs.zip"), str(target))
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(ValueError):
        nutils._extract_zip_confined(zip_path, str(out))
    assert not target.exists()


def test_zip_member_cannot_escape_through_a_symlink(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    os.symlink(str(outside), str(out / "link"))
    zip_path = _zip_with_member(str(tmp_path / "sym.zip"), "link/pwned.txt")
    with pytest.raises(ValueError):
        nutils._extract_zip_confined(zip_path, str(out))
    assert not (outside / "pwned.txt").exists()


def test_a_normal_zip_still_extracts(tmp_path):
    zip_path = _zip_with_member(str(tmp_path / "ok.zip"), "sub/file.txt",
                                b"hello")
    out = tmp_path / "out"
    out.mkdir()
    nutils._extract_zip_confined(zip_path, str(out))
    assert (out / "sub" / "file.txt").read_bytes() == b"hello"


def test_tar_member_cannot_escape_the_output_dir(tmp_path):
    tar_path = str(tmp_path / "evil.tar")
    with tarfile.open(tar_path, "w") as t:
        data = b"pwned"
        info = tarfile.TarInfo("../escaped.txt")
        info.size = len(data)
        t.addfile(info, io.BytesIO(data))
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(ValueError) as exc:
        nutils._extract_tar_confined(tar_path, str(out))
    assert "escaping output dir" in str(exc.value)
    assert not (tmp_path / "escaped.txt").exists()


def test_a_normal_tar_still_extracts(tmp_path):
    tar_path = str(tmp_path / "ok.tar")
    with tarfile.open(tar_path, "w") as t:
        data = b"hello"
        info = tarfile.TarInfo("sub/file.txt")
        info.size = len(data)
        t.addfile(info, io.BytesIO(data))
    out = tmp_path / "out"
    out.mkdir()
    nutils._extract_tar_confined(tar_path, str(out))
    assert (out / "sub" / "file.txt").read_bytes() == b"hello"


def test_every_extraction_in_the_farm_is_confined():
    """No bare extractall may remain outside the shared helper.

    This scans the WHOLE tree, not one module: a check that only
    looked at the build-farm path missed the artifact bundler, which
    extracted a bundle with no confinement at all.
    """
    import ast

    # The one place allowed to extract: the shared helper, which
    # confines every member first.
    allowed = os.path.join(ROOT, "obfuscator", "core", "archive_safety.py")
    skipped_dirs = {".git", "build", "archive", "node_modules", "__pycache__",
                    ".venv", "venv", "target", "dist"}
    bare = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skipped_dirs]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            path = os.path.join(dirpath, filename)
            if os.path.abspath(path) == os.path.abspath(allowed):
                continue
            try:
                tree = ast.parse(open(path, encoding="utf-8").read())
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not (isinstance(node.func, ast.Attribute)
                        and node.func.attr == "extractall"):
                    continue
                bare.append("%s:%d" % (os.path.relpath(path, ROOT), node.lineno))
    assert not bare, ("unconfined extractall() at %r" % (bare,))


def test_the_bundler_cannot_be_escaped(tmp_path):
    """The artifact bundler's verify path must not extract outside.

    It used to extract the bundle with no confinement at all.  The
    escape is refused and the bundle is reported invalid -- and
    nothing lands outside the extraction directory.
    """
    from scripts.artifacts.bundler import ReproducibilityBundle

    bundle = ReproducibilityBundle(str(tmp_path))

    # A zip whose member escapes the extraction directory.
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr("../escaped.txt", b"pwned")
    result = bundle.verify_bundle(str(evil))
    assert result.get("valid") is False, result
    assert not (tmp_path / "escaped.txt").exists()


def test_a_normal_bundle_still_verifies(tmp_path):
    """The confinement must not break the ordinary path."""
    from scripts.artifacts.bundler import ReproducibilityBundle

    bundle = ReproducibilityBundle(str(tmp_path))
    bundle.add_file("/etc/hostname", "data/host.txt")
    zip_path = bundle.bundle(str(tmp_path / "bundle.zip"))
    result = bundle.verify_bundle(zip_path)
    assert result.get("valid") is True, result


def test_the_shared_helper_is_where_extraction_happens():
    """The confinement helper is one module, shared by every caller."""
    from obfuscator.core import archive_safety

    assert hasattr(archive_safety, "extract_zip_confined")
    assert hasattr(archive_safety, "extract_tar_confined")
    assert hasattr(archive_safety, "confined_member_path")
