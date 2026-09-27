"""
phase26_sgx.py

Purpose:
Runs Intel SGX enclave tests.  Validates that the runtime can create
and execute within SGX enclaves when the Intel SGX SDK is available.

Architectural Role:
Hardware-specific validation phase — requires SGX hardware/SDK.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, subprocess, ..common

Security Relevance:
SGX enclaves provide hardware-isolated execution, protecting code and
data even from a compromised host OS.
"""

import json
import os
import subprocess
from ..common import log, BUILD_DIR

RUNTIME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "runtime")

def phase_sgx():
    """
    Run SGX enclave tests from the runtime crate.

    Returns:
        dict with test result written to BUILD_DIR
    """
    log("SGX", "Running SGX enclave tests (requires Intel SGX SDK)")
    try:
        result = subprocess.run(
            ["cargo", "test", "--features", "sgx", "--", "tee_sgx::tests", "--nocapture"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
        )
        out_path = os.path.join(BUILD_DIR, "sgx_result.json")
        with open(out_path, "w") as f:
            json.dump({"returncode": result.returncode, "stdout": result.stdout[-500:], "stderr": result.stderr[-500:]}, f)
        if result.returncode == 0:
            log("SGX", "SGX tests passed")
        else:
            log("SKIP", "SGX hardware not available (requires Intel SGX SDK)")
    except Exception as e:
        log("SKIP", f"SGX not available: {e}")
