import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestHPC:

    def test_tsc_reading_works(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hpc::tests::test_read_tsc_returns_value", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"TSC test failed:\n{result.stderr}"

    def test_hpc_key_derivation_deterministic(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hpc_key::tests::test_derive_key_deterministic_same_seed", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Deterministic key derivation failed:\n{result.stderr}"

    def test_hpc_key_different_seeds(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hpc_key::tests::test_derive_key_different_seeds", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Different seeds test failed:\n{result.stderr}"

    def test_hpc_key_not_identity(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hpc_key::tests::test_derive_key_not_identity", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Not-identity test failed:\n{result.stderr}"

    def test_hpc_cache_priming_does_not_crash(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hpc::tests::test_prime_cache_pattern_does_not_crash", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Cache priming crashed:\n{result.stderr}"

    def test_hpc_emulator_detection_runs(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hpc_detect::tests::test_detect_emulator_runs", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Emulator detection failed:\n{result.stderr}"

    def test_hpc_pmc_read_attempt(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hpc::tests::test_read_pmc_attempt", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"PMC read attempt failed:\n{result.stderr}"

    def test_hpc_l2_cache_misses_attempt(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hpc::tests::test_read_l2_cache_misses_attempt", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"L2 miss read failed:\n{result.stderr}"

    def test_hpc_branch_mispredictions_attempt(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hpc::tests::test_read_branch_mispredictions_attempt", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"Branch mispredict read failed:\n{result.stderr}"

    def test_hpc_all_tests_pass(self):
        import subprocess, os
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hpc::tests", "hpc_key::tests", "hpc_detect::tests", "--nocapture"],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "runtime"),
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"Some HPC tests failed:\n{result.stderr}"
        pass_count = 0
        fail_count = 0
        for line in result.stdout.splitlines():
            if ("test hpc::tests::" in line or "test hpc_key::tests::" in line or "test hpc_detect::tests::" in line) and "FAILED" in line:
                fail_count += 1
            elif ("test hpc::tests::" in line or "test hpc_key::tests::" in line or "test hpc_detect::tests::" in line) and "ok" in line:
                pass_count += 1
        assert fail_count == 0, f"{fail_count} HPC tests FAILED"
        assert pass_count >= 10, f"Expected at least 10 passing HPC tests, got {pass_count}"
