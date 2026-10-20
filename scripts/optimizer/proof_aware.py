from __future__ import annotations

from typing import Optional

from .cost_optimizer import CostOptimizer, PROTECTION_COSTS, CLASSIFICATION_MAP
from .profiler import FunctionInfo

PROOF_CONFIDENCE_BONUS = 0.25
UNPROVEN_PENALTY = 0.15

PROVEN_PROTECTIONS: dict[str, float] = {
    "ast_rename": 0.9,
    "ast_dead_code": 0.85,
    "ast_mba": 0.75,
    "cfg_flatten": 0.7,
    "opaque_predicates": 0.65,
}

UNPROVEN_PROTECTIONS: dict[str, float] = {
    "vm_exec": 0.3,
    "jit_compile": 0.35,
    "rop_exec": 0.25,
    "oram_exec": 0.2,
    "fragment": 0.4,
    "data_obfuscation": 0.5,
    "string_encoding": 0.55,
    "control_flow_integrity": 0.45,
}


class ProofAwareOptimizer(CostOptimizer):
    def __init__(
        self,
        max_overhead_pct: float = 20.0,
        max_size_mult: float = 3.0,
        min_security: float = 0.5,
    ):
        super().__init__(max_overhead_pct, max_size_mult, min_security)
        self._confidence_map: dict[str, float] = {}
        for p, conf in PROVEN_PROTECTIONS.items():
            self._confidence_map[p] = conf
        for p, conf in UNPROVEN_PROTECTIONS.items():
            self._confidence_map[p] = conf

    def update_proof_status(self, proof_results: dict[str, bool]):
        for protection, has_proof in proof_results.items():
            if has_proof:
                self._confidence_map[protection] = PROVEN_PROTECTIONS.get(protection, 0.7)
            else:
                self._confidence_map[protection] = UNPROVEN_PROTECTIONS.get(protection, 0.3)

    def _proof_adjusted_security(self, protection: str) -> float:
        base_cost = PROTECTION_COSTS.get(protection, {})
        base_security = base_cost.get("security", 0.0)
        confidence = self._confidence_map.get(protection, 0.5)
        if confidence >= 0.7:
            adjusted = base_security + PROOF_CONFIDENCE_BONUS
        else:
            adjusted = base_security - UNPROVEN_PENALTY
        return max(0.0, min(1.0, adjusted))

    def optimize_with_proofs(
        self,
        functions: list[FunctionInfo],
        proofs: dict[str, bool],
        budget: Optional[dict[str, float]] = None,
    ) -> dict[str, list[str]]:
        if budget:
            self.max_overhead = budget.get("max_cpu_overhead", self.max_overhead * 100) / 100.0
            self.max_size_mult = budget.get("max_size_mult", self.max_size_mult)
            self.min_security = budget.get("min_security", self.min_security)

        self.update_proof_status(proofs)

        valid_passes = [p for p in PROTECTION_COSTS.keys()]

        function_weights = {}
        for fn in functions:
            weight = fn.exec_frequency * max(fn.lines_of_code, 1)
            function_weights[fn.name] = weight

        total_weight = sum(function_weights.values()) or 1.0
        cpu_budget = self.max_overhead * total_weight
        size_budget = (self.max_size_mult - 1.0) * total_weight

        assignment = self._proof_aware_knapsack(
            functions, valid_passes, function_weights, cpu_budget, size_budget, proofs
        )

        for fn in functions:
            if fn.name not in assignment or not assignment[fn.name]:
                assignment.setdefault(fn.name, []).append("ast_rename")

        return assignment

    def _proof_aware_knapsack(
        self,
        functions: list[FunctionInfo],
        passes: list[str],
        weights: dict[str, float],
        cpu_budget: float,
        size_budget: float,
        proofs: dict[str, bool],
    ) -> dict[str, list[str]]:
        candidates = []
        for fn in functions:
            preferred = CLASSIFICATION_MAP.get(fn.category, ["ast_rename", "ast_dead_code"])
            for p in passes:
                if p not in PROTECTION_COSTS:
                    continue
                cost = PROTECTION_COSTS[p]
                adjusted_security = self._proof_adjusted_security(p)
                cpu_cost = cost["cpu"] - 1.0
                size_cost = cost["size"] - 1.0
                density = adjusted_security / max(cpu_cost + size_cost, 0.01)
                is_preferred = p in preferred
                has_proof = proofs.get(p, False)
                proof_mult = 1.5 if has_proof else 0.7
                candidates.append({
                    "fn": fn.name,
                    "pass": p,
                    "security": adjusted_security,
                    "cpu_cost": cpu_cost,
                    "size_cost": size_cost,
                    "density": density * proof_mult * (1.5 if is_preferred else 1.0),
                    "preferred": is_preferred,
                    "has_proof": has_proof,
                })

        candidates.sort(key=lambda x: (-x["density"], x["has_proof"], -x["security"]))

        assignment: dict[str, list[str]] = {fn.name: [] for fn in functions}
        used_cpu = 0.0
        used_size = 0.0

        proven_first = [c for c in candidates if c["has_proof"]]
        unproven = [c for c in candidates if not c["has_proof"]]
        prioritized = proven_first + unproven

        for c in prioritized:
            fn_weight = weights.get(c["fn"], 1.0)
            inc_cpu = c["cpu_cost"] * fn_weight
            inc_size = c["size_cost"] * fn_weight
            if (
                used_cpu + inc_cpu <= cpu_budget * 1.1
                and used_size + inc_size <= size_budget * 1.1
            ):
                if c["pass"] not in assignment[c["fn"]]:
                    assignment[c["fn"]].append(c["pass"])
                    used_cpu += inc_cpu
                    used_size += inc_size

        for fn_name in assignment:
            proven_avail = [
                p for p in assignment[fn_name]
                if proofs.get(p, False)
            ]
            if not proven_avail and any(proofs.values()):
                for c in proven_first:
                    if c["fn"] == fn_name and c["pass"] not in assignment[fn_name]:
                        fn_weight = weights.get(fn_name, 1.0)
                        inc_cpu = c["cpu_cost"] * fn_weight
                        inc_size = c["size_cost"] * fn_weight
                        if (
                            used_cpu + inc_cpu <= cpu_budget * 1.1
                            and used_size + inc_size <= size_budget * 1.1
                        ):
                            assignment[fn_name].append(c["pass"])
                            used_cpu += inc_cpu
                            used_size += inc_size
                            break

            if "ast_rename" not in assignment[fn_name]:
                assignment[fn_name].append("ast_rename")

        return assignment

    def generate_proof_report(
        self,
        functions: list[FunctionInfo],
        assignment: dict[str, list[str]],
        proofs: dict[str, bool],
    ) -> str:
        lines = []
        W = 66
        lines.append("┌" + "─" * W + "┐")
        lines.append("│  Proof-Aware Optimizer Report" + " " * (W - 32) + "│")
        lines.append("├" + "─" * W + "┤")
        lines.append(f"│  Max CPU Overhead:  {self.max_overhead*100:>5.1f}%"
                     f"    Max Size: {self.max_size_mult:>4.1f}x{'':>10s}│")
        lines.append(f"│  Min Security:      {self.min_security:>5.2f}{'':>46s}│")
        lines.append("├" + "─" * W + "┤")
        lines.append("│  Protection Proof Status:" + " " * (W - 27) + "│")

        for p in sorted(PROTECTION_COSTS.keys()):
            has_proof = proofs.get(p, False)
            conf = self._confidence_map.get(p, 0.5)
            icon = "✓" if has_proof else "✗"
            status = f"   {icon} {p:<28s} conf={conf:.2f}"
            lines.append("│" + status + " " * (W - len(status) - 1) + "│")

        lines.append("├" + "─" * W + "┤")
        lines.append("│  Function Assignments:" + " " * (W - 24) + "│")

        for fn in sorted(functions, key=lambda f: -len(assignment.get(f.name, []))):
            passes = assignment.get(fn.name, [])
            proven = sum(1 for p in passes if proofs.get(p, False))
            label = f"    {fn.name:<20s} [{', '.join(passes[:4])}]"
            if proven:
                label += f" ({proven} proven)"
            lines.append("│" + label + " " * (W - len(label) - 1) + "│")

        lines.append("└" + "─" * W + "┘")
        return "\n".join(lines)

    def optimize(self, functions: list[FunctionInfo], available_passes: list[str]) -> dict[str, list[str]]:
        return self.optimize_with_proofs(functions, {}, None)
