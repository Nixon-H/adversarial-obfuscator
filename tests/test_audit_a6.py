"""Regression tests for the audit-a6 shard fixes."""
import ast
import os

import pytest


def _exec_tree(tree):
    ns = {}
    exec(compile(tree, "<audit-a6>", "exec"), ns)
    return ns


# ── provenance.py ────────────────────────────────────────────────────────

def test_algorithmic_constants_reconstruct_original_values():
    from obfuscator.provenance import obfuscate_algorithmic_constants

    for value in (0x6A09E667, 0x9E3779B97F4A7C15):
        tree = ast.parse(f"x = {value}\nresult = x\n")
        out = obfuscate_algorithmic_constants(tree)
        ns = _exec_tree(ast.fix_missing_locations(out))
        assert ns["result"] == value


def test_sensitive_string_encoder_preserves_long_strings_exactly():
    from obfuscator.provenance import encode_sensitive_strings

    text = "Content-Type: application/json; " + ("x" * 250) + " base64"
    tree = ast.parse("S = " + repr(text) + "\nresult = S\n")
    out = encode_sensitive_strings(tree, b"seed")
    ns = _exec_tree(ast.fix_missing_locations(out))
    assert ns["result"] == text


def test_sensitive_string_encoder_leaves_fstring_parts_well_formed():
    from obfuscator.provenance import encode_sensitive_strings

    tree = ast.parse(
        'def f(x):\n    return f"Content-Type: application/json {x}"\nresult = f(7)\n'
    )
    out = encode_sensitive_strings(tree, b"seed")
    # The transform previously put a Name directly inside JoinedStr; compile()
    # accepted the malformed shape but ast.unparse() (the pipeline output path)
    # raised ValueError. It must remain a valid f-string and evaluate exactly.
    source = ast.unparse(ast.fix_missing_locations(out))
    ns = {}
    exec(source, ns)
    assert ns["result"] == "Content-Type: application/json 7"


def test_library_wrappers_do_not_precede_docstring_or_future_import():
    from obfuscator.provenance import wrap_library_calls

    src = (
        '"""doc"""\nfrom __future__ import annotations\n'
        "def chacha20_poly1305_encrypt(x):\n    return x\n"
        "result = chacha20_poly1305_encrypt(41) + 1\n"
    )
    out = wrap_library_calls(ast.parse(src), {"enc": "chacha20_poly1305_encrypt"})
    ns = _exec_tree(ast.fix_missing_locations(out))
    assert ns["result"] == 42


def test_error_code_map_write_failure_is_not_silent(tmp_path):
    from obfuscator.provenance import replace_error_messages

    tree = ast.parse('raise ValueError("Invalid input")')
    with pytest.raises(IsADirectoryError):
        replace_error_messages(tree, codes_path=str(tmp_path))


# ── adversarial.py ───────────────────────────────────────────────────────

def test_adversarial_module_dead_code_respects_docstring_and_future_import():
    from obfuscator.adversarial import inject_adversarial_code

    src = '"""doc"""\nfrom __future__ import annotations\ndef f():\n    return 1\n'
    out = inject_adversarial_code(
        src, {"seed": 1, "level": 2, "prompt_injection": False})
    compile(out, "<adv>", "exec")


def test_prompt_injection_does_not_mutate_executable_strings():
    from obfuscator.adversarial import inject_adversarial_code

    src = "result = 'this operational string is long enough'\n"
    out = inject_adversarial_code(
        src, {"seed": 7, "level": 5, "prompt_injection": True})
    ns = {}
    exec(compile(out, "<adv>", "exec"), ns)
    assert ns["result"] == "this operational string is long enough"
    assert "SYSTEM:" in out or "Ignore all previous instructions" in out


# ── dataflow.py ──────────────────────────────────────────────────────────

def test_split_value_evaluates_rhs_exactly_once():
    from obfuscator.dataflow import split_value

    src = (
        "calls = 0\n"
        "def f():\n    global calls\n    calls += 1\n    return 42\n"
        "x = f()\nresult = x + calls\n"
    )
    out = split_value(ast.parse(src), "x", 2, b"seed")
    ns = _exec_tree(ast.fix_missing_locations(out))
    assert ns["calls"] == 1
    assert ns["result"] == 43


def test_split_value_self_reassignment_uses_previous_parts():
    from obfuscator.dataflow import split_value

    out = split_value(ast.parse("x = 5\nx = x + 1\nresult = x\n"), "x", 2, b"seed")
    ns = _exec_tree(ast.fix_missing_locations(out))
    assert ns["result"] == 6


