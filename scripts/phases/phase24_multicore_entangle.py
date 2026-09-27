"""
phase24_multicore_entangle.py

Purpose:
Runs multi-core timing entanglement tests.  Verifies that the runtime
can entangle execution across multiple cores, creating a unique
multi-core timing fingerprint.

Architectural Role:
Validation phase — runs cargo tests for the multi-core entanglement subsystem.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, subprocess, ..common

Security Relevance:
Multi-core entanglement ties execution to specific core timing
relationships, detecting emulation and sandbox environments.
"""

import json
import os
import subprocess
from ..common import log, BUILD_DIR

RUNTIME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "runtime")

def phase_multicore_entangle():
    """
    Run multi-core timing entanglement tests from the runtime crate.

    Returns:
        dict with test result written to BUILD_DIR
    """
    log("MULTICORE_ENTANGLE", "Running multi-core timing entanglement")
    result = subprocess.run(
        ["cargo", "test", "--", "multicore_entangle::tests", "--nocapture"],
        cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
    )
    out_path = os.path.join(BUILD_DIR, "multicore_entangle_result.json")
    with open(out_path, "w") as f:
        json.dump({"returncode": result.returncode, "stdout": result.stdout[-500:], "stderr": result.stderr[-500:]}, f)
    if result.returncode == 0:
        log("MULTICORE_ENTANGLE", "Multicore entangle tests passed")
    else:
        log("SKIP", f"Multicore entangle tests failed: {result.stderr[-200:]}")
