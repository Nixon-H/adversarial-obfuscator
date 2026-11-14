"""Regression tests for module-prologue insertion and adaptive renaming.

The transforms that prepend helpers/imports used ``tree.body.insert(0, ...)``.
That put a definition before ``from __future__ import ...`` (SyntaxError) and
before the module docstring (lost ``__doc__``).  The adaptive renamer also
renamed external attributes/keywords that merely shared a local name.
"""
import ast
import types


def _exec(tree_or_src):
    if isinstance(tree_or_src, str):
        tree = ast.parse(tree_or_src)
    else:
        tree = tree_or_src
    code = ast.unparse(ast.fix_missing_locations(tree))
    ns = {}
    exec(compile(code, "<test>", "exec"), ns)
    return ns, code


def _profile(*actions):
    return types.SimpleNamespace(recommended_actions=list(actions),
                                 to_dict=lambda: {})


FUTURE_SRC = (
    '"""module doc"""\n'
    'from __future__ import annotations\n'
    '\n'
    'def f():\n'
    '    return "hello world"\n'
)


def test_module_prologue_index_skips_docstring_and_future():
    from obfuscator.core.ast_prologue import module_prologue_index
    tree = ast.parse(FUTURE_SRC)
    assert module_prologue_index(tree) == 2


def test_adaptive_string_encoding_survives_future_import():
    from obfuscator.adaptive_rewriter import AdaptiveRewriter
    out = AdaptiveRewriter().rewrite(_profile("add_string_encoding"), FUTURE_SRC)
    ns, _ = _exec(out)
    assert ns["__doc__"] == "module doc"
    assert ns["f"]() == "hello world"


def test_adaptive_misleading_imports_survive_future_import():
    from obfuscator.adaptive_rewriter import AdaptiveRewriter
    out = AdaptiveRewriter().rewrite(_profile("add_misleading_imports"),
                                     FUTURE_SRC)
    ns, _ = _exec(out)
    assert ns["__doc__"] == "module doc"


def test_provenance_survives_future_import():
    from obfuscator.provenance import encode_sensitive_strings
    tree = encode_sensitive_strings(ast.parse(FUTURE_SRC), b"seed")
    ns, _ = _exec(tree)
    assert ns["__doc__"] == "module doc"


def test_dataflow_survives_future_import():
    from obfuscator.dataflow import encode_variables_affine
    src = ('"""module doc"""\nfrom __future__ import annotations\n\n'
           'x = 5\nresult = x * 2 + 1\n')
    out = encode_variables_affine(ast.parse(src), ["x"], b"seed")
    ns, _ = _exec(out)
    assert ns["__doc__"] == "module doc"
    assert ns["result"] == 11


def test_replay_poison_survives_future_import():
    from obfuscator.replay_poison import inject_entropy_branches
    out = inject_entropy_branches(FUTURE_SRC, {"enabled": True})
    ns, _ = _exec(out)
    assert ns["__doc__"] == "module doc"
    assert ns["f"]() == "hello world"


def test_timing_traps_survive_future_import():
    from obfuscator.timing_traps import inject_timing_checks
    out = inject_timing_checks(FUTURE_SRC, {})
    ns, _ = _exec(out)
    assert ns["__doc__"] == "module doc"


def test_llm_fingerprint_survives_future_import():
    from obfuscator.llm_fingerprint import LLMFingerprinter
    out = LLMFingerprinter().embed_fingerprint(ast.parse(FUTURE_SRC), "gpt")
    ns, _ = _exec(out)
    assert ns["__doc__"] == "module doc"


def test_adaptive_does_not_encode_match_pattern_literals():
    from obfuscator.adaptive_rewriter import AdaptiveRewriter
    src = ('def f(x):\n'
           '    match x:\n'
           '        case "hello world":\n'
           '            return 1\n'
           '        case _:\n'
           '            return 0\n')
    out = AdaptiveRewriter().rewrite(_profile("add_string_encoding"), src)
    ns, _ = _exec(out)
    assert ns["f"]("hello world") == 1
    assert ns["f"]("other") == 0


def test_adaptive_leaves_external_keyword_arguments_alone():
    from obfuscator.adaptive_rewriter import AdaptiveRewriter
    src = ('import json\n\n'
           'def f(default):\n'
           '    return json.dumps({"x": object()}, default=default)\n')
    out = AdaptiveRewriter().rewrite(_profile("strengthen_symbol_renaming"),
                                     src)
    ns, _ = _exec(out)
    assert ns["f"](lambda o: 2) == '{"x": 2}'


def test_adaptive_leaves_external_attributes_alone():
    from obfuscator.adaptive_rewriter import AdaptiveRewriter
    src = ('import types\n\n'
           'def f(data):\n'
           '    o = types.SimpleNamespace(data=1)\n'
           '    return o.data + data\n')
    out = AdaptiveRewriter().rewrite(_profile("strengthen_symbol_renaming"),
                                     src)
    ns, _ = _exec(out)
    assert ns["f"](2) == 3


def test_adaptive_renames_local_keywords_and_methods_consistently():
    from obfuscator.adaptive_rewriter import AdaptiveRewriter
    src = ('def api(data=0):\n'
           '    return data\n\n'
           'def caller(data):\n'
           '    return api(data=data)\n\n'
           'class Box:\n'
           '    def data(self):\n'
           '        return 7\n'
           '    def run(self):\n'
           '        return self.data()\n\n'
           'RESULT = caller(5)\n'
           'BOX_RESULT = Box().run()\n')
    out = AdaptiveRewriter().rewrite(_profile("strengthen_symbol_renaming"),
                                     src)
    ns, _ = _exec(out)
    assert ns["RESULT"] == 5
    assert ns["BOX_RESULT"] == 7
