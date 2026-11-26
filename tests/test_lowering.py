"""Tests for semantic lowering registry + AST pass + shim (V10 headline)."""
import pytest

from obfuscator import lowering, lowering_shim


def test_registry_shape():
    assert len(lowering.FAMILIES) == 20
    on = {n for n, f in lowering.FAMILIES.items() if f["default_on"]}
    assert on == {"io", "scalar", "string", "container", "service",
                  "protocol", "function", "import", "fusion",
                  "list", "dict", "set", "tuple", "bytes", "range"}
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


def test_lower_source_self_contained_executes_without_module_import():
    """Pipeline artifacts do not ship a top-level lowering_shim module."""
    from obfuscator.lowering import lower_source_self_contained
    src = "xs = [1, 2, 3]\nout = len(xs)\nprint(out)\n"
    lowered, n = lower_source_self_contained(src, "container")
    assert n >= 1
    assert "from lowering_shim import" not in lowered
    assert "def _nxk_len" in lowered
    ns = {"__name__": "__main__"}
    exec(compile(lowered, "<lowered-self-contained>", "exec"), ns)


def test_apply_ast_mutation_wires_lowering_into_real_build_path():
    """Regression: --lowering must not be a parsed-but-inert pipeline flag."""
    from obfuscator.core.sources import apply_ast_mutation
    src = "xs = [1, 2, 3]\nout = len(xs)\n"
    out, _meta = apply_ast_mutation(src, {"lowering": "container", "opt_level": 0}, strict=True)
    assert "_nxk_len" in out
    assert "lowering_shim" not in out
    ns = {"__name__": "__main__"}
    exec(compile(out, "<mutated-lowering>", "exec"), ns)
    assert ns["out"] == 3


def test_native_build_option_subset_forwards_lowering():
    """Static wiring regression for the exact native-only defect found in audit.

    build_local_cython receives a deliberately small native AST option subset;
    omitting lowering there makes the flag active only in the Python fallback
    and completely absent in native-only artifacts.
    """
    from pathlib import Path
    text = Path("obfuscator/core/pipeline.py").read_text(encoding="utf-8")
    native_start = text.index("_native_ast_opts = {")
    native_end = text.index("if _native_ast_opts.get('vm_dispatch')", native_start)
    native_block = text[native_start:native_end]
    assert "'lowering': str(getattr(args, 'lowering', '') or '')," in native_block
