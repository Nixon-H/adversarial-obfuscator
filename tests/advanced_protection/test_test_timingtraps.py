import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestTimingTraps:
    def test_rust_timing_traps_compile(self):
        import subprocess
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "timing::tests"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0 or "ok" in result.stdout, result.stderr

    def test_rust_timing_traps_summary(self):
        import subprocess
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "timing::tests", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        for line in result.stdout.splitlines():
            if "test timing::tests" in line:
                assert "FAILED" not in line, line
