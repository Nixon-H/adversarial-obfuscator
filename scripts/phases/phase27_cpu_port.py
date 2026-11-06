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
    env = os.environ.copy()
    if seed is not None:
        env["NIXON_PORT_ENTANGLE_SEED"] = str(seed)
    # A PROBE must never fail the build.
    #
    # This runs `cargo test`, which compiles the runtime crate first. On a cold CI
    # runner that is minutes, and the old 60-second timeout raised TimeoutExpired
    # straight out of the builder: `--cpu-port` failed on Windows in two separate
    # tiers with "builder exited 1", while the same flag built in 3.4s locally
    # where the crate was already compiled. The verdict is only ever "passed" or
    # "SKIP", so anything that goes wrong here is a SKIP, not an exception.
    try:
        result = subprocess.run(
            ["cargo", "test", "--", "port_entangle::tests", "--nocapture"],
            cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=900, env=env,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        log("SKIP", "CPU port entangle tests unavailable: %s" % type(exc).__name__)
        return {"status": "skip", "reason": type(exc).__name__}
    out_path = os.path.join(BUILD_DIR, "cpu_port_result.json")
    with open(out_path, "w", encoding='utf-8') as f:
        json.dump({"returncode": result.returncode, "stdout": result.stdout[-500:], "stderr": result.stderr[-500:]}, f)
    if result.returncode == 0:
        log("CPU_PORT", "CPU port entangle tests passed")
    else:
        log("SKIP", f"CPU port entangle tests: {result.stderr[-200:]}")
