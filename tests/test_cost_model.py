import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evaluation.cost_model import ReverseEngineeringCostModel, CostBreakdown
from scripts.evaluation.calibration_data import CALIBRATION_SOURCES


class TestCostModel:
    """
    TestCostModel
    
    Positive test cases for costmodel.
    """
    def test_estimate_returns_breakdown(self):
        model = ReverseEngineeringCostModel()
        metrics = {
            'cfg_entropy': {'entropy_ratio': 2.5},
            'cyclomatic_complexity': {'complexity_ratio': 4.0},
            'symbolic_resistance': {'protected_opaque_predicates': 15, 'protected_mba_depth': 6},
            'dead_code': {'protected_dead_code_pct': 30.0},
            'vm_instructions': 200,
            'fragment_count': 5,
            'antidebug_layers': 3,
        }
        result = model.estimate(metrics)
        assert isinstance(result, CostBreakdown)
        assert isinstance(result.static_analysis_hours, float)
        assert isinstance(result.dynamic_analysis_hours, float)
        assert isinstance(result.deobfuscation_hours, float)
        assert isinstance(result.total_hours, float)
        assert isinstance(result.confidence_interval, tuple)
        assert len(result.confidence_interval) == 2
        assert isinstance(result.cost_class, str)

    def test_hours_non_negative(self):
        model = ReverseEngineeringCostModel()
        metrics = {
            'cfg_entropy': {'entropy_ratio': 1.0},
            'cyclomatic_complexity': {'complexity_ratio': 1.0},
            'symbolic_resistance': {'protected_opaque_predicates': 0, 'protected_mba_depth': 0},
            'dead_code': {'protected_dead_code_pct': 0.0},
            'vm_instructions': 0,
            'fragment_count': 0,
            'antidebug_layers': 0,
        }
        result = model.estimate(metrics)
        assert result.static_analysis_hours >= 0
        assert result.dynamic_analysis_hours >= 0
        assert result.deobfuscation_hours >= 0
        assert result.total_hours >= 0

    def test_monotonic_increasing(self):
        model = ReverseEngineeringCostModel()
        base = {
            'cfg_entropy': {'entropy_ratio': 1.0},
            'cyclomatic_complexity': {'complexity_ratio': 1.0},
            'symbolic_resistance': {'protected_opaque_predicates': 0, 'protected_mba_depth': 0},
            'dead_code': {'protected_dead_code_pct': 0.0},
            'vm_instructions': 0,
            'fragment_count': 0,
            'antidebug_layers': 0,
        }
        low = model.estimate(base)
        high_metrics = dict(base)
        high_metrics['vm_instructions'] = 500
        high_metrics['fragment_count'] = 20
        high_metrics['antidebug_layers'] = 5
        high = model.estimate(high_metrics)
        assert high.total_hours >= low.total_hours
        assert high.static_analysis_hours >= low.static_analysis_hours
        assert high.dynamic_analysis_hours >= low.dynamic_analysis_hours

    def test_zero_protection_near_zero(self):
        model = ReverseEngineeringCostModel()
        metrics = {
            'cfg_entropy': {'entropy_ratio': 1.0},
            'cyclomatic_complexity': {'complexity_ratio': 1.0},
            'symbolic_resistance': {'protected_opaque_predicates': 0, 'protected_mba_depth': 0},
            'dead_code': {'protected_dead_code_pct': 0.0},
            'vm_instructions': 0,
            'fragment_count': 0,
            'antidebug_layers': 0,
        }
        result = model.estimate(metrics)
        assert result.total_hours < 1.0
        assert result.cost_class == "trivial"

    def test_extreme_inputs_extreme_class(self):
        model = ReverseEngineeringCostModel()
        metrics = {
            'cfg_entropy': {'entropy_ratio': 20.0},
            'cyclomatic_complexity': {'complexity_ratio': 50.0},
            'symbolic_resistance': {'protected_opaque_predicates': 100, 'protected_mba_depth': 30},
            'dead_code': {'protected_dead_code_pct': 80.0},
            'vm_instructions': 5000,
            'fragment_count': 100,
            'antidebug_layers': 20,
        }
        result = model.estimate(metrics)
        assert result.cost_class == "extreme"
        assert result.total_hours > 100

    def test_calibration_data_keys(self):
        expected_keys = {'ollvm_fla', 'tigress_opaque', 'vm_protected', 'ollvm_sub', 'mba_obfuscation'}
        assert set(CALIBRATION_SOURCES.keys()) == expected_keys
        for key in CALIBRATION_SOURCES:
            entry = CALIBRATION_SOURCES[key]
            assert 'source' in entry
            assert 'hours' in entry
            assert isinstance(entry['hours'], (int, float))
            assert entry['hours'] > 0

    def test_estimate_from_benchmark_accepts_dict(self):
        model = ReverseEngineeringCostModel()
        results = {
            'cfg_entropy': {'entropy_ratio': 3.0},
            'cyclomatic_complexity': {'complexity_ratio': 5.0},
            'symbolic_resistance': {'protected_opaque_predicates': 10, 'protected_mba_depth': 4},
            'dead_code': {'protected_dead_code_pct': 25.0},
        }
        result = model.estimate_from_benchmark(results)
        assert isinstance(result, CostBreakdown)
        assert result.total_hours > 0

    def test_confidence_interval_symmetric(self):
        model = ReverseEngineeringCostModel()
        metrics = {
            'cfg_entropy': {'entropy_ratio': 3.0},
            'cyclomatic_complexity': {'complexity_ratio': 4.0},
            'symbolic_resistance': {'protected_opaque_predicates': 10, 'protected_mba_depth': 5},
            'dead_code': {'protected_dead_code_pct': 20.0},
            'vm_instructions': 100,
            'fragment_count': 3,
            'antidebug_layers': 2,
        }
        result = model.estimate(metrics)
        low, high = result.confidence_interval
        assert low <= result.total_hours <= high
        assert high - result.total_hours >= result.total_hours - low
