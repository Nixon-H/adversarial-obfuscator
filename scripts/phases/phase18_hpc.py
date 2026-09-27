"""
phase18_hpc.py

Purpose:
Runs hardware performance counter (HPC) integration tests from the
Rust runtime.  Validates that RDTSC, PMC reading, LFSR stepping,
cache priming, and access patterns work correctly (Item 120).

Architectural Role:
Validation phase — runs cargo tests for the HPC subsystem and records
results.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, subprocess, ..common

Security Relevance:
HPC integration is the foundation for timing-based protections
(entropy gathering, emulator detection, key derivation).
"""

import json
import os
import subprocess

from ..common import log, BUILD_DIR

RUNTIME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "runtime")


def phase_hpc(ir_output=None, obfuscated_output=None):
    """
    Run HPC integration tests from the runtime crate.

    Args:
        ir_output: optional IR path (unused)
        obfuscated_output: optional obfuscated path (unused)

    Returns:
        dict with phase results written to BUILD_DIR
    """
    log("HPC", "Running hardware performance counter integration (Item 120)")
    results = {"phase": "hpc", "status": "ok", "tests": []}
    tests = [
        "hpc::tests::test_read_tsc_returns_value",
        "hpc::tests::test_read_tsc_monotonic",
        "hpc::tests::test_read_pmc_attempt",
        "hpc::tests::test_lfsr_step_does_not_stall",
        "hpc::tests::test_prime_cache_pattern_does_not_crash",
        "hpc::tests::test_execute_access_pattern_does_not_crash",
        "hpc::tests::test_expected_counter_value_deterministic",
        "hpc::tests::test_expected_counter_value_different_seeds",
        "hpc::tests::test_read_l2_cache_misses_attempt",
        "hpc::tests::test_read_branch_mispredictions_attempt",
    ]
    for test in tests:
        try:
            r = subprocess.run(
                ["cargo", "test", "--", test, "--nocapture"],
                cwd=RUNTIME_DIR, capture_output=True, text=True, timeout=60,
            )
            ok = r.returncode == 0
            results["tests"].append({"name": test, "ok": ok})
            if ok:
                log("HPC", f"  {test}: ok")
            else:
                log("HPC", f"  {test}: FAIL")
                results["status"] = "partial"
        except Exception as e:
            log("HPC", f"  {test}: error: {e}")
            results["tests"].append({"name": test, "ok": False, "error": str(e)})
            results["status"] = "partial"
    out_path = os.path.join(BUILD_DIR, "phase18_hpc.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    log("HPC", f"Results written to {out_path}")
