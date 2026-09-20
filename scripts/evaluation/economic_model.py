class EconomicAttackModel:
    """
    Models the economic cost of attacking the protected software.

    Inputs:
      - RE hours (from cost model)
      - Analyst hourly rate
      - Tool licenses costs
      - Infrastructure costs

    Outputs:
      - total_attack_cost
      - break_even_analysis
      - attacker_decision (profitable? / not worth it?)
    """

    DEFAULT_ASSUMPTIONS = {
        'analyst_rate': 150.0,
        'tool_licenses': 5000.0,
        'infra_per_day': 200.0,
    }

    def __init__(self):
        self.assumptions = dict(self.DEFAULT_ASSUMPTIONS)

    def analyze(self, protection_metrics: dict, assumptions: dict = None) -> dict:
        merged = dict(self.DEFAULT_ASSUMPTIONS)
        if assumptions:
            merged.update(assumptions)
        self.assumptions = merged

        re_hours = self._extract_re_hours(protection_metrics)
        attack_days = re_hours / 8.0

        labor_cost = re_hours * self.assumptions['analyst_rate']
        infra_cost = attack_days * self.assumptions['infra_per_day']
        tool_cost = self.assumptions['tool_licenses']

        total_attack_cost = labor_cost + infra_cost + tool_cost

        break_even = self._compute_break_even(total_attack_cost, protection_metrics)
        decision = self._attacker_decision(total_attack_cost, break_even)

        return {
            're_hours': round(re_hours, 2),
            'attack_days': round(attack_days, 2),
            'labor_cost': round(labor_cost, 2),
            'infrastructure_cost': round(infra_cost, 2),
            'tool_cost': round(tool_cost, 2),
            'total_attack_cost': round(total_attack_cost, 2),
            'break_even_analysis': break_even,
            'attacker_decision': decision,
            'assumptions_used': dict(self.assumptions),
        }

    def _extract_re_hours(self, metrics: dict) -> float:
        if 'total_hours' in metrics:
            return metrics['total_hours']
        if 'total_estimated_hours' in metrics:
            return metrics['total_estimated_hours']
        if 're_hours' in metrics:
            return metrics['re_hours']

        cfg = metrics.get('cfg_entropy', metrics.get('entropy_ratio', 1.0))
        if isinstance(cfg, dict):
            cfg = cfg.get('entropy_ratio', 1.0)
        cyclo = metrics.get('cyclomatic_complexity', metrics.get('complexity_ratio', 1.0))
        if isinstance(cyclo, dict):
            cyclo = cyclo.get('complexity_ratio', 1.0)
        opaques = metrics.get('protected_opaque_predicates', 0)
        if isinstance(metrics.get('symbolic_resistance'), dict):
            opaques = metrics['symbolic_resistance'].get('protected_opaque_predicates', opaques)
        mba = metrics.get('protected_mba_depth', 0)
        if isinstance(metrics.get('symbolic_resistance'), dict):
            mba = metrics['symbolic_resistance'].get('protected_mba_depth', mba)
        fragments = metrics.get('fragment_count', 0)
        vm = metrics.get('vm_instructions', 0)
        antidebug = metrics.get('antidebug_layers', 0)

        static_h = max(0.0, (cfg - 1.0) / 0.1) * 10.0 + max(0.0, (cyclo - 1.0)) * 5.0 + opaques * 8.0
        dynamic_h = vm * 0.5 + fragments * 15.0 + antidebug * 20.0
        deobf_h = mba * 12.0
        return static_h + dynamic_h + deobf_h

    def _compute_break_even(self, total_cost: float, metrics: dict) -> dict:
        software_value = metrics.get('software_value', 50000.0)
        ip_value = metrics.get('ip_value', 100000.0)
        total_value = software_value + ip_value
        if total_cost <= 0:
            return {
                'software_value': software_value,
                'ip_value': ip_value,
                'total_value': total_value,
                'cost_vs_value_ratio': float('inf'),
                'break_even': False,
            }
        ratio = total_value / total_cost
        return {
            'software_value': software_value,
            'ip_value': ip_value,
            'total_value': total_value,
            'cost_vs_value_ratio': round(ratio, 4),
            'break_even': ratio >= 1.0,
        }

    def _attacker_decision(self, total_cost: float, break_even: dict) -> str:
        if break_even['break_even']:
            return 'profitable'
        if total_cost > break_even['total_value'] * 2:
            return 'not worth it'
        return 'marginal'

    def analyze_scenario(self, protection_metrics: dict, assumptions: dict = None) -> dict:
        base = self.analyze(protection_metrics, assumptions)
        return base

    def scenario_analysis(self, protection_metrics: dict) -> list:
        scenarios = [
            {'label': 'low_cost', 'analyst_rate': 50.0, 'tool_licenses': 1000.0, 'infra_per_day': 50.0},
            {'label': 'medium_cost', 'analyst_rate': 150.0, 'tool_licenses': 5000.0, 'infra_per_day': 200.0},
            {'label': 'high_cost', 'analyst_rate': 300.0, 'tool_licenses': 20000.0, 'infra_per_day': 500.0},
        ]
        results = []
        for s in scenarios:
            result = self.analyze(protection_metrics, s)
            result['scenario'] = s['label']
            results.append(result)
        return results
