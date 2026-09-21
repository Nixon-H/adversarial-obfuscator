"""Tests for semantic lowering registry + AST pass + shim (V10 headline)."""
import pytest

from obfuscator import lowering, lowering_shim


def test_registry_shape():
    assert len(lowering.FAMILIES) == 14
    on = {n for n, f in lowering.FAMILIES.items() if f["default_on"]}
    assert on == {"io", "scalar", "string", "container", "service",
                  "protocol", "function", "import", "fusion"}
    assert set(lowering.FAMILIES) - on == {"arithmetic", "truth", "slice",
                                           "format", "augassign"}


def test_resolve_families():
    assert lowering.resolve_families("") == frozenset()
    assert lowering.resolve_families("all") == frozenset(lowering.FAMILIES)
    assert lowering.resolve_families("none") == frozenset()
    assert "io" in lowering.resolve_families("io")
    assert "arithmetic" in lowering.resolve_families("+arithmetic")
    assert "io" not in lowering.resolve_families("-io")
    with pytest.raises(ValueError):
        lowering.resolve_families("nope")


def test_lower_calls_semantics_preserved():
    src = "x = len([1, 2, 3])\ny = sorted([3, 1])\n"
    out, n = lowering.lower_source(src, "container")
    assert n >= 2 and "_nxk_len" in out and "_nxk_sorted" in out
    ns: dict = {}
    for name in ("_nxk_len", "_nxk_sorted"):
        ns[name] = getattr(lowering_shim, name)
    exec(compile(out, "<t>", "exec"), ns)
    assert ns["x"] == 3 and ns["y"] == [1, 3]


def test_empty_spec_no_rewrite():
    src = "print('hi')\n"
    out, n = lowering.lower_source(src, "")
    assert n == 0 and out.strip() == src.strip()


def test_shim_covers_registry():
    import ast as _ast
    missing = []
    for fam, info in lowering.FAMILIES.items():
        for op in info["ops"]:
            if "." in op or op in ("BinOp", "Compare", "BoolOp", "Not",
                                   "Subscript", "JoinedStr", "FormattedValue",
                                   "AugAssign"):
                continue
            token = "_nxk_" + op
            if not hasattr(lowering_shim, token):
                missing.append((fam, op))
    assert not missing, missing


def test_fusion_shim():
    calls = []
    out = lowering_shim._nxk_fuse(lambda: calls.append(1),
                                  lambda: calls.append(2))
    assert calls == [1, 2] and out is None
