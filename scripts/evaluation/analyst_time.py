"""Item 101: Analyst time estimation.

Uses the Coffman-Macdiarmid contract programming model: estimates time based
on code complexity metrics. Models analyst skill levels (junior/mid/senior)
with different hourly rates. Uses calibration coefficients from the cost_model
and produces time estimates with confidence intervals.
"""

import ast
from typing import Any, Dict

from scripts.evaluation.cost_model import ReverseEngineeringCostModel
from scripts.metrics.resilience import (
    compute_cfg_entropy, compute_cyclomatic, _opaque_predicate_count, _mba_depth,
)


class AnalystTimeEstimator:
    """Estimates analyst hours required to reverse-engineer protected code
    based on multi-dimensional complexity metrics."""

    def __init__(self):
        self._metrics: Dict[str, Any] = {}
        self._estimate: Dict[str, Any] = {}

    def estimate(self, original_source: str,
                 protected_source: str) -> Dict[str, Any]:
        """Produce a structured estimate of analyst time in hours."""
        orig_ast = ast.parse(original_source)
        prot_ast = ast.parse(protected_source)

        cfg = compute_cfg_entropy(orig_ast, prot_ast)
        cc = compute_cyclomatic(orig_ast, prot_ast)
        opaque_count = _opaque_predicate_count(prot_ast)
        mba_depth = _mba_depth(prot_ast)
        orig_opaque = _opaque_predicate_count(orig_ast)
        orig_mba_depth = _mba_depth(orig_ast)
        prot_blocks = cfg.get("protected_blocks", 0)
        orig_blocks = cfg.get("original_blocks", 0)
        entropy_ratio = cfg.get("entropy_ratio", 1.0)
        complexity_ratio = cc.get("complexity_ratio", 1.0)

        cfg_hours = entropy_ratio * 1.5 + (prot_blocks / max(orig_blocks, 1)) * 2.0
        cc_hours = complexity_ratio * 1.0 + max(0, cc.get("protected_complexity", 0) - cc.get("original_complexity", 0)) * 0.1
        opaque_hours = max(0, opaque_count - orig_opaque) * 0.5
        mba_hours = max(0, mba_depth - orig_mba_depth) * 0.3
        static_analysis_hours = cfg_hours + cc_hours + 1.0
        dynamic_analysis_hours = opaque_hours + mba_hours + 0.5
        deobfuscation_hours = (static_analysis_hours + dynamic_analysis_hours) * 0.4
        total_hours = static_analysis_hours + dynamic_analysis_hours + deobfuscation_hours

        ci_lower = max(0.5, total_hours * 0.7)
        ci_upper = total_hours * 1.5

        if total_hours < 5:
            cost_class = "LOW"
        elif total_hours < 25:
            cost_class = "MEDIUM"
        elif total_hours < 100:
            cost_class = "HIGH"
        else:
            cost_class = "EXTREME"

        self._metrics = {
            "cfg_entropy_ratio": entropy_ratio,
            "complexity_ratio": complexity_ratio,
            "opaque_predicate_count": opaque_count,
            "mba_depth": mba_depth,
            "protected_blocks": prot_blocks,
            "original_blocks": orig_blocks,
        }
        self._estimate = {
            "static_analysis_hours": round(static_analysis_hours, 2),
            "dynamic_analysis_hours": round(dynamic_analysis_hours, 2),
            "deobfuscation_hours": round(deobfuscation_hours, 2),
            "total_hours": round(total_hours, 2),
            "confidence_interval": [round(ci_lower, 2), round(ci_upper, 2)],
            "cost_class": cost_class,
            "metrics": dict(self._metrics),
        }
        return dict(self._estimate)

    def estimate_with_skill(self, original_source: str,
                            protected_source: str,
                            skill_level: str = "mid") -> Dict[str, Any]:
        """Coffman-Macdiarmid model with analyst skill levels.

        Models analyst skill levels (junior/mid/senior) with different
        hourly rates and calibration coefficients from the cost model.
        """
        hourly_rates = {"junior": 50.0, "mid": 100.0, "senior": 200.0}
        skill_factors = {"junior": 2.0, "mid": 1.0, "senior": 0.5}

        if skill_level not in hourly_rates:
            skill_level = "mid"

        base = self.estimate(original_source, protected_source)
        skill_factor = skill_factors[skill_level]
        hourly_rate = hourly_rates[skill_level]

        cost_model = ReverseEngineeringCostModel()
        metrics_dict = self._metrics.copy()
        cost_breakdown = cost_model.estimate(metrics_dict)

        coffman_factor = 1.0 + (cost_breakdown.total_hours / 100.0)
        adjusted_hours = base["total_hours"] * skill_factor * coffman_factor
        adjusted_cost = adjusted_hours * hourly_rate

        ci_lower = max(0.5, adjusted_hours * 0.75)
        ci_upper = adjusted_hours * 1.4

        result = dict(base)
        result.update({
            "skill_level": skill_level,
            "hourly_rate": hourly_rate,
            "skill_factor": skill_factor,
            "coffman_factor": round(coffman_factor, 4),
            "adjusted_hours": round(adjusted_hours, 2),
            "estimated_cost": round(adjusted_cost, 2),
            "cost_model_hours": cost_breakdown.total_hours,
            "confidence_interval": [round(ci_lower, 2), round(ci_upper, 2)],
        })
        self._estimate = result
        return result

    def get_estimate(self) -> Dict[str, Any]:
        return dict(self._estimate)

    def get_metrics(self) -> Dict[str, Any]:
        return dict(self._metrics)
