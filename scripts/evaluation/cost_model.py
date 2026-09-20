import math
from dataclasses import dataclass
from .calibration_data import CALIBRATION_SOURCES


@dataclass
class CostBreakdown:
    static_analysis_hours: float
    dynamic_analysis_hours: float
    deobfuscation_hours: float
    total_hours: float
    confidence_interval: tuple
    cost_class: str

    def __post_init__(self):
        self.total_hours = (
            self.static_analysis_hours
            + self.dynamic_analysis_hours
            + self.deobfuscation_hours
        )


class ReverseEngineeringCostModel:
    """
    Estimates RE time from protection metrics.

    Maps metrics -> hours using published calibration data:
    - CFG entropy ratio: +10h per 0.1 increase (static analysis)
    - Cyclomatic complexity ratio: +5h per unit (static)
    - Opaque predicate count: +8h per predicate (static)
    - VM instructions: +0.5h per instruction (dynamic)
    - Fragment count: +15h per fragment (dynamic)
    - Anti-debug layers: +20h per layer (dynamic)
    - MBA depth: +12h per level (deobfuscation)
    - Dead code %: +3h per 10% (deobfuscation)
    """

    def __init__(self):
        self.calibration = {
            'cfg_entropy_per_01': 10.0,
            'cyclomatic_per_unit': 5.0,
            'opaque_predicate_each': 8.0,
            'vm_instruction_each': 0.5,
            'fragment_each': 15.0,
            'antidebug_layer_each': 20.0,
            'mba_depth_per_level': 12.0,
            'dead_code_per_10pct': 3.0,
        }

    def estimate(self, metrics: dict) -> CostBreakdown:
        cfg_ratio = self._get(metrics, ('cfg_entropy', 'entropy_ratio'), 1.0)
        cyclomatic_ratio = self._get(metrics, ('cyclomatic_complexity', 'complexity_ratio'), 1.0)
        opaque_predicates = self._get(metrics, ('symbolic_resistance', 'protected_opaque_predicates'), 0)
        dead_code_pct = self._get(metrics, ('dead_code', 'protected_dead_code_pct'), 0.0)
        mba_depth = self._get(metrics, ('symbolic_resistance', 'protected_mba_depth'), 0)

        static_h = (
            max(0.0, (cfg_ratio - 1.0) / 0.1) * self.calibration['cfg_entropy_per_01']
            + max(0.0, (cyclomatic_ratio - 1.0)) * self.calibration['cyclomatic_per_unit']
            + opaque_predicates * self.calibration['opaque_predicate_each']
        )

        vm_instructions = metrics.get('vm_instructions', 0)
        fragment_count = metrics.get('fragment_count', 0)
        antidebug_layers = metrics.get('antidebug_layers', 0)

        dynamic_h = (
            vm_instructions * self.calibration['vm_instruction_each']
            + fragment_count * self.calibration['fragment_each']
            + antidebug_layers * self.calibration['antidebug_layer_each']
        )

        deobf_h = (
            mba_depth * self.calibration['mba_depth_per_level']
            + (dead_code_pct / 10.0) * self.calibration['dead_code_per_10pct']
        )

        total = static_h + dynamic_h + deobf_h
        ci_low = max(0.0, total * 0.8)
        ci_high = total * 1.2

        if total <= 10:
            cost_class = "trivial"
        elif total <= 50:
            cost_class = "moderate"
        elif total <= 100:
            cost_class = "hard"
        else:
            cost_class = "extreme"

        return CostBreakdown(
            static_analysis_hours=round(static_h, 2),
            dynamic_analysis_hours=round(dynamic_h, 2),
            deobfuscation_hours=round(deobf_h, 2),
            total_hours=round(total, 2),
            confidence_interval=(round(ci_low, 2), round(ci_high, 2)),
            cost_class=cost_class,
        )

    def estimate_from_benchmark(self, benchmark_results: dict) -> CostBreakdown:
        metrics = {}
        for key in ('cfg_entropy', 'cyclomatic_complexity', 'symbolic_resistance', 'dead_code'):
            if key in benchmark_results:
                metrics[key] = benchmark_results[key]
        metrics['vm_instructions'] = benchmark_results.get('vm_instructions', 0)
        metrics['fragment_count'] = benchmark_results.get('fragment_count', 0)
        metrics['antidebug_layers'] = benchmark_results.get('antidebug_layers', 0)
        return self.estimate(metrics)

    @staticmethod
    def _get(d: dict, keys: tuple, default):
        for key in keys:
            if isinstance(d, dict):
                d = d.get(key, default)
            else:
                return default
        return d
