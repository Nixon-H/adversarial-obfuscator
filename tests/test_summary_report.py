import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evaluation.summary_report import EvaluationSummary


class TestEvaluationSummary:
    """
    TestEvaluationSummary
    
    Positive test cases for evaluationsummary.
    """
    def test_summary_combines_all(self):
        summary = EvaluationSummary()
        result = summary.generate("/nonexistent/file.bin", {
            'cfg_entropy': {'entropy_ratio': 2.0},
            'cyclomatic_complexity': {'complexity_ratio': 2.0},
            'symbolic_resistance': {'protected_opaque_predicates': 10, 'protected_mba_depth': 3},
            'dead_code': {'protected_dead_code_pct': 20.0},
            'vm_instructions': 50,
            'fragment_count': 5,
            'antidebug_layers': 2,
        })
        assert isinstance(result, dict)
        assert 'protection_effectiveness_score' in result
        assert 'component_scores' in result
        assert 'executive_summary' in result
        assert 'details' in result
        assert 'cost_model' in result['details']
        assert 'multi_tool' in result['details']
        assert 'survivability' in result['details']
        assert 'difficulty_curves' in result['details']
        assert 'economic_model' in result['details']

    def test_protection_score_range(self):
        summary = EvaluationSummary()
        result = summary.generate("/nonexistent/file.bin", {
            'cfg_entropy': {'entropy_ratio': 1.0},
            'cyclomatic_complexity': {'complexity_ratio': 1.0},
        })
        score = result['protection_effectiveness_score']
        assert 0 <= score <= 100

    def test_protection_score_extreme(self):
        summary = EvaluationSummary()
        result = summary.generate("/nonexistent/file.bin", {
            'cfg_entropy': {'entropy_ratio': 10.0},
            'cyclomatic_complexity': {'complexity_ratio': 20.0},
            'symbolic_resistance': {'protected_opaque_predicates': 100, 'protected_mba_depth': 30},
            'dead_code': {'protected_dead_code_pct': 80.0},
            'vm_instructions': 5000,
            'fragment_count': 100,
            'antidebug_layers': 10,
        })
        score = result['protection_effectiveness_score']
        assert score > 0

    def test_executive_summary_format(self):
        summary = EvaluationSummary()
        result = summary.generate("/nonexistent/file.bin", {
            'cfg_entropy': {'entropy_ratio': 2.0},
            'cyclomatic_complexity': {'complexity_ratio': 1.5},
        })
        assert isinstance(result['executive_summary'], str)
        assert 'Protection Effectiveness Score' in result['executive_summary']

    def test_json_output(self):
        summary = EvaluationSummary()
        result = summary.generate("/nonexistent/file.bin", {
            'cfg_entropy': {'entropy_ratio': 1.0},
            'cyclomatic_complexity': {'complexity_ratio': 1.0},
        })
        json_str = summary.to_json(result)
        parsed = json.loads(json_str)
        assert parsed['protection_effectiveness_score'] == result['protection_effectiveness_score']

    def test_rating_function(self):
        assert EvaluationSummary._rating(90) == 'Excellent'
        assert EvaluationSummary._rating(75) == 'Good'
        assert EvaluationSummary._rating(60) == 'Moderate'
        assert EvaluationSummary._rating(40) == 'Weak'
        assert EvaluationSummary._rating(10) == 'Poor'
