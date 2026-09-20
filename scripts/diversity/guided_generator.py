"""
Item 79: AI-Guided Diversity Generation
Wraps DiversityGenerator with an evolutionary loop: initial population,
fitness evaluation via AIBenchmark, selection, crossover/mutation, iteration.
"""

import ast
import json
import os
import random
import secrets
import shutil
import sys
import tempfile
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.diversity import DiversityGenerator, generate_variant


class GuidedDiversityGenerator:
    def __init__(
        self,
        population_size: int = 10,
        generations: int = 3,
        selection_topk: float = 0.25,
        evolution_history_path: str | None = None,
    ):
        self.population_size = population_size
        self.generations = generations
        self.selection_topk = selection_topk
        self.evolution_history_path = evolution_history_path or os.path.join(
            _ROOT, "build", "diversity_evolution.json"
        )
        self._history: list[dict[str, Any]] = []
        self._base_generator = DiversityGenerator()

    def evolve(self, source_path: str, output_dir: str) -> list[str]:
        os.makedirs(output_dir, exist_ok=True)
        try:
            from scripts.benchmark.ai_eval import AIBenchmark
            benchmark = AIBenchmark()
        except ImportError:
            benchmark = None

        with open(source_path, encoding="utf-8") as f:
            source = f.read()

        pop_dir = os.path.join(output_dir, "population")
        os.makedirs(pop_dir, exist_ok=True)

        pop_paths = self._base_generator.generate(
            source_path, self.population_size, pop_dir
        )

        for gen in range(self.generations):
            gen_dir = os.path.join(output_dir, f"gen_{gen}")
            os.makedirs(gen_dir, exist_ok=True)

            scores = self._evaluate_population(pop_paths, source_path, benchmark)
            self._record_generation(gen, pop_paths, scores)

            sorted_indices = sorted(
                range(len(scores)), key=lambda i: scores[i], reverse=True
            )
            num_parents = max(2, int(len(pop_paths) * self.selection_topk))
            parent_indices = sorted_indices[:num_parents]
            parent_paths = [pop_paths[i] for i in parent_indices]

            if gen == self.generations - 1:
                break

            new_pop_paths: list[str] = []
            num_offspring = max(1, self.population_size - num_parents)

            for i in range(num_offspring):
                p1_idx = parent_indices[i % len(parent_indices)]
                p2_idx = parent_indices[(i + 1) % len(parent_indices)]
                child_path = self._create_offspring(
                    pop_paths[p1_idx], pop_paths[p2_idx], i, gen_dir
                )
                if child_path:
                    new_pop_paths.append(child_path)

            pop_paths = parent_paths[:num_parents] + new_pop_paths[:self.population_size - num_parents]
            if len(pop_paths) < self.population_size:
                extra = self._base_generator.generate(
                    source_path,
                    self.population_size - len(pop_paths),
                    gen_dir,
                )
                pop_paths.extend(extra)

            for p in pop_paths:
                if os.path.exists(p) and os.path.dirname(p) != gen_dir:
                    shutil.copy2(p, gen_dir)

        self._save_history()
        return pop_paths

    def _evaluate_population(
        self, paths: list[str], source_path: str, benchmark
    ) -> list[float]:
        scores: list[float] = []
        for p in paths:
            if not os.path.exists(p):
                scores.append(0.0)
                continue
            if benchmark is None:
                with open(p) as f:
                    try:
                        ast.parse(f.read())
                        scores.append(0.5)
                    except SyntaxError:
                        scores.append(0.0)
            else:
                try:
                    results = benchmark.evaluate(source_path, p)
                    scores.append(results.get("overall", 0.0))
                except Exception:
                    scores.append(0.0)
        return scores

    def _create_offspring(
        self, parent_a_path: str, parent_b_path: str, index: int, output_dir: str
    ) -> str | None:
        try:
            with open(parent_a_path) as f:
                code_a = f.read()
            seed_a = hash(code_a) & 0xFFFFFFFF
            seed_b = hash(open(parent_b_path).read()) & 0xFFFFFFFF
            child_seed = seed_a ^ seed_b ^ index
            options = self._evolve_pass_set(code_a, child_seed)
            child_code = generate_variant(code_a, index, {
                "master_seed": child_seed,
                "pass_sets": [options],
            })
            child_path = os.path.join(output_dir, f"offspring_{index:04d}.py")
            with open(child_path, "w") as f:
                f.write(child_code)
            return child_path
        except Exception:
            return None

    def _evolve_pass_set(self, code: str, seed: int) -> list[str]:
        base_sets = [
            ["rename", "dead_code", "mba", "cfg_flatten"],
            ["rename", "dead_code", "opaque_pred", "string_encode"],
            ["rename", "mba", "cfg_flatten", "opaque_pred", "string_encode"],
            ["rename", "dead_code", "mba", "cfg_flatten", "opaque_pred", "string_encode", "exception_flow"],
        ]
        rng = random.Random(seed)
        chosen = list(rng.choice(base_sets))
        if rng.random() < 0.3:
            extra = rng.choice(["bogus_exceptions", "split_vars", "exception_flow"])
            chosen.append(extra)
        if rng.random() < 0.2:
            chosen.remove(rng.choice(chosen))
        return chosen

    def _record_generation(
        self, gen: int, paths: list[str], scores: list[float]
    ):
        self._history.append({
            "generation": gen,
            "population_size": len(paths),
            "scores": [
                {"path": p, "score": s} for p, s in zip(paths, scores)
            ],
            "mean_score": round(
                sum(scores) / max(len(scores), 1), 4
            ),
        })

    def _save_history(self):
        os.makedirs(os.path.dirname(self.evolution_history_path), exist_ok=True)
        with open(self.evolution_history_path, "w") as f:
            json.dump(self._history, f, indent=2)

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._history)
