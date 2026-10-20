import os
import sys
import ast
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.parametrize("transformer", ["TypeHintStripper", "FStringLowering"])
def test_ast_transformer_runs(transformer):
    import importlib
    mod = importlib.import_module("obfuscator.core.transforms")
    cls = getattr(mod, transformer)
    tr = cls()
    t = ast.parse('x=1\ny=2\ndef f(): pass')
    tr.visit(t)
    ast.fix_missing_locations(t)
    assert isinstance(t, ast.Module)


def test_symbol_renamer_works():
    from obfuscator.core.transforms import SymbolRenamer
    tr = SymbolRenamer()
    t = ast.parse('def my_func(a, b):\n    return a + b')
    tr.visit(t)
    assert t.body[0].name.startswith('_nixon_'), f"Bad rename: {t.body[0].name}"


def test_string_literal_obfuscator_works():
    from obfuscator.core.transforms import StringLiteralObfuscator
    slo = StringLiteralObfuscator()
    t = ast.parse('x = "secretsauce"')
    slo.visit(t)
    assert not isinstance(t.body[0].value, ast.Constant), "String wasn't obfuscated"
    assert isinstance(t.body[0].value, ast.Call), "Expected Call node after obfuscation"