@pytest.mark.parametrize(
    "src",
    [
        "x = y = 5\nresult = x + y\n",
        "x: int = 5\nresult = x\n",
    ],
)
def test_affine_unsupported_binding_forms_stay_plaintext_and_run(src):
    from obfuscator.dataflow import encode_variables_affine

    out = encode_variables_affine(ast.parse(src), ["x"], b"seed")
    ns = _exec_tree(ast.fix_missing_locations(out))
    expected = 10 if "x + y" in src else 5
    assert ns["result"] == expected


@pytest.mark.parametrize("value", [-1, 1 << 64])
def test_affine_out_of_range_values_fail_loudly(value):
    from obfuscator.dataflow import encode_variables_affine

    out = encode_variables_affine(ast.parse(f"x = {value}\nresult = x\n"), ["x"], b"seed")
    with pytest.raises(ValueError, match="unsigned 64-bit"):
        _exec_tree(ast.fix_missing_locations(out))


@pytest.mark.parametrize("value", [-1, 1 << 64])
def test_split_out_of_range_values_fail_loudly(value):
    from obfuscator.dataflow import split_value

    out = split_value(ast.parse(f"x = {value}\nresult = x\n"), "x", 2, b"seed")
    with pytest.raises(ValueError, match="unsigned 64-bit"):
        _exec_tree(ast.fix_missing_locations(out))


def test_mba_pipeline_is_deterministic_for_one_seed():
    from obfuscator.dataflow import obfuscate_dataflow

    cfg = {"sensitive_vars": ["key"], "encode_method": "mba", "seed": b"same"}
    outputs = [
        ast.unparse(obfuscate_dataflow(ast.parse("key = 41\n"), dict(cfg)))
        for _ in range(3)
    ]
    assert len(set(outputs)) == 1
    ns = {}
    exec(outputs[0], ns)
    assert ns["key"] == 41


# ── internal_rename.py ───────────────────────────────────────────────────

def test_internal_proof_blocks_duck_typed_receiver_inside_class():
    from obfuscator.internal_rename import find_internal_methods

    src = (
        "class Other:\n    def helper(self):\n        return 1\n"
        "class Worker:\n    def helper(self):\n        return 2\n"
        "    def run(self, obj):\n        return obj.helper()\n"
    )
    assert ("Worker", "helper") not in find_internal_methods(ast.parse(src))


def test_internal_proof_blocks_vars_string_lookup():
    from obfuscator.internal_rename import find_internal_methods

    src = (
        "class Worker:\n    def helper(self):\n        return 2\n"
        "    def run(self):\n        return vars(Worker)['helper'](self)\n"
    )
    assert ("Worker", "helper") not in find_internal_methods(ast.parse(src))


# ── nyser.py ─────────────────────────────────────────────────────────────

def test_nyser_roundtrips_lone_surrogate_string_constant():
    from obfuscator.nyser import dumps, loads, roundtrip_supported

    if not roundtrip_supported():
        pytest.skip("NYSER1 unsupported on this Python")
    co = compile("x = '\\ud800'\n", "<surrogate-test>", "exec")
    rt = loads(dumps(co))
    assert rt.co_consts == co.co_consts


# ── vm_score.py ──────────────────────────────────────────────────────────

def test_vm_verdict_nonfinite_values_do_not_fail_open():
    from obfuscator.vm_score import emit_loader_snippet, verdict

    assert verdict(100.0, float("nan")) == "VM"  # impossible threshold defaults
    assert verdict(float("nan"), 50.0) == "VM"
    assert verdict(100.0, float("inf")) == "VM"  # finite fallback is 50
    with pytest.raises(ValueError, match="finite"):
        emit_loader_snippet(float("nan"))


# ── licensing.py ─────────────────────────────────────────────────────────

def test_save_token_handles_short_os_writes(monkeypatch, tmp_path):
    from obfuscator.licensing import save_token

    real_write = os.write

    def short_write(fd, data):
        # POSIX permits a short write. Write at most three bytes per call.
        return real_write(fd, bytes(data[:3]))

    monkeypatch.setattr(os, "write", short_write)
    target = tmp_path / "licence.token"
    token = "x" * 100
    assert save_token(token, str(target)) == str(target)
    assert target.read_text(encoding="utf-8") == token + "\n"


# ── chacha20.py positive control (RFC 8439; unchanged correct behavior) ──

def test_chacha20_rfc8439_block_vector_positive_control():
    from obfuscator.chacha20 import chacha20_block

    key = bytes(range(32))
    nonce = bytes.fromhex("000000090000004a00000000")
    expected = (
        "10f1e7e4d13b5915500fdd1fa32071c4"
        "c7d1f4c733c068030422aa9ac3d46c4e"
        "d2826446079faa0914c2d705d98b02a2"
        "b5129cd1de164eb9cbd083e8a2503c4e"
    )
    assert chacha20_block(key, 1, nonce).hex() == expected
