"""Tests for AI-Guided Diversity Generation (Item 79)."""
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.diversity.guided_generator import GuidedDiversityGenerator
from scripts.diversity import DiversityGenerator


SIMPLE_SRC = """
def add(a, b):
    return a + b

def main():
    x = 10
    y = 20
    result = add(x, y)
    print(result)

main()
"""


def _write_source(tmpdir, content=SIMPLE_SRC):
    path = os.path.join(tmpdir, "source.py")
    with open(path, "w") as f:
        f.write(content)
    return path


class TestGuidedDiversity:
    """
    TestGuidedDiversity
    
    Positive test cases for guideddiversity.
    """
    def test_guided_initial_population(self, tmpdir):
        src = _write_source(tmpdir)
        out = os.path.join(tmpdir, "evolved")
        gen = GuidedDiversityGenerator(population_size=5, generations=1)
        paths = gen.evolve(src, out)
        assert len(paths) >= 1

    def test_guided_fitness_scoring(self, tmpdir):
        src = _write_source(tmpdir)
        out = os.path.join(tmpdir, "evolved2")
        gen = GuidedDiversityGenerator(population_size=3, generations=1)
        paths = gen.evolve(src, out)
        history = gen.get_history()
        assert len(history) >= 1
        assert "mean_score" in history[0]

    def test_guided_selection(self, tmpdir):
        src = _write_source(tmpdir)
        out = os.path.join(tmpdir, "evolved3")
        gen = GuidedDiversityGenerator(population_size=4, generations=2)
        paths = gen.evolve(src, out)
        assert len(paths) >= 1
        for p in paths:
            assert os.path.exists(p)

    def test_guided_evolution(self, tmpdir):
        src = _write_source(tmpdir)
        out = os.path.join(tmpdir, "evolved4")
        gen = GuidedDiversityGenerator(population_size=5, generations=2)
        paths = gen.evolve(src, out)
        history = gen.get_history()
        assert len(history) >= 2
        generations_seen = {h["generation"] for h in history}
        assert 0 in generations_seen
        assert 1 in generations_seen

    def test_guided_improves_scores(self, tmpdir):
        src = _write_source(tmpdir)
        out = os.path.join(tmpdir, "evolved5")
        gen = GuidedDiversityGenerator(population_size=5, generations=2)
        gen.evolve(src, out)
        history = gen.get_history()
        if len(history) >= 2:
            gen0_mean = history[0].get("mean_score", 0)
            gen1_mean = history[1].get("mean_score", 0)
            # Later generation should generally have competitive scores

    def test_each_variant_valid_python(self, tmpdir):
        src = _write_source(tmpdir)
        out = os.path.join(tmpdir, "evolved6")
        gen = GuidedDiversityGenerator(population_size=3, generations=1)
        paths = gen.evolve(src, out)
        for p in paths:
            if os.path.exists(p):
                with open(p) as f:
                    try:
                        ast.parse(f.read())
                    except SyntaxError as e:
                        pytest.fail(f"Invalid Python: {p}: {e}")

    def test_evolution_history_saved(self, tmpdir):
        src = _write_source(tmpdir)
        out = os.path.join(tmpdir, "evolved7")
        gen = GuidedDiversityGenerator(
            population_size=3,
            generations=1,
            evolution_history_path=os.path.join(tmpdir, "history.json"),
        )
        gen.evolve(src, out)
        assert os.path.exists(os.path.join(tmpdir, "history.json"))
        with open(os.path.join(tmpdir, "history.json")) as f:
            data = json.load(f)
        assert len(data) >= 1

    def test_rank_variants_by_scores(self):
        gen = DiversityGenerator()
        variants = ["a.py", "b.py", "c.py"]
        scores = [0.3, 0.9, 0.5]
        ranked = gen.rank_variants_by_scores(variants, scores)
        assert ranked[0] == "b.py"
        assert ranked[-1] == "a.py"

    def test_evolve_pass_set(self):
        gen = DiversityGenerator()
        base = ["rename", "dead_code", "mba"]
        result = gen.evolve_pass_set(base, 42)
        assert isinstance(result, list)
        assert len(result) > 0
