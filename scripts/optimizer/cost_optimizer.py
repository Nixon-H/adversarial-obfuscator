import copy
from typing import Dict, List, Tuple

from .profiler import FunctionInfo

PROTECTION_COSTS = {
    'ast_rename': {'cpu': 1.0, 'size': 1.0, 'security': 0.1},
    'ast_dead_code': {'cpu': 1.0, 'size': 1.5, 'security': 0.15},
    'ast_mba': {'cpu': 1.5, 'size': 1.8, 'security': 0.4},
    'cfg_flatten': {'cpu': 1.3, 'size': 2.0, 'security': 0.35},
    'opaque_predicates': {'cpu': 1.2, 'size': 1.5, 'security': 0.3},
    'vm_exec': {'cpu': 10.0, 'size': 3.0, 'security': 0.8},
    'jit_compile': {'cpu': 8.0, 'size': 2.5, 'security': 0.7},
    'rop_exec': {'cpu': 5.0, 'size': 4.0, 'security': 0.9},
    'oram_exec': {'cpu': 20.0, 'size': 5.0, 'security': 0.85},
    'fragment': {'cpu': 3.0, 'size': 2.0, 'security': 0.6},
    'data_obfuscation': {'cpu': 2.0, 'size': 1.5, 'security': 0.5},
    'string_encoding': {'cpu': 1.1, 'size': 1.2, 'security': 0.2},
    'control_flow_integrity': {'cpu': 1.4, 'size': 1.3, 'security': 0.45},
}

CLASSIFICATION_MAP = {
    'simple_helper': ['ast_rename', 'ast_dead_code'],
    'crypto': ['vm_exec', 'string_encoding'],
    'license_check': ['jit_compile', 'opaque_predicates'],
    'key_derivation': ['rop_exec', 'cfg_flatten'],
    'sensitive_algo': ['oram_exec', 'fragment', 'data_obfuscation'],
}


