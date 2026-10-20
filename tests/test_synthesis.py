"""
test_synthesis.py

Tests for Protection Synthesis Engine (Feature 150).

Test Categories:
- Positive tests verify cost models, plan generation, optimization algorithms
  (greedy, knapsack, genetic), flag generation, report generation, and comparison.
- Negative tests verify zero-resource limits, excessive protection costs,
  and no-valid-plan scenarios.

Coverage:
- ProtectionCost dataclass: security gain, overhead, size, conflicts, prerequisites
- ProtectionPlan dataclass: protections, scoring, flags, rationale
- SynthesisEngine: cost loading, security/overhead/size computation, conflict detection
- Optimization: greedy, knapsack, genetic algorithms
- Pareto frontier analysis
- CLI flag generation from plans
- Plan comparison (delta, shared protections)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.synthesis import (
    SynthesisEngine,
    ProtectionPlan,
    ProtectionCost,
    ProtectionOptimizer,
    optimize_protections,
    plan_to_cli_args,
    PROTECTION_COSTS,
)


def test_protection_cost():
    cost = ProtectionCost(
        name="test_protection",
        security_gain=50.0,
        overhead_percent=20.0,
        size_multiplier=2.0,
        conflicts=["other_protection"],
        prerequisites=["base_feature"],
        category="test",
    )
    assert cost.name == "test_protection"
    assert cost.security_gain == 50.0
    assert cost.overhead_percent == 20.0
    assert cost.size_multiplier == 2.0
    assert "other_protection" in cost.conflicts
    assert "base_feature" in cost.prerequisites
    assert cost.category == "test"


def test_protection_plan():
    plan = ProtectionPlan(
        protections=["cfg_flatten", "mba_subs"],
        expected_security_score=55.0,
        expected_overhead=20.0,
        expected_size_multiplier=2.4,
        flags={"synthesis-enable-cfg-flatten": True},
        rationale={"cfg_flatten": "Good gain"},
        timestamp="2025-01-01T00:00:00",
    )
    assert len(plan.protections) == 2
    assert plan.expected_security_score == 55.0
    assert plan.expected_overhead == 20.0
    assert plan.expected_size_multiplier == 2.4
    assert plan.flags["synthesis-enable-cfg-flatten"] is True
    assert plan.rationale["cfg_flatten"] == "Good gain"


def test_engine_load_costs():
    engine = SynthesisEngine()
    engine.load_protection_costs()
    assert len(engine._costs) > 0
    assert "cfg_flatten" in engine._costs
    assert "mba_subs" in engine._costs


def test_engine_compute_security():
    engine = SynthesisEngine()
    engine.load_protection_costs()
    plan = ProtectionPlan(protections=["cfg_flatten", "opaque_predicates"])
    score = engine.compute_security_score(plan)
    expected = engine._costs["cfg_flatten"].security_gain + engine._costs["opaque_predicates"].security_gain
    assert score == min(expected, 100.0)
    assert score > 0


def test_engine_compute_overhead():
    engine = SynthesisEngine()
    engine.load_protection_costs()
    plan = ProtectionPlan(protections=["cfg_flatten", "opaque_predicates"])
    overhead = engine.compute_overhead(plan)
    expected = engine._costs["cfg_flatten"].overhead_percent + engine._costs["opaque_predicates"].overhead_percent
    assert overhead == expected


def test_engine_compute_size():
    engine = SynthesisEngine()
    engine.load_protection_costs()
    plan = ProtectionPlan(protections=["cfg_flatten", "opaque_predicates"])
    size = engine.compute_size(plan)
    expected = engine._costs["cfg_flatten"].size_multiplier * engine._costs["opaque_predicates"].size_multiplier
    assert size == round(expected, 4)


def test_engine_check_conflicts():
    engine = SynthesisEngine()
    engine.load_protection_costs()
    plan = ProtectionPlan(protections=["cfg_flatten", "no_cfg_flatten"])
    conflicts = engine.check_conflicts(plan)
    assert len(conflicts) > 0
    assert any("cfg_flatten" in c and "no_cfg_flatten" in c for c in conflicts)


def test_greedy_optimization():
    engine = SynthesisEngine()
    engine.load_protection_costs()
    plan = engine.solve_optimization(target_security=30.0, max_overhead=30.0, max_size=2.0)
    assert plan is not None
    assert len(plan.protections) > 0
    assert plan.expected_security_score >= 0
    assert plan.expected_overhead >= 0
    assert plan.expected_size_multiplier >= 1.0


def test_knapsack_optimization():
    optimizer = ProtectionOptimizer(PROTECTION_COSTS)
    plan = optimizer.optimize_with_knapsack({
        "target_security": 50.0,
        "max_overhead": 40.0,
        "max_size": 2.5,
    })
    assert plan is not None
    assert len(plan.protections) > 0
    assert plan.expected_security_score >= 0


def test_generate_flags():
    engine = SynthesisEngine()
    engine.load_protection_costs()
    plan = ProtectionPlan(protections=["cfg_flatten", "mba_subs"])
    flags = engine.generate_flags(plan)
    assert isinstance(flags, dict)
    assert "synthesis-plan" in flags
    assert any("cfg" in k for k in flags)


def test_generate_report():
    engine = SynthesisEngine()
    engine.load_protection_costs()
    plan = ProtectionPlan(
        protections=["cfg_flatten"],
        expected_security_score=30.0,
        expected_overhead=5.0,
        expected_size_multiplier=1.2,
    )
    report = engine.generate_report(plan)
    assert "PROTECTION SYNTHESIS REPORT" in report
    assert "cfg_flatten" in report
    assert "30.0" in report


def test_compare_plans():
    engine = SynthesisEngine()
    engine.load_protection_costs()
    plan_a = ProtectionPlan(protections=["cfg_flatten"], expected_security_score=30.0, expected_overhead=5.0, expected_size_multiplier=1.2)
    plan_b = ProtectionPlan(protections=["cfg_flatten", "mba_subs"], expected_security_score=55.0, expected_overhead=20.0, expected_size_multiplier=2.4)
    comparison = engine.compare_plans(plan_a, plan_b)
    assert comparison["security_delta"] > 0
    assert comparison["overhead_delta"] > 0
    assert "cfg_flatten" in comparison["shared_protections"]


def test_plan_to_cli():
    plan = ProtectionPlan(
        protections=["cfg_flatten", "mba_subs"],
        flags={"synthesis-plan": True, "synthesis-enable-cfg-flatten": True},
    )
    args = plan_to_cli_args(plan)
    assert "--cfg-flatten" in args
    assert "--mba-subs" in args
    assert "--synthesis-plan" in args


def test_protection_costs_defined():
    assert len(PROTECTION_COSTS) >= 25
    for name, cost in PROTECTION_COSTS.items():
        assert cost.name == name
        assert 0 <= cost.security_gain <= 100
        assert cost.overhead_percent >= 0
        assert cost.size_multiplier >= 1.0


def test_no_valid_plan():
    engine = SynthesisEngine()
    engine.load_protection_costs()
    plan = engine.solve_optimization(target_security=0.0, max_overhead=0.001, max_size=1.001)
    assert plan is not None
    assert plan.expected_security_score < 1.0 or len(plan.protections) <= len(engine._base_protections)


def test_all_protections_exceeds_limits():
    engine = SynthesisEngine()
    engine.load_protection_costs()
    all_prots = list(PROTECTION_COSTS.keys())
    plan = ProtectionPlan(protections=all_prots)
    overhead = engine.compute_overhead(plan)
    size = engine.compute_size(plan)
    assert overhead > 100
    assert size > 5.0


def test_zero_targets():
    engine = SynthesisEngine()
    engine.load_protection_costs()
    plan = engine.solve_optimization(target_security=0.0, max_overhead=0.0, max_size=1.0)
    assert plan is not None
    assert plan.expected_overhead >= 0
    assert plan.expected_size_multiplier >= 1.0


def test_pareto_frontier():
    optimizer = ProtectionOptimizer(PROTECTION_COSTS)
    plans = [
        ProtectionPlan(protections=["cfg_flatten"], expected_security_score=30.0, expected_overhead=5.0, expected_size_multiplier=1.2),
        ProtectionPlan(protections=["cfg_flatten", "mba_subs"], expected_security_score=55.0, expected_overhead=20.0, expected_size_multiplier=2.4),
        ProtectionPlan(protections=["cfg_flatten", "mba_subs", "fhe_vm"], expected_security_score=90.0, expected_overhead=1020.0, expected_size_multiplier=24.0),
    ]
    pareto = optimizer.pareto_frontier(plans)
    assert len(pareto) > 0


def test_genetic_optimization():
    optimizer = ProtectionOptimizer(PROTECTION_COSTS)
    plan = optimizer.optimize_with_genetic(
        {"target_security": 50.0, "max_overhead": 60.0, "max_size": 3.0},
        population=20,
        generations=10,
    )
    assert plan is not None
    assert len(plan.protections) >= len(optimizer._base_protections)


def test_score_plan():
    optimizer = ProtectionOptimizer(PROTECTION_COSTS)
    plan = ProtectionPlan(
        protections=["cfg_flatten"],
        expected_security_score=30.0,
        expected_overhead=5.0,
        expected_size_multiplier=1.2,
    )
    score = optimizer.score_plan(plan, {"target_security": 50.0, "max_overhead": 30.0, "max_size": 2.0})
    assert score > 0


def test_engine_solve_respects_constraints():
    engine = SynthesisEngine()
    engine.load_protection_costs()
    plan = engine.solve_optimization(target_security=10.0, max_overhead=100.0, max_size=5.0)
    assert plan.expected_overhead <= 110.0
    assert plan.expected_size_multiplier <= 5.5


def test_optimize_protections_function():
    plan = optimize_protections(target_security=50.0, max_overhead=30.0, max_size=2.0)
    assert plan is not None
    assert len(plan.protections) > 0
