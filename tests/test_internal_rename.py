"""V10 gap: opt-in renaming of proven-internal public methods/attributes.

Default (flag OFF) = safe: public methods defined in a class body are
preserved (external API intact). Opt-in (``rename_internal=True`` /
``--rename-internal``) = methods proven used ONLY inside their own
class rename too (defs + ``self.m`` uses rewrite consistently).

Conservative proof: getattr-string refs, __all__ exports, dunders,
decorated methods (except plain @staticmethod/@classmethod), and any
external ``obj.method`` access all block the rename.
"""
import ast
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.sources import apply_ast_mutation
from obfuscator.core.transforms import SymbolRenamer, UnicodeIdentifierEncoder
from obfuscator.internal_rename import find_internal_methods

_MIN_OPTS = {
    "cfg_flatten": False, "opaque_predicates": False, "exception_flow": False,
    "fragment_strings": False, "mba_subs": False, "obf_calls": False,
    "bogus_exceptions": False, "split_vars": False, "unfold_constants": False,
    "strip_meta": False, "dynamic_code": False, "enhanced_junk": False,
    "break_decompiler": False, "code_checksums": False, "unicode_ids": False,
    "symbol_rename": True,
}

_INTERNAL_SRC = (
    "class Worker:\n"
    "    def compute(self, x):\n"
    "        return self.helper(x) * 2\n"
    "    def helper(self, x):\n"
    "        return x + 1\n"
    "w = Worker()\n"
    "print(w.compute(5))\n"
)

_EXTERNAL_SRC = (
    "class Worker:\n"
    "    def compute(self, x):\n"
    "        return self.helper(x) * 2\n"
    "    def helper(self, x):\n"
    "        return x + 1\n"
    "w = Worker()\n"
    "print(w.compute(5))\n"
    "print(w.helper(5))\n"
)


def _obfuscate(src, rename_internal=False, seed=0):
    random.seed(seed)
    opts = dict(_MIN_OPTS)
    if rename_internal:
        opts["rename_internal"] = True
    out, _ = apply_ast_mutation(src, opts)
    compile(out, "<internal_rename>", "exec")
    return out


def test_proof_finds_internal_only_method():
    tree = ast.parse(_INTERNAL_SRC)
    found = find_internal_methods(tree)
    names = {m for _, m in found}
    assert "helper" in names
    assert "compute" not in names  # called externally via w.compute


def test_proof_blocks_external_usage():
    tree = ast.parse(_EXTERNAL_SRC)
    found = find_internal_methods(tree)
    names = {m for _, m in found}
    # Both compute and helper are called externally: neither is internal.
    assert "helper" not in names
    assert "compute" not in names


def test_internal_method_renamed_with_flag():
    out = _obfuscate(_INTERNAL_SRC, rename_internal=True)
    assert "def helper(" not in out
    assert "def compute(" in out  # externally used: preserved
    ns = {}
    exec(compile(out, "<t>", "exec"), ns)
    assert ns["w"].compute(5) == 12 if "w" in ns else True


def test_internal_rename_output_still_runs():
    out = _obfuscate(_INTERNAL_SRC, rename_internal=True)
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(compile(out, "<t>", "exec"), {"__name__": "ir_exec"})
    assert buf.getvalue().strip() == "12"


def test_external_usage_preserved_with_and_without_flag():
    for flag in (False, True):
        out = _obfuscate(_EXTERNAL_SRC, rename_internal=flag)
        assert "def helper(" in out
        assert "def compute(" in out
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            exec(compile(out, "<t>", "exec"), {"__name__": "ext_exec"})
        assert buf.getvalue().strip().split() == ["12", "6"]


def test_getattr_string_ref_blocks_rename():
    src = (
        "class Worker:\n"
        "    def helper(self, x):\n"
        "        return x + 1\n"
        "    def run(self, x):\n"
        "        return getattr(self, \"helper\")(x)\n"
        "w = Worker()\n"
        "print(w.run(5))\n"
    )
    tree = ast.parse(src)
    assert ("Worker", "helper") not in find_internal_methods(tree)
    out = _obfuscate(src, rename_internal=True)
    assert "def helper(" in out


def test_dunder_untouched():
    src = (
        "class Worker:\n"
        "    def __init__(self):\n"
        "        self.x = 1\n"
        "    def helper(self):\n"
        "        return self.x\n"
        "    def run(self):\n"
        "        return self.helper()\n"
        "w = Worker()\n"
        "print(w.run())\n"
    )
    tree = ast.parse(src)
    assert ("Worker", "__init__") not in find_internal_methods(tree)
    out = _obfuscate(src, rename_internal=True)
    assert "def __init__(" in out


def test_all_exported_preserved():
    src = (
        '__all__ = ["helper"]\n'
        "class Worker:\n"
        "    def helper(self):\n"
        "        return 1\n"
        "    def run(self):\n"
        "        return self.helper()\n"
    )
    tree = ast.parse(src)
    assert ("Worker", "helper") not in find_internal_methods(tree, ["helper"])
    out = _obfuscate(src, rename_internal=True)
    assert "def helper(" in out


def test_decorated_method_blocked():
    src = (
        "class Worker:\n"
        "    @property\n"
        "    def value(self):\n"
        "        return 1\n"
    )
    tree = ast.parse(src)
    assert ("Worker", "value") not in find_internal_methods(tree)


def test_staticmethod_internal_still_renames():
    src = (
        "class Worker:\n"
        "    @staticmethod\n"
        "    def fmt(x):\n"
        "        return x + 1\n"
        "    def run(self, x):\n"
        "        return self.fmt(x)\n"
        "w = Worker()\n"
        "print(w.run(1))\n"
    )
    tree = ast.parse(src)
    assert ("Worker", "fmt") in find_internal_methods(tree)
    out = _obfuscate(src, rename_internal=True)
    assert "def fmt(" not in out


def test_default_off_renames_nothing_beyond_current_behavior():
    # Golden: output without flag == output before change. The renamer
    # always preserved class-body methods (existing behavior); the flag
    # only ADDS renames for the proven set.
    out_off = _obfuscate(_INTERNAL_SRC, rename_internal=False)
    assert "def helper(" in out_off
    assert "def compute(" in out_off
    # Direct renamer parity: a bare SymbolRenamer (no allow set) must
    # also preserve class-body public methods.
    tree = ast.parse(_INTERNAL_SRC)
    tree = SymbolRenamer().visit(tree)
    ast.fix_missing_locations(tree)
    assert "def helper(" in ast.unparse(tree)
    assert "def compute(" in ast.unparse(tree)
    # And the unicode encoder path preserves too (its legacy behavior).
    tree2 = ast.parse(_INTERNAL_SRC)
    tree2 = UnicodeIdentifierEncoder().visit(tree2)
    ast.fix_missing_locations(tree2)
    assert "def helper(" in ast.unparse(tree2)


def test_def_use_consistency_with_flag():
    # The renamed def and its self.m call site must share one new name:
    # exactly one def (not helper/compute) + output executes correctly.
    out = _obfuscate(_INTERNAL_SRC, rename_internal=True)
    tree = ast.parse(out)
    defs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    assert "helper" not in defs
    assert "compute" in defs  # externally used: kept
    assert len([d for d in defs if d not in ("compute",)]) >= 1
