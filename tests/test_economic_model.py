import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evaluation.economic_model import EconomicAttackModel


class TestEconomicAttackModel:
    """
    TestEconomicAttackModel
    
    Positive test cases for economicattackmodel.
    """
    def test_cost_calculation(self):
        model = EconomicAttackModel()
        metrics = {
            'total_hours': 100,
        }
        result = model.analyze(metrics)
        assert result['total_attack_cost'] > 0
        assert result['labor_cost'] == 100 * 150
        assert result['tool_cost'] == 5000

    def test_break_even(self):
        model = EconomicAttackModel()
        metrics = {
            'total_hours': 10,
            'software_value': 100000,
            'ip_value': 200000,
        }
        result = model.analyze(metrics)
        assert 'break_even_analysis' in result
        be = result['break_even_analysis']
        assert 'break_even' in be
        assert 'cost_vs_value_ratio' in be

    def test_attacker_decision(self):
        model = EconomicAttackModel()
        result = model.analyze({'total_hours': 1000})
        assert result['attacker_decision'] in ('profitable', 'marginal', 'not worth it')

    def test_different_rate_scenarios(self):
        model = EconomicAttackModel()
        low = model.analyze({'total_hours': 100}, {'analyst_rate': 50, 'tool_licenses': 1000, 'infra_per_day': 50})
        high = model.analyze({'total_hours': 100}, {'analyst_rate': 300, 'tool_licenses': 20000, 'infra_per_day': 500})
        assert high['total_attack_cost'] > low['total_attack_cost']

    def test_extract_re_hours(self):
        model = EconomicAttackModel()
        hours = model._extract_re_hours({'total_hours': 42})
        assert hours == 42.0
        hours2 = model._extract_re_hours({'cfg_entropy': {'entropy_ratio': 2.0}})
        assert hours2 > 0

    def test_scenario_analysis(self):
        model = EconomicAttackModel()
        results = model.scenario_analysis({'total_hours': 100})
        assert len(results) == 3
        for r in results:
            assert 'scenario' in r
            assert 'total_attack_cost' in r

    def test_zero_hours(self):
        model = EconomicAttackModel()
        result = model.analyze({'total_hours': 0})
        assert result['total_attack_cost'] == 5000
