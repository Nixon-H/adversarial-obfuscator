"""
optimizer.py

Purpose:
Multi-strategy protection optimizer providing greedy, knapsack (DP),
and genetic algorithm approaches to select optimal protection sets
under security, overhead, and size constraints.

Architectural Role:
Advanced optimizer for the synthesis engine. Offers three strategies:
- optimize_with_greedy: fast, prioritizes security gain per cost ratio
- optimize_with_knapsack: optimal under combined overhead+size budget
- optimize_with_genetic: explores non-convex solution spaces

Execution Context:
Instantiated with the PROTECTION_COSTS dict. Each strategy returns a
ProtectionPlan. The caller (e.g., build pipeline) chooses which
strategy to use based on the desired trade-off between speed and
optimality.

Dependencies:
- engine (ProtectionPlan, ProtectionCost)
- Standard library (copy, math, random, typing)

Security Relevance:
The knapsack optimizer provides the theoretical optimal protection
set for a given overhead+size budget (assuming cost independence).
The genetic algorithm explores solutions the greedy solver would
miss, potentially finding higher-security plans at similar cost.

Maintenance Notes:
- The knapsack DP uses discretized budgets (overhead * 10, size * 200).
  This quantization may cause small rounding errors.
- The genetic algorithm uses a simple crossover (union of two parents)
  and mutation (add/remove protections). For complex constraints,
  a more sophisticated GA with constraint-handling may be needed.
- Pareto frontier filtering in pareto_frontier() is O(n^2); for
  large populations, a sweep-line algorithm is more efficient.
"""

from __future__ import annotations

import copy  # noqa: F401 (this line binds a name used by an embedded template)
import math  # noqa: F401 (this line binds a name used by an embedded template)
import random
from typing import Dict, List, Tuple

from scripts.synthesis.engine import ProtectionPlan, ProtectionCost

