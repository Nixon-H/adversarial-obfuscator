"""Smoke coverage: every opt-level must produce importable output for REAL modules.

**What this does cover:** that four corpus modules -- one per construct family (a stress fixture,
a library with heavy imports, a bulk utility, a third-party module) -- survive all six levels and
still import.

**What it does not cover, measured rather than assumed:** the four build defects of 2026-11 are
NOT caught here. `apply_ast_mutation(..., {"opt_level": n})` does not reach `UnicodeIdentifierEncoder`
or the exception-flow trigger, so reinstating the import fix, the exception fix or the trigger fix
leaves all 25 of these tests green. They were checked one at a time and each stayed green.

The guards for those defects are the direct ones in `tests/test_opt_level_behaviour.py`, each of
which was verified to fail when its defect is reinstated. This file is a breadth check, not a
substitute for them, and saying so is the point of this paragraph.

Kept to `apply_ast_mutation` rather than a full build because a build is ~20s per module.
"""
import importlib.util
import os
import sys
import tempfile

import pytest

from obfuscator.core.sources import apply_ast_mutation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "scripts", "transfer", "corpus")

MODULES = [
    ("stress", os.path.join(CORPUS, "fixtures", "stress.py")),
    ("recipes", os.path.join(CORPUS, "pkg", "more_itertools", "recipes.py")),
    ("iterutils", os.path.join(CORPUS, "bulk", "iterutils.py")),
    ("strutils", os.path.join(CORPUS, "external3", "strutils.py")),
]


def _imports_cleanly(code, name):
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, name + ".py")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(code)
        spec = importlib.util.spec_from_file_location(name + "_probe", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


@pytest.mark.parametrize("label,path", MODULES, ids=[m[0] for m in MODULES])
@pytest.mark.parametrize("level", [0, 1, 2, 3, 4, 5])
def test_level_output_compiles_and_imports(label, path, level):
    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    out, _ = apply_ast_mutation(source, {"opt_level": level})
    compile(out, f"<{label}@{level}>", "exec")
    module = _imports_cleanly(out, f"{label}_{level}")
    assert module is not None


def test_no_output_loads_a_name_nothing_binds():
    """The invariant behind five separate defects in this subsystem."""
    import ast

    import builtins

    for label, path in MODULES:
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        for level in (0, 1, 5):
            out, _ = apply_ast_mutation(source, {"opt_level": level})
            tree = ast.parse(out)
            bound = set(dir(builtins))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        bound.add((alias.asname or alias.name).split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name != "*":
                            bound.add(alias.asname or alias.name)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    bound.add(node.name)
                elif isinstance(node, ast.arg):
                    bound.add(node.arg)
                elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                    bound.add(node.id)
                elif isinstance(node, ast.ExceptHandler) and node.name:
                    bound.add(node.name)
                elif isinstance(node, (ast.Global, ast.Nonlocal)):
                    bound.update(node.names)
            used = {n.id for n in ast.walk(tree)
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
            missing = used - bound
            assert not missing, f"{label}@{level}: loads unbound names {sorted(missing)}"
