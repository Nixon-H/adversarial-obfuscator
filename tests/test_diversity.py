import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.diversity import DiversityGenerator, DiversityMetrics
from scripts.diversity.generator import generate_variant
from scripts.diversity.metrics import (
    compute_cfg_similarity,
    compute_ast_similarity,
    compute_bytecode_similarity,
    compute_ir_similarity,
    compute_diversity_matrix,
)

SIMPLE_SRC = """
def add(a, b):
    return a + b

def main():
    x = 10
    y = 20
    result = add(x, y)
    print(result)
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_source(tmpdir, name="source.py", content=SIMPLE_SRC):
    path = os.path.join(tmpdir, name)
    with open(path, "w") as f:
        f.write(content)
    return path


def _generate_n(tmpdir, n=3, master_seed=None):
    src = _write_source(tmpdir)
    out = os.path.join(tmpdir, "variants")
    config = {}
    if master_seed is not None:
        config["master_seed"] = master_seed
    gen = DiversityGenerator(config)
    paths = gen.generate(src, n, out)
    return paths, src


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDiversityGenerator:
    """
    TestDiversityGenerator
    
    Positive test cases for diversitygenerator.
    """
    def test_different_seeds_produce_different_variants(self, tmpdir):
        paths, _ = _generate_n(tmpdir, n=2)
        with open(paths[0]) as f:
            c0 = f.read()
        with open(paths[1]) as f:
            c1 = f.read()
        assert c0 != c1, "variants with different seeds should differ"

    def test_same_seeds_produce_identical_variants(self, tmpdir):
        src = _write_source(tmpdir)
        config = {"master_seed": 42}
        gen = DiversityGenerator(config)
        out1 = os.path.join(tmpdir, "v1")
        os.makedirs(out1, exist_ok=True)
        paths1 = gen.generate(src, 1, out1)

        gen2 = DiversityGenerator(config)
        out2 = os.path.join(tmpdir, "v2")
        os.makedirs(out2, exist_ok=True)
        paths2 = gen2.generate(src, 1, out2)

        with open(paths1[0]) as f:
            c1 = f.read()
        with open(paths2[0]) as f:
            c2 = f.read()
        assert c1 == c2, "same seed should produce identical output"

    def test_cfg_similarity_between_variants(self, tmpdir):
        paths, _ = _generate_n(tmpdir, n=2)
        with open(paths[0]) as f: tree_a = ast.parse(f.read())
        with open(paths[1]) as f: tree_b = ast.parse(f.read())
        sim = compute_cfg_similarity(tree_a, tree_b)
        assert 0.0 <= sim <= 1.0, f"cfg_similarity out of range: {sim}"

    def test_ast_similarity_between_variants(self, tmpdir):
        paths, _ = _generate_n(tmpdir, n=2)
        with open(paths[0]) as f: tree_a = ast.parse(f.read())
        with open(paths[1]) as f: tree_b = ast.parse(f.read())
        sim = compute_ast_similarity(tree_a, tree_b)
        assert 0.0 <= sim <= 1.0, f"ast_similarity out of range: {sim}"

    def test_fingerprinting_unique_for_different_variants(self, tmpdir):
        paths, _ = _generate_n(tmpdir, n=3)
        dm = DiversityMetrics()
        fps = [dm.fingerprint(p) for p in paths]
        assert len(set(fps)) == len(fps), "different variants must have unique fingerprints"

    def test_fingerprint_is_deterministic(self, tmpdir):
        src = _write_source(tmpdir)
        config = {"master_seed": 12345}
        gen = DiversityGenerator(config)
        out = os.path.join(tmpdir, "det")
        os.makedirs(out, exist_ok=True)
        path = gen.generate(src, 1, out)[0]

        dm = DiversityMetrics()
        fp1 = dm.fingerprint(path)
        fp2 = dm.fingerprint(path)
        assert fp1 == fp2, "fingerprint must be deterministic"

    def test_diversity_generation_produces_n_files(self, tmpdir):
        paths, _ = _generate_n(tmpdir, n=5)
        assert len(paths) == 5

    def test_each_generated_file_is_valid_python(self, tmpdir):
        paths, _ = _generate_n(tmpdir, n=3)
        for p in paths:
            with open(p) as f:
                code = f.read()
            try:
                ast.parse(code)
            except SyntaxError as e:
                pytest.fail(f"Invalid Python: {p}: {e}")

    def test_each_generated_file_preserves_output(self, tmpdir):
        src_text = """def main():\n    print("hello")\nif __name__ == "__main__":\n    main()\n"""
        src = os.path.join(tmpdir, "source.py")
        with open(src, "w") as f:
            f.write(src_text)

        expected = subprocess.run(
            [sys.executable, src], capture_output=True, text=True
        ).stdout

        out = os.path.join(tmpdir, "var_out")
        gen = DiversityGenerator()
        paths = gen.generate(src, 2, out)

        for p in paths:
            result = subprocess.run(
                [sys.executable, p], capture_output=True, text=True
            )
            assert result.returncode == 0, f"Variant {p} failed: {result.stderr}"
            assert result.stdout == expected, f"Variant {p} output mismatch"

    def test_diversity_matrix_generation(self, tmpdir):
        paths, _ = _generate_n(tmpdir, n=3)
        matrix = compute_diversity_matrix(paths)
        assert len(matrix) == 3
        for pair, metrics in matrix.items():
            assert "overall_diversity" in metrics
            assert 0.0 <= metrics["overall_diversity"] <= 1.0

    def test_diversity_report(self, tmpdir):
        paths, _ = _generate_n(tmpdir, n=2)
        report_path = os.path.join(tmpdir, "report.json")
        dm = DiversityMetrics()
        dm.generate_report(paths, report_path)
        assert os.path.exists(report_path)
        with open(report_path) as f:
            report = json.load(f)
        assert "num_variants" in report
        assert "fingerprints" in report

    def test_edge_case_n_equals_1(self, tmpdir):
        paths, _ = _generate_n(tmpdir, n=1)
        assert len(paths) == 1
        # A single variant should be valid Python
        with open(paths[0]) as f:
            ast.parse(f.read())

    def test_edge_case_n_equals_0(self, tmpdir):
        src = _write_source(tmpdir)
        out = os.path.join(tmpdir, "empty")
        gen = DiversityGenerator()
        paths = gen.generate(src, 0, out)
        assert len(paths) == 0

    def test_ir_similarity_between_variants(self, tmpdir):
        paths, _ = _generate_n(tmpdir, n=2)
        with open(paths[0]) as f: tree_a = ast.parse(f.read())
        with open(paths[1]) as f: tree_b = ast.parse(f.read())
        sim = compute_ir_similarity(tree_a, tree_b)
        assert 0.0 <= sim <= 1.0

    def test_bytecode_similarity_between_variants(self, tmpdir):
        paths, _ = _generate_n(tmpdir, n=2)
        sim = compute_bytecode_similarity(paths[0], paths[1])
        assert 0.0 <= sim <= 1.0

    def test_diversitymetrics_compare_api(self, tmpdir):
        paths, _ = _generate_n(tmpdir, n=2)
        dm = DiversityMetrics()
        result = dm.compare(paths[0], paths[1])
        assert "cfg_similarity" in result
        assert "ast_similarity" in result
        assert "ir_similarity" in result
        assert "bytecode_similarity" in result
        assert "overall_diversity" in result

    def test_diversitymetrics_compare_all_api(self, tmpdir):
        paths, _ = _generate_n(tmpdir, n=3)
        dm = DiversityMetrics()
        result = dm.compare_all(paths)
        assert result["num_variants"] == 3
        assert result["num_pairs"] == 3

    def test_generate_variant_function(self, tmpdir):
        result = generate_variant(SIMPLE_SRC, 0, {"master_seed": 42})
        assert isinstance(result, str)
        ast.parse(result)

    def test_diversity_between_two_variants_is_positive(self, tmpdir):
        paths, _ = _generate_n(tmpdir, n=2)
        dm = DiversityMetrics()
        result = dm.compare(paths[0], paths[1])
        div = result["overall_diversity"]
        assert div > 0.0, "two different variants must have some diversity"
