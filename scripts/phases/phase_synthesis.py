"""
phase_synthesis.py

Purpose:
Protection Synthesis Engine — automatically selects an optimal set of
protections based on a target security score, maximum overhead, and
maximum size multiplier.  Uses a cost-benefit optimization to recommend
a ProtectionPlan.

Architectural Role:
Configuration/optimization phase — can optionally apply the plan's
CLI flags to the running pipeline.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, datetime, scripts.common, scripts.synthesis

Security Relevance:
Synthesis prevents both under-protection (gaps) and over-protection
(unnecessary overhead) by optimizing the protection set.
"""

from __future__ import annotations

import json
import os
import datetime

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.synthesis import (
    SynthesisEngine,
    ProtectionPlan,
    optimize_protections,
    plan_to_cli_args,
    PROTECTION_COSTS,
)


def phase_synthesis(args) -> ProtectionPlan:
    """
    Run the protection synthesis engine to recommend optimal protections.

    Args:
        args: argparse.Namespace

    Returns:
        ProtectionPlan or None if disabled
    """
    enabled = getattr(args, "synthesis", False)
    if not enabled:
        log("SYNTHESIS", "Protection synthesis disabled (use --synthesis to enable)")
        return None

    target_security = getattr(args, "synthesis_target_security", 70.0)
    max_overhead = getattr(args, "synthesis_max_overhead", 50.0)
    max_size = getattr(args, "synthesis_max_size", 3.0)
    output_path = getattr(args, "synthesis_output", None)

    log("SYNTHESIS", f"Target security: {target_security}/100")
    log("SYNTHESIS", f"Max overhead: {max_overhead}%")
    log("SYNTHESIS", f"Max size multiplier: {max_size}x")

    engine = SynthesisEngine()
    engine.load_protection_costs()

    plan = engine.solve_optimization(target_security, max_overhead, max_size)

    report = engine.generate_report(plan)
    print(report)

    report_data = {
        "timestamp": plan.timestamp,
        "target_security": target_security,
        "max_overhead": max_overhead,
        "max_size": max_size,
        "protections": plan.protections,
        "expected_security_score": plan.expected_security_score,
        "expected_overhead": plan.expected_overhead,
        "expected_size_multiplier": plan.expected_size_multiplier,
        "flags": plan.flags,
        "rationale": plan.rationale,
    }

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        atomic_write(output_path, json.dumps(report_data, indent=2))
        log("SYNTHESIS", f"Report written to {output_path}")
    else:
        default_path = os.path.join(BUILD_DIR, "synthesis_report.json")
        os.makedirs(BUILD_DIR, exist_ok=True)
        atomic_write(default_path, json.dumps(report_data, indent=2))
        log("SYNTHESIS", f"Report written to {default_path}")

    apply_synthesis = getattr(args, "apply_synthesis", False)
    if apply_synthesis:
        log("SYNTHESIS", "Applying synthesis plan to pipeline configuration...")
        cli_args = plan_to_cli_args(plan)
        log("SYNTHESIS", f"Generated CLI flags: {' '.join(cli_args)}")
        synthesis_apply_path = os.path.join(BUILD_DIR, "synthesis_plan_flags.json")
        atomic_write(synthesis_apply_path, json.dumps({
            "cli_args": cli_args,
            "plan": report_data,
        }, indent=2))
        log("SYNTHESIS", f"Plan flags written to {synthesis_apply_path}")

    return plan
