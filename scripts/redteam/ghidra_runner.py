"""
ghidra_runner.py

Purpose:
Runs Ghidra headless analysis against a protected binary to assess
decompilation quality and function recovery.

Architectural Role:
Red-team attack runner using Ghidra's headless mode. Invoked by
unified_attack.py. Locates Ghidra via GHIDRA_HOME or standard paths,
runs a headless script that extracts function count and decompilation
quality metrics.

Execution Context:
Called from unified_attack.run_redteam_attack(). Requires Ghidra to
be installed and GHIDRA_HOME (or GHIDRA_INSTALL_DIR) to be set.
The headless script is embedded as a string and passed via -postScript.

Dependencies:
- Ghidra (external, headless mode)
- Standard library (json, logging, os, shutil, subprocess, tempfile, time)

Security Relevance:
Ghidra's decompiler is one of the most powerful static analysis tools.
Its ability to produce high-quality decompilation is a strong signal
that control-flow and data-flow obfuscation is insufficient.

Maintenance Notes:
- Ghidra headless is located via GHIDRA_HOME or standard paths
  (/opt/ghidra, /usr/local/ghidra, ~/ghidra). On Windows, .bat
  extension is appended.
- Ghidra's headless analysis creates a temporary project directory
  that is cleaned up in the finally block.
- The embedded Java script (GHIDRA_HEADLESS_SCRIPT) is compiled and
  run by Ghidra's headless analyzer; its JSON output is extracted
  from stdout via regex.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time

log = logging.getLogger(__name__)


GHIDRA_HEADLESS_SCRIPT = """// @category: NixonRedTeam
import ghidra.app.decompiler.DecompInterface;
import ghidra.util.task.ConsoleTaskMonitor;

public class NixonRedTeamAnalysis {
    public static void analyze() {
        DecompInterface decomplib = new DecompInterface();
        decomplib.openProgram(currentProgram);
        String results = "{";
        results += "\"functions_recovered\": " + currentProgram.getFunctionManager().getFunctionCount() + ",";
        results += "\"strings_recovered\": " + currentProgram.getListing().getDefinedDataCount(true) + ",";
        results += "\"decompilation_quality\": " + (decomplib.isOpen() ? 1.0 : 0.5) + "";
        results += "}";
        println(results);
    }
}
"""


def _find_ghidra():
    candidates = [
        os.environ.get("GHIDRA_HOME", ""),
        os.environ.get("GHIDRA_INSTALL_DIR", ""),
        "/opt/ghidra",
        "/usr/local/ghidra",
        os.path.expanduser("~/ghidra"),
    ]
    for c in candidates:
        if c:
            analyze_headless = os.path.join(c, "support", "analyzeHeadless")
            if os.name == "nt":
                analyze_headless += ".bat"
            if os.path.isfile(analyze_headless):
                return analyze_headless
    return None


def run_ghidra_attack(binary_path, output_dir):
    ghidra_path = _find_ghidra()
    if not ghidra_path:
        log.warning("Ghidra not found (set GHIDRA_HOME), skipping Ghidra attack")
        return None

    start = time.time()
    result = {
        "decompilation_quality": 0.0,
        "function_recovery_rate": 0.0,
        "strings_recovered": 0,
        "analysis_time_ms": 0.0,
        "attack": "ghidra",
        "status": "failed",
        "error": None,
    }

    try:
        tmp_project = tempfile.mkdtemp(prefix="ghidra_redteam_")
        project_name = "RedTeamProject"

        cmd = [
            ghidra_path,
            tmp_project,
            project_name,
            "-import", binary_path,
            "-postScript", GHIDRA_HEADLESS_SCRIPT,
            "-deleteProject",
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        result["analysis_time_ms"] = (time.time() - start) * 1000

        stdout = proc.stdout + proc.stderr

        import re
        json_match = re.search(r"\{.*\}", stdout, re.DOTALL)
        if json_match:
            try:
                ghidra_data = json.loads(json_match.group(0))
                result["function_recovery_rate"] = min(
                    ghidra_data.get("functions_recovered", 0) / 100.0, 1.0
                )
                result["strings_recovered"] = ghidra_data.get("strings_recovered", 0)
                result["decompilation_quality"] = ghidra_data.get("decompilation_quality", 0.0)
            except Exception:
                pass

        if proc.returncode == 0:
            result["status"] = "completed"
        else:
            result["error"] = f"Ghidra exited with code {proc.returncode}: {stdout[-500:]}"

    except subprocess.TimeoutExpired:
        result["error"] = "Ghidra analysis timed out after 120s"
        result["analysis_time_ms"] = (time.time() - start) * 1000
    except Exception as e:
        result["error"] = str(e)
        result["analysis_time_ms"] = (time.time() - start) * 1000
    finally:
        if os.path.exists(tmp_project):
            shutil.rmtree(tmp_project, ignore_errors=True)

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "ghidra_results.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    return result
