import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.macros import (
    MACROS,
    apply_macros,
    collect_macros,
    emit_runtime_helpers,
    parse_trial,
)


def test_macros_set():
    assert MACROS == {
        "IS_OBFUSCATED", "GET_HWID", "SELF_DELETE", "SECURE_DELETE",
        "CRASH", "DETECT_FILE_TYPE", "__all__",
    }


def test_collect_finds_each_macro():
    for name in ("IS_OBFUSCATED", "GET_HWID", "SELF_DELETE",
                 "SECURE_DELETE", "CRASH", "DETECT_FILE_TYPE"):
        src = f"def f():\n    return {name}\n" if name != "GET_HWID" else "x = GET_HWID()\n"
        found = collect_macros(src)
        assert name in found, name
    # Calls also detected.
    assert "CRASH" in collect_macros("CRASH()\n")
    assert "SELF_DELETE" in collect_macros("SELF_DELETE()\n")
    # Comparisons detected (Name nodes).
    assert "IS_OBFUSCATED" in collect_macros("if IS_OBFUSCATED == True:\n    pass\n")


def test_collect_no_macros_empty():
    assert collect_macros("x = 1\nprint(x)\n") == set()


def test_collect_does_not_execute():
    # Would raise / exit if executed; collect must be side-effect free.
    src = "CRASH()\nraise RuntimeError('boom')\nimport os; os._exit(99)\n"
    assert collect_macros(src) == {"CRASH"}


def test_apply_replaces_is_obfuscated():
    out = apply_macros("if IS_OBFUSCATED:\n    x = 1\n")
    assert "IS_OBFUSCATED" not in out
    assert "True" in out
    compile(out, "<t>", "exec")


def test_apply_replaces_get_hwid():
    out = apply_macros("h = GET_HWID()\n", hwid="ABC-123")
    assert "GET_HWID" not in out
    assert "ABC-123" in out
    ns = {}
    exec(compile(out, "<t>", "exec"), ns)
    assert ns["h"] == "ABC-123"


def test_apply_leaves_runtime_macros():
    src = "SELF_DELETE()\nSECURE_DELETE('f', passes=1)\nCRASH()\nDETECT_FILE_TYPE('x')\n"
    out = apply_macros(src)
    for name in ("SELF_DELETE", "SECURE_DELETE", "CRASH", "DETECT_FILE_TYPE"):
        assert name in out


def test_no_macro_source_same_ast():
    src = "def f(a):\n    b = a + 1\n    return b\n"
    out = apply_macros(src)
    assert ast.dump(ast.parse(out)) == ast.dump(ast.parse(src))


def test_trial_simple_units():
    assert parse_trial("1s") == 1
    assert parse_trial("90s") == 90
    assert parse_trial("1m") == 60
    assert parse_trial("1h") == 3600
    assert parse_trial("1d") == 86400
    assert parse_trial("1w") == 7 * 86400
    assert parse_trial("1mo") == 30 * 86400


def test_trial_combos():
    assert parse_trial("1w2d") == 7 * 86400 + 2 * 86400
    assert parse_trial("1mo1hr") == 30 * 86400 + 3600
    assert parse_trial("1h30m") == 5400
    assert parse_trial("2d12h") == 2 * 86400 + 12 * 3600


def test_trial_empty_none():
    assert parse_trial("") is None
    assert parse_trial(None) is None
    assert parse_trial("   ") is None


def test_trial_garbage_raises():
    for bad in ("garbage", "abc", "1x", "1", "--", "1.5h"):
        try:
            parse_trial(bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad!r}")


def test_helpers_compile_and_present():
    src = emit_runtime_helpers()
    compile(src, "<t>", "exec")
    for name in ("SELF_DELETE", "SECURE_DELETE", "CRASH", "DETECT_FILE_TYPE"):
        assert f"def {name}" in src


def test_detect_file_type_classifies(tmp_path):
    src = emit_runtime_helpers()
    ns = {}
    exec(compile(src, "<t>", "exec"), ns)
    det = ns["DETECT_FILE_TYPE"]
    pyf = tmp_path / "a.py"
    pyf.write_text("def f():\n    return 1\n")
    assert det(str(pyf)) == "python_script"
    elff = tmp_path / "a.bin"
    elff.write_bytes(b"\x7fELF" + b"\x00" * 100)
    assert det(str(elff)) == "binary_executable"
    txtf = tmp_path / "a.txt"
    txtf.write_text("hello world, just text\n")
    assert det(str(txtf)) == "text_file"
    assert det(str(tmp_path / "missing")) == "unknown"
