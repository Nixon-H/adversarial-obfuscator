import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evaluation.difficulty_curves import DifficultyCurveAnalyzer


class TestDifficultyCurveAnalyzer:
    """
    TestDifficultyCurveAnalyzer
    
    Positive test cases for difficultycurveanalyzer.
    """
    def test_curve_monotonic_increasing(self):
        dca = DifficultyCurveAnalyzer()
        result = dca.analyze({'protected_mba_depth': 10, 'protected_blocks': 50, 'fragment_count': 20})
        for curve_name in ('mba_depth', 'cfg_flattening', 'fragment_count'):
            points = result[curve_name]['points']
            for i in range(1, len(points)):
                assert points[i]['estimated_hours'] >= points[i - 1]['estimated_hours']

    def test_mba_depth_curve(self):
        dca = DifficultyCurveAnalyzer()
        result = dca.analyze({'protected_mba_depth': 10})
        assert 'mba_depth' in result
        assert len(result['mba_depth']['points']) == 11
        assert result['mba_depth']['points'][0]['estimated_hours'] >= 0

    def test_cfg_flat_curve(self):
        dca = DifficultyCurveAnalyzer()
        result = dca.analyze({'cfg_entropy': {'protected_blocks': 50}})
        assert 'cfg_flattening' in result
        assert len(result['cfg_flattening']['points']) > 0

    def test_fragment_count_curve(self):
        dca = DifficultyCurveAnalyzer()
        result = dca.analyze({'fragment_count': 20})
        assert 'fragment_count' in result
        assert len(result['fragment_count']['points']) == 21

    def test_curve_parameters_reasonable(self):
        dca = DifficultyCurveAnalyzer()
        result = dca.analyze({'protected_mba_depth': 10, 'fragment_count': 20})
        for curve_name in ('mba_depth', 'fragment_count'):
            params = result[curve_name]['curve_parameters']
            assert 'a' in params
            assert 'b' in params
            assert 'c' in params
            assert params['b'] > 0

    def test_inflection_point(self):
        dca = DifficultyCurveAnalyzer()
        result = dca.analyze({'protected_mba_depth': 10})
        inflection = result['mba_depth']['inflection_point']
        assert 'exists' in inflection
        assert 'intensity' in inflection
        assert 'hours' in inflection

    def test_overall_curve(self):
        dca = DifficultyCurveAnalyzer()
        result = dca.analyze({'protected_mba_depth': 5, 'protected_blocks': 30, 'fragment_count': 10})
        assert 'overall' in result
        assert len(result['overall']['points']) > 0
