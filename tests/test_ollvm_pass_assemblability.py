"""Every OLLVM pass must emit IR that LLVM can actually assemble.

Three passes (``replay``, ``crypto_cfg``, ``speculative``) used to prepend a
``declare`` above the module preamble, which LLVM rejects with "expected
top-level entity".  ``replay`` additionally emitted both a ``declare`` and an
``internal`` ``define`` of ``@__rdrand_stub``, which LLVM rejects as an
invalid redefinition.  Nothing caught either defect because the build only
ever ran ``bcf``/``fla``/``sub``.

These tests pin the whole vocabulary, not just the passes the build uses
today, so a pass cannot silently rot back into unassemblable output.
"""
import json
import os
import shutil
import subprocess

import pytest

from llvmgen import passes as P
from llvmgen.lower import lower_ir_to_llvm

IR = """module @nixon_module
  func @add(%a: i32, %b: i32) -> i32 {
    entry:
      %0 = alloca i32
      store i32 %a, ptr %0
      %2 = alloca i32
      store i32 %b, ptr %2
      %4 = load i32, ptr %0
      %5 = load i32, ptr %2
      %6 = add i32 %4, %5
      ret i32 %6
  }
  func @pick(%x: i32) -> i32 {
    entry:
      %0 = alloca i32
      store i32 %x, ptr %0
      %2 = load i32, ptr %0
      %3 = icmp eq i32 %2, 0
      br i1 %3, label %a, label %b
    a:
      ret i32 10
    b:
      ret i32 20
  }
"""

# Every spelling apply_all() understands, mapped to the pass it dispatches to.
PASS_VOCABULARY = [
    "bcf", "bogus", "fla", "flatten", "sub", "substitute",
    "replay", "replay_poison", "transient",
    "crypto_cfg", "crypto_checkpoint", "speculative", "spec_traps",
]

PREAMBLE_PREFIXES = ("; ModuleID", "source_filename", "target datalayout", "target triple")


@pytest.fixture(scope="module")
def lowered():
    return lower_ir_to_llvm(IR, module_name="nixon_module")


def _assemble(ir_text, tmp_path, name):
    path = tmp_path / f"{name}.ll"
    path.write_text(ir_text)
    return subprocess.run(
        ["llc", "-filetype=obj", "-o", os.devnull, str(path)],
        capture_output=True, text=True,
    )


def test_insert_header_decls_keeps_preamble_first():
    module = (
        "; ModuleID = 'm'\n"
        'target triple = "x86_64-pc-linux-gnu"\n'
        'target datalayout = "e-m:e"\n'
        "define i32 @f() {\nentry:\n  ret i32 1\n}\n"
    )
    out = P._insert_header_decls(module, "declare i64 @helper()")
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert lines[0].startswith("; ModuleID")
    assert lines[1].startswith("target triple")
    assert lines[2].startswith("target datalayout")
    assert lines[3] == "declare i64 @helper()"
    assert out.index("declare i64 @helper()") < out.index("define i32 @f()")


def test_insert_header_decls_is_a_noop_for_empty_decls():
    module = 'target triple = "x86_64-pc-linux-gnu"\ndefine i32 @f() {\nentry:\n  ret i32 1\n}\n'
    assert P._insert_header_decls(module, "") == module
    assert P._insert_header_decls(module, "\n\n") == module


@pytest.mark.parametrize("pass_name", PASS_VOCABULARY)
def test_pass_keeps_the_module_preamble_first(pass_name, lowered):
    out = P.apply_all(lowered, [pass_name])
    first = next(ln for ln in out.splitlines() if ln.strip())
    assert first.startswith(PREAMBLE_PREFIXES), (
        f"{pass_name} put {first!r} above the module preamble"
    )


@pytest.mark.skipif(shutil.which("llc") is None, reason="llc not installed")
@pytest.mark.parametrize("pass_name", PASS_VOCABULARY)
def test_every_pass_assembles(pass_name, lowered, tmp_path):
    out = P.apply_all(lowered, [pass_name])
    result = _assemble(out, tmp_path, pass_name)
    assert result.returncode == 0, f"{pass_name} emitted invalid IR:\n{result.stderr}"


