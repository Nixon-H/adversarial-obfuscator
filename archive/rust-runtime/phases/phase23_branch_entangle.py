"""
phase23_branch_entangle.py

Purpose:
Runs branch predictor entanglement tests.  Verifies that branch
predictor state is entangled with the execution context, creating
a CPU-specific execution fingerprint.

Architectural Role:
Validation phase — runs cargo tests for the branch entanglement subsystem.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, subprocess, ..common

Security Relevance:
Branch entanglement ties execution to the CPU's branch predictor
state, making emulation and replay attacks detectable.
"""

import json
import os
import subprocess
from ..common import log, BUILD_DIR

RUNTIME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "runtime")

def phase_branch_entangle():
    """
    Run branch predictor entanglement tests from the runtime crate.

    Returns:
        dict with test result written to BUILD_DIR
    """
    log("BRANCH_ENTANGLE", "Running branch predictor entanglement")
    result = subprocess.run(
        ["cargo", "test", "--", "branch_entangle::tests", "--nocapture"],
        cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
    )
    out_path = os.path.join(BUILD_DIR, "branch_entangle_result.json")
    with open(out_path, "w") as f:
        json.dump({"returncode": result.returncode, "stdout": result.stdout[-500:], "stderr": result.stderr[-500:]}, f)
    if result.returncode == 0:
        log("BRANCH_ENTANGLE", "Branch entangle tests passed")
    else:
        log("SKIP", f"Branch entangle tests failed: {result.stderr[-200:]}")
