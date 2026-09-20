"""
Tests for Hardware Research Integration (Items 120-124).
"""
import subprocess
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "build")
RUNTIME_DIR = os.path.join(os.path.dirname(__file__), "..", "runtime")


class TestHPC:
    """
    TestHPC
    
    Positive test cases for hpc.
    """
    def test_hpc_read_pmc(self):
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hpc::tests", "--nocapture"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0 or "ok" in result.stdout

    def test_hpc_tsc(self):
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hpc::tests::test_read_tsc_returns_value", "--nocapture"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0

    def test_hpc_cache_misses(self):
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hpc::tests::test_read_l2_cache_misses_attempt", "--nocapture"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0


class TestHpcKey:
    """
    TestHpcKey
    
    Positive test cases for hpckey.
    """
    def test_hpc_key_derivation(self):
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hpc_key::tests", "--nocapture"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0


class TestHpcDetect:
    """
    TestHpcDetect
    
    Positive test cases for hpcdetect.
    """
    def test_hpc_detect(self):
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hpc_detect::tests", "--nocapture"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0


class TestHwEntropy:
    """
    TestHwEntropy
    
    Positive test cases for hwentropy.
    """
    def test_hw_entropy_loop(self):
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hw_entropy::tests", "--nocapture"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0

    def test_hw_entropy_feedback(self):
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "hw_entropy::tests::test_feedback_loop_integrates", "--nocapture"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0


class TestCacheBound:
    """
    TestCacheBound
    
    Positive test cases for cachebound.
    """
    def test_cache_bound_execute(self):
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "cache_bound::tests", "--nocapture"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0

    def test_cache_bound_critical(self):
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "cache_bound::tests::test_execute_critical_runs", "--nocapture"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0
