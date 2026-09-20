import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evaluation.angr_bench import AngrBenchmark, AngrSimulator


class TestAngrSimulator:
    """
    TestAngrSimulator
    
    Positive test cases for angrsimulator.
    """
    def test_simulator_produces_scores(self):
        sim = AngrSimulator()
        result = sim.simulate({})
        assert isinstance(result, dict)
        assert 'bb_recovery' in result
        assert 'path_exploration' in result
        assert 'cfg_accuracy' in result

    def test_scores_in_range(self):
        sim = AngrSimulator()
        result = sim.simulate({})
        for k, v in result.items():
            assert 0 <= v <= 100, f"{k} = {v}"

    def test_higher_complexity_lower_score(self):
        sim = AngrSimulator()
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
        assert hard['bb_recovery'] <= easy['bb_recovery']
        assert hard['path_exploration'] <= easy['path_exploration']
        assert hard['cfg_accuracy'] <= easy['cfg_accuracy']

    def test_results_dict_structure(self):
        sim = AngrSimulator()
        result = sim.simulate({'protected_blocks': 30, 'protected_mba_depth': 5, 'protected_opaque_predicates': 10})
        assert all(key in result for key in ('bb_recovery', 'path_exploration', 'cfg_accuracy'))

    def test_composite_score(self):
        sim = AngrSimulator()
        scores = {'bb_recovery': 100, 'path_exploration': 100, 'cfg_accuracy': 100}
        composite = sim.composite_score(scores)
        assert composite == 100.0


class TestAngrBenchmark:
    """
    TestAngrBenchmark
    
    Positive test cases for angrbenchmark.
    """
    def test_benchmark_returns_dict(self):
        bench = AngrBenchmark()
        result = bench.run("/nonexistent/file.bin")
        assert isinstance(result, dict)
        assert 'bb_recovery' in result
        assert 'path_exploration' in result
        assert 'cfg_accuracy' in result
        assert 'angr_resistance_score' in result
        assert 'tool' in result

    def test_scores_in_range(self):
        bench = AngrBenchmark()
        result = bench.run("/nonexistent/file.bin")
        for key in ('bb_recovery', 'path_exploration', 'cfg_accuracy'):
            assert 0 <= result[key] <= 100
        assert 0 <= result['angr_resistance_score'] <= 100
