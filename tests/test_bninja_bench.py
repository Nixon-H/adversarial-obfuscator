import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evaluation.bninja_bench import BinaryNinjaBenchmark, BinaryNinjaSimulator


class TestBinaryNinjaSimulator:
    """
    TestBinaryNinjaSimulator
    
    Positive test cases for binaryninjasimulator.
    """
    def test_bninja_simulator(self):
        sim = BinaryNinjaSimulator()
        result = sim.simulate({})
        assert isinstance(result, dict)
        assert 'il_translation' in result
        assert 'analysis_completeness' in result
        assert 'hlil_quality' in result

    def test_scores_range(self):
        sim = BinaryNinjaSimulator()
        result = sim.simulate({})
        for v in result.values():
            assert 0 <= v <= 100

    def test_higher_complexity_lower(self):
        sim = BinaryNinjaSimulator()
        easy = sim.simulate({'protected_blocks': 0, 'protected_opaque_predicates': 0, 'protected_mba_depth': 0})
        hard = sim.simulate({'protected_blocks': 500, 'protected_opaque_predicates': 100, 'protected_mba_depth': 50})
        assert hard['il_translation'] <= easy['il_translation']

    def test_benchmark_returns_dict(self):
        bench = BinaryNinjaBenchmark()
        result = bench.run("/nonexistent/file.bin")
        assert isinstance(result, dict)
        assert 'il_translation' in result
        assert 'analysis_completeness' in result
        assert 'hlil_quality' in result
        assert 'tool' in result
