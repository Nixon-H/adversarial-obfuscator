import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestCryptoCFG:

    def test_state_chain_initializes_correctly(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "crypto_cfg::tests::test_state_chain_initializes_correctly", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"State chain init test failed:\n{result.stderr}"

    def test_advance_deterministic_sequence(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "crypto_cfg::tests::test_advance_produces_deterministic_sequence", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Deterministic advance test failed:\n{result.stderr}"

    def test_verify_transition_valid(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "crypto_cfg::tests::test_verify_transition_valid", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Valid transition test failed:\n{result.stderr}"

    def test_verify_transition_invalid_token(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "crypto_cfg::tests::test_verify_transition_invalid_token", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Invalid token test failed:\n{result.stderr}"

    def test_block_key_unique_per_block(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "crypto_cfg::tests::test_block_key_unique_per_block", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Unique block key test failed:\n{result.stderr}"

    def test_llvm_pass_inserts_checkpoint_calls(self):
        from llvmgen.passes import apply_crypto_checkpointing
        ir = """
define i32 @test(i32 %x) {
entry:
  %r = add i32 %x, 1
  ret i32 %r
}
"""
        result = apply_crypto_checkpointing(ir, {"seed": 42})
        assert "__cfg_chain_init" in result
        assert "__cfg_advance_chain" in result
        assert "declare i64 @__cfg_chain_init(i64)" in result
        assert "declare i1 @__cfg_verify_block(i64, i64)" in result

    def test_invalid_token_causes_decryption_failure(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "crypto_cfg::tests::test_check_block_authorization_invalid_token", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Invalid token decryption test failed:\n{result.stderr}"

    def test_llvm_pass_adds_verify_blocks(self):
        from llvmgen.passes import apply_crypto_checkpointing
        ir = """
define i32 @test(i32 %x) {
entry:
  %cmp = icmp slt i32 %x, 0
  br i1 %cmp, label %pos, label %neg
pos:
  %r1 = add i32 %x, 1
  ret i32 %r1
neg:
  %r2 = sub i32 0, %x
  ret i32 %r2
}
"""
        result = apply_crypto_checkpointing(ir, {"seed": 7})
        assert "__cfg_verify_block" in result
        assert "__cfg_abort" in result
        assert "cfail" in result or "fail" in result

    def test_rust_crypto_cfg_all_tests_pass(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "crypto_cfg::tests", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"Some crypto_cfg tests failed:\n{result.stderr}"
        pass_count = 0
        fail_count = 0
        for line in result.stdout.splitlines():
            if "test crypto_cfg::tests::" in line and "FAILED" in line:
                fail_count += 1
            elif "test crypto_cfg::tests::" in line and "ok" in line:
                pass_count += 1
        assert fail_count == 0, f"{fail_count} crypto_cfg tests FAILED"
        assert pass_count >= 12, f"Expected at least 12 passing tests, got {pass_count}"

    def test_llvm_pass_registered_in_apply_all(self):
        from llvmgen.passes import apply_all
        ir = """
define i32 @test(i32 %x) {
entry:
  ret i32 %x
}
"""
        result = apply_all(ir, ["crypto_cfg"])
        assert "__cfg_chain_init" in result
        assert "__cfg_advance_chain" in result
        assert "__cfg_get_current_token" in result
