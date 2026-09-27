"""Tests for speculation/attention/nyser/timing/intent fixes (items 9-14)."""
import ast
import types

import pytest

from obfuscator import nyser
from obfuscator.attention_poison import AttentionPoisonInjector
from obfuscator.function_intent import FunctionIntentObfuscator
from obfuscator.timing_traps import generate_rdtsc_ir_pattern, inject_timing_checks


def _exec(tree):
    ns = {}
    exec(compile(tree, "<test>", "exec"), ns)
    return ns


def test_speculation_gadget_runs():
    from obfuscator.speculation_obfuscation import SpeculationObfuscator
    for seed in (1234, 7, 99, 2024, 555):
        obf = SpeculationObfuscator(seed=seed)
        tree = ast.parse("def f(x):\n    y = x + 1\n    return y\n", feature_version=(3, 10))
        out = obf.visit(tree)
        out = ast.fix_missing_locations(out)
        ns = _exec(out)
        assert ns["f"](41) == 42, seed


def test_speculation_all_gadget_types_exec():
    # Force each gadget maker directly (choice is random otherwise).
    from obfuscator.speculation_obfuscation import SpeculationObfuscator
    import random as _r
    for maker in ("_make_spectre_training", "_make_speculation_gadget",
                  "_make_misprediction_training", "_make_array_bounds_gadget"):
        obf = SpeculationObfuscator(seed=1)
        # Drive rng state variety; maker must still emit runnable code.
        obf.rng = _r.Random(hash(maker) & 0xFFFFFFFF)
        tree = ast.parse("def f(x):\n    y = x * 2\n    return y\n",
                         feature_version=(3, 10))
        fn = tree.body[0]
        guard = "_spec_guard_f"
        fn.body.insert(0, ast.Assign(targets=[ast.Name(id=guard, ctx=ast.Store())],
                                    value=ast.Constant(value=5000)))
        gadget = getattr(obf, maker)(guard)
        fn.body.insert(1, gadget)
        ns = _exec(ast.fix_missing_locations(tree))
        assert ns["f"](21) == 42, maker


def test_attention_poison_skips_multi_return():
    inj = AttentionPoisonInjector(fan_out=2)
    src = "def f(c):\n    x = 1\n    return x\n    y = 2\n    return y\n"
    tree = ast.parse(src, feature_version=(3, 10))
    before = ast.dump(tree)
    out = inj.visit(tree)
    # Non-tail Return present -> body must be left structurally unchanged.
    rets = [n for n in out.body[0].body if isinstance(n, ast.Return)]
    assert len(rets) == 2
    assert ast.dump(out) == before or len(out.body[0].body) == 4


def test_attention_poison_single_tail_return_ok():
    inj = AttentionPoisonInjector(fan_out=1)
    tree = ast.parse("def f():\n    x = 1\n    return x\n", feature_version=(3, 10))
    out = inj.visit(tree)
    ns = _exec(ast.fix_missing_locations(out))
    assert ns["f"]() == 1


def test_nyser_bigint_zigzag_roundtrip():
    for v in (2**63 - 1, 2**63, 2**63 + 1, 2**64, 2**100, -(2**63), -(2**100)):
        enc = nyser._encode_zigzag(v)
        r = nyser._Reader(enc)
        assert r.zigzag() == v, v


def test_nyser_code_roundtrip_with_big_const():
    if not nyser.roundtrip_supported():
        pytest.skip("version gated")
    src = f"def f():\n    return {2**63 + 12345}\n"
    co = compile(src, "<t>", "exec")
    blob = nyser.dumps(co)
    back = nyser.loads(blob)
    ns1, ns2 = {}, {}
    exec(co, ns1)
    exec(back, ns2)
    assert ns1["f"]() == ns2["f"]() == 2**63 + 12345


def test_nyser_tamper_rejected_before_parse():
    if not nyser.roundtrip_supported():
        pytest.skip("version gated")
    co = compile("def f():\n    return 1\n", "<t>", "exec")
    blob = bytearray(nyser.dumps(co))
    blob[-1] ^= 0xFF
    with pytest.raises(ValueError):
        nyser.loads(bytes(blob))


def test_timing_hard_exit_imports_sys():
    out = inject_timing_checks("def f():\n    return 1\n", {"timing_hard_exit": True})
    assert "import sys" in out
    tree = ast.parse(out, feature_version=(3, 10))
    assert any(
        isinstance(n, ast.Import) and any(a.name == "sys" for a in n.names)
        for n in tree.body
    )


def test_rdtsc_single_terminator():
    for hard in (True, False):
        ir = generate_rdtsc_ir_pattern({"timing_hard_exit": hard})
        label = "degradation_exit:" if hard else "degradation_silent:"
        block = ir.split(label)[-1]
        terms = block.count("ret void") + block.count("unreachable")
        assert terms == 1, block
        if hard:
            assert "call void @exit(i32 1)" in block


def test_function_intent_public_multi_caller_untouched():
    obf = FunctionIntentObfuscator(seed=1)
    src = "def add(a, b):\n    return a + b\nx = add(1, 2)\ny = add(3, 4)\n"
    tree = ast.parse(src, feature_version=(3, 10))
    out = obf.obfuscate_intent(tree)
    fdef = next(n for n in out.body if isinstance(n, ast.FunctionDef))
    params = [a.arg for a in fdef.args.args]
    assert params == ["a", "b"], params  # swap pass dropped


def test_function_intent_single_caller_private_swap_safe():
    obf = FunctionIntentObfuscator(seed=1)
    src = "def _nx_add(a, b):\n    return a - b\nx = _nx_add(10, 3)\n"
    tree = ast.parse(src, feature_version=(3, 10))
    out = obf.obfuscate_intent(tree)
    ns = _exec(ast.fix_missing_locations(out))
    assert ns["x"] == 7  # order preserved via call-site rewrite


def test_trial_bind_rejects_bad_func_name():
    from obfuscator.trial_bind import emit_trial_snippet
    with pytest.raises(ValueError):
        emit_trial_snippet(999, "ab" * 32, "cd" * 32, func_name="not a name!")
