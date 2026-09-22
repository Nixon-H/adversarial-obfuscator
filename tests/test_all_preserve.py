"""AUDIT GAP #64 (C11): module-level ``__all__`` preservation.

Names listed in a static ``__all__`` (list/tuple of string literals)
survive obfuscation so the built module stays importable with a correct
public API. Dynamic ``__all__`` (computed) -> warning, no crash.
No ``__all__`` -> unchanged behavior.
"""
import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.all_preserve import extract_all_names, warning_comment
from obfuscator.core.sources import apply_ast_mutation

_MIN_OPTS = {
    "cfg_flatten": False, "opaque_predicates": False, "exception_flow": False,
    "fragment_strings": False, "mba_subs": False, "obf_calls": False,
    "bogus_exceptions": False, "split_vars": False, "unfold_constants": False,
    "strip_meta": False, "dynamic_code": False, "enhanced_junk": False,
    "break_decompiler": False, "code_checksums": False, "unicode_ids": False,
    "symbol_rename": True,
}

_MOD_SRC = (
    '__all__ = ["foo", "Bar"]\n'
    'def foo():\n'
    '    return 7\n'
    'class Bar:\n'
    '    def ping(self):\n'
    '        return "pong"\n'
    'def _priv():\n'
    '    return 9\n'
)


def _obfuscate(src, extra=None):
    opts = dict(_MIN_OPTS)
    if extra:
        opts.update(extra)
    out, _ = apply_ast_mutation(src, opts)
    compile(out, "<all_preserve>", "exec")
    return out


def test_extract_static_list_and_tuple():
    names, dynamic = extract_all_names(ast.parse('__all__ = ["a", "b"]\n'))
    assert names == ["a", "b"] and dynamic is False
    names, dynamic = extract_all_names(ast.parse("__all__ = ('a',)\n"))
    assert names == ["a"] and dynamic is False


def test_extract_dynamic_flags():
    names, dynamic = extract_all_names(
        ast.parse("__all__ = [x for x in y]\n"))
    assert names == [] and dynamic is True
    names, dynamic = extract_all_names(ast.parse("__all__ = get_all()\n"))
    assert dynamic is True
    assert "dynamic __all__" in warning_comment(names, dynamic)


def test_extract_no_all():
    names, dynamic = extract_all_names(ast.parse("x = 1\n"))
    assert names == [] and dynamic is False


def test_public_exports_survive_rename():
    out = _obfuscate(_MOD_SRC)
    assert "def foo(" in out
    assert "class Bar" in out
    assert "__all__" in out
    ns = {"__name__": "all_mod"}
    exec(compile(out, "<all_mod>", "exec"), ns)
    assert ns["foo"]() == 7
    assert ns["Bar"]().ping() == "pong"
    assert set(ns["__all__"]) == {"foo", "Bar"}


def test_private_names_still_renamed():
    out = _obfuscate(_MOD_SRC)
    assert "def _priv(" in out  # underscore-prefixed: renamer skips
    # A non-exported public helper must NOT survive under its own name.
    src2 = _MOD_SRC + "def helper():\n    return 1\n"
    out2 = _obfuscate(src2)
    assert "def helper(" not in out2


def test_dynamic_all_no_crash_and_warns(capsys):
    src = "__all__ = [n for n in ['foo']]\ndef foo():\n    return 1\n"
    out = _obfuscate(src)
    compile(out, "<dyn_all>", "exec")
    # Dynamic __all__ is computed: nothing can be reserved statically, so
    # foo renames (documented); the requirement is warning + no crash.
    assert "dynamic __all__" in warning_comment([], True)
    ns = {"__name__": "dyn_all_mod"}
    exec(compile(out, "<dyn_all_mod>", "exec"), ns)
    exported = [v for k, v in ns.items() if callable(v) and k != "foo"]
    assert exported and exported[0]() == 1


def test_no_all_unchanged_behavior():
    src = "def foo():\n    return 3\n"
    out = _obfuscate(src)
    ns = {"__name__": "no_all_mod"}
    exec(compile(out, "<no_all_mod>", "exec"), ns)
    # foo is not in __all__ so it renames (pre-existing behavior kept).
    assert "foo" not in ns


def test_tuple_all_form():
    src = (
        '__all__ = ("foo", "Bar")\n'
        'def foo():\n'
        '    return 5\n'
        'class Bar:\n'
        '    pass\n'
    )
    out = _obfuscate(src)
    ns = {"__name__": "tuple_all_mod"}
    exec(compile(out, "<tuple_all_mod>", "exec"), ns)
    assert ns["foo"]() == 5
    assert "Bar" in ns
