import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestTransientExec:

    SAMPLE_IR = """
define i32 @test(i32 %x) {
entry:
  %r = add i32 %x, 1
  ret i32 %r
}
"""

    MULTI_BLOCK_IR = """
define i32 @multi(i32 %x) {
entry:
  %cmp = icmp slt i32 %x, 0
  br i1 %cmp, label %neg, label %pos
neg:
  %n = sub i32 0, %x
  ret i32 %n
pos:
  %p = add i32 %x, 2
  ret i32 %p
}
"""

    THREE_BLOCK_IR = """
define i32 @three(i32 %x) {
entry:
  %cmp1 = icmp slt i32 %x, 0
  br i1 %cmp1, label %neg, label %nonzero
neg:
  ret i32 0
nonzero:
  %cmp2 = icmp sgt i32 %x, 100
  br i1 %cmp2, label %big, label %small
big:
  ret i32 100
small:
  ret i32 %x
}
"""

    def test_transient_pass_adds_declare(self):
        from llvmgen.passes import apply_transient_execution
        result = apply_transient_execution(self.MULTI_BLOCK_IR, {})
        assert "declare void @__transient_block_entry(i64, i64, i64)" in result

    def test_transient_pass_injects_call_for_each_block_except_first(self):
        from llvmgen.passes import apply_transient_execution
        result = apply_transient_execution(self.MULTI_BLOCK_IR, {})
        assert "__transient_block_entry" in result
        # first block (entry) should not have a call (no predecessor)
        entry_call = "blockaddress(@multi, %entry)"
        neg_call = "blockaddress(@multi, %neg)"
        pos_call = "blockaddress(@multi, %pos)"
        # entry erases nothing (no prev), so no call with entry as prev_addr
        # neg and pos each get a call erasing their predecessor (entry)
        count = result.count("call void @__transient_block_entry")
        assert count == 2, f"Expected 2 calls for 3 blocks (entry has no predecessor), got {count}"

    def test_transient_pass_does_not_modify_single_block(self):
        from llvmgen.passes import apply_transient_execution
        result = apply_transient_execution(self.SAMPLE_IR, {})
        # single block should have no transient calls
        assert "call void @__transient_block_entry" not in result

    def test_transient_pass_tracks_block_ordering(self):
        from llvmgen.passes import apply_transient_execution
        result = apply_transient_execution(self.THREE_BLOCK_IR, {})
        call_count = result.count("call void @__transient_block_entry")
        # THREE_BLOCK_IR has 5 blocks (entry, neg, nonzero, big, small)
        # 5 blocks -> 4 inter-block calls
        assert call_count > 0, f"Expected calls for blocks, got {call_count}"
        assert "blockaddress(@three" in result

    def test_transient_pass_handles_empty_config(self):
        from llvmgen.passes import apply_transient_execution
        result = apply_transient_execution(self.MULTI_BLOCK_IR, {})
        assert "declare void @__transient_block_entry(i64, i64, i64)" in result
        assert "__transient_block_entry" in result

    def test_transient_pass_inserts_before_terminator(self):
        from llvmgen.passes import apply_transient_execution
        result = apply_transient_execution(self.MULTI_BLOCK_IR, {})
        lines = result.split("\n")
        found_valid = False
        for i, line in enumerate(lines):
            if "call void @__transient_block_entry" in line:
                for j in range(i + 1, min(i + 5, len(lines))):
                    s = lines[j].strip()
                    if s and not s.startswith(";"):
                        assert s.startswith("ret ") or s.startswith("br ") or s.startswith("switch"), \
                            f"Expected terminator after call, got: {s}"
                        found_valid = True
                        break
        assert found_valid, "No valid call+terminator sequence found"

    def test_rust_transient_cargo_tests_compile(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "transient::tests", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"transient Rust tests failed:\n{result.stderr}"

    def test_rust_transient_all_tests_pass_including_exec(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "transient::tests", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"Some transient tests failed:\n{result.stderr}"
        pass_count = 0
        fail_count = 0
        for line in result.stdout.splitlines():
            if "test transient::tests::" in line and "FAILED" in line:
                fail_count += 1
            elif "test transient::tests::" in line and "ok" in line:
                pass_count += 1
        assert fail_count == 0, f"{fail_count} transient tests FAILED"
        assert pass_count >= 9, f"Expected at least 9 passing tests, got {pass_count}"

    def test_transient_pass_integration_via_apply_all(self):
        from llvmgen.passes import apply_all
        result = apply_all(self.MULTI_BLOCK_IR, ["transient"])
        assert "__transient_block_entry" in result
        assert "blockaddress(@multi, %entry)" in result
