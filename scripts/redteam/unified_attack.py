"""
unified_attack.py

Purpose:
Orchestrates the autonomous red-team attack pipeline. Runs all
configured attack tools (angr, Ghidra, Binary Ninja, LLM, symbolic)
against a protected binary/source and produces a combined security
score, weakest-link analysis, and remediation recommendations.

Architectural Role:
Central orchestrator for the red-team module. Accepts command-line
args via RedTeamConfig, dispatches each attack runner, aggregates
results into a RedTeamReport, computes scores, and writes the report
to disk. Called by the build pipeline after protection is applied.

Execution Context:
Invoked from scripts/build.py when --red-team is set. Each runner
runs sequentially with a configurable per-attack timeout (default 300s).

Dependencies:
- angr_runner, ghidra_runner, bninja_runner, llm_runner, symbolic_runner
- scripts.common for pipeline logging

Security Relevance:
This is the 'adversarial oracle' — it simulates what a real attacker
would do. The combined security score is a key gating metric used by
the security regression gates. If the score drops below threshold,
the build fails.

Maintenance Notes:
- Adding a new runner requires adding it to RedTeamConfig.attacks_to_run,
  the dispatch block in run_redteam_attack(), _compute_security_score(),
  _find_weakest_link(), and _generate_recommendations().
- Security scores are inverse (lower = more secure). The combined
  score inverts this to 0-100 where higher = more secure.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

from scripts.common import log as pipeline_log

from .angr_runner import run_angr_attack
from .ghidra_runner import run_ghidra_attack
from .bninja_runner import run_binaryninja_attack
from .llm_runner import run_llm_attack
from .symbolic_runner import run_symbolic_attack

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


@dataclass
class RedTeamConfig:
    """
    Configuration for the red-team attack pipeline.

    Specifies the binary/source paths, which attacks to run, and
    the per-attack timeout. Defaults to running all five attack types.
    """
    output_dir: str = "build/redteam"
    binary_path: Optional[str] = None
    source_path: Optional[str] = None
    attacks_to_run: list = field(default_factory=lambda: ["angr", "ghidra", "bninja", "llm", "symbolic"])
    timeout_per_attack: int = 300


@dataclass
class RedTeamReport:
    """
    Aggregated results from all red-team attack runners.

    Stores per-attack results, the combined security score
    (0-100, higher = more secure), the weakest attack vector,
    and generated remediation recommendations.
    """
    angr_result: Optional[dict] = None
    ghidra_result: Optional[dict] = None
    bninja_result: Optional[dict] = None
    llm_result: Optional[dict] = None
    symbolic_result: Optional[dict] = None
    combined_security_score: float = 0.0
    weakest_link: str = ""
    recommendations: list = field(default_factory=list)
    attack_times_ms: dict = field(default_factory=dict)
    timestamp: float = 0.0

    def to_dict(self):
        """
        Serialize the report to a dict with report type metadata.
        """
        d = asdict(self)
        d["report_type"] = "autonomous_red_team"
        d["timestamp"] = self.timestamp or time.time()
        return d


def run_redteam_attack(args):
    """
    Run the full red-team attack pipeline.

    Accepts an argparse.Namespace (or any object with matching attrs)
    containing red_team_output, binary_path, payload, attacks_to_run,
    and timeout_per_attack. Dispatches each attack, computes the
    combined score, and writes the report to the output directory.
    Returns the RedTeamReport.
    """
    cfg = RedTeamConfig(
        output_dir=args.red_team_output if hasattr(args, "red_team_output") else "build/redteam",
        binary_path=args.binary_path if hasattr(args, "binary_path") and args.binary_path else None,
        source_path=args.payload if hasattr(args, "payload") else None,
        attacks_to_run=args.attacks_to_run if hasattr(args, "attacks_to_run") else ["angr", "ghidra", "bninja", "llm", "symbolic"],
        timeout_per_attack=getattr(args, "timeout_per_attack", 300),
    )

    os.makedirs(cfg.output_dir, exist_ok=True)

    binary_path = cfg.binary_path

    report = RedTeamReport(timestamp=time.time())

    attack_times = {}

    if "angr" in cfg.attacks_to_run:
        pipeline_log("REDTEAM", "Running angr analysis...")
        t0 = time.time()
        report.angr_result = run_angr_attack(binary_path, cfg.output_dir)
        attack_times["angr"] = (time.time() - t0) * 1000
        if report.angr_result:
            pipeline_log("REDTEAM", f"  angr: cfg={report.angr_result.get('cfg_recovered')}, "
                        f"functions={report.angr_result.get('num_functions_found')}, "
                        f"paths={report.angr_result.get('symbolic_paths')}")
        else:
            pipeline_log("REDTEAM", "  angr: skipped (not available)")

    if "ghidra" in cfg.attacks_to_run:
        pipeline_log("REDTEAM", "Running Ghidra analysis...")
        t0 = time.time()
        report.ghidra_result = run_ghidra_attack(binary_path, cfg.output_dir)
        attack_times["ghidra"] = (time.time() - t0) * 1000
        if report.ghidra_result:
            pipeline_log("REDTEAM", f"  Ghidra: decomp={report.ghidra_result.get('decompilation_quality')}, "
                        f"fn_recovery={report.ghidra_result.get('function_recovery_rate')}")
        else:
            pipeline_log("REDTEAM", "  Ghidra: skipped (not available)")

    if "bninja" in cfg.attacks_to_run:
        pipeline_log("REDTEAM", "Running Binary Ninja analysis...")
        t0 = time.time()
        report.bninja_result = run_binaryninja_attack(binary_path, cfg.output_dir)
        attack_times["bninja"] = (time.time() - t0) * 1000
        if report.bninja_result:
            pipeline_log("REDTEAM", f"  Binary Ninja: functions={report.bninja_result.get('function_count')}, "
                        f"strings={report.bninja_result.get('string_count')}")
        else:
            pipeline_log("REDTEAM", "  Binary Ninja: skipped (not available)")

    if "llm" in cfg.attacks_to_run:
        pipeline_log("REDTEAM", "Running LLM analysis...")
        source_path = cfg.source_path
        t0 = time.time()
        report.llm_result = run_llm_attack(source_path, cfg.output_dir)
        attack_times["llm"] = (time.time() - t0) * 1000
        if report.llm_result:
            pipeline_log("REDTEAM", f"  LLM: intent_recovered={report.llm_result.get('intent_recovered')}, "
                        f"confidence={report.llm_result.get('confidence_level')}, "
                        f"provider={report.llm_result.get('provider_used')}")
        else:
            pipeline_log("REDTEAM", "  LLM: skipped (no valid source/config)")

    if "symbolic" in cfg.attacks_to_run:
        pipeline_log("REDTEAM", "Running symbolic analysis...")
        t0 = time.time()
        report.symbolic_result = run_symbolic_attack(binary_path, cfg.output_dir)
        attack_times["symbolic"] = (time.time() - t0) * 1000
        if report.symbolic_result:
            pipeline_log("REDTEAM", f"  Symbolic: constraints_solved={report.symbolic_result.get('constraints_solved')}, "
                        f"paths={report.symbolic_result.get('path_count')}")
        else:
            pipeline_log("REDTEAM", "  Symbolic: skipped (not available)")

    report.attack_times_ms = attack_times
    report.combined_security_score = _compute_security_score(report)
    report.weakest_link = _find_weakest_link(report)
    report.recommendations = _generate_recommendations(report)

    report_dict = report.to_dict()
    out_path = os.path.join(cfg.output_dir, "attack_report.json")
    with open(out_path, "w") as f:
        json.dump(report_dict, f, indent=2, default=str)

    pipeline_log("REDTEAM", f"Attack report written to {out_path}")
    pipeline_log("REDTEAM", f"Combined security score: {report.combined_security_score:.1f}/100")
    pipeline_log("REDTEAM", f"Weakest link: {report.weakest_link}")

    return report


def _compute_security_score(report):
    """
    Compute a combined security score from all attack results.

    Each attack is scored 0-100 (higher = more secure). The overall
    score is the average of individual scores. Attacks that didn't
    run are excluded. Falls back to 50 if no attacks ran.
    """
    scores = []

    if report.angr_result:
        if report.angr_result.get("status") == "completed":
            s = (1.0 - report.angr_result.get("success_rate", 0)) * 100
            scores.append(s)

    if report.ghidra_result:
        if report.ghidra_result.get("status") == "completed":
            decomp = report.ghidra_result.get("decompilation_quality", 0)
            fn_rec = report.ghidra_result.get("function_recovery_rate", 0)
            s = (1.0 - (decomp * 0.6 + fn_rec * 0.4)) * 100
            scores.append(s)

    if report.bninja_result:
        if report.bninja_result.get("status") == "completed":
            fn_count = min(report.bninja_result.get("function_count", 0) / 50.0, 1.0)
            str_count = min(report.bninja_result.get("string_count", 0) / 20.0, 1.0)
            s = (1.0 - (fn_count * 0.5 + str_count * 0.5)) * 100
            scores.append(s)

    if report.llm_result:
        if report.llm_result.get("status") == "completed":
            conf = report.llm_result.get("confidence_level", 0)
            intent = 1.0 if report.llm_result.get("intent_recovered") else 0.0
            s = (1.0 - (conf * 0.7 + intent * 0.3)) * 100
            scores.append(s)

    if report.symbolic_result:
        if report.symbolic_result.get("status") == "completed":
            rec = report.symbolic_result.get("recovery_rate", 0)
            s = (1.0 - rec) * 100
            scores.append(s)

    if scores:
        return sum(scores) / len(scores)
    return 50.0


def _find_weakest_link(report):
    """
    Identify the attack vector that achieved the lowest security score.

    Returns the attack name ('angr', 'ghidra', etc.) or
    'no_attacks_ran' if none completed.
    """
    link_scores = {}

    if report.angr_result and report.angr_result.get("status") == "completed":
        link_scores["angr"] = (1.0 - report.angr_result.get("success_rate", 0)) * 100
    if report.ghidra_result and report.ghidra_result.get("status") == "completed":
        decomp = report.ghidra_result.get("decompilation_quality", 0)
        fn_rec = report.ghidra_result.get("function_recovery_rate", 0)
        link_scores["ghidra"] = (1.0 - (decomp * 0.6 + fn_rec * 0.4)) * 100
    if report.bninja_result and report.bninja_result.get("status") == "completed":
        fn_count = min(report.bninja_result.get("function_count", 0) / 50.0, 1.0)
        str_count = min(report.bninja_result.get("string_count", 0) / 20.0, 1.0)
        link_scores["bninja"] = (1.0 - (fn_count * 0.5 + str_count * 0.5)) * 100
    if report.llm_result and report.llm_result.get("status") == "completed":
        conf = report.llm_result.get("confidence_level", 0)
        link_scores["llm"] = (1.0 - conf) * 100
    if report.symbolic_result and report.symbolic_result.get("status") == "completed":
        link_scores["symbolic"] = (1.0 - report.symbolic_result.get("recovery_rate", 0)) * 100

    if not link_scores:
        return "no_attacks_ran"

    return min(link_scores, key=link_scores.get)


def _generate_recommendations(report):
    """
    Generate human-readable remediation recommendations based on
    attack results. Each attack that found a weakness produces one
    or more recommendations.
    """
    recommendations = []

    if report.angr_result and report.angr_result.get("cfg_recovered"):
        recommendations.append("STRENGTHEN CFG obfuscation: angr recovered control flow graph")
        if report.angr_result.get("symbolic_paths", 0) > 5:
            recommendations.append("REDUCE symbolic paths: angr found multiple execution paths")

    if report.ghidra_result and report.ghidra_result.get("decompilation_quality", 0) > 0.5:
        recommendations.append("IMPROVE decompilation resistance: Ghidra achieved high decompilation quality")

    if report.bninja_result and report.bninja_result.get("function_count", 0) > 20:
        recommendations.append("INCREASE function obfuscation: Binary Ninja recovered many functions")

    if report.llm_result and report.llm_result.get("intent_recovered"):
        recommendations.append("ADD intent obfuscation: LLM recovered original algorithm intent")
        recommendations.append(f"  Guessed algorithm: {report.llm_result.get('original_algorithm_guessed')}")

    if report.symbolic_result and report.symbolic_result.get("path_count", 0) > 0:
        recommendations.append("ADD opaque predicates: symbolic execution solved constraints")
        recommendations.append("INCREASE MBA complexity: Z3-based symbolic execution found paths")

    if report.angr_result is None and report.ghidra_result is None and report.bninja_result is None:
        recommendations.append("INSTALL deobfuscation tools (angr, Ghidra, Binary Ninja) for full red team coverage")
    if report.llm_result and report.llm_result.get("provider_used") is None:
        recommendations.append("CONFIGURE LLM API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, DEEPSEEK_API_KEY) for LLM-based deobfuscation")

    return recommendations