@pytest.mark.skipif(shutil.which("llc") is None, reason="llc not installed")
def test_fla_skips_cross_block_ssa_values():
    """A dispatcher edge destroys the entry block's dominance of %value."""
    ir = (
        "define i32 @f(i32 %x) {\n"
        "entry:\n"
        "  %value = add i32 %x, 1\n"
        "  %cond = icmp eq i32 %x, 0\n"
        "  br i1 %cond, label %yes, label %no\n"
        "yes:\n"
        "  ret i32 %value\n"
        "no:\n"
        "  ret i32 0\n"
        "}\n"
    )
    assert P.apply_fla(ir).strip() == ir.strip()


@pytest.mark.skipif(shutil.which("llvm-as") is None or shutil.which("llc") is None
                    or shutil.which("clang") is None,
                    reason="LLVM assembly/execution tools not installed")
def test_fla_cross_block_ssa_skip_and_safe_execution(tmp_path):
    unsafe = (
        "define i32 @unsafe(i32 %x) {\n"
        "entry:\n"
        "  %value = add i32 %x, 1\n"
        "  %cond = icmp eq i32 %x, 0\n"
        "  br i1 %cond, label %yes, label %no\n"
        "yes:\n"
        "  ret i32 %value\n"
        "no:\n"
        "  ret i32 0\n"
        "}\n"
    )
    safe = unsafe + (
        "define i32 @pick(i32 %x) {\n"
        "entry:\n"
        "  %cond = icmp eq i32 %x, 0\n"
        "  br i1 %cond, label %yes, label %no\n"
        "yes:\n"
        "  ret i32 10\n"
        "no:\n"
        "  ret i32 20\n"
        "}\n"
        "define i32 @main() {\n"
        "entry:\n"
        "  %a = call i32 @unsafe(i32 0)\n"
        "  %b = call i32 @unsafe(i32 1)\n"
        "  %c = call i32 @pick(i32 0)\n"
        "  %d = call i32 @pick(i32 1)\n"
        "  %ca = icmp eq i32 %a, 1\n"
        "  %cb = icmp eq i32 %b, 0\n"
        "  %cc = icmp eq i32 %c, 10\n"
        "  %cd = icmp eq i32 %d, 20\n"
        "  %ab = and i1 %ca, %cb\n"
        "  %cdboth = and i1 %cc, %cd\n"
        "  %both = and i1 %ab, %cdboth\n"
        "  %bad = xor i1 %both, true\n"
        "  %code = zext i1 %bad to i32\n"
        "  ret i32 %code\n"
        "}\n"
    )
    out = P.apply_fla(safe)
    # The unsafe function is preserved verbatim; the safe helper is flattened.
    assert unsafe in out
    assert "dispatcher_" in out

    ll = tmp_path / "fla.ll"
    bc = tmp_path / "fla.bc"
    obj = tmp_path / "fla.o"
    exe = tmp_path / "fla"
    ll.write_text(out)
    subprocess.run(["llvm-as", str(ll), "-o", str(bc)], check=True,
                   capture_output=True, text=True, timeout=20)
    subprocess.run(["llc", "-filetype=obj", str(bc), "-o", str(obj)], check=True,
                   capture_output=True, text=True, timeout=20)
    subprocess.run(["clang", str(obj), "-o", str(exe)], check=True,
                   capture_output=True, text=True, timeout=20)
    result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("llc") is None, reason="llc not installed")
def test_default_build_pass_chain_assembles(lowered, tmp_path):
    """The chain the build actually runs must assemble as a whole."""
    chain = ["bcf", "fla", "sub", "replay", "speculative"]
    out = P.apply_all(lowered, chain)
    result = _assemble(out, tmp_path, "chain")
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("llc") is None, reason="llc not installed")
def test_all_passes_together_assemble(lowered, tmp_path):
    out = P.apply_all(lowered, PASS_VOCABULARY)
    result = _assemble(out, tmp_path, "all")
    assert result.returncode == 0, result.stderr


