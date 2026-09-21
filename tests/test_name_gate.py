"""Tests for obfuscator/name_gate.py — runtime API name gate."""
import ast

from obfuscator.name_gate import (
    PRIVILEGED,
    build_mapping,
    emit_gate_snippet,
    rewrite_calls,
)


def test_mapping_deterministic_and_distinct():
    m1 = build_mapping(b"seed")
    m2 = build_mapping(b"seed")
    assert m1 == m2
    assert len(set(m1.values())) == len(m1)
    assert all(v.startswith("_nxg_") and len(v) == 5 + 12 for v in m1.values())
    assert build_mapping(b"other") != m1


def test_snippet_compiles():
    snippet = emit_gate_snippet(build_mapping(b"seed"))
    compile(snippet, "<gate>", "exec")
    assert "_nx_get" in snippet and "_NXG_MAP" in snippet


def test_rewrite_converts_privileged_call():
    mapping = build_mapping(b"seed")
    out = rewrite_calls("import marshal\nx = marshal.loads(data)\n", mapping)
    assert "marshal.loads" not in out
    assert "_nx_get(" in out
    compile(out, "<rw>", "exec")


def test_non_privileged_calls_untouched():
    src = "def f(a, b):\n    return a + b\n\ny = f(1, 2)\n"
    out = rewrite_calls(src, build_mapping(b"seed"))
    assert "_nx_get" not in out
    assert ast.dump(ast.parse(src)) == ast.dump(ast.parse(out))


def test_no_privileged_name_at_call_sites():
    mapping = build_mapping(b"seed")
    src = "import marshal, os\nx = marshal.loads(d)\nos.system('x')\n"
    out = rewrite_calls(src, mapping)
    tree = ast.parse(out)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            assert not (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in ("loads", "system")
            ), "privileged dotted call survived at a call site"


def test_end_to_end_exec():
    mapping = build_mapping(b"seed")
    snippet = emit_gate_snippet(mapping)
    src = rewrite_calls("import marshal\nblob_out = marshal.dumps((1, 2))\n", mapping)
    ns: dict = {}
    exec(compile(snippet, "<gate>", "exec"), ns)
    exec(compile(src, "<rw>", "exec"), ns)
    import marshal as _m
    assert ns["blob_out"] == _m.dumps((1, 2))


def test_builtin_bare_names_rewritten():
    mapping = build_mapping(b"seed")
    out = rewrite_calls("x = eval('1+1')\n", mapping)
    assert "_nx_get(" in out
