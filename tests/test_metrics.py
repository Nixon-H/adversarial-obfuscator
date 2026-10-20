import os
import sys
import json
import ast
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.metrics.resilience import (
    ResilienceMetrics,
    compute_cfg_entropy,
    compute_cyclomatic,
    compute_instruction_diversity,
    compute_dead_code,
    compute_symbolic_resistance,
)


def _make_simple_func():
    return ast.parse("""
def add(a, b):
    return a + b

def main():
    x = 1
    y = 2
    result = add(x, y)
    print(result)
""")


def _make_obfuscated_func():
    return ast.parse("""
def _nx_add(a, b):
    return a + b

def _nx_main():
    _nx_a = (1 ^ 42) ^ 42
    _nx_b = 2
    _nx_r = _nx_add(_nx_a, _nx_b)
    if (7 * 7) % 2 == 1:
        print(_nx_r)
    else:
        print("Integrity Valid")

def _nx_honey_1():
    if 0 == 1:
        pass

def _nx_honey_2():
    pass
""")


class TestMetrics:
    """
    TestMetrics
    
    Positive test cases for metrics.
    """
    def test_cfg_entropy_returns_expected_keys(self):
        orig = _make_simple_func()
        prot = _make_obfuscated_func()
        result = compute_cfg_entropy(orig, prot)
        assert "original_entropy" in result
        assert "protected_entropy" in result
        assert "entropy_ratio" in result
        assert isinstance(result["entropy_ratio"], float)

    def test_cfg_entropy_increases_after_obfuscation(self):
        orig = _make_simple_func()
        prot = _make_obfuscated_func()
        result = compute_cfg_entropy(orig, prot)
        assert result["protected_entropy"] >= result["original_entropy"]

    def test_cyclomatic_returns_expected_keys(self):
        orig = _make_simple_func()
        prot = _make_obfuscated_func()
        result = compute_cyclomatic(orig, prot)
        assert "original_complexity" in result
        assert "protected_complexity" in result
        assert "complexity_ratio" in result

    def test_cyclomatic_increases_after_obfuscation(self):
        orig = _make_simple_func()
        prot = _make_obfuscated_func()
        result = compute_cyclomatic(orig, prot)
        assert result["protected_complexity"] >= result["original_complexity"]

    def test_instruction_diversity_returns_expected_keys(self):
        orig = _make_simple_func()
        prot = _make_obfuscated_func()
        result = compute_instruction_diversity(orig, prot)
        assert "original_diversity" in result
        assert "protected_diversity" in result
        assert "diversity_ratio" in result

    def test_instruction_diversity_increases_after_obfuscation(self):
        orig = _make_simple_func()
        prot = _make_obfuscated_func()
        result = compute_instruction_diversity(orig, prot)
        assert result["protected_diversity"] >= result["original_diversity"]

    def test_dead_code_counts_honey_functions(self):
        orig = _make_simple_func()
        prot = _make_obfuscated_func()
        result = compute_dead_code(orig, prot)
        assert result["honey_function_increase"] >= 2

    def test_dead_code_percentage_increases(self):
        orig = _make_simple_func()
        prot = _make_obfuscated_func()
        result = compute_dead_code(orig, prot)
        assert result["dead_code_increase_pct"] >= 0

    def test_symbolic_resistance_returns_expected_keys(self):
        orig = _make_simple_func()
        prot = _make_obfuscated_func()
        result = compute_symbolic_resistance(orig, prot)
        assert "resistance_score" in result
        assert "original_opaque_predicates" in result

    def test_symbolic_resistance_higher_for_obfuscated(self):
        orig = _make_simple_func()
        prot = _make_obfuscated_func()
        result = compute_symbolic_resistance(orig, prot)
        assert result["resistance_score"] > 0

    def test_measure_full_pipeline(self):
        orig_src = "def main():\n    return 42\n"
        prot_src = """
def _nx_main():
    if (7 * 7) % 2 == 1:
        return 42
    else:
        return 0
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(orig_src)
            orig_path = f.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(prot_src)
            prot_path = f.name

        try:
            metrics = ResilienceMetrics()
            result = metrics.measure(orig_path, prot_path)
            assert "cfg_entropy" in result
            assert "cyclomatic_complexity" in result
            assert "instruction_diversity" in result
            assert "dead_code" in result
            assert "symbolic_resistance" in result
            assert "static_confusion" in result
            assert "overall" in result
        finally:
            os.unlink(orig_path)
            os.unlink(prot_path)

    def test_json_report_is_valid(self):
        orig_src = "x = 1\n"
        prot_src = """
x = 1
y = 2
if (7 * 7) % 2 == 1:
    z = 3
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(orig_src)
            orig_path = f.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(prot_src)
            prot_path = f.name

        try:
            metrics = ResilienceMetrics()
            metrics.measure(orig_path, prot_path)
            report_json = metrics.to_json()
            parsed = json.loads(report_json)
            assert "overall" in parsed
        finally:
            os.unlink(orig_path)
            os.unlink(prot_path)

    def test_resilience_metrics_from_empty_source(self):
        orig_src = ""
        prot_src = ""
        orig_ast = ast.parse(orig_src)
        prot_ast = ast.parse(prot_src)
        result = compute_cfg_entropy(orig_ast, prot_ast)
        assert result["entropy_ratio"] == 1.0
