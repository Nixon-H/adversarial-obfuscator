"""Builder 3.10-floor lock (GAP 6 audit).

Locks the honest minimal fix: scripts/build.py requires Python >= 3.10
(matching the nyser/py_matrix payload range 3.10-3.14 and the CI matrix),
not 3.11+. Guards:

- the floor tuple in validate_dependencies is (3, 10)
- docs/DEVELOPER.md states 3.10+ and names the payload range
- the build import closure stays 3.10-grammar-parseable

Python 3.10 compatible: stdlib only, no match statements, no X|Y
annotations in evaluated positions.
"""
import ast
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_PY = os.path.join(REPO_ROOT, "scripts", "build.py")
DEV_DOC = os.path.join(REPO_ROOT, "docs", "DEVELOPER.md")

CLOSURE_DIRS = ("scripts", "obfuscator", "irgen", "llvmgen", "vm",
                "encrypt", "config")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_floor_is_310():
    src = _read(BUILD_PY)
    assert "sys.version_info < (3, 10)" in src
    assert "sys.version_info < (3, 11)" not in src
    assert "Python >= 3.10 required" in src


def test_no_stale_311_floor_claim():
    src = _read(BUILD_PY)
    for i, line in enumerate(src.splitlines(), 1):
        if "3.11" in line and ("Python >=" in line or "Python>" in line):
            raise AssertionError("stale 3.11 floor claim %s:%d: %s"
                                 % (BUILD_PY, i, line.strip()))


def test_developer_doc_states_310():
    text = _read(DEV_DOC)
    assert "3.10" in text
    assert "Python 3.11+" not in text


def test_payload_range_consistent():
    from obfuscator.nyser import SUPPORTED_MINORS
    from obfuscator.py_matrix import SUPPORTED
    assert (3, 10) in SUPPORTED_MINORS
    assert (3, 10) in SUPPORTED


def test_build_closure_parses_on_310_grammar():
    bad = []
    n = 0
    for d in CLOSURE_DIRS:
        root_dir = os.path.join(REPO_ROOT, d)
        if not os.path.isdir(root_dir):
            continue
        for root, _dirs, files in os.walk(root_dir):
            if "test_data" in root:
                continue
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(root, fn)
                n += 1
                try:
                    with open(p, encoding="utf-8",
                              errors="replace") as f:
                        src = f.read()
                except OSError:
                    continue
                try:
                    ast.parse(src, feature_version=(3, 10))
                except SyntaxError as e:
                    bad.append("%s: %s" % (p, e))
    assert n > 0
    assert not bad, bad[:10]


def test_build_imports_on_current_interpreter():
    import scripts.common  # noqa: F401
    import scripts.metrics  # noqa: F401
    import scripts.classification  # noqa: F401
    import scripts.phases  # noqa: F401
    assert sys.version_info >= (3, 10)


def test_no_311_only_syntax_in_build_py():
    tree = ast.parse(_read(BUILD_PY))
    for node in ast.walk(tree):
        assert not isinstance(node, ast.Match), "match statement in build.py"
        assert node.__class__.__name__ != "TryStar", "except* in build.py"
    assert "import tomllib" not in _read(BUILD_PY)
    assert "from tomllib" not in _read(BUILD_PY)
