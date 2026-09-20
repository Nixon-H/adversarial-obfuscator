import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestSpeculative:

    SIMPLE_IR = """
define i32 @test(i32 %x, i32 %y) {
entry:
  %cmp = icmp slt i32 %x, %y
  br i1 %cmp, label %true_block, label %false_block
true_block:
  %r1 = add i32 %x, 1
  ret i32 %r1
false_block:
  %r2 = sub i32 %y, 1
  ret i32 %r2
}
"""

    def test_trap_blocks_added(self):
        from llvmgen.passes import apply_speculative_traps
        result = apply_speculative_traps(self.SIMPLE_IR)
        assert "spec_trap" in result
        assert "real_check" in result

    def test_trap_contains_cache_poisoning(self):
        from llvmgen.passes import apply_speculative_traps
        result = apply_speculative_traps(self.SIMPLE_IR)
        assert "getelementptr" in result
        assert "@__spec_poison_buf" in result
        assert "load volatile" in result
        assert "store volatile" in result
        assert "@__spec_state" in result
        assert "@__spec_scratch" in result

    def test_expect_intrinsic_inserted(self):
        from llvmgen.passes import apply_speculative_traps
        result = apply_speculative_traps(self.SIMPLE_IR)
        assert "@llvm.expect.i64" in result

    def test_global_poison_buffer_declared(self):
        from llvmgen.passes import apply_speculative_traps
        result = apply_speculative_traps(self.SIMPLE_IR)
        assert "@__spec_poison_buf = global [4096 x i8]" in result
        assert "@__spec_state = global i64" in result
        assert "@__spec_scratch = global i64" in result

    def test_no_branches_unchanged(self):
        from llvmgen.passes import apply_speculative_traps
        ir = """
define i32 @no_branches(i32 %x) {
entry:
  %r = add i32 %x, 1
  ret i32 %r
}
"""
        result = apply_speculative_traps(ir)
        assert "spec_trap" not in result

    def test_rust_speculative_module_valid(self):
        import subprocess, os
        spec_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "runtime", "src", "speculative.rs"
        )
        assert os.path.exists(spec_path), "speculative.rs not found"
        with open(spec_path) as f:
            content = f.read()
        assert "pub static mut SPEC_POISON_BUF" in content
        assert "pub static mut SPEC_STATE" in content
        assert "pub static mut SPEC_SCRATCH" in content
        assert "mod tests" in content
        result = subprocess.run(
            ["rustfmt", "--check", spec_path],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"speculative.rs has syntax errors:\n{result.stderr}"
        )
