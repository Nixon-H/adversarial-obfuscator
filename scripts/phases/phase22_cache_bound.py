"""
phase22_cache_bound.py

Purpose:
Runs cache-bound execution tests.  Validates that cache priming changes
CPU state, execution depends on cache state, and different CPUs fail
verification (Item 124).

Architectural Role:
Validation phase — runs cargo tests for the cache-bound execution subsystem.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, subprocess, ..common

Security Relevance:
Cache-bound execution ties code to a specific CPU cache state,
defeating cross-CPU replay and cloning attacks.
"""

import json
import os
import subprocess

from ..common import log, BUILD_DIR

RUNTIME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "runtime")


def phase_cache_bound():
    """
    Run cache-bound execution tests from the runtime crate.

    Returns:
        dict with test results written to BUILD_DIR
    """
    log("CACHE_BOUND", "Running cache-bound execution (Item 124)")
    log("CACHE_BOUND", "Running cache-bound execution (Item 124)")
    results = {"phase": "cache_bound", "status": "ok", "tests": []}
    tests = [
        "cache_bound::tests::test_cache_priming_changes_state",
        "cache_bound::tests::test_execution_depends_on_cache",
        "cache_bound::tests::test_different_cpu_fails",
        "cache_bound::tests::test_priming_deterministic",
        "cache_bound::tests::test_execute_critical_runs",
        "cache_bound::tests::test_cache_bound_hash_deterministic",
        "cache_bound::tests::test_cache_bound_hash_different_inputs",
        "cache_bound::tests::test_verify_cache_state_on_new",
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
                log("CACHE_BOUND", f"  {test}: ok")
            else:
                log("CACHE_BOUND", f"  {test}: FAIL")
                results["status"] = "partial"
        except Exception as e:
            log("CACHE_BOUND", f"  {test}: error: {e}")
            results["tests"].append({"name": test, "ok": False, "error": str(e)})
            results["status"] = "partial"
    out_path = os.path.join(BUILD_DIR, "phase22_cache_bound.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    log("CACHE_BOUND", f"Results written to {out_path}")