class CostOptimizer:
    def __init__(self, max_overhead_pct: float = 20.0,
                 max_size_mult: float = 3.0,
                 min_security: float = 0.5):
        self.max_overhead = max_overhead_pct / 100.0
        self.max_size_mult = max_size_mult
        self.min_security = min_security

    def optimize(self, functions: List[FunctionInfo],
                 available_passes: List[str]) -> Dict[str, List[str]]:
        valid_passes = [p for p in available_passes if p in PROTECTION_COSTS]
        if not valid_passes:
            return {fn.name: ['ast_rename'] for fn in functions}

        function_weights = {}
        for fn in functions:
            weight = fn.exec_frequency * max(fn.lines_of_code, 1)
            function_weights[fn.name] = weight

        total_weight = sum(function_weights.values()) or 1.0

        cpu_budget = self.max_overhead * total_weight
        size_budget = (self.max_size_mult - 1.0) * total_weight

        assignment = self._greedy_knapsack(functions, valid_passes,
                                            function_weights, cpu_budget, size_budget)

        total_cpu, total_size, total_sec = self._compute_costs(functions, assignment,
                                                                function_weights, total_weight)

        if total_cpu > self.max_overhead or total_size > self.max_size_mult - 1.0:
            assignment = self._tighten_budget(functions, valid_passes, assignment,
                                              function_weights, cpu_budget, size_budget)

        for fn in functions:
            if fn.name not in assignment or not assignment[fn.name]:
                assignment.setdefault(fn.name, []).append('ast_rename')

        return assignment

    def _greedy_knapsack(self, functions: List[FunctionInfo],
                         passes: List[str],
                         weights: Dict[str, float],
                         cpu_budget: float,
                         size_budget: float) -> Dict[str, List[str]]:
        candidates = []
        for fn in functions:
            preferred = CLASSIFICATION_MAP.get(fn.category, ['ast_rename', 'ast_dead_code'])
            for p in passes:
                if p not in PROTECTION_COSTS:
                    continue
                cost = PROTECTION_COSTS[p]
                security_gain = cost['security']
                cpu_cost = cost['cpu'] - 1.0
                size_cost = cost['size'] - 1.0
                density = security_gain / max(cpu_cost + size_cost, 0.01)
                is_preferred = p in preferred
                candidates.append({
                    'fn': fn.name,
                    'pass': p,
                    'security': security_gain,
                    'cpu_cost': cpu_cost,
                    'size_cost': size_cost,
                    'density': density * (1.5 if is_preferred else 1.0),
                    'preferred': is_preferred,
                })

        candidates.sort(key=lambda x: (-x['density'], -x['security']))

        assignment = {fn.name: [] for fn in functions}
        used_cpu = 0.0
        used_size = 0.0

        for c in candidates:
            fn_weight = weights.get(c['fn'], 1.0)
            inc_cpu = c['cpu_cost'] * fn_weight
            inc_size = c['size_cost'] * fn_weight
            if (used_cpu + inc_cpu <= cpu_budget * 1.1
                    and used_size + inc_size <= size_budget * 1.1):
                assignment[c['fn']].append(c['pass'])
                used_cpu += inc_cpu
                used_size += inc_size

        for fn_name in assignment:
            if 'ast_rename' not in assignment[fn_name]:
                assignment[fn_name].append('ast_rename')

        return assignment

    def _tighten_budget(self, functions: List[FunctionInfo],
                        passes: List[str],
                        assignment: Dict[str, List[str]],
                        weights: Dict[str, float],
                        cpu_budget: float,
                        size_budget: float) -> Dict[str, List[str]]:
        fn_security = {}
        for fn in functions:
            sec = sum(
                PROTECTION_COSTS[p]['security']
                for p in assignment.get(fn.name, [])
                if p in PROTECTION_COSTS
            )
            fn_security[fn.name] = sec

        sorted_by_sec = sorted(functions, key=lambda f: fn_security.get(f.name, 0.0))

        new_assignment = {fn.name: ['ast_rename'] for fn in functions}
        used_cpu = 0.0
        used_size = 0.0

        baseline_cost_cpu = sum(
            (PROTECTION_COSTS['ast_rename']['cpu'] - 1.0) * weights.get(fn.name, 1.0)
            for fn in functions
        )
        baseline_cost_size = sum(
            (PROTECTION_COSTS['ast_rename']['size'] - 1.0) * weights.get(fn.name, 1.0)
            for fn in functions
        )
        used_cpu = baseline_cost_cpu
        used_size = baseline_cost_size

        for fn in reversed(sorted_by_sec):
            current = new_assignment[fn.name]
            for p in passes:
                if p == 'ast_rename':
                    continue
                if p in current:
                    continue
                if p not in PROTECTION_COSTS:
                    continue
                cost = PROTECTION_COSTS[p]
                inc_cpu = (cost['cpu'] - 1.0) * weights.get(fn.name, 1.0)
                inc_size = (cost['size'] - 1.0) * weights.get(fn.name, 1.0)
                if (used_cpu + inc_cpu <= cpu_budget
                        and used_size + inc_size <= size_budget):
                    current.append(p)
                    used_cpu += inc_cpu
                    used_size += inc_size

        return new_assignment

    def _compute_costs(self, functions: List[FunctionInfo],
                       assignment: Dict[str, List[str]],
                       weights: Dict[str, float],
                       total_weight: float) -> Tuple[float, float, float]:
        total_cpu = 0.0
        total_size = 0.0
        total_sec = 0.0

        for fn in functions:
            fn_weight = weights.get(fn.name, 1.0)
            for p in assignment.get(fn.name, []):
                if p in PROTECTION_COSTS:
                    cost = PROTECTION_COSTS[p]
                    total_cpu += (cost['cpu'] - 1.0) * fn_weight
                    total_size += (cost['size'] - 1.0) * fn_weight
                    total_sec += cost['security']

        avg_cpu_pct = (total_cpu / total_weight) * 100 if total_weight else 0
        avg_size_mult = (total_size / total_weight) if total_weight else 0

        return avg_cpu_pct, avg_size_mult, total_sec

    def generate_report(self, functions: List[FunctionInfo],
                        assignment: Dict[str, List[str]]) -> str:
        total_weight = sum(f.exec_frequency * max(f.lines_of_code, 1) for f in functions) or 1.0
        weights = {f.name: f.exec_frequency * max(f.lines_of_code, 1) for f in functions}
        cpu_pct, size_mult, sec = self._compute_costs(functions, assignment, weights, total_weight)

        lines = []
        W = 60
        lines.append('┌' + '─' * W + '┐')
        lines.append('│  Protection Cost Optimizer Report' + ' ' * (W - 36) + '│')
        lines.append('├' + '─' * W + '┤')
        lines.append(f'│  Max CPU Overhead:  {self.max_overhead*100:>5.1f}%'
                     f'    Used: {cpu_pct:>5.1f}%{"":>12s}│')
        lines.append(f'│  Max Size Mult:     {self.max_size_mult:>5.1f}x'
                     f'    Used: {1+size_mult:>5.2f}x{"":>12s}│')
        lines.append(f'│  Min Security:      {self.min_security:>5.2f}'
                     f'    Total: {sec:>5.2f}{"":>12s}│')
        lines.append('├' + '─' * W + '┤')
        lines.append('│  Function Assignments:' + ' ' * (W - 24) + '│')

        for fn in sorted(functions, key=lambda f: -len(assignment.get(f.name, []))):
            passes = assignment.get(fn.name, [])
            sec_score = sum(PROTECTION_COSTS.get(p, {}).get('security', 0) for p in passes)
            if len(passes) > 3:
                label = f'    {fn.name:<20s} [{", ".join(passes[:3])}...]'
            else:
                label = f'    {fn.name:<20s} [{", ".join(passes)}]'
            if len(passes) == 0:
                label = f'    {fn.name:<20s} [none]'
            sec_str = f' sec={sec_score:.2f}'
            line = label + sec_str
            lines.append('│' + line + ' ' * (W - len(line) - 1) + '│')

        lines.append('└' + '─' * W + '┘')
        return '\n'.join(lines)
