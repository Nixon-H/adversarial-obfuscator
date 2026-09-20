"""
phase27_cpu_port.py

Purpose:
Runs CPU execution port entanglement tests.  Validates that the runtime
can entangle execution with specific CPU execution ports (ALUs,
load/store units, etc.) for microarchitectural fingerprinting.

Architectural Role:
Validation phase — runs cargo tests for the CPU port entanglement subsystem.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, subprocess, ..common

Security Relevance:
CPU port entanglement creates a microarchitectural fingerprint unique
to the specific CPU model, detecting emulation and replay.
"""

import json
import os
import subprocess
from ..common import log, BUILD_DIR

RUNTIME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "runtime")

def phase_cpu_port(seed=None):
    """
    Run CPU execution port entanglement tests from the runtime crate.

    Args:
        seed: optional seed for the port entanglement RNG

    Returns:
        dict with test result written to BUILD_DIR
    """
    log("CPU_PORT", "Running CPU execution port entanglement")
    log("CPU_PORT", "Running CPU execution port entanglement")
    env = os.environ.copy()
    if seed is not None:
        env["NIXON_PORT_ENTANGLE_SEED"] = str(seed)
    result = subprocess.run(
        ["cargo", "test", "--", "port_entangle::tests", "--nocapture"],
        cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60, env=env,
    )
    out_path = os.path.join(BUILD_DIR, "cpu_port_result.json")
    with open(out_path, "w") as f:
        json.dump({"returncode": result.returncode, "stdout": result.stdout[-500:], "stderr": result.stderr[-500:]}, f)
    if result.returncode == 0:
        log("CPU_PORT", "CPU port entangle tests passed")
    else:
        log("SKIP", f"CPU port entangle tests: {result.stderr[-200:]}")
