#!/usr/bin/env python3
"""
Compiler Mutation Engine — evolves compiler configuration based on
deobfuscation agent feedback to create self-improving obfuscation.
"""

import copy
import hashlib
import json
import os
import secrets
from typing import List


class CompilerMutationEngine:
    def __init__(self, config: dict):
        self.config = config
        self.seed = config.get("seed", None)
        # secrets does not support seeding; crypto-grade randomness used directly
        self.feedback_history = config.get("feedback_history", [])
        self.mba_cache = {}

    def mutate_pass_parameters(self, feedback: dict, current_params: dict) -> dict:
        params = copy.deepcopy(current_params)
        weaknesses = feedback.get("weaknesses", [])

        for weakness in weaknesses:
            if weakness == "opaque_predicates_too_simple":
                params["opaque_predicate_nesting"] = params.get("opaque_predicate_nesting", 1) + 1
                params["opaque_predicate_vars"] = params.get("opaque_predicate_vars", 2) + 2
                params["opaque_predicate_comparison"] = secrets.choice(
                    ["eq", "ne", "sgt", "slt", "sge", "sle"]
                )

            elif weakness == "mba_patterns_detectable":
                params["mba_bit_width"] = min(
                    params.get("mba_bit_width", 32) * 2,
                    128
                )
                params["mba_ops_per_expr"] = params.get("mba_ops_per_expr", 4) + 3

            elif weakness == "cfg_flattening_too_few_cases":
                params["flattening_switch_cases"] = params.get("flattening_switch_cases", 4) + 4
                params["flattening_random_dispatchers"] = (
                    params.get("flattening_random_dispatchers", 0) + 1
                )

            elif weakness == "constant_folding_possible":
                params["use_dynamic_values"] = True
                params["constant_indirection"] = params.get("constant_indirection", 0) + 2

            elif weakness == "insufficient_dead_code":
                params["dead_code_ratio"] = min(
                    params.get("dead_code_ratio", 0.3) + 0.15,
                    0.9
                )

        return params

    def generate_novel_mba_formula(self, seed: int, complexity: int) -> str:
        cache_key = f"{seed}_{complexity}"
        if cache_key in self.mba_cache:
            return self.mba_cache[cache_key]

        ops = ["ADD", "XOR", "SUB", "AND", "OR", "SHL", "SHR"]
        num_ops = max(3, complexity * 4)

        variables = ["x", "y", "z", "w"]
        rhs_vars = [secrets.choice(variables) for _ in range(num_ops + 1)]
        lhs_vars = [f"t{i}" for i in range(num_ops)]

        steps = []
        for i in range(num_ops):
            op = secrets.choice(ops)
            a = rhs_vars[i] if i == 0 else lhs_vars[i - 1]
            b = rhs_vars[i + 1]
            if op == "ADD":
                steps.append(f"{lhs_vars[i]} = {a} + {b}")
            elif op == "XOR":
                steps.append(f"{lhs_vars[i]} = {a} ^ {b}")
            elif op == "SUB":
                steps.append(f"{lhs_vars[i]} = {a} - {b}")
            elif op == "AND":
                steps.append(f"{lhs_vars[i]} = {a} & {b}")
            elif op == "OR":
                steps.append(f"{lhs_vars[i]} = {a} | {b}")
            elif op == "SHL":
                shift = secrets.randbelow(4) + 1
                steps.append(f"{lhs_vars[i]} = {a} << {shift}")
            elif op == "SHR":
                shift = secrets.randbelow(4) + 1
                steps.append(f"{lhs_vars[i]} = {a} >> {shift}")

        result_var = lhs_vars[-1]
        formula = f"((({')\\n  '.join(steps)}))"
        result = f"def mba_{seed}({', '.join(variables)}):\n  {formula}\n  return {result_var}"

        self.mba_cache[cache_key] = result
        return result

    def evolve(self, current_config: dict, feedback: dict) -> dict:
        evolved = copy.deepcopy(current_config)

        ollvm = evolved.get("llvmgen", {})
        ollvm_params = ollvm.get("pass_parameters", {})
        ollvm_params = self.mutate_pass_parameters(feedback, ollvm_params)
        ollvm["pass_parameters"] = ollvm_params
        evolved["llvmgen"] = ollvm

        obfuscator = evolved.get("obfuscator", {})
        weaknesses = feedback.get("weaknesses", [])

        if "opaque_predicates_too_simple" in weaknesses:
            obfuscator["opaque_predicates"] = True
        if "mba_patterns_detectable" in weaknesses:
            obfuscator["mba_subs"] = True
        if "cfg_flattening_too_few_cases" in weaknesses:
            obfuscator["cfg_flatten"] = True
        if "insufficient_dead_code" in weaknesses:
            obfuscator["bogus_exceptions"] = True

        evolved["obfuscator"] = obfuscator

        if "seed" in evolved and evolved["seed"] is not None:
            evolved["seed"] = hashlib.sha256(
                str(evolved["seed"]).encode() + str(feedback.get("deobfuscation_score", 0.5)).encode()
            ).hexdigest()[:16]

        self.feedback_history.append({
            "config": evolved,
            "feedback": feedback,
        })

        return evolved


def simulate_build_iteration(initial_config: dict, iterations: int = 10) -> List[dict]:
    from scripts.deobfuscation_agent import DeobfuscationAgent

    engine = CompilerMutationEngine(initial_config)
    agent = DeobfuscationAgent(initial_config)
    history = []

    config = copy.deepcopy(initial_config)

    for i in range(iterations):
        ir_path = config.get("_ir_path", None)

        if ir_path and os.path.exists(ir_path):
            report = agent.analyze_obfuscated_ir(ir_path)
        else:
            report = agent.analyze_obfuscated_ast(
                f"# simulated iteration {i}\nx = (1 + 2) ^ 3\ny = x & 0xFF\n"
            )

        feedback = agent.generate_feedback(report)

        config = engine.evolve(config, feedback)

        sim_ir = f"; Simulated IR iteration {i}\n"
        sim_ir += f"; score: {report.deobfuscation_score:.2f}\n"
        sim_ir += f"; weaknesses: {feedback['weaknesses']}\n"

        history.append({
            "iteration": i,
            "score": report.deobfuscation_score,
            "feedback": feedback,
            "config": copy.deepcopy(config),
        })

    return history


if __name__ == "__main__":
    import sys
    config = {"seed": 42, "llvmgen": {"pass_parameters": {}}, "obfuscator": {}}
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    history = simulate_build_iteration(config, iterations)
    for h in history:
        print(f"Iteration {h['iteration']:2d}: score={h['score']:.2f}  weaknesses={h['feedback']['weaknesses']}")
