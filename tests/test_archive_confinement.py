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
    """No bare extractall may remain outside the helpers."""
    import ast
    src = open(os.path.join(ROOT, "obfuscator", "core", "utils.py"),
               encoding="utf-8").read()
    tree = ast.parse(src)
    helper_lines = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in (
                "_extract_zip_confined", "_extract_tar_confined"):
            helper_lines.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    bare = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Attribute)
                and node.func.attr == "extractall"):
            continue
        if node.lineno in helper_lines:
            continue
        bare.append(node.lineno)
    assert not bare, ("unconfined extractall() at lines %r" % (bare,))