class ProtectionOptimizer:
    def __init__(self, costs: Dict[str, ProtectionCost]):
        self._costs = dict(costs)
        self._base_protections = [
            "cfg_flatten", "opaque_predicates", "mba_subs",
            "bogus_exceptions", "fragment_strings", "unicode_ids",
        ]

    def _validate(self, plan: ProtectionPlan) -> bool:
        if not plan.protections:
            return True
        pset = set(plan.protections)
        for p in plan.protections:
            cost = self._costs.get(p)
            if cost is None:
                continue
            for c in cost.conflicts:
                if c in pset:
                    return False
            for prereq in cost.prerequisites:
                if prereq in pset:
                    return False
        return True

    def _score(self, plan: ProtectionPlan, targets: Dict[str, float]) -> float:
        max_overhead = targets.get("max_overhead", 50.0)
        max_size = targets.get("max_size", 3.0)

        if plan.expected_overhead > max_overhead * 1.5:
            return -1e9
        if plan.expected_size_multiplier > max_size * 1.5:
            return -1e9

        security_score = plan.expected_security_score
        overhead_penalty = max(0, plan.expected_overhead - max_overhead) * 2.0
        size_penalty = max(0, plan.expected_size_multiplier - max_size) * 20.0

        return security_score - overhead_penalty - size_penalty

    def optimize_with_greedy(self, targets: Dict[str, float]) -> ProtectionPlan:
        plan = ProtectionPlan()
        plan.protections = list(self._base_protections)

        candidates = []
        for name, cost in self._costs.items():
            if name in self._base_protections:
                continue
            score_per_cost = cost.security_gain / max(cost.overhead_percent + cost.size_multiplier * 10, 0.1)
            candidates.append((score_per_cost, name, cost))

        candidates.sort(key=lambda x: x[0], reverse=True)

        max_overhead = targets.get("max_overhead", 50.0)
        max_size = targets.get("max_size", 3.0)

        added = set(self._base_protections)
        for _, name, cost in candidates:
            if name in added:
                continue

            trial_protections = plan.protections + [name]
            trial_overhead = self._compute_total_overhead(trial_protections)
            trial_size = self._compute_total_size(trial_protections)

            if trial_overhead > max_overhead:
                continue
            if trial_size > max_size:
                continue

            trial_plan = ProtectionPlan(protections=trial_protections)
            if not self._validate(trial_plan):
                continue

            plan.protections.append(name)
            added.add(name)
            plan.rationale[name] = f"Greedy: score/cost ratio {score_per_cost:.2f}"

        plan.expected_security_score = self._compute_total_security(plan.protections)
        plan.expected_overhead = self._compute_total_overhead(plan.protections)
        plan.expected_size_multiplier = self._compute_total_size(plan.protections)
        return plan

    def optimize_with_knapsack(self, targets: Dict[str, float]) -> ProtectionPlan:
        max_overhead = targets.get("max_overhead", 50.0)
        max_size = targets.get("max_size", 3.0)

        items: List[Tuple[str, float, float, float, float]] = []
        for name, cost in self._costs.items():
            if name in self._base_protections:
                continue
            overhead_cost = cost.overhead_percent
            size_cost = (cost.size_multiplier - 1.0) * 100
            combined_cost = overhead_cost + size_cost
            if combined_cost <= 0:
                combined_cost = 0.1
            items.append((name, cost.security_gain, overhead_cost, size_cost, combined_cost))

        n = len(items)
        overhead_budget = int(max_overhead * 10)
        size_budget = int((max_size - 1.0) * 200)
        dp = [[[0 for _ in range(size_budget + 1)] for _ in range(overhead_budget + 1)] for _ in range(n + 1)]
        choice = [[[None for _ in range(size_budget + 1)] for _ in range(overhead_budget + 1)] for _ in range(n + 1)]

        for i in range(1, n + 1):
            name, gain, ov_cost, sz_cost, _ = items[i - 1]
            ov_cost_int = max(1, int(ov_cost * 10))
            sz_cost_int = max(1, int(sz_cost))
            for o in range(overhead_budget + 1):
                for s in range(size_budget + 1):
                    dp[i][o][s] = dp[i - 1][o][s]
                    choice[i][o][s] = None
                    if o >= ov_cost_int and s >= sz_cost_int:
                        val = dp[i - 1][o - ov_cost_int][s - sz_cost_int] + int(gain * 10)
                        if val > dp[i][o][s]:
                            dp[i][o][s] = val
                            choice[i][o][s] = True

        o, s = overhead_budget, size_budget
        selected = []
        for i in range(n, 0, -1):
            if choice[i][o][s]:
                name, _, ov_cost, sz_cost, _ = items[i - 1]
                selected.append(name)
                o -= max(1, int(ov_cost * 10))
                s -= max(1, int(sz_cost))

        plan = ProtectionPlan()
        plan.protections = list(self._base_protections) + selected
        plan.expected_security_score = self._compute_total_security(plan.protections)
        plan.expected_overhead = self._compute_total_overhead(plan.protections)
        plan.expected_size_multiplier = self._compute_total_size(plan.protections)
        for s in selected:
            plan.rationale[s] = "Knapsack: optimal under combined overhead+size budget"
        return plan

    def optimize_with_genetic(
        self,
        targets: Dict[str, float],
        population: int = 50,
        generations: int = 100,
    ) -> ProtectionPlan:
        all_protections = [n for n in self._costs if n not in self._base_protections]
        pop: List[List[str]] = []
        for _ in range(population):
            extra = [p for p in all_protections if random.random() < 0.3]
            pop.append(list(self._base_protections) + extra)

        def make_plan(prots: List[str]) -> ProtectionPlan:
            p = ProtectionPlan(protections=prots)
            p.expected_security_score = self._compute_total_security(prots)
            p.expected_overhead = self._compute_total_overhead(prots)
            p.expected_size_multiplier = self._compute_total_size(prots)
            return p

        best_plan = make_plan(list(self._base_protections))
        best_score = -1e9

        for gen in range(generations):
            scored: List[Tuple[float, List[str]]] = []
            for prots in pop:
                plan = make_plan(prots)
                score = self._score(plan, targets)
                if score > best_score and self._validate(plan):
                    best_score = score
                    best_plan = plan
                scored.append((score, prots))

            scored.sort(key=lambda x: x[0], reverse=True)
            keep = max(2, population // 5)
            parents = [s[1] for s in scored[:keep]]

            new_pop = list(parents)
            while len(new_pop) < population:
                p1 = random.choice(parents)
                p2 = random.choice(parents)
                split = random.randint(0, min(len(p1), len(p2)))
                child = list(set(p1[:split] + p2[split:]))
                if random.random() < 0.2:
                    if child and random.random() < 0.5:
                        child.remove(random.choice(child))
                    else:
                        extra = [p for p in all_protections if p not in child and random.random() < 0.3]
                        child.extend(extra)
                if not child:
                    child = list(self._base_protections)
                new_pop.append(child)
            pop = new_pop

        return best_plan

    def pareto_frontier(self, plans: List[ProtectionPlan]) -> List[ProtectionPlan]:
        points = [(i, p.expected_security_score, p.expected_overhead, p.expected_size_multiplier) for i, p in enumerate(plans)]
        pareto: List[int] = []
        for i in range(len(points)):
            dominated = False
            _, si, oi, mi = points[i]
            for j in range(len(points)):
                if i == j:
                    continue
                _, sj, oj, mj = points[j]
                if sj >= si and oj <= oi and mj <= mi and (sj > si or oj < oi or mj < mi):
                    dominated = True
                    break
            if not dominated:
                pareto.append(i)
        return [plans[i] for i in pareto]

    def score_plan(self, plan: ProtectionPlan, targets: Dict[str, float]) -> float:
        return self._score(plan, targets)

    def _compute_total_security(self, protections: List[str]) -> float:
        total = 0.0
        for p in protections:
            cost = self._costs.get(p)
            if cost is not None:
                total += cost.security_gain
        return min(total, 100.0)

    def _compute_total_overhead(self, protections: List[str]) -> float:
        total = 0.0
        for p in protections:
            cost = self._costs.get(p)
            if cost is not None:
                total += cost.overhead_percent
        return round(total, 2)

    def _compute_total_size(self, protections: List[str]) -> float:
        mult = 1.0
        for p in protections:
            cost = self._costs.get(p)
            if cost is not None:
                mult *= cost.size_multiplier
        return round(mult, 4)