def test_replay_poison_defines_its_stub_exactly_once(lowered):
    out = P.apply_all(lowered, ["replay"])
    assert out.count("define internal i64 @__rdrand_stub") == 1
    # A `declare` alongside an `internal` `define` is an invalid redefinition.
    assert "declare i64 @__rdrand_stub" not in out


def test_replay_poison_is_idempotent_on_its_stub(lowered):
    once = P.apply_all(lowered, ["replay"])
    twice = P.apply_all(once, ["replay"])
    assert twice.count("define internal i64 @__rdrand_stub") == 1


def test_crypto_cfg_declares_its_helpers_once(lowered):
    out = P.apply_all(lowered, ["crypto_cfg"])
    assert out.count("declare i64 @__cfg_chain_init") == 1


def test_speculative_declares_expect_once(lowered):
    out = P.apply_all(lowered, ["speculative"])
    assert out.count("declare i64 @llvm.expect.i64") == 1


def test_unknown_pass_is_ignored(lowered):
    assert P.apply_all(lowered, ["not_a_pass"]) == lowered


def test_codegen_accepts_every_pass_in_the_vocabulary():
    """argparse `choices` must not be narrower than apply_all's vocabulary."""
    import argparse

    from llvmgen import codegen

    captured = {}
    real_parse = argparse.ArgumentParser.parse_args

    def spy(self, *a, **kw):
        captured["parser"] = self
        raise SystemExit(0)

    argparse.ArgumentParser.parse_args = spy
    try:
        with pytest.raises(SystemExit):
            codegen.main()
    finally:
        argparse.ArgumentParser.parse_args = real_parse

    action = next(
        a for a in captured["parser"]._actions if a.dest == "ollvm_passes"
    )
    missing = set(PASS_VOCABULARY) - set(action.choices)
    assert not missing, f"codegen rejects passes apply_all supports: {sorted(missing)}"


def test_default_config_passes_are_all_known():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "config", "default.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    configured = cfg["shadow_compiler"]["llvmgen"]["ollvm_passes"]
    assert configured, "default config must name at least one pass"
    unknown = set(configured) - set(PASS_VOCABULARY)
    assert not unknown, f"config names passes apply_all cannot dispatch: {sorted(unknown)}"


def test_phase_reads_the_configured_pass_list(monkeypatch):
    """The config key was inert; the phase must consume it."""
    from scripts.phases import phase03_compile as p3

    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd

    monkeypatch.setattr(p3, "run", fake_run)
    monkeypatch.setattr(p3, "_ollvm_passes_from_config", lambda: ["bcf", "replay"])
    p3.phase_llvm_codegen("in.ir", "out.o")
    cmd = seen["cmd"]
    assert cmd[cmd.index("--ollvm-passes") + 1:] == ["bcf", "replay"]


def test_phase_falls_back_to_defaults_when_config_is_unreadable(monkeypatch):
    from scripts.phases import phase03_compile as p3

    monkeypatch.setattr(p3.os.path, "join", lambda *a: "/nonexistent/default.json")
    assert p3._ollvm_passes_from_config() == list(p3.DEFAULT_OLLVM_PASSES)


def test_runtime_dependent_passes_are_not_in_the_default_chain():
    """Passes whose helpers have no runtime implementation must stay opt-in."""
    from scripts.phases import phase03_compile as p3

    assert not (set(p3.DEFAULT_OLLVM_PASSES) & p3._OLLVM_PASSES_NEEDING_RUNTIME)


def test_schema_allows_every_pass_the_codegen_allows():
    """config_schema's allow-list must not be narrower than codegen's."""
    from scripts.config_schema import OLLVM_KNOWN_PASSES

    missing = set(PASS_VOCABULARY) - set(OLLVM_KNOWN_PASSES)
    assert not missing, f"schema rejects passes apply_all supports: {sorted(missing)}"


def test_schema_default_matches_the_shipped_config():
    """The schema default and config/default.json must agree."""
    from scripts.config_schema import SCHEMA

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "config", "default.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    shipped = cfg["shadow_compiler"]["llvmgen"]["ollvm_passes"]
    spec = SCHEMA["shadow_compiler.llvmgen.ollvm_passes"]
    assert list(spec["default"]) == list(shipped)
