"""Execution regressions for per-return CPU port entanglement checks."""

import re
import shutil
import subprocess

import pytest

from irgen.port_entangle import PortEntanglementPass


IR = """define i32 @choose(i32 %x) {
entry:
  %cond = icmp eq i32 %x, 0
  br i1 %cond, label %early, label %late
early:
  ret i32 11
late:
  ret i32 22
}
"""

HELPERS = """declare void @nixon_reset_corruptions()
declare i32 @nixon_corruptions()
"""

MAIN = """define i32 @main() {
entry:
  call void @nixon_reset_corruptions()
  %early = call i32 @choose(i32 0)
  %early_corrupt = call i32 @nixon_corruptions()
  call void @nixon_reset_corruptions()
  %late = call i32 @choose(i32 1)
  %late_corrupt = call i32 @nixon_corruptions()
  %early_ok = icmp eq i32 %early, 11
  %late_ok = icmp eq i32 %late, 22
  %early_check_ok = icmp eq i32 %early_corrupt, __EXPECTED__
  %late_check_ok = icmp eq i32 %late_corrupt, __EXPECTED__
  %values_ok = and i1 %early_ok, %late_ok
  %checks_ok = and i1 %values_ok, %early_check_ok
  %all_ok = and i1 %checks_ok, %late_check_ok
  %bad = xor i1 %all_ok, true
  %code = zext i1 %bad to i32
  ret i32 %code
}
"""


def _function_bodies(text):
    bodies = []
    start = 0
    while True:
        start = text.find("define ", start)
        if start < 0:
            return bodies
        brace = text.find("{", start)
        end = text.find("\n}", brace)
        if end < 0:
            end = text.find("}", brace)
        if end < 0:
            raise AssertionError("unterminated function in generated IR")
        bodies.append(text[brace + 1:end])
        start = end + 1


@pytest.mark.parametrize("hard_exit", [False, True])
def test_every_return_routes_through_one_checked_epilogue(hard_exit):
    out = PortEntanglementPass().embed_timing_check(
        IR, {"timing_hard_exit": hard_exit})
    body = _function_bodies(out)[0]
    assert body.count("ret i32") == 1
    assert len(re.findall(r"^pe_check_[0-9a-f]+:$", body, re.MULTILINE)) == 1
    assert len(re.findall(r"^pe_checked_[0-9a-f]+:$", body, re.MULTILINE)) == 1
    assert body.count("br label %pe_check_") == 2


def test_void_returns_share_one_checked_epilogue():
    ir = (
        "define void @f(i32 %x) {\n"
        "entry:\n"
        "  %c = icmp eq i32 %x, 0\n"
        "  br i1 %c, label %early, label %late\n"
        "early:\n"
        "  ret void\n"
        "late:\n"
        "  ret void\n"
        "}\n"
    )
    body = _function_bodies(PortEntanglementPass().apply_to_ir(ir))[0]
    assert body.count("ret void") == 1
    assert len(re.findall(
        r"^port_entangle_check_[0-9a-f]+:$", body, re.MULTILINE)) == 1
    assert len(re.findall(
        r"^port_entangle_clean_[0-9a-f]+:$", body, re.MULTILINE)) == 1


def test_uncalibrated_timing_floor_defaults_to_zero():
    out = PortEntanglementPass().embed_timing_check(IR, {})
    assert "store i64 0, ptr %pe_seed_" in out
    assert "store i64 5000, ptr %pe_seed_" not in out


@pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("llvm-as", "llc", "clang")),
    reason="LLVM assembly/execution tools not installed",
)
@pytest.mark.parametrize("hard_exit", [False, True])
@pytest.mark.parametrize("threshold", [0, 1_000_000_000])
def test_hard_and_soft_checks_execute_on_normal_and_early_returns(
        tmp_path, hard_exit, threshold):
    config = {"timing_threshold": threshold, "timing_hard_exit": hard_exit}
    out = PortEntanglementPass().embed_timing_check(IR, config)
    expected_corruptions = int(threshold != 0)
    source = HELPERS + out + MAIN.replace(
        "__EXPECTED__", str(expected_corruptions))
    ll = tmp_path / "port.ll"
    bc = tmp_path / "port.bc"
    obj = tmp_path / "port.o"
    exe = tmp_path / "port"
    rdtsc_c = tmp_path / "rdtsc.c"
    rdtsc_c.write_text(
        "#include <stdint.h>\n"
        "static int corruptions;\n"
        "uint64_t nixon_rdtsc(void) __asm__(\"__rdtsc\");\n"
        "uint64_t nixon_rdtsc(void) { return 0; }\n"
        "void __corrupt_key(void) { ++corruptions; }\n"
        "void nixon_reset_corruptions(void) { corruptions = 0; }\n"
        "int nixon_corruptions(void) { return corruptions; }\n")
    ll.write_text(source)
    subprocess.run(["llvm-as", str(ll), "-o", str(bc)], check=True,
                   capture_output=True, text=True, timeout=20)
    subprocess.run(["llc", "-filetype=obj", str(bc), "-o", str(obj)], check=True,
                   capture_output=True, text=True, timeout=20)
    subprocess.run(["clang", str(obj), str(rdtsc_c), "-o", str(exe)], check=True,
                   capture_output=True, text=True, timeout=20)
    result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10)
    # MAIN returns nonzero for wrong values or a missed early/late check.
    assert result.returncode == 0, result.stderr
