"""Regressions for the follow-up fixes to the 2026-11-24 audit.

Covers the small, sharp edges found after the main remediation: void IR calls,
LLVM value-name prefixes, deterministic replay-poison case values, secret ORAM
seeds, fail-loud config loading, and the unimplemented binary watermark path.
"""

import os
import re


def test_void_call_renders_without_result_assignment():
    from irgen.compile import IrInstruction, IrModule, IrFunction, IrBlock, IrType

    module = IrModule("voidcall")
    func = IrFunction("init", IrType.void())
    block = IrBlock("entry")
    func.blocks.append(block)
    block.instructions.append(IrInstruction(
        "call", result_type=IrType.void(), operands=[], func_name="register"))
    block.set_terminator("ret")
    module.functions.append(func)

    text = str(module)
    assert "call void @register()" in text
    assert "= call void" not in text


def test_fla_rename_does_not_corrupt_longer_numeric_names():
    """Renaming %17 must not turn %170 into %alloca_170."""
    from llvmgen.passes import apply_fla

    ir = (
        "define i32 @f() {\n"
        "entry:\n"
        "  %17 = alloca i32\n"
        "  %170 = alloca i32\n"
        "  store i32 1, ptr %17\n"
        "  store i32 2, ptr %170\n"
        "  br label %next\n"
        "next:\n"
        "  %x = load i32, ptr %17\n"
        "  %y = load i32, ptr %170\n"
        "  %z = add i32 %x, %y\n"
        "  ret i32 %z\n"
        "}\n"
    )
    out = apply_fla(ir)
    assert "%alloca_17" in out
    assert "%alloca_170" in out
    assert "%alloca_170 = add" not in out
    assert "load i32, ptr %alloca_170" in out


def test_replay_poison_case_values_are_stable():
    """The old salted hash() made these change between processes."""
    from llvmgen.passes import apply_replay_poison

    ir = (
        "define i32 @f(i32 %x) {\n"
        "entry:\n"
        "  switch i32 %x, label %default [i32 1, label %a]\n"
        "default:\n"
        "  ret i32 0\n"
        "a:\n"
        "  ret i32 1\n"
        "}\n"
    )
    out = apply_replay_poison(ir, 4)
    values = [int(v) for v in re.findall(r"i32 (\d+), label %rddead", out)]
    assert values == [85227, 85228, 85229, 85230]
    assert len(values) == len(set(values))


def test_corrupt_config_is_not_silently_loaded_as_empty(monkeypatch, tmp_path):
    from obfuscator.core.utils import ConfigManager

    path = tmp_path / "builder_config.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(ConfigManager, "CONFIG_FILE", str(path))
    try:
        ConfigManager()
    except SystemExit as exc:
        assert "cannot read config" in str(exc)
    else:
        raise AssertionError("corrupt config was silently replaced with {}")
    assert path.read_text(encoding="utf-8") == "{not json"


def test_oram_seed_is_configurable_not_committed(monkeypatch):
    from irgen.oram import generate_oram_config

    seed = bytes(range(32))
    monkeypatch.setenv("NIXON_ORAM_SEED", seed.hex())
    first = generate_oram_config(["a", "b", "c"], 256)
    second = generate_oram_config(["a", "b", "c"], 256)
    assert first == second
    monkeypatch.setenv("NIXON_ORAM_SEED", bytes(reversed(seed)).hex())
    assert generate_oram_config(["a", "b", "c"], 256) != first
    assert all(isinstance(v, int) for v in first["leaf_mapping"].values())


def test_binary_watermark_detection_fails_loudly():
    import pytest
    from irgen.watermark import detect_watermark_from_binary

    with pytest.raises(NotImplementedError, match="machine-code lifter"):
        detect_watermark_from_binary("/no/such/binary", b"seed")


