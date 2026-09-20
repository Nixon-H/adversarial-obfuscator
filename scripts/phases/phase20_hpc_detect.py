"""
phase20_hpc_detect.py

Purpose:
Runs emulator detection via HPC tests.  Validates that the runtime can
detect emulation/virtualization using RDTSCP, CPUID hypervisor bit,
and branch misprediction rates (Item 122).

Architectural Role:
Validation phase — runs cargo tests for the HPC detection subsystem.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, subprocess, ..common

Security Relevance:
Emulator detection allows the payload to alter behavior when run inside
analysis environments (sandbox evasion).
"""

import json
import os
import subprocess

from ..common import log, BUILD_DIR

RUNTIME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "runtime")


def phase_hpc_detect():
    """
    Run emulator detection via HPC tests from the runtime crate.

    Returns:
        dict with test results written to BUILD_DIR
    """
    log("HPC_DETECT", "Running emulator detection via HPC (Item 122)")
    log("HPC_DETECT", "Running emulator detection via HPC (Item 122)")
    results = {"phase": "hpc_detect", "status": "ok", "tests": []}
    tests = [
        "hpc_detect::tests::test_detect_emulator_runs",
        "hpc_detect::tests::test_rdtscp_returns_value",
        "hpc_detect::tests::test_rdtscp_tsc_related_to_rdtsc",
        "hpc_detect::tests::test_cpuid_hypervisor_bit_check",
        "hpc_detect::tests::test_branch_mispredict_rate_abnormal_runs",
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
                log("HPC_DETECT", f"  {test}: ok")
            else:
                log("HPC_DETECT", f"  {test}: FAIL")
                results["status"] = "partial"
        except Exception as e:
            log("HPC_DETECT", f"  {test}: error: {e}")
            results["tests"].append({"name": test, "ok": False, "error": str(e)})
            results["status"] = "partial"
    out_path = os.path.join(BUILD_DIR, "phase20_hpc_detect.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    log("HPC_DETECT", f"Results written to {out_path}")
