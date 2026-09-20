import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.benchmark.hybrid_bench import HybridBenchmark


class TestHybridBenchmark:
    """
    TestHybridBenchmark
    
    Positive test cases for hybridbenchmark.
    """
    def test_time_estimate_increases_with_protection(self):
        hb = HybridBenchmark()
        low = hb.estimate({'cfg_entropy': {'entropy_ratio': 1.0}, 'cyclomatic_complexity': {'complexity_ratio': 1.0}})
        high = hb.estimate({'cfg_entropy': {'entropy_ratio': 5.0}, 'cyclomatic_complexity': {'complexity_ratio': 5.0},
                            'protected_opaque_predicates': 50, 'protected_mba_depth': 10, 'fragment_count': 20, 'vm_instructions': 500})
        assert high['time_estimate'] > low['time_estimate']

    def test_success_probability_decreases(self):
        hb = HybridBenchmark()
        low = hb.estimate({'cfg_entropy': {'entropy_ratio': 1.0}})
        high = hb.estimate({'cfg_entropy': {'entropy_ratio': 10.0}, 'protected_mba_depth': 20, 'fragment_count': 50})
        assert high['success_probability'] <= low['success_probability']

    def test_cost_estimate(self):
        hb = HybridBenchmark()
        result = hb.estimate({'cfg_entropy': {'entropy_ratio': 2.0}})
        assert 'cost_estimate' in result
        assert result['cost_estimate'] > 0
        assert isinstance(result['cost_estimate'], float)

    def test_hybrid_vs_ai_only(self):
        hb = HybridBenchmark()
        result = hb.estimate({'cfg_entropy': {'entropy_ratio': 3.0}, 'protected_mba_depth': 5})
        assert 'ai_only' in result
        assert result['ai_only']['time_estimate'] < result['time_estimate']
        assert result['ai_only']['success_probability'] <= result['success_probability']

    def test_phases_structure(self):
        hb = HybridBenchmark()
        result = hb.estimate({'cfg_entropy': {'entropy_ratio': 1.0}})
        assert 'phases' in result
        assert 'ai_pre_analysis' in result['phases']
        assert 'human_review' in result['phases']
        assert 'ai_refinement' in result['phases']
        assert 'human_conclusion' in result['phases']

    def test_complexity_index(self):
        hb = HybridBenchmark()
        idx = hb._compute_complexity_index({'cfg_entropy': {'entropy_ratio': 1.0}, 'cyclomatic_complexity': {'complexity_ratio': 1.0}})
        assert idx == 0.0
        idx2 = hb._compute_complexity_index({'cfg_entropy': {'entropy_ratio': 3.0}, 'protected_mba_depth': 5})
        assert idx2 > 0
