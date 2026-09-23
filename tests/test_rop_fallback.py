"""Coverage for RopCompiler._fallback_compile (scripts/rop/rop_compiler.py).

An unhandled AST node must never be silently dropped: the compiler must
record a warning AND emit an int3 trap placeholder.
"""

import ast
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.rop import GadgetFinder, RopCompiler
from scripts.rop.rop_compiler import TRAP_PLACEHOLDER


def _make_compiler():
    finder = GadgetFinder()
    finder.find_gadgets()
    return RopCompiler(finder=finder)


def test_fallback_records_warning_and_emits_trap(caplog):
    compiler = _make_compiler()
    tree = ast.parse("def f():\n    x = 1\n    assert x\n    return x")
    # 'assert x' is ast.Assert — not handled by _compile_stmt → fallback.
    assert any(isinstance(n, ast.Assert) for n in tree.body[0].body)
    with caplog.at_level(logging.WARNING, logger="scripts.rop.rop_compiler"):
        chain = compiler.compile(tree.body[0])
    assert "Assert" in compiler.warnings
    assert compiler.fallback_count == 1
    assert TRAP_PLACEHOLDER in chain.entries
    assert any("Assert" in r.message for r in caplog.records)


def test_fallback_import_statement_warns_and_traps():
    compiler = _make_compiler()
    tree = ast.parse("def f():\n    import os\n    return 1")
    chain = compiler.compile(tree.body[0])
    assert "Import" in compiler.warnings
    assert compiler.fallback_count >= 1
    assert TRAP_PLACEHOLDER in chain.entries


def test_fallback_strict_mode_raises():
    import pytest

    compiler = _make_compiler()
    compiler.strict = True
    tree = ast.parse("def f():\n    import os\n    return 1")
    with pytest.raises(NotImplementedError, match="Import"):
        compiler.compile(tree.body[0])


def test_handled_nodes_emit_no_warnings():
    compiler = _make_compiler()
    tree = ast.parse("def f():\n    x = 1\n    return x")
    chain = compiler.compile(tree.body[0])
    assert compiler.warnings == []
    assert compiler.fallback_count == 0
    assert TRAP_PLACEHOLDER not in chain.entries
