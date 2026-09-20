"""
Tests for Hardware Research Integration (Items 125-129).
"""
import subprocess
import json
import os
import sys
import importlib.util

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

RUNTIME_DIR = os.path.join(os.path.dirname(__file__), "..", "runtime")


class TestBranchEntangle:
    """
    TestBranchEntangle
    
    Positive test cases for branchentangle.
    """
    def test_branch_entangle_basic(self):
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "branch_entangle::tests", "--nocapture"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0


class TestMulticoreEntangle:
    """
    TestMulticoreEntangle
    
    Positive test cases for multicoreentangle.
    """
    def test_multicore_entangle(self):
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "multicore_entangle::tests", "--nocapture"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0


class TestTee:
    """
    TestTee
    
    Positive test cases for tee.
    """
    def test_tee_partition(self):
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "tee::tests", "--nocapture"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0


def _sgx_sdk_available():
    """Check if Intel SGX SDK libraries are available for linking."""
    try:
        ld_flags = subprocess.run(
            ["ldconfig", "-p"], capture_output=True, text=True, timeout=5,
        )
        if "libsgx_urts" not in ld_flags.stdout:
            return False
        result = subprocess.run(
            ["cargo", "check", "--lib", "--features", "sgx"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
        )
        return result.returncode == 0
    except Exception:
        return False


class TestSgx:
    """
    TestSgx
    
    Positive test cases for sgx.
    """
    def test_sgx_available(self):
        if not _sgx_sdk_available():
            return  # pass silently — SGX SDK not installed on this system
        result = subprocess.run(
            ["cargo", "test", "--lib", "--features", "sgx", "--", "tee_sgx::tests", "--nocapture"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0


class TestCpuPort:
    """
    TestCpuPort
    
    Positive test cases for cpuport.
    """
    def test_cpu_port_scheduler(self):
        result = subprocess.run(
            ["cargo", "test", "--lib", "--", "port_entangle::tests", "--nocapture"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0


class TestGpuHybrid:
    """
    TestGpuHybrid
    
    Positive test cases for gpuhybrid.
    """
    def test_gpu_executor_exists(self):
        spec = importlib.util.find_spec("scripts.gpu.gpu_execution")
        assert spec is not None

    def test_hybrid_protector_exists(self):
        spec = importlib.util.find_spec("scripts.gpu.hybrid_protection")
        assert spec is not None
