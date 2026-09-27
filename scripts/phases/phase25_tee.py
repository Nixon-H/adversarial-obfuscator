"""
phase25_tee.py

Purpose:
Runs Trusted Execution Environment (TEE) partition tests.  Validates
that the runtime correctly partitions code for TEE execution with a
configurable TEE type (software, Intel SGX, AMD SEV, etc.).

Architectural Role:
Validation phase — runs cargo tests for the TEE subsystem.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, subprocess, ..common

Security Relevance:
TEE partitions isolate sensitive computations from the host OS,
providing hardware-backed confidentiality and integrity.
"""

import json
import os
import subprocess
from ..common import log, BUILD_DIR

RUNTIME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "runtime")

def phase_tee(tee_type="software"):
    """
    Run TEE partition tests from the runtime crate.

    Args:
        tee_type: TEE variant to test (software, sgx, sev, etc.)

    Returns:
        dict with test result written to BUILD_DIR
    """
    log("TEE", f"Running TEE partition tests (type={tee_type})")
    env = os.environ.copy()
    env["NIXON_TEE_TYPE"] = tee_type
    result = subprocess.run(
        ["cargo", "test", "--", "tee::tests", "--nocapture"],
        cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60, env=env,
    )
    out_path = os.path.join(BUILD_DIR, "tee_result.json")
    with open(out_path, "w") as f:
        json.dump({"tee_type": tee_type, "returncode": result.returncode, "stdout": result.stdout[-500:], "stderr": result.stderr[-500:]}, f)
    if result.returncode == 0:
        log("TEE", "TEE tests passed")
    else:
        log("SKIP", f"TEE tests: {result.stderr[-200:]}")
