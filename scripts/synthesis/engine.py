"""
engine.py

Purpose:
Core data structures (ProtectionCost, ProtectionPlan) and the greedy
solver (SynthesisEngine) for the protection synthesis engine. The
solver selects protections from a cost database to meet target
security, overhead, and size constraints.

Architectural Role:
Central solver for protection planning. Part of the synthesis module.
Called by optimize_protections() to produce a ProtectionPlan that is
then converted to CLI arguments via plan_to_cli_args().

Execution Context:
Instantiated with an optional knowledge graph for conflict-aware
planning. The solve_optimization() method implements a greedy
selection algorithm that iteratively adds the highest-ratio
protection that satisfies all constraints.

Dependencies:
- Standard library (copy, datetime, json, dataclasses, typing)
- Optionally: scripts.synthesis.costs (PROTECTION_COSTS)

Security Relevance:
The solver's greedy algorithm selects protections by security gain
per overhead ratio. It is NOT optimal (NP-hard knapsack). For
optimal plans, use ProtectionOptimizer in optimizer.py which provides
dynamic programming and genetic algorithm approaches.

Maintenance Notes:
- The greedy solver in solve_optimization() may produce suboptimal
  plans for tight budgets; use ProtectionOptimizer for production.
- Base protections (cfg_flatten, opaque_predicates, etc.) are always
  included and cannot be excluded by the solver.
- Conflict checking in check_conflicts() also flags prerequisite
  violations (features that require each other).
"""

from __future__ import annotations

import copy
import datetime
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ProtectionCost:
    name: str
    security_gain: float
    overhead_percent: float
    size_multiplier: float
    conflicts: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    category: str = ""


