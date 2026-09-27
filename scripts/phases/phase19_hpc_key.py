"""
phase19_hpc_key.py

Purpose:
Runs HPC-based key derivation tests.  Validates that keys mixed from
hardware counter values are deterministic under same parameters and
differ across seeds/emulators (Item 121).

Architectural Role:
Validation phase — runs cargo tests for the HPC key derivation subsystem.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, subprocess, ..common

Security Relevance:
HPC-derived keys bind cryptographic keys to the specific hardware
environment, making key extraction useless on different machines.
"""

import json
import os
import subprocess

from ..common import log, BUILD_DIR

RUNTIME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "runtime")


def phase_hpc_key():
    """
    Run HPC key derivation tests from the runtime crate.

    Returns:
        dict with test results written to BUILD_DIR
    """
    log("HPC_KEY", "Running HPC-based key derivation (Item 121)")
    results = {"phase": "hpc_key", "status": "ok", "tests": []}
    tests = [
        "hpc_key::tests::test_mix_key_deterministic_same_params",
        "hpc_key::tests::test_mix_key_different_seeds",
        "hpc_key::tests::test_mix_key_not_identity",
        "hpc_key::tests::test_mix_key_emulator_differs",
        "hpc_key::tests::test_derive_key_from_hpc_attempt",
        "hpc_key::tests::test_compute_key_delta_returns_value",
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
                log("HPC_KEY", f"  {test}: ok")
            else:
                log("HPC_KEY", f"  {test}: FAIL")
                results["status"] = "partial"
        except Exception as e:
            log("HPC_KEY", f"  {test}: error: {e}")
            results["tests"].append({"name": test, "ok": False, "error": str(e)})
            results["status"] = "partial"
    out_path = os.path.join(BUILD_DIR, "phase19_hpc_key.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    log("HPC_KEY", f"Results written to {out_path}")
