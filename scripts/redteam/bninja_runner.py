"""
bninja_runner.py

Purpose:
Runs Binary Ninja analysis against a protected binary to assess
function recovery and string extraction capabilities.

Architectural Role:
Red-team attack runner using Binary Ninja's commercial analysis engine.
Invoked by unified_attack.py. Produces a JSON result with function
count and recovered strings.

Execution Context:
Called from unified_attack.run_redteam_attack(). Requires the
binaryninja Python package (commercial, requires license).
If unavailable, returns None gracefully.

Dependencies:
- binaryninja (optional, third-party, commercial)
- Standard library (json, logging, os, time)

Security Relevance:
Binary Ninja's function detection rate measures how well the
obfuscation hides function boundaries. A high function count suggests
the obfuscator's function-hiding techniques are ineffective.

Maintenance Notes:
- Binary Ninja's API uses BinaryViewType.get_view_of_file() to load
  binaries, which may fail for non-standard formats.
- Strings are extracted from bv.strings (Binary Ninja's built-in
  string detection), limited to the first 100 results.
"""

import json
import logging
import os
import time

log = logging.getLogger(__name__)


def run_binaryninja_attack(binary_path, output_dir):
    """
    Run Binary Ninja analysis against a protected binary.

    Loads the binary with BinaryViewType.get_view_of_file(), updates
    analysis, counts functions, and extracts strings. Writes results
    to output_dir/bninja_results.json. Returns the result dict, or
    None if Binary Ninja is not installed.
    """
    try:
        import binaryninja
    except ImportError:
        log.warning("binaryninja not installed, skipping Binary Ninja attack")
        return None

    start = time.time()
    result = {
        "function_count": 0,
        "string_count": 0,
        "strings_recovered": [],
        "analysis_complete": False,
        "analysis_time_ms": 0.0,
        "attack": "binaryninja",
        "status": "failed",
        "error": None,
    }

    try:
        bv = binaryninja.BinaryViewType.get_view_of_file(binary_path)
        bv.update_analysis()

        result["function_count"] = len(list(bv.functions))
        result["analysis_complete"] = True

        strings = []
        for s in bv.strings:
            try:
                val = str(s.value)
                if len(val) >= 3:
                    strings.append(val)
            except Exception:
                pass
        result["string_count"] = len(strings)
        result["strings_recovered"] = strings[:100]

        result["status"] = "completed"

    except Exception as e:
        result["error"] = str(e)

    result["analysis_time_ms"] = (time.time() - start) * 1000

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "bninja_results.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    return result