@dataclass
class ProtectionPlan:
    protections: List[str] = field(default_factory=list)
    expected_security_score: float = 0.0
    expected_overhead: float = 0.0
    expected_size_multiplier: float = 1.0
    flags: Dict[str, Any] = field(default_factory=dict)
    rationale: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class SynthesisEngine:
    def __init__(self, knowledge_graph=None):
        self._costs: Dict[str, ProtectionCost] = {}
        self.knowledge_graph = knowledge_graph
        self._base_protections = [
            "cfg_flatten", "opaque_predicates", "mba_subs",
            "bogus_exceptions", "fragment_strings", "unicode_ids",
        ]

    def load_protection_costs(self, costs: Optional[Dict[str, ProtectionCost]] = None) -> None:
        if costs is not None:
            self._costs = costs
        else:
            from scripts.synthesis.costs import PROTECTION_COSTS
            self._costs = dict(PROTECTION_COSTS)

    def compute_security_score(self, plan: ProtectionPlan) -> float:
        if not plan.protections:
            return 0.0
        total = 0.0
        for p in plan.protections:
            cost = self._costs.get(p)
            if cost is not None:
                total += cost.security_gain
        return min(total, 100.0)

    def compute_overhead(self, plan: ProtectionPlan) -> float:
        total = 0.0
        for p in plan.protections:
            cost = self._costs.get(p)
            if cost is not None:
                total += cost.overhead_percent
        return round(total, 2)

    def compute_size(self, plan: ProtectionPlan) -> float:
        mult = 1.0
        for p in plan.protections:
            cost = self._costs.get(p)
            if cost is not None:
                mult *= cost.size_multiplier
        return round(mult, 4)

    def check_conflicts(self, plan: ProtectionPlan) -> List[Tuple[str, str]]:
        conflicts: List[Tuple[str, str]] = []
        protections_set = set(plan.protections)
        for p in plan.protections:
            cost = self._costs.get(p)
            if cost is None:
                continue
            for c in cost.conflicts:
                if c in protections_set:
                    conflicts.append((p, c))
            for prereq in cost.prerequisites:
                if prereq in protections_set:
                    conflicts.append((p, prereq))
        return conflicts

    def solve_optimization(
        self,
        target_security: float,
        max_overhead: float,
        max_size: float,
    ) -> ProtectionPlan:
        plan = ProtectionPlan()
        plan.protections = list(self._base_protections)
        plan.rationale = {p: "Base protection (always included)" for p in self._base_protections}

        candidates = [
            (name, cost)
            for name, cost in self._costs.items()
            if name not in self._base_protections
        ]
        candidates.sort(key=lambda x: x[1].security_gain / max(x[1].overhead_percent, 0.1), reverse=True)

        added = set(self._base_protections)
        changed = True
        while changed:
            changed = False
            for name, cost in candidates:
                if name in added:
                    continue
                trial = ProtectionPlan(protections=list(plan.protections) + [name])
                trial_overhead = self.compute_overhead(trial)
                trial_size = self.compute_size(trial)
                trial_score = self.compute_security_score(trial)
                trial_conflicts = self.check_conflicts(trial)

                if trial_overhead > max_overhead:
                    continue
                if trial_size > max_size:
                    continue
                if trial_conflicts:
                    continue
                if trial_score < target_security and trial_score <= self.compute_security_score(plan):
                    continue

                plan.protections.append(name)
                added.add(name)
                plan.rationale[name] = (
                    f"Security gain: {cost.security_gain}, "
                    f"Overhead: {cost.overhead_percent}%, "
                    f"Size: {cost.size_multiplier}x"
                )
                changed = True
                break

        plan.expected_security_score = self.compute_security_score(plan)
        plan.expected_overhead = self.compute_overhead(plan)
        plan.expected_size_multiplier = self.compute_size(plan)
        plan.flags = self.generate_flags(plan)
        plan.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return plan

    def generate_flags(self, plan: ProtectionPlan) -> Dict[str, Any]:
        flags: Dict[str, Any] = {}
        for p in plan.protections:
            flag_name = p.replace("_protection", "").replace("_", "-")
            flags[f"synthesis-enable-{flag_name}"] = True
        flags["synthesis-plan"] = True
        return flags

    def generate_report(self, plan: ProtectionPlan) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("  PROTECTION SYNTHESIS REPORT")
        lines.append("=" * 60)
        lines.append(f"  Generated: {plan.timestamp}")
        lines.append(f"  Protections: {len(plan.protections)}")
        lines.append(f"  Expected Security Score: {plan.expected_security_score:.1f}/100")
        lines.append(f"  Expected Overhead: {plan.expected_overhead:.1f}%")
        lines.append(f"  Expected Size Multiplier: {plan.expected_size_multiplier:.2f}x")
        lines.append("-" * 60)
        lines.append("  Protection Plan:")
        for p in plan.protections:
            rationale = plan.rationale.get(p, "")
            lines.append(f"    + {p}")
            if rationale:
                lines.append(f"      {rationale}")
        lines.append("-" * 60)
        lines.append("  CLI Flags:")
        for flag, val in sorted(plan.flags.items()):
            lines.append(f"    --{flag}={val}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def compare_plans(self, plan_a: ProtectionPlan, plan_b: ProtectionPlan) -> Dict[str, Any]:
        return {
            "plan_a_protections": len(plan_a.protections),
            "plan_b_protections": len(plan_b.protections),
            "plan_a_security": plan_a.expected_security_score,
            "plan_b_security": plan_b.expected_security_score,
            "plan_a_overhead": plan_a.expected_overhead,
            "plan_b_overhead": plan_b.expected_overhead,
            "plan_a_size": plan_a.expected_size_multiplier,
            "plan_b_size": plan_b.expected_size_multiplier,
            "shared_protections": list(set(plan_a.protections) & set(plan_b.protections)),
            "only_in_a": list(set(plan_a.protections) - set(plan_b.protections)),
            "only_in_b": list(set(plan_b.protections) - set(plan_a.protections)),
            "security_delta": plan_b.expected_security_score - plan_a.expected_security_score,
            "overhead_delta": plan_b.expected_overhead - plan_a.expected_overhead,
            "size_delta": plan_b.expected_size_multiplier - plan_a.expected_size_multiplier,
        }


def plan_to_cli_args(plan: ProtectionPlan) -> List[str]:
    args = []
    for p in plan.protections:
        flag = f"--{p.replace('_', '-')}"
        args.append(flag)
    for flag, val in plan.flags.items():
        if isinstance(val, bool):
            if val:
                args.append(f"--{flag}")
        else:
            args.append(f"--{flag}={val}")
    return args


def optimize_protections(
    target_security: float = 70.0,
    max_overhead: float = 50.0,
    max_size: float = 3.0,
    costs: Optional[Dict[str, ProtectionCost]] = None,
) -> ProtectionPlan:
    engine = SynthesisEngine()
    engine.load_protection_costs(costs)
    return engine.solve_optimization(target_security, max_overhead, max_size)
