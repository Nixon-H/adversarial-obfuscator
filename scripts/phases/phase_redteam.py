"""
phase_redteam.py

Purpose:
Runs the autonomous red-team pipeline — launches multiple deobfuscation
attacks (angr, Ghidra, Binary Ninja, LLM-based, symbolic execution)
against the protected binary and returns a combined security score.

Architectural Role:
Adversarial evaluation phase — tests protection effectiveness.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, time, ..common, scripts.redteam.unified_attack

Security Relevance:
Red-team testing provides the most realistic measure of protection
strength by simulating actual attacker tooling.
"""

import json
import os
import time

from ..common import log as pipeline_log, BUILD_DIR


def phase_redteam(args, binary_path, source_path):
    """
    Launch the autonomous red-team attack suite against the protected binary.

    Args:
        args: argparse.Namespace
        binary_path: path to the protected binary
        source_path: path to the original source

    Returns:
        RedTeamReport or None on failure
    """
    pipeline_log("REDTEAM", "Starting autonomous red team pipeline...")
    pipeline_log("REDTEAM", "Starting autonomous red team pipeline...")

    # Anchor relative output dirs at BUILD_DIR so CWD-independent invocation works.
    from ..common import ROOT as _ROOT
    _raw_out = getattr(args, "red_team_output", None) or os.path.join(BUILD_DIR, "redteam")
    if os.path.isabs(_raw_out):
        output_dir = _raw_out
    elif _raw_out == os.path.join("build", "redteam"):
        output_dir = os.path.join(BUILD_DIR, "redteam")
    else:
        output_dir = os.path.join(_ROOT, _raw_out)
    os.makedirs(output_dir, exist_ok=True)

    try:
        from scripts.redteam.unified_attack import run_redteam_attack

        report = run_redteam_attack(args)

        summary = {
            "combined_security_score": report.combined_security_score,
            "weakest_link": report.weakest_link,
            "attacks_completed": sum(
                1 for r in [
                    report.angr_result,
                    report.ghidra_result,
                    report.bninja_result,
                    report.llm_result,
                    report.symbolic_result,
                ] if r is not None and r.get("status") == "completed"
            ),
            "attack_times_ms": report.attack_times_ms,
            "recommendations": report.recommendations,
            "timestamp": time.time(),
        }

        summary_path = os.path.join(output_dir, "redteam_summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        pipeline_log("REDTEAM", f"Red team summary → {summary_path}")
        # combined_security_score is None when no attack completed
        # (fail-closed: unknown, not 50.0) — never format blindly.
        if report.combined_security_score is None:
            pipeline_log("REDTEAM", "Security score: n/a (no attacks completed)")
        else:
            pipeline_log("REDTEAM", f"Security score: {report.combined_security_score:.1f}/100")
        pipeline_log("REDTEAM", f"Weakest link: {report.weakest_link}")
        pipeline_log("REDTEAM", f"Recommendations: {len(report.recommendations)}")

        return report
    except ImportError as e:
        pipeline_log("REDTEAM", f"Red team modules not available: {e}")
        return None
    except Exception as e:
        pipeline_log("REDTEAM", f"Red team attack failed: {e}")
        import traceback
        traceback.print_exc()
        return None
