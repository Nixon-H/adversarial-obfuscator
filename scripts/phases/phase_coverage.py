"""
phase_coverage.py

Purpose:
Generates a protection coverage map — a detailed report of which
protections have been applied to each function in the IR module.
Outputs JSON, HTML, and text formats.

Architectural Role:
Measurement/audit phase — runs after all protections to verify coverage.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, ..common, ..coverage.*

Security Relevance:
Coverage maps reveal gaps in protection — functions or regions that
were not obfuscated or transformed.
"""

from __future__ import annotations

import json
import os

from ..common import log, BUILD_DIR
from ..coverage.coverage_map import generate_coverage_map, coverage_to_json, coverage_to_html, coverage_to_text
from ..coverage.pipeline_tracker import PipelineTracker  # noqa: F401 (this line binds a name used by an embedded template)


def phase_coverage(args, ir_module, pipeline_state=None):
    """
    Generate a protection coverage map for the IR module.

    Args:
        args: argparse.Namespace
        ir_module: IrModule from compile_py_to_ir
        pipeline_state: optional PipelineTracker state

    Returns:
        CoverageMap or None if disabled
    """
    enabled = getattr(args, "coverage_map", False)
    if not enabled:
        log("COVERAGE", "Protection coverage map disabled (use --coverage-map to enable)")
        return None

    if ir_module is None:
        log("COVERAGE", "No IR module available, skipping coverage generation")
        return None

    output_dir = getattr(args, "coverage_output", os.path.join(BUILD_DIR, "coverage"))
    os.makedirs(output_dir, exist_ok=True)

    log("COVERAGE", "Generating protection coverage map...")
    coverage_map = generate_coverage_map(ir_module, pipeline_state)

    json_path = os.path.join(output_dir, "protection_coverage.json")
    json_data = coverage_to_json(coverage_map)
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    log("COVERAGE", f"JSON coverage map → {json_path}")

    html_path = os.path.join(output_dir, "protection_coverage.html")
    html_data = coverage_to_html(coverage_map)
    with open(html_path, "w") as f:
        f.write(html_data)
    log("COVERAGE", f"HTML coverage report → {html_path}")

    txt_path = os.path.join(output_dir, "protection_coverage.txt")
    txt_data = coverage_to_text(coverage_map)
    with open(txt_path, "w") as f:
        f.write(txt_data)
    log("COVERAGE", f"Text coverage summary → {txt_path}")

    print()
    print("=" * 60)
    print("  PROTECTION COVERAGE MAP")
    print("=" * 60)
    print(txt_data)
    print("=" * 60)
    print()

    return coverage_map
