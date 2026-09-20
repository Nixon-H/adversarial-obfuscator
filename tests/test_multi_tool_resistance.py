import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evaluation.multi_tool import MultiToolResistance, MultiToolEvaluator


class TestMultiToolResistance:
    """
    TestMultiToolResistance
    
    Positive test cases for multitoolresistance.
    """
    def test_composite_score(self):
        mt = MultiToolResistance()
        result = mt.evaluate("/nonexistent/file.bin")
        assert isinstance(result, dict)
        assert 'composite_score' in result
        assert 0 <= result['composite_score'] <= 100

    def test_partial_tools(self):
        mt = MultiToolResistance()
        result = mt.evaluate("/nonexistent/file.bin")
        assert len(result['tools_tested']) >= 3

    def test_no_tools_fallback(self):
        mt = MultiToolResistance()
        result = mt.evaluate("/nonexistent/file.bin")
        assert len(result['tools_simulated']) > 0

    def test_scores_range(self):
        mt = MultiToolResistance()
        result = mt.evaluate("/nonexistent/file.bin")
        for tool, tool_scores in result['scores'].items():
            for metric, score in tool_scores.items():
                assert 0 <= score <= 100, f"{tool}.{metric} = {score}"

    def test_weighted_avg_100(self):
        mt = MultiToolResistance()
        scores = {
            'angr': {'bb_accuracy': 100, 'function_recovery': 100, 'decompilation': 100},
            'ghidra': {'bb_accuracy': 100, 'function_recovery': 100, 'decompilation': 100},
            'bninja': {'bb_accuracy': 100, 'function_recovery': 100, 'decompilation': 100},
            'readelf': {'bb_accuracy': 100, 'function_recovery': 100, 'decompilation': 100},
        }
        composite = mt._compute_composite(scores)
        assert composite == 100.0

    def test_weights_distribution(self):
        mt = MultiToolResistance()
        assert abs(mt.WEIGHTS['angr'] - 0.30) < 0.01
        assert abs(mt.WEIGHTS['ghidra'] - 0.25) < 0.01
        assert abs(mt.WEIGHTS['bninja'] - 0.20) < 0.01
        total = sum(mt.WEIGHTS.values())
        assert abs(total - 1.0) < 0.01

    def test_empty_returns_0(self):
        mt = MultiToolResistance()
        composite = mt._compute_composite({})
        assert composite == 0.0


class TestMultiToolEvaluatorWrapper:
    """
    TestMultiToolEvaluatorWrapper
    
    Positive test cases for multitoolevaluatorwrapper.
    """
    def test_evaluator_still_works(self):
        evaluator = MultiToolEvaluator()
        result = evaluator.evaluate("/nonexistent/artifact.bin")
        assert 'composite_score' in result
        assert 'tools_tested' in result
