"""Every opt-level must preserve behaviour for a payload with imports, a class and try/except.

Added after two build defects found only by using the tool as a user would:

  * `import zlib` kept its spelling while its uses were renamed (the identifier encoder had no
    visit_Import, and its reserved set was a hardcoded module list that omitted zlib);
  * `except ZeroDivisionError:` became a reference to an undefined name, because
    ZeroDivisionError was in no reserved set and the dynamic_unbounds branch renamed before the
    reserved check;
  * a method's parameter uses were renamed while the parameter kept its spelling.

None was visible to the artefact gate, whose payloads avoid these constructs. This test builds
the payload at every level and compares what it prints to what the source prints.
"""
import ast
import contextlib
import io

import pytest

from obfuscator.core.sources import apply_ast_mutation

SOURCE = '''import zlib


class Vault:
    def __init__(self, name):
        self.name = name
        self.items = {}

    def put(self, key, value):
        self.items[key] = value
        return self


def pack(text):
    return zlib.compress(text.encode()).hex()[:12]


def guarded(depth):
    total = 0
    for i in range(depth):
        try:
            total += 10 // (2 - i) if i != 2 else (_ for _ in ()).throw(ZeroDivisionError())
        except ZeroDivisionError:
            total += 1
    return total


vault = Vault("demo").put("a", 1)
print("vault:", vault.name, sorted(vault.items))
print("pack:", pack("abc"))
print("guarded:", guarded(5))
print("OK")
'''


def _run(code, filename):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(code, filename, "exec"), {"__name__": "__main__"})
    return buf.getvalue()


EXPECTED = _run(SOURCE, "<source>")


@pytest.mark.parametrize("level", [0, 1, 2, 3, 4, 5])
def test_opt_level_preserves_behaviour(level):
    out, _ = apply_ast_mutation(SOURCE, {"opt_level": level})
    compile(out, "<artifact>", "exec")  # must at least be valid syntax
    assert _run(out, f"<level{level}>") == EXPECTED, (
        f"opt-level {level} changed the program's output")


def test_imported_module_is_not_renamed_into_oblivion():
    """The specific defect: `import zlib` must keep a usable binding at every level."""
    for level in range(6):
        out, _ = apply_ast_mutation(SOURCE, {"opt_level": level})
        assert "zlib" in out, f"opt-level {level} renamed zlib out of the module"
        _run(out, f"<zlib{level}>")


def test_exception_type_is_never_renamed():
    """`except ZeroDivisionError` must survive: it has no binding in the module."""
    for level in range(6):
        out, _ = apply_ast_mutation(SOURCE, {"opt_level": level})
        assert "ZeroDivisionError" in out, (
            f"opt-level {level} renamed a builtin exception that nothing binds")


# ---------------------------------------------------------------------------
# Direct encoder coverage: apply_ast_mutation does not reach this transform, so
# the tests above cannot catch its defects. Verified by reinstating the missing
# visit_Import and watching these fail while the ones above still passed.
# ---------------------------------------------------------------------------

def _encode(source):
    import ast

    from obfuscator.core.transforms import UnicodeIdentifierEncoder

    tree = ast.parse(source)
    encoded = UnicodeIdentifierEncoder().visit(tree)
    return ast.unparse(ast.fix_missing_locations(encoded))


def test_encoder_keeps_import_bindings_and_their_uses():
    out = _encode("import zlib\nx = zlib.compress(b'a')\nprint(len(x))\n")
    assert "zlib" in out, "the encoder renamed a module binding it never re-declares"
    namespace = {}
    exec(compile(out, "<encoded>", "exec"), namespace)


def test_encoder_keeps_from_import_bindings():
    out = _encode("from sys import hexversion\nprint(hexversion > 0)\n")
    assert "hexversion" in out, "the encoder renamed a from-import binding"


def test_encoder_does_not_rename_parameters():
    """A method parameter and its uses must agree.

    Module-level names are encoded by design, so the test observes the result
    through `print` (a reserved builtin) rather than by looking a name up.
    """
    out = _encode(
        "class C:\n"
        "    def m(self, n):\n"
        "        return n + 1\n"
        "print(C().m(2))\n"
    )
    assert _run(out, "<encoded>") == "3\n", "a method parameter and its uses disagreed"


def test_encoder_never_renames_builtin_exceptions():
    out = _encode(
        "def f():\n"
        "    try:\n"
        "        return 1\n"
        "    except ZeroDivisionError:\n"
        "        return 0\n"
        "print(f())\n"
    )
    assert "ZeroDivisionError" in out, "a builtin exception name was renamed"
    assert _run(out, "<encoded>") == "1\n"


