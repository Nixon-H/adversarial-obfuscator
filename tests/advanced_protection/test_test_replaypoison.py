import ast
import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestReplayPoison:

    def test_llvm_replay_poison_pass_applies(self):
        from llvmgen.passes import apply_replay_poison
        ir = """
define i32 @test(i32 %x) {
entry:
  %state = alloca i32, align 4
  store i32 0, ptr %state, align 4
  %sw = load i32, ptr %state, align 4
  switch i32 %sw, label %bb0 [
    i32 0, label %bb0
    i32 1, label %bb1
  ]
bb0:
  %r = add i32 %x, 1
  ret i32 %r
bb1:
  ret i32 0
}
"""
        result = apply_replay_poison(ir, num_dead_cases=2)
        assert "rddead" in result or "__rdrand_stub" in result
        assert "switch" in result
        assert "__rdrand_stub" in result

    def test_python_entropy_branch_injection(self):
        from obfuscator.replay_poison import inject_entropy_branches
        source = """
def compute(x):
    return x * 2

def process(data):
    result = 0
    for d in data:
        result += d
    return result
"""
        result = inject_entropy_branches(source, {})
        assert "os.urandom" in result
        assert "_entropy_buf" in result
        assert "_entropy_idx" in result
        tree = ast.parse(result)
        assert isinstance(tree, ast.Module)

    def test_python_entropy_branch_empty_source(self):
        from obfuscator.replay_poison import inject_entropy_branches
        assert inject_entropy_branches("", {}) == ""

    def test_python_entropy_branch_syntax_error(self):
        from obfuscator.replay_poison import inject_entropy_branches
        result = inject_entropy_branches("def foo(::", {})
        assert result == "def foo(::"

    def test_python_cfg_poisoning_ir_module(self):
        from obfuscator.replay_poison import inject_cfg_poisoning
        from irgen.compile import IrModule, IrFunction, IrType
        mod = IrModule("test")
        func = IrFunction("test_func", IrType.i32())
        entry = func.new_block("entry")
        mod.functions.append(func)
        result = inject_cfg_poisoning(mod, {"cfgp_num_dead_cases": 4})
        assert isinstance(result, IrModule)

    def test_rust_replay_poison_all_tests_pass(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "replay_poison::tests", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"Some replay_poison tests failed:\n{result.stderr}"
        pass_count = 0
        fail_count = 0
        for line in result.stdout.splitlines():
            if "test replay_poison::tests::" in line and "FAILED" in line:
                fail_count += 1
            elif "test replay_poison::tests::" in line and "ok" in line:
                pass_count += 1
        assert fail_count == 0, f"{fail_count} replay_poison tests FAILED"
        assert pass_count >= 9, f"Expected at least 9 passing tests, got {pass_count}"
