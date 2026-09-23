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
        # APPLY (not just record): merge the plan's protections + flags
        # into the live argparse namespace so DOWNSTREAM phases (Stage 1
        # obfuscation honors cfg_flatten/mba/etc. via phase01's no-* loop;
        # boolean flags enable their features) actually change. Idempotent:
        # only sets attributes that are currently falsy/empty, never
        # downgrades an explicit user flag. The sidecar JSON is still
        # written for auditability.
        try:
            from scripts.synthesis.engine import ProtectionPlan as _PP
            _applied = []
            for _p in list(getattr(plan, "protections", []) or []):
                _dest = str(_p).replace("-", "_")
                try:
                    if not getattr(args, _dest, False):
                        setattr(args, _dest, True)
                        _applied.append("--" + str(_p).replace("_", "-"))
                except Exception:
                    continue
            for _flag, _val in dict(getattr(plan, "flags", {}) or {}).items():
                _dest = str(_flag).replace("-", "_")
                try:
                    _cur = getattr(args, _dest, None)
                    if _cur in (None, False, "", 0, 0.0):
                        setattr(args, _dest, _val)
                        _applied.append("--%s=%r" % (_flag, _val))
                except Exception:
                    continue
            if _applied:
                log("SYNTHESIS", f"Applied to live config: {' '.join(_applied)}")
            else:
                log("SYNTHESIS", "Live config already satisfied plan (no changes)")
        except Exception as _apply_err:
            log("SYNTHESIS", f"Live apply failed (non-fatal, sidecar kept): {_apply_err}")
        synthesis_apply_path = os.path.join(BUILD_DIR, "synthesis_plan_flags.json")
        atomic_write(synthesis_apply_path, json.dumps({
            "cli_args": cli_args,
            "plan": report_data,
        }, indent=2))
        log("SYNTHESIS", f"Plan flags written to {synthesis_apply_path}")

    return plan
