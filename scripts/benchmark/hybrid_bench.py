"""
hybrid_bench.py

Purpose:
Models a hybrid AI-guided human reverse-engineering analyst to estimate
the cost, time, and success probability of deobfuscating protected code.

Architectural Role:
Provides a cost-model benchmark that complements the static proxy metrics
in ai_eval.py. While AIBenchmark measures protection strength against
automated tools, HybridBenchmark estimates the resources a determined
human+AI analyst would need to defeat the protection.

Dependencies:
math

Security Relevance:
Quantifies the economic cost of deobfuscation. High estimated analyst
hours and low success probability indicate strong real-world protection.
The complexity index synthesises multiple protection dimensions
(cfg_entropy, cyclomatic complexity, opaque predicates, MBA depth,
fragment count, VM instructions) into a single difficulty metric.
"""

import math
import os


PHASE_CONFIGS = {
    'ai_pre_analysis': {
        'base_time_hours': 2.0,
        'time_per_complexity': 0.5,
        'base_success': 0.85,
        'decay_per_complexity': 0.05,
    },
    'human_review': {
        'base_time_hours': 8.0,
        'time_per_complexity': 2.0,
        'base_success': 0.70,
        'decay_per_complexity': 0.08,
    },
    'ai_refinement': {
        'base_time_hours': 1.0,
        'time_per_complexity': 0.3,
        'base_success': 0.90,
        'decay_per_complexity': 0.03,
    },
    'human_conclusion': {
        'base_time_hours': 4.0,
        'time_per_complexity': 1.0,
        'base_success': 0.75,
        'decay_per_complexity': 0.06,
    },
}

COST_PER_ANALYST_HOUR = float(os.environ.get("NIXON_ANALYST_COST", "150.0"))
AI_TOOL_COST_PER_RUN = float(os.environ.get("NIXON_AI_TOOL_COST", "50.0"))


class HybridBenchmark:
    """
    Models a hybrid AI-guided human reverse engineering analyst.

    Phases:
      1. AI pre-analysis  – AI tools scan the binary, identify patterns
      2. Human review     – human analyst reviews AI findings
      3. AI refinement    – AI refines deobfuscation based on human feedback
      4. Human conclusion – human makes final judgement

    Each phase has a time cost that scales with protection complexity,
    and a success probability that decreases with protection intensity.
    """

    def estimate(self, protection_metrics: dict) -> dict:
        """
        Estimate time, cost, and success probability for deobfuscation.

        Builds a complexity index from the protection metrics, then
        computes per-phase estimates and aggregates into overall
        metrics. Also provides an AI-only comparison baseline.
        """
        complexity = self._compute_complexity_index(protection_metrics)

        phases = {}
        total_time = 0.0
        phase_successes = []

        for phase_name, cfg in PHASE_CONFIGS.items():
            time_h = cfg['base_time_hours'] + cfg['time_per_complexity'] * complexity
            success_p = max(0.01, cfg['base_success'] - cfg['decay_per_complexity'] * complexity)
            phases[phase_name] = {
                'time_hours': round(time_h, 2),
                'success_probability': round(success_p, 4),
            }
            total_time += time_h
            phase_successes.append(success_p)

        max_success = max(phase_successes)
        overall_success = 1.0 - (1.0 - max_success) ** 2

        cost_estimate = self._compute_cost(total_time, phases)
        ai_only_time, ai_only_success = self._estimate_ai_only(complexity)

        return {
            'time_estimate': round(total_time, 2),
            'success_probability': round(overall_success, 4),
            'cost_estimate': round(cost_estimate, 2),
            'phases': phases,
            'complexity_index': round(complexity, 2),
            'ai_only': {
                'time_estimate': round(ai_only_time, 2),
                'success_probability': round(ai_only_success, 4),
                'cost_estimate': round(ai_only_time * AI_TOOL_COST_PER_RUN, 2),
            },
        }

    def _compute_complexity_index(self, metrics: dict) -> float:
        """
        Compute a scalar complexity index from multi-dimensional metrics.

        Factors:
          - cfg_entropy / entropy_ratio (weight 2.0)
          - cyclomatic_complexity / complexity_ratio (weight 1.5)
          - opaque_predicate count (weight 0.3)
          - MBA expression depth (weight 0.5)
          - fragment count (weight 0.8)
          - VM instruction count (weight 0.02)
        """
        cfg = metrics.get('cfg_entropy', metrics.get('entropy_ratio', 1.0))
        if isinstance(cfg, dict):
            cfg = cfg.get('entropy_ratio', 1.0)
        cyclo = metrics.get('cyclomatic_complexity', metrics.get('complexity_ratio', 1.0))
        if isinstance(cyclo, dict):
            cyclo = cyclo.get('complexity_ratio', 1.0)
        opaques = metrics.get('protected_opaque_predicates', 0)
        if isinstance(metrics.get('symbolic_resistance'), dict):
            opaques = metrics['symbolic_resistance'].get('protected_opaque_predicates', opaques)
        mba = metrics.get('protected_mba_depth', 0)
        if isinstance(metrics.get('symbolic_resistance'), dict):
            mba = metrics['symbolic_resistance'].get('protected_mba_depth', mba)
        fragments = metrics.get('fragment_count', 0)
        vm_inst = metrics.get('vm_instructions', 0)

        index = (
            max(0.0, cfg - 1.0) * 2.0
            + max(0.0, cyclo - 1.0) * 1.5
            + opaques * 0.3
            + mba * 0.5
            + fragments * 0.8
            + vm_inst * 0.02
        )
        return index

    def _compute_cost(self, total_time: float, phases: dict) -> float:
        """Compute total monetary cost combining analyst labor and AI tool fees."""
        labor = total_time * COST_PER_ANALYST_HOUR
        ai_runs = sum(1 for p in phases if 'ai' in p)
        tool_cost = ai_runs * AI_TOOL_COST_PER_RUN
        return labor + tool_cost

    def _estimate_ai_only(self, complexity: float) -> tuple:
        """Estimate time and success probability for AI-only (no human) analysis."""
        time_h = 4.0 + 0.8 * complexity
        success_p = max(0.01, 0.60 - 0.06 * complexity)
        return time_h, success_p
