"""Roundtrip tests for dataflow split_value / affine fixes (audit items 1-3)."""
import ast

from obfuscator.dataflow import (
    encode_variables_affine,
    obfuscate_dataflow,
    split_value,
)


def _exec(tree):
    ns = {}
    exec(compile(tree, "<test>", "exec"), ns)
    return ns


def test_split_roundtrip_n2_low_bits():
    # Low half must survive (regression: both parts extracted rhs>>32).
    for val in (0, 1, 42, 0xFFFFFFFF, 0x123456789ABCDEF0, 0xFFFFFFFFFFFFFFFF):
        tree = ast.parse(f"x = {val}\nresult = x\n", feature_version=(3, 10))
        out = split_value(tree, "x", 2, b"seed")
        ns = _exec(ast.fix_missing_locations(out))
        assert ns["result"] == val, (val, ns["result"])


def test_split_roundtrip_n3_n4():
    for n in (3, 4):
        for val in (0, 1, 7, 0xFFFFFFFF, 0xABCDEF0123456789, 0xFFFFFFFFFFFFFFFF):
            tree = ast.parse(f"x = {val}\nresult = x + 0\n", feature_version=(3, 10))
            out = split_value(tree, "x", n, b"seed")
            ns = _exec(ast.fix_missing_locations(out))
            assert ns["result"] == val, (n, val, ns["result"])


def test_affine_exec_roundtrip():
    tree = ast.parse("x = 5\nresult = x * 2 + 1\n", feature_version=(3, 10))
    out = encode_variables_affine(tree, ["x"], b"seed")
    ns = _exec(ast.fix_missing_locations(out))
    assert ns["result"] == 11


def test_affine_helper_emitted_once():
    tree = ast.parse("x = 1\n", feature_version=(3, 10))
    out = encode_variables_affine(tree, ["x"], b"seed")
    helpers = [
        n for n in out.body
        if isinstance(n, ast.ClassDef) and n.name == "_affine_enc"
    ]
    assert len(helpers) == 1
    # Idempotent: second pass must not duplicate the helper.
    out2 = encode_variables_affine(out, ["x"], b"seed")
    helpers2 = [
        n for n in out2.body
        if isinstance(n, ast.ClassDef) and n.name == "_affine_enc"
    ]
    assert len(helpers2) == 1


def test_mba_pipeline_preserves_semantics():
    tree = ast.parse(
        "key = 41\ny = key + 1\nz = y * 2\n", feature_version=(3, 10)
    )
    out = obfuscate_dataflow(tree, {"sensitive_vars": ["key", "z"], "encode_method": "mba", "seed": b"s"})
    ns = _exec(ast.fix_missing_locations(out))
    assert ns["key"] == 41
    assert ns["y"] == 42
    assert ns["z"] == 84
