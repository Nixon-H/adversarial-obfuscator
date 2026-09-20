"""
phase21_hw_entropy.py

Purpose:
Runs hardware entropy loop tests.  Validates that entropy is collected
from RDTSC jitter, cache misses, and branch mispredictions, and that
the feedback loop integrates and produces protection keys (Item 123).

Architectural Role:
Validation phase — runs cargo tests for the hardware entropy subsystem.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, subprocess, ..common

Security Relevance:
Hardware entropy is the root of trust for all runtime-generated keys
used by other protection layers.
"""

import json
import os
import subprocess

from ..common import log, BUILD_DIR

RUNTIME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "runtime")


def phase_hw_entropy():
    """
    Run hardware entropy collection tests from the runtime crate.

    Returns:
        dict with test results written to BUILD_DIR
    """
    log("HW_ENTROPY", "Running hardware entropy loop (Item 123)")
    log("HW_ENTROPY", "Running hardware entropy loop (Item 123)")
    results = {"phase": "hw_entropy", "status": "ok", "tests": []}
    tests = [
        "hw_entropy::tests::test_collects_rdtsc_jitter",
        "hw_entropy::tests::test_cache_miss_entropy",
        "hw_entropy::tests::test_branch_miss_entropy",
        "hw_entropy::tests::test_feedback_loop_integrates",
        "hw_entropy::tests::test_collect_all_produces_entropy",
        "hw_entropy::tests::test_feed_forward_changes_key",
        "hw_entropy::tests::test_derive_protection_key_changes",
        "hw_entropy::tests::test_pool_accumulates",
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
                log("HW_ENTROPY", f"  {test}: ok")
            else:
                log("HW_ENTROPY", f"  {test}: FAIL")
                results["status"] = "partial"
        except Exception as e:
            log("HW_ENTROPY", f"  {test}: error: {e}")
            results["tests"].append({"name": test, "ok": False, "error": str(e)})
            results["status"] = "partial"
    out_path = os.path.join(BUILD_DIR, "phase21_hw_entropy.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    log("HW_ENTROPY", f"Results written to {out_path}")
