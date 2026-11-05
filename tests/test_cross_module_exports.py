"""Defect 13: a module's public name renamed while its importer is not rewritten.

The scan helper is exercised against a real package layout, and the option is shown
to prevent the ImportError the defect produces.
"""
import sys


from obfuscator.core.sources import apply_ast_mutation
from obfuscator.cross_module import sibling_imports

_MIN_OPTS = {
    "cfg_flatten": False, "opaque_predicates": False, "exception_flow": False,
    "fragment_strings": False, "mba_subs": False, "obf_calls": False,
    "bogus_exceptions": False, "split_vars": False, "unfold_constants": False,
    "strip_meta": False, "dynamic_code": False, "enhanced_junk": False,
    "break_decompiler": False, "code_checksums": False, "unicode_ids": False,
    "symbol_rename": True,
}

_MOD_SRC = '''def cmp_using(**kwargs):
    return sorted(kwargs)


def not_imported_fn(x):
    return x + 1
'''


def _make_package(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "_mod.py").write_text(_MOD_SRC, encoding="utf-8")
    (pkg / "__init__.py").write_text(
        "from ._mod import cmp_using\n\n__all__ = ['cmp_using']\n", encoding="utf-8")
    return pkg


def test_scanner_finds_sibling_imports(tmp_path):
    pkg = _make_package(tmp_path)
    assert sibling_imports(str(pkg / "_mod.py")) == {"cmp_using"}


def test_scanner_ignores_unrelated_modules(tmp_path):
    pkg = _make_package(tmp_path)
    (pkg / "other.py").write_text("X = 1\n", encoding="utf-8")
    assert "X" not in sibling_imports(str(pkg / "_mod.py"))


def _obfuscate(tmp_path, extra=None):
    pkg = _make_package(tmp_path)
    opts = dict(_MIN_OPTS)
    if extra:
        opts.update(extra)
    out, _ = apply_ast_mutation(_MOD_SRC, opts)
    (pkg / "_mod.py").write_text(out, encoding="utf-8")
    return pkg


def _imports(pkg):
    """Import the package in a fresh interpreter path and report the error, if any."""
    import importlib
    sys.path.insert(0, str(pkg.parent))
    try:
        for name in [m for m in sys.modules if m == "pkg" or m.startswith("pkg.")]:
            del sys.modules[name]
        importlib.import_module("pkg")
        return None
    except Exception as exc:  # noqa: BLE001 - the message is the assertion subject
        return exc
    finally:
        sys.path.remove(str(pkg.parent))


def test_unrenamed_import_breaks_without_the_option(tmp_path):
    """The defect: without the option, the import fails."""
    pkg = _obfuscate(tmp_path)
    err = _imports(pkg)
    assert err is not None, (
        "expected the defect to reproduce: the importer should fail when the "
        "export is renamed and the importer is not rewritten")


def test_option_preserves_the_imported_name_and_the_import_works(tmp_path):
    """The fix: supply the sibling-imported names and the package imports again."""
    probe = _make_package(tmp_path)
    names = sibling_imports(str(probe / "_mod.py"))
    out, _ = apply_ast_mutation(_MOD_SRC, dict(_MIN_OPTS, imported_names=names))
    assert "cmp_using" in out, "the imported name must survive the rename"
    (probe / "_mod.py").write_text(out, encoding="utf-8")
    assert _imports(probe) is None


def test_other_public_names_are_still_renamed(tmp_path):
    """Narrowing, not disabling: names no sibling imports are renamed as before.

    Without this the option would silently disable the documented contract that a
    module without ``__all__`` has its public names renamed.
    """
    probe = _make_package(tmp_path)
    names = sibling_imports(str(probe / "_mod.py"))
    out, _ = apply_ast_mutation(_MOD_SRC, dict(_MIN_OPTS, imported_names=names))
    assert "not_imported_fn" not in out, (
        "a public name that no sibling imports must still be renamed")
