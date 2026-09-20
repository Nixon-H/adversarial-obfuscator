import json

from .cost_model import ReverseEngineeringCostModel
from .multi_tool import MultiToolResistance
from .survivability import SurvivabilityIndex
from .difficulty_curves import DifficultyCurveAnalyzer
from .economic_model import EconomicAttackModel


class EvaluationSummary:
    """
    Aggregates all evaluation results:
      - Cost model (Item 100)
      - Multi-tool resistance (Item 104)
      - Survivability index (Item 106)
      - Difficulty curves (Item 107)
      - Economic model (Item 108)

    Produces a single "Protection Effectiveness Score" (0-100)
    and outputs executive summary + detailed JSON.
    """

    WEIGHTS = {
        'cost_model': 0.20,
        'multi_tool': 0.25,
        'survivability': 0.25,
        'difficulty_curves': 0.15,
        'economic_model': 0.15,
    }

    def __init__(self):
        self.cost_model = ReverseEngineeringCostModel()
        self.multi_tool = MultiToolResistance()
        self.survivability = SurvivabilityIndex()
        self.difficulty_curves = DifficultyCurveAnalyzer()
        self.economic_model = EconomicAttackModel()

    def generate(self, artifact_path: str, protection_metrics: dict = None) -> dict:
        if protection_metrics is None:
            protection_metrics = {}

        cost_result = self.cost_model.estimate(protection_metrics)
        multi_tool_result = self.multi_tool.evaluate(artifact_path)
        survivability_result = self.survivability.measure(artifact_path)
        difficulty_result = self.difficulty_curves.analyze(protection_metrics)
        economic_result = self.economic_model.analyze(protection_metrics)

        scores = {
            'cost_model_score': self._score_cost_model(cost_result),
            'multi_tool_score': multi_tool_result['composite_score'],
            'survivability_score': survivability_result.combined_index * 100,
            'difficulty_score': self._score_difficulty(difficulty_result),
            'economic_score': self._score_economic(economic_result),
        }

        protection_effectiveness_score = self._compute_weighted_score(scores)

        executive_summary = self._generate_executive_summary(
            protection_effectiveness_score, scores,
            cost_result, multi_tool_result, survivability_result,
            difficulty_result, economic_result,
        )

        return {
            'protection_effectiveness_score': round(protection_effectiveness_score, 2),
            'component_scores': scores,
            'executive_summary': executive_summary,
            'details': {
                'cost_model': {
                    'total_hours': cost_result.total_hours,
                    'cost_class': cost_result.cost_class,
                },
                'multi_tool': {
                    'composite_score': multi_tool_result['composite_score'],
                    'tools_tested': multi_tool_result['tools_tested'],
                    'tools_available': multi_tool_result.get('tools_available', []),
                    'tools_simulated': multi_tool_result.get('tools_simulated', []),
                },
                'survivability': {
                    'combined_index': survivability_result.combined_index,
                    'active_layers': survivability_result.active_layers,
                    'watermark_survival': survivability_result.watermark_survival,
                    'vm_opcode_recovery': survivability_result.vm_opcode_recovery,
                    'cfg_reconstruction': survivability_result.cfg_reconstruction,
                    'fragment_isolation': survivability_result.fragment_isolation,
                },
                'difficulty_curves': {
                    'curve_count': len(difficulty_result),
                    'curve_types': list(difficulty_result.keys()),
                },
                'economic_model': {
                    'total_attack_cost': economic_result['total_attack_cost'],
                    'attacker_decision': economic_result['attacker_decision'],
                },
            },
        }

    def _score_cost_model(self, cost_result) -> float:
        hours = cost_result.total_hours
        if hours <= 0:
            return 0.0
        if hours <= 10:
            return 10.0
        if hours <= 50:
            return 30.0
        if hours <= 100:
            return 50.0
        if hours <= 500:
            return 70.0
        if hours <= 1000:
            return 85.0
        return 95.0

    def _score_difficulty(self, difficulty_result: dict) -> float:
        if not difficulty_result:
            return 0.0
        overall = difficulty_result.get('overall', {})
        points = overall.get('points', [])
        if not points:
            return 0.0
        max_hours = max(p['estimated_hours'] for p in points)
        if max_hours <= 0:
            return 0.0
        return min(100.0, max_hours * 2.0)

    def _score_economic(self, economic_result: dict) -> float:
        decision = economic_result.get('attacker_decision', 'marginal')
        total_cost = economic_result.get('total_attack_cost', 0)
        if decision == 'not worth it':
            return 95.0
        if decision == 'marginal':
            return 60.0
        if total_cost > 100000:
            return 50.0
        return 20.0

    def _compute_weighted_score(self, scores: dict) -> float:
        total = 0.0
        weight_sum = 0.0
        for key, weight in self.WEIGHTS.items():
            score_key = f'{key}_score'
            if score_key in scores:
                total += scores[score_key] * weight
                weight_sum += weight
        if weight_sum == 0:
            return 0.0
        return total / weight_sum

    def _generate_executive_summary(
        self, overall_score, scores, cost_result, multi_tool_result,
        survivability_result, difficulty_result, economic_result,
    ) -> str:
        rating = self._rating(overall_score)
        lines = [
            f"Protection Effectiveness Score: {overall_score:.1f}/100 ({rating})",
            "",
            "Component Scores:",
        ]
        for key, score in scores.items():
            lines.append(f"  {key}: {score:.1f}/100")
        lines.extend([
            "",
            f"Cost Model: {cost_result.total_hours}h ({cost_result.cost_class})",
            f"Multi-Tool: {multi_tool_result['composite_score']:.1f}/100 "
            f"(tools: {len(multi_tool_result.get('tools_available', []))} real, "
            f"{len(multi_tool_result.get('tools_simulated', []))} simulated)",
        ])
        if survivability_result.combined_index is not None:
            lines.append(
                f"Survivability: {survivability_result.combined_index:.4f} "
                f"(layers: {', '.join(survivability_result.active_layers)})"
            )
        economic_decision = economic_result.get('attacker_decision', 'unknown')
        lines.append(
            f"Economic: ${economic_result.get('total_attack_cost', 0):,.2f} attack cost "
            f"({economic_decision})"
        )
        lines.append("")
        lines.append("Break-even Analysis:")
        be = economic_result.get('break_even_analysis', {})
        lines.append(f"  Software Value: ${be.get('software_value', 0):,.2f}")
        lines.append(f"  IP Value: ${be.get('ip_value', 0):,.2f}")
        lines.append(f"  Cost/Value Ratio: {be.get('cost_vs_value_ratio', 0):.2f}x")
        lines.append(f"  Break-even: {'YES' if be.get('break_even') else 'NO'}")
        return '\n'.join(lines)

    def to_json(self, result: dict) -> str:
        return json.dumps(result, indent=2, default=str)

    @staticmethod
    def _rating(score: float) -> str:
        if score >= 85:
            return 'Excellent'
        if score >= 70:
            return 'Good'
        if score >= 50:
            return 'Moderate'
        if score >= 30:
            return 'Weak'
        return 'Poor'
