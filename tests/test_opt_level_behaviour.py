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
