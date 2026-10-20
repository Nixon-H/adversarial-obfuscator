"""
angr_runner.py

Purpose:
Runs angr-based symbolic analysis against a protected binary to assess
CFG recovery success, string extraction, and symbolic path exploration.

Architectural Role:
One of five red-team attack runners. Invoked by unified_attack.py.
Produces a JSON result file used by the attack report to compute the
combined security score and identify weaknesses.

Execution Context:
Called from unified_attack.run_redteam_attack(). Requires angr to be
installed (pip install angr). If unavailable, returns None gracefully.

Dependencies:
- angr (optional, third-party)
- Standard library (json, logging, os, time)

Security Relevance:
angr's CFGFast recovery rate directly measures the effectiveness of
control-flow obfuscation. If angr can reconstruct the CFG, the
obfuscation is insufficient. Symbolic path count measures opaque
predicate and bogus exception effectiveness.

Maintenance Notes:
- The bounded symbolic execution runs only 10 steps for performance.
- Strings are extracted from .rodata, .strtab, and .text sections;
  section names use bytes (b".rodata") for Python 3 compatibility.
"""

import json
import logging
import os
import time

log = logging.getLogger(__name__)


def run_angr_attack(binary_path, output_dir):
    """
    Run angr CFG recovery and symbolic execution against a binary.

    Analyses: CFG reconstruction (CFGFast), function recovery, string
    extraction from rodata/strtab/text sections, and bounded symbolic
    execution (10 steps). Writes results to output_dir/angr_results.json.
    Returns the result dict, or None if angr is not installed.
    """
    try:
        import angr
    except ImportError:
        log.warning("angr not installed, skipping angr attack")
        return None

    start = time.time()
    result = {
        "cfg_recovered": False,
        "num_functions_found": 0,
        "strings_recovered": [],
        "symbolic_paths": 0,
        "success_rate": 0.0,
        "analysis_time_ms": 0.0,
        "attack": "angr",
        "status": "failed",
        "error": None,
    }

    try:
        proj = angr.Project(binary_path, auto_load_libs=False)

        cfg = proj.analyses.CFGFast()
        result["cfg_recovered"] = True
        result["num_functions_found"] = len(cfg.functions)

        try:
            strings = []
            for sec in proj.loader.main_object.sections:
                if sec.name in (b".rodata", b".strtab", b".text"):
                    data = sec.data()
                    decoded = []
                    i = 0
                    while i < len(data):
                        end = data.find(b"\x00", i)
                        if end == -1 or end - i < 4:
                            i = end + 1 if end != -1 else len(data)
                            continue
                        try:
                            s = data[i:end].decode("utf-8", errors="replace")
                            if len(s) >= 4 and all(32 <= ord(c) < 127 or c in "\n\r\t" for c in s):
                                decoded.append(s)
                        except Exception:
                            pass
                        i = end + 1
                    strings.extend(decoded)
            result["strings_recovered"] = strings[:100]
        except Exception:
            result["strings_recovered"] = []

        try:
            start_addr = proj.entry
            if start_addr:
                state = proj.factory.entry_state(
                    add_options=angr.options.unicorn,
                    remove_options={angr.options.LAZY_SOLVES},
                )
                simgr = proj.factory.simulation_manager(state)
                simgr.run(n=10)
                result["symbolic_paths"] = len(simgr.active) + len(simgr.deadended)
        except Exception:
            result["symbolic_paths"] = 0

        recovered = len(result["strings_recovered"])
        result["success_rate"] = min(recovered / 100.0, 1.0) * 0.3
        if result["cfg_recovered"]:
            result["success_rate"] += 0.4
        result["success_rate"] += min(result["symbolic_paths"] / 10.0, 1.0) * 0.3
        result["status"] = "completed"

    except Exception as e:
        result["error"] = str(e)

    result["analysis_time_ms"] = (time.time() - start) * 1000

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "angr_results.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    return result
