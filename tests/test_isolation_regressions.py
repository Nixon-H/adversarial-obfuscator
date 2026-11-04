"""Regressions found by isolating single flags (scripts/ci/isolate_flags.py).

Each of these was invisible in a bundled build and appeared only when one flag
was applied alone. They share a shape: a name or a scope created in one place
and used in another, with nothing forcing the two to agree.
"""
import ast
import contextlib
import io

import pytest

from obfuscator.core.sources import apply_ast_mutation
from obfuscator.core.transforms import stego_encode, _scope_safe_insert_index


def _run(code):
    buf = io.StringIO()
    ns = {"__name__": "__main__"}
    with contextlib.redirect_stdout(buf):
        exec(compile(code, "<t>", "exec"), ns)
    return buf.getvalue()


# --- steganography round-trips BYTES, then decodes UTF-8 -------------------
@pytest.mark.parametrize("src", [
    'print("ascii only")',
    '名前 = "日本語"\nprint(名前)',
])
def test_stego_round_trips_including_non_ascii(src):
    code = stego_encode(src)
    compile(code, "<stego>", "exec")
    assert _run(code) == _run(src)


def test_stego_bootstrap_decodes_utf8_not_latin1():
    # The old bootstrap built a str of code points 0..255, so any multi-byte
    # UTF-8 character became two Latin-1 characters and the decoded source was
    # invalid for an artefact full of Unicode identifiers.
    bootstrap = stego_encode('print("x")')
    assert ".decode(\"utf-8\")" in bootstrap or ".decode('utf-8')" in bootstrap


# --- the call-graph table must not be clobbered by a second instance -------
def test_each_call_graph_table_gets_its_own_name():
    from obfuscator.core.transforms import CallGraphObfuscator
    a = CallGraphObfuscator()
    b = CallGraphObfuscator()
    assert a.table_var != b.table_var, (
        "two instances emitting the same table name means the later assignment "
        "silently replaces the earlier one and call sites resolve to the wrong "
        "builtin (observed as 'can't concat int to bytes')")


# --- the JIT template must see module globals ------------------------------
def test_jit_wrapped_function_can_read_a_module_global():
    src = (
        "G = 7\n"
        "def use():\n"
        "    a = G + 1\n"
        "    b = a * 2\n"
        "    return b\n"
        "print('g:', use())\n"
    )
    # dynamic_code is probabilistic per function; retry until it fires.
    for _ in range(40):
        out, _o = apply_ast_mutation(src, {"opt_level": 5, "dynamic_code": True})
        if "_nx_tmpl_" in out:
            assert "dict(globals())" in out, (
                "the JIT namespace must include module globals, or any function "
                "referencing a global raises NameError inside the template")
            assert _run(out) == _run(src)
            return
    pytest.skip("the JIT transform never fired on this input")


# --- injected statements must not precede a scope declaration -------------
def test_insert_index_skips_scope_declarations():
    body = [
        ast.Expr(value=ast.Constant(value="docstring")),
        ast.Nonlocal(names=["count"]),
        ast.Global(names=["x"]),
        ast.Assign(targets=[ast.Name(id="count", ctx=ast.Store())],
                   value=ast.Constant(value=1)),
    ]
    idx = _scope_safe_insert_index(body)
    assert idx == 3, "a statement inserted before nonlocal/global is a SyntaxError"


def test_insert_index_keeps_docstring_first():
    body = [ast.Expr(value=ast.Constant(value="doc")), ast.Pass()]
    assert _scope_safe_insert_index(body) == 1


def test_attention_poison_keeps_closures_valid():
    src = (
        "def make():\n"
        "    count = 0\n"
        "    def bump():\n"
        "        nonlocal count\n"
        "        count += 1\n"
        "        return count\n"
        "    return bump\n"
        "print('c:', make()())\n"
    )
    out, _o = apply_ast_mutation(src, {"opt_level": 5, "attention_poison": True})
    compile(out, "<n>", "exec")
    assert _run(out) == _run(src)
