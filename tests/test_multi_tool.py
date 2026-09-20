import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evaluation.multi_tool import MultiToolEvaluator
from scripts.evaluation.tool_simulator import ToolSimulator
from scripts.evaluation.tool_profiles import TOOL_PROFILES


REQUIRED_PROFILE_KEYS = {'cfg_flatten_sensitivity', 'opaque_predicate_limit', 'mba_depth_limit', 'vm_resistance'}


class TestMultiToolEvaluator:
    """
    TestMultiToolEvaluator
    
    Positive test cases for multitoolevaluator.
    """
    def test_evaluator_returns_scores(self):
        evaluator = MultiToolEvaluator()
        result = evaluator.evaluate("/nonexistent/artifact.bin")
        assert isinstance(result, dict)
        assert 'tools_tested' in result
        assert 'scores' in result
        assert 'composite_score' in result
        assert 'tools_found' in result
        assert 'tools_simulated' in result
        assert len(result['tools_tested']) >= 2

    def test_scores_in_range(self):
        evaluator = MultiToolEvaluator()
        result = evaluator.evaluate("/nonexistent/artifact.bin")
        for tool, tool_scores in result['scores'].items():
            for metric, score in tool_scores.items():
                assert 0 <= score <= 100, f"{tool}.{metric} = {score} not in [0,100]"

    def test_composite_score_average(self):
        evaluator = MultiToolEvaluator()
        scores = {
            'angr': {'bb_accuracy': 100, 'function_recovery': 100, 'decompilation': 100},
            'rizin': {'bb_accuracy': 100, 'function_recovery': 100, 'decompilation': 100},
            'readelf': {'bb_accuracy': 100, 'function_recovery': 100, 'decompilation': 100},
            'objdump': {'bb_accuracy': 100, 'function_recovery': 100, 'decompilation': 100},
        }
        composite = evaluator._compute_composite(scores)
        assert composite == 100.0

    def test_composite_zero_with_no_scores(self):
        evaluator = MultiToolEvaluator()
        composite = evaluator._compute_composite({})
        assert composite == 0.0

    def test_composite_with_varied_scores(self):
        evaluator = MultiToolEvaluator()
        scores = {
            'angr': {'bb_accuracy': 50, 'function_recovery': 50, 'decompilation': 50},
            'rizin': {'bb_accuracy': 0, 'function_recovery': 0, 'decompilation': 0},
        }
        composite = evaluator._compute_composite(scores)
        assert 0 < composite < 100

    def test_extract_metrics_does_not_crash(self):
        evaluator = MultiToolEvaluator()
        metrics = evaluator._extract_metrics("/nonexistent/file.bin")
        assert isinstance(metrics, dict)


class TestToolSimulator:
    """
    TestToolSimulator
    
    Positive test cases for toolsimulator.
    """
    def test_tool_simulator_produces_scores(self):
        sim = ToolSimulator()
        metrics = {
            'cfg_entropy': {'protected_blocks': 30},
            'symbolic_resistance': {'protected_opaque_predicates': 5, 'protected_mba_depth': 3},
        }
        for tool in ('angr', 'rizin', 'readelf', 'objdump'):
            result = sim.simulate(metrics, tool)
            assert isinstance(result, dict)
            assert 'bb_accuracy' in result
            assert 'function_recovery' in result
            assert 'decompilation' in result

    def test_simulated_scores_in_range(self):
        sim = ToolSimulator()
        metrics = {
            'cfg_entropy': {'protected_blocks': 50},
            'symbolic_resistance': {'protected_opaque_predicates': 20, 'protected_mba_depth': 5},
        }
        for tool in ('angr', 'rizin', 'readelf', 'objdump'):
            result = sim.simulate(metrics, tool)
            for v in result.values():
                assert 0 <= v <= 100

    def test_simulator_degrades_with_complexity(self):
        sim = ToolSimulator()
        easy_metrics = {
            'cfg_entropy': {'protected_blocks': 5},
            'symbolic_resistance': {'protected_opaque_predicates': 1, 'protected_mba_depth': 0},
        }
        hard_metrics = {
            'cfg_entropy': {'protected_blocks': 500},
            'symbolic_resistance': {'protected_opaque_predicates': 100, 'protected_mba_depth': 50},
        }
        easy = sim.simulate(easy_metrics, 'angr')
        hard = sim.simulate(hard_metrics, 'angr')
        assert hard['bb_accuracy'] <= easy['bb_accuracy']
        assert hard['function_recovery'] <= easy['function_recovery']
        assert hard['decompilation'] <= easy['decompilation']

    def test_simulator_with_empty_metrics(self):
        sim = ToolSimulator()
        result = sim.simulate({}, 'angr')
        for v in result.values():
            assert 0 <= v <= 100

    def test_simulator_angr_more_sensitive_than_readelf(self):
        sim = ToolSimulator()
        hard_metrics = {
            'cfg_entropy': {'protected_blocks': 200},
            'symbolic_resistance': {'protected_opaque_predicates': 50, 'protected_mba_depth': 10},
        }
        angr = sim.simulate(hard_metrics, 'angr')
        readelf = sim.simulate(hard_metrics, 'readelf')
        assert angr['bb_accuracy'] <= readelf['bb_accuracy']
        assert angr['decompilation'] <= readelf['decompilation']


class TestToolProfiles:
    """
    TestToolProfiles
    
    Positive test cases for toolprofiles.
    """
    def test_tool_profiles_valid(self):
        for tool, profile in TOOL_PROFILES.items():
            missing = REQUIRED_PROFILE_KEYS - set(profile.keys())
            assert not missing, f"{tool} missing keys: {missing}"
            assert isinstance(profile['cfg_flatten_sensitivity'], (int, float))
            assert isinstance(profile['opaque_predicate_limit'], (int, float))
            assert isinstance(profile['mba_depth_limit'], (int, float))
            assert profile['vm_resistance'] in ('high', 'medium', 'low')

    def test_profile_sensitivity_ordering(self):
        assert TOOL_PROFILES['angr']['cfg_flatten_sensitivity'] < TOOL_PROFILES['rizin']['cfg_flatten_sensitivity']
        assert TOOL_PROFILES['angr']['opaque_predicate_limit'] < TOOL_PROFILES['rizin']['opaque_predicate_limit']
