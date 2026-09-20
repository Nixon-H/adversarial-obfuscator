import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestExecGuard:
    def test_rust_exec_guard_new(self):
        import subprocess
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "exec_guard::tests::test_new_succeeds", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"test_new_succeeds failed:\n{result.stderr}\n{result.stdout}"

    def test_rust_exec_guard_guard_pages(self):
        import subprocess
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "exec_guard::tests::test_guard_pages_protected", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"test_guard_pages_protected failed:\n{result.stderr}\n{result.stdout}"

    def test_rust_exec_guard_permission_toggling(self):
        import subprocess
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "exec_guard::tests::test_permission_toggling", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"test_permission_toggling failed:\n{result.stderr}\n{result.stdout}"

    def test_rust_exec_guard_drop_cleanup(self):
        import subprocess
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "exec_guard::tests::test_drop_cleans_memory", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"test_drop_cleans_memory failed:\n{result.stderr}\n{result.stdout}"

    def test_rust_exec_guard_multiple_guards(self):
        import subprocess
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "exec_guard::tests::test_multiple_guards_no_conflict", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"test_multiple_guards_no_conflict failed:\n{result.stderr}\n{result.stdout}"

    def test_rust_exec_guard_all_tests_pass(self):
        import subprocess
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "exec_guard::tests", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"Some exec_guard tests failed:\n{result.stderr}\n{result.stdout}"
        pass_count = 0
        fail_count = 0
        for line in result.stdout.splitlines():
            if "test exec_guard::tests::" in line and "FAILED" in line:
                fail_count += 1
            elif "test exec_guard::tests::" in line and "ok" in line:
                pass_count += 1
        assert fail_count == 0, f"{fail_count} exec_guard tests FAILED"
        assert pass_count >= 5, f"Expected at least 5 passing tests, got {pass_count}"
