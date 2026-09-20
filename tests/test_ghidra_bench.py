import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evaluation.ghidra_bench import GhidraBenchmark, GhidraSimulator


class TestGhidraSimulator:
    """
    TestGhidraSimulator
    
    Positive test cases for ghidrasimulator.
    """
    def test_simulator_scores(self):
        sim = GhidraSimulator()
        result = sim.simulate({})
        assert isinstance(result, dict)
        assert 'decompilation_quality' in result
        assert 'function_recovery' in result
        assert 'type_recovery' in result

    def test_scores_in_range(self):
        sim = GhidraSimulator()
        result = sim.simulate({})
        for v in result.values():
            assert 0 <= v <= 100

    def test_decompilation_quality(self):
        sim = GhidraSimulator()
        easy = sim.simulate({
            'protected_blocks': 0,
            'protected_opaque_predicates': 0,
            'protected_mba_depth': 0,
        })
        hard = sim.simulate({
            'protected_blocks': 500,
            'protected_opaque_predicates': 100,
            'protected_mba_depth': 50,
        })
        assert hard['decompilation_quality'] <= easy['decompilation_quality']

    def test_benchmark_returns_dict(self):
        bench = GhidraBenchmark()
        result = bench.run("/nonexistent/file.bin")
        assert isinstance(result, dict)
        assert 'decompilation_quality' in result
        assert 'function_recovery' in result
        assert 'type_recovery' in result
        assert 'tool' in result