def test_variant_pool_variants_preserve_semantics(monkeypatch):
    import ast

    import irgen.variant_pool as vp

    class _NormalizeNames(ast.NodeTransformer):
        """Erase renamed identifiers so structure can be compared."""

        def visit_Name(self, node):
            node.id = "V"
            return node

        def visit_arg(self, node):
            node.arg = "V"
            return node

        def visit_FunctionDef(self, node):
            self.generic_visit(node)
            node.name = "F"
            return node

    monkeypatch.setattr(vp, "_phase2_enabled", lambda: True)
    source = "def f(a, b):\n    x = a + b\n    return x * 2\n"
    expected = ast.dump(_NormalizeNames().visit(ast.parse(source)))
    variants = vp.generate_variants(source, "f", 4, b"seed")
    assert len(variants) == 4
    for variant in variants:
        assert ast.dump(_NormalizeNames().visit(ast.parse(variant))) == expected


def test_variant_renamer_keeps_calls_and_import_names(monkeypatch):
    import ast

    import irgen.variant_pool as vp

    monkeypatch.setattr(vp, "_phase2_enabled", lambda: True)
    source = (
        "import math\n"
        "def helper(x):\n    return x + 1\n"
        "def f(a):\n    return helper(a) + math.floor(2.5)\n"
    )
    renamed = vp._scramble_variable_names(source, b"seed")
    tree = ast.parse(renamed)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert {"helper", "f"} <= functions
    calls = {node.func.id for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert "helper" in calls
    assert any(isinstance(node, ast.Attribute)
               and isinstance(node.value, ast.Name) and node.value.id == "math"
               for node in ast.walk(tree))


def test_microjit_refuses_codecases_it_cannot_model():
    from irgen.microjit import MicroJITEngine, _instruction_length

    engine = MicroJITEngine(seed=1)
    # VEX.2 encoded vzeroupper followed by ret: the hand decoder cannot
    # determine the real instruction boundary.
    vex = bytes([0xC5, 0xF8, 0x77, 0xC3])
    assert _instruction_length(vex, 0) == 0
    assert engine.swap_registers(vex, {0: 1, 1: 0}) == vex
    assert engine.alter_stack_offsets(vex, 8) == vex

    # push rax; ret uses implicit stack registers.
    implicit = bytes([0x50, 0xC3])
    assert engine.swap_registers(implicit, {0: 1, 1: 0}) == implicit
    assert engine.alter_stack_offsets(implicit, 8) == implicit

    # A plain register-to-register mov is still rewritable.
    simple = bytes([0x48, 0x89, 0xC3])
    swapped = engine.swap_registers(simple, {0: 1, 1: 0})
    assert len(swapped) == len(simple) and swapped != simple


def test_port_entangle_patches_all_functions_with_correct_condition():
    from irgen.port_entangle import PortEntanglementPass

    ir = (
        "define i32 @a(i32 %x) {\nentry:\n  ret i32 %x\n}\n"
        "define i32 @b(i32 %x) {\nentry:\n  ret i32 %x\n}\n"
    )
    out = PortEntanglementPass().apply_to_ir(ir)
    assert out.count("@__rdtsc()") == 5  # one declaration + two reads per function
    assert out.count("declare i64 @__rdtsc()") == 1
    assert out.count("port_entangle_corrupt_") == 4  # branch + label per function
    assert "icmp uge" in out

    soft = PortEntanglementPass().embed_timing_check(
        ir, {"timing_threshold": 5000})
    assert "icmp ult" in soft
    assert "icmp ne" not in soft
    assert soft.count("pe_t0_") == 4  # definition + use in delta, per function


def test_native_lowering_matches_vm_python_semantics():
    """Native must floor ``//`` and ``%`` and shift arithmetically.

    The IR is compiled from Python, and the VM implements Python's floored
    division/remainder and arithmetic ``>>``.  LLVM's ``udiv``/``lshr`` are
    wrong for negative operands, and a bare ``sdiv``/``srem`` truncates
    instead of flooring.  This test pins the lowering to the VM semantics;
    tests/test_div_mod_semantics.py proves both by execution.
    """
    from llvmgen.lower import _emit_instruction

    instruction = {"type": "i32", "result": "%1", "operands": ["%2", "%3"]}
    shift = _emit_instruction(dict(instruction, opcode="shr"))
    assert "ashr" in shift
    assert "lshr" not in shift

    division = _emit_instruction(dict(instruction, opcode="div"))
    assert "sdiv" in division
    assert "srem" in division
    assert "select i1" in division
    assert "udiv" not in division

    remainder = _emit_instruction(dict(instruction, opcode="mod"))
    assert "srem" in remainder
    assert "add i32" in remainder
    assert "select i1" in remainder


def test_every_ci_action_is_sha_pinned():
    import re
    from pathlib import Path

    workflows = Path(__file__).resolve().parents[1] / ".github" / "workflows"
    floating = []
    for path in workflows.glob("*.yml"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or "uses:" not in line:
                continue
            ref = stripped.split("uses:", 1)[1].strip().split()[0]
            if ref.startswith("./"):
                continue
            _, _, pin = ref.partition("@")
            if not re.fullmatch(r"[0-9a-f]{40}", pin):
                floating.append(f"{path.name}: {ref}")
    assert not floating, "floating action refs: %r" % floating


def test_flag_matrix_matches_live_catalogue(capsys):
    import json
    import sys
    from pathlib import Path

    ci_dir = str(Path(__file__).resolve().parents[1] / "scripts" / "ci")
    if ci_dir not in sys.path:
        sys.path.insert(0, ci_dir)
    from flag_catalogue import catalogue
    from matrix_flags import WANTED, main

    entries = {entry["flag"]: entry for entry in catalogue()}
    assert WANTED, "the matrix must exercise at least one catalogue flag"
    for name in WANTED:
        assert name in entries, "%r is not in the live flag catalogue" % name
        assert entries[name]["kind"] != "excluded", "%r is excluded" % name

    assert main() == 0
    emitted = json.loads(capsys.readouterr().out)
    assert len(emitted) == len(WANTED)


def test_deep_matrix_uses_every_live_isolatable_flag(capsys):
    import json
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    ci_dir = str(root / "scripts" / "ci")
    if ci_dir not in sys.path:
        sys.path.insert(0, ci_dir)
    from flag_catalogue import catalogue, collect
    from matrix_flags import main

    live = collect()
    runnable = [entry for entry in catalogue() if entry["kind"] != "excluded"]
    old_argv = sys.argv
    try:
        sys.argv = ["matrix_flags.py", "--all"]
        assert main() == 0
    finally:
        sys.argv = old_argv
    emitted = json.loads(capsys.readouterr().out)
    assert len(emitted) == len(runnable) > 0
    for argv in emitted:
        for token in argv.split():
            if token.startswith("--"):
                assert token in live, "matrix emits unsupported flag %r" % token

    workflow = (root / ".github" / "workflows" / "portable-deep-matrix.yml").read_text()
    assert "matrix_flags.py --all" in workflow
    ladder = workflow.split("  ladder-flags:", 1)[1]
    assert "matrix.args" not in ladder


def test_vm_compile_rejects_lowered_ir_text_with_clear_message(tmp_path, capsys):
    from vm.__main__ import main

    ir_path = tmp_path / "input.ir"
    ir_path.write_text("module @m\n  func @main() {\n    ret void\n  }\n", encoding="utf-8")
    output = tmp_path / "out.json"

    try:
        main(["compile", str(ir_path), "-o", str(output),
              "--functions", "main", "--seed", "00" * 16])
    except SystemExit as exc:
        assert "expects Python source" in str(exc)
    else:
        raise AssertionError("lowered IR text was accepted as Python source")
    assert not output.exists()

    try:
        main(["compile", "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    assert "Python source" in capsys.readouterr().out


def test_encrypt_cli_reports_bad_keys_without_traceback(tmp_path):
    from encrypt import main

    source = tmp_path / "plain.txt"
    source.write_bytes(b"audit payload\n")
    container = tmp_path / "payload.nix"
    output = tmp_path / "roundtrip.txt"
    key = os.urandom(32)

    assert main(["pack", str(source), "-o", str(container),
                 "--key", key.hex()]) in (None, 0)
    try:
        main(["unpack", str(container), "-o", str(output),
              "--key", os.urandom(32).hex()])
    except SystemExit as exc:
        assert "unpack failed" in str(exc)
    else:
        raise AssertionError("wrong key was not rejected")
    assert not output.exists()

    try:
        main(["unpack", str(container), "-o", str(output), "--key", "00"])
    except SystemExit as exc:
        assert "32 bytes" in str(exc)
    else:
        raise AssertionError("short key was not rejected")