def test_symbol_renamer_never_renames_builtin_exceptions():
    """The exact path that produced `_nx_f640f1`.

    `except ZeroDivisionError:` became md5("ZeroDivisionError")[:6], because the
    dynamic_unbounds branch renames BEFORE the reserved check. Adding the name to
    the reserved set was not enough; the guard has to come first.
    """
    from obfuscator.core.transforms import SymbolRenamer

    renamer = SymbolRenamer()
    renamer.dynamic_unbounds = {"ZeroDivisionError", "ValueError", "StopIteration"}
    for name in ("ZeroDivisionError", "ValueError", "StopIteration"):
        assert renamer.get_new_name(name) == name, (
            f"{name} was renamed to {renamer.get_new_name(name)}; nothing binds it")


def test_fault_triggers_raise_the_exception_their_handler_catches():
    """The trigger list and the handler list are aligned by index.

    Index 6 used to be `{}.__getitem__(0)`, which raises KeyError, while
    _exc_types[6] is RuntimeError. The block's handler caught RuntimeError,
    nothing matched, the fallback re-raised, and the exception escaped the
    function -- which is why opt-level 5 appeared to drop statements.
    """
    import ast

    from obfuscator.core.sources import ExceptionFlowTransformer

    transformer = ExceptionFlowTransformer()
    for idx, build in enumerate(transformer._triggers):
        declared = transformer._exc_types[idx % len(transformer._exc_types)]
        node = build()
        stmt = node if isinstance(node, ast.stmt) else ast.Expr(value=node)
        tree = ast.Module(body=[stmt], type_ignores=[])
        code = compile(ast.fix_missing_locations(tree), "<trigger>", "exec")
        try:
            exec(code, {})
        except BaseException as exc:  # noqa: BLE001 - the type is the assertion
            assert type(exc).__name__ == declared, (
                f"trigger {idx} raises {type(exc).__name__} but its handler "
                f"catches {declared}; the exception would escape the function")
        else:
            raise AssertionError(f"trigger {idx} raised nothing; expected {declared}")


def _undefined_names(tree):
    """Names loaded but never bound anywhere in the module, and not builtins."""
    import builtins

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
    return used - bound


def test_injected_decoys_never_reference_an_unbound_name():
    """The provenance poisoner injected code using `secrets` with no import.

    Two templates were affected. The module then referenced a name nothing binds:
    invisible while the decoys are never called, fatal to static analysis of the
    output, and a NameError the moment one is.
    """
    from scripts.provenance.poisoner import ProvenancePoisoner

    poisoner = ProvenancePoisoner()
    tree = ast.parse("def target(x):\n    return x + 1\n")
    for generator in ("_generate_fake_apis", "_generate_fake_protocol_parsers"):
        method = getattr(poisoner, generator, None)
        if method is None:
            raise AssertionError(f"poisoner no longer has {generator}; update this test")
        method(tree)
    missing = _undefined_names(tree)
    assert not missing, f"injected module loads names nothing binds: {sorted(missing)}"


def test_fragmentation_never_leaves_a_dangling_branch():
    """Splitting a function mid-flow moved the block its last kept block jumped to.

    llvmgen then emitted `br label %bb0` with no `bb0` in that function, and llc
    rejected the module with "use of undefined value '%bb0'". SSA values cannot
    cross into a fragment without parameter passing, so such a split cannot be
    repaired; the transform must decline it.
    """
    from irgen.compile import IrFunction, IrModule
    from scripts.watermark.semantic_watermark import embed_fragmentation_watermark

    module = IrModule("fragtest")
    func = IrFunction("victim", None)
    a = func.new_block("a")
    b = func.new_block("b")
    c = func.new_block("c")
    a.set_terminator("jmp", target_label=b.label)
    b.set_terminator("jmp", target_label=c.label)
    c.set_terminator("ret")
    module.functions.append(func)

    embed_fragmentation_watermark(module, [1, 1, 1], seed=0)

    for fn in module.functions:
        labels = {blk.label for blk in fn.blocks}
        for blk in fn.blocks:
            term = getattr(blk, "terminator", None)
            if term is None:
                continue
            for key in ("target_label", "true_label", "false_label"):
                label = getattr(term, key, None)
                if label is not None:
                    assert label in labels, (
                        f"{fn.name}: block {blk.label} branches to {label}, "
                        f"which that function does not define")
