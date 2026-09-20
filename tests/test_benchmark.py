import os
import sys
import json
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.benchmark.ai_eval import (
    AIBenchmark,
    measure_naming_recovery,
    measure_semantic_leakage,
    measure_decompilation_resistance,
    measure_complexity_impact,
    measure_information_entropy,
    compute_protection_score,
)
from scripts.benchmark.report import BenchmarkReport
from scripts.benchmark.llm_api import LLMEvaluator

SIMPLE_SRC = """def greet(name):
    msg = "hello " + name
    return msg

def main():
    result = greet("world")
    print(result)
"""

OBFUSCATED_LIGHT = """def _nx_greet(a):
    _nx_msg = "hello " + a
    return _nx_msg

def _nx_main():
    _nx_r = _nx_greet("world")
    _ = _nx_r
    print(_nx_r)
"""

OBFUSCATED_HEAVY = """def _nx_greet(_nx_a):
    if (123 ^ 456) % 2 == 1:
        _nx_m = "hello " + _nx_a
        return _nx_m
    else:
        return None

def _nx_main():
    _nx_r = None
    for _nx_i in range(1):
        _nx_r = _nx_greet("world")
    if _nx_r is not None:
        print(_nx_r)
    _nx_dc_0 = 42
    _nx_dc_1 = _nx_dc_0 + 1
"""

EMPTY_SRC = ""
TRIVIAL_SRC = "x = 1"


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture
def temp_simple():
    fd, path = tempfile.mkstemp(suffix=".py", prefix="bench_orig_", text=True)
    os.close(fd)
    with open(path, "w") as f:
        f.write(SIMPLE_SRC)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def temp_light():
    fd, path = tempfile.mkstemp(suffix=".py", prefix="bench_prot_light_", text=True)
    os.close(fd)
    with open(path, "w") as f:
        f.write(OBFUSCATED_LIGHT)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def temp_heavy():
    fd, path = tempfile.mkstemp(suffix=".py", prefix="bench_prot_heavy_", text=True)
    os.close(fd)
    with open(path, "w") as f:
        f.write(OBFUSCATED_HEAVY)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def ai_benchmark():
    return AIBenchmark()


# =========================================================================
# Individual Metric Tests
# =========================================================================

class TestNamingRecovery:
    """
    TestNamingRecovery
    
    Positive test cases for namingrecovery.
    """
    def test_naming_recovery_returns_expected_keys(self):
        result = measure_naming_recovery(SIMPLE_SRC, OBFUSCATED_LIGHT)
        for key in ("recovery_rate", "score", "original_function_count",
                     "original_variable_count", "recovered_functions", "recovered_variables"):
            assert key in result, f"Missing key: {key}"

    def test_protected_code_lower_recovery(self):
        result = measure_naming_recovery(SIMPLE_SRC, OBFUSCATED_LIGHT)
        assert result["recovery_rate"] < 0.5, "Light obfuscation should reduce naming recovery"

    def test_heavy_protection_zero_recovery(self):
        result = measure_naming_recovery(SIMPLE_SRC, OBFUSCATED_HEAVY)
        assert result["recovered_functions"] == []
        assert result["recovery_rate"] == 0.0

    def test_identical_code_full_recovery(self):
        result = measure_naming_recovery(SIMPLE_SRC, SIMPLE_SRC)
        assert result["recovery_rate"] == 1.0
        assert result["score"] == 0.0


class TestSemanticLeakage:
    """
    TestSemanticLeakage
    
    Positive test cases for semanticleakage.
    """
    def test_returns_expected_keys(self):
        result = measure_semantic_leakage(SIMPLE_SRC, OBFUSCATED_LIGHT)
        assert "hellinger_distance" in result
        assert "score" in result

    def test_identical_code_zero_distance(self):
        result = measure_semantic_leakage(SIMPLE_SRC, SIMPLE_SRC)
        assert result["hellinger_distance"] == 0.0
        assert result["score"] == 0.0

    def test_heavy_obfuscation_increases_distance(self):
        light = measure_semantic_leakage(SIMPLE_SRC, OBFUSCATED_LIGHT)
        heavy = measure_semantic_leakage(SIMPLE_SRC, OBFUSCATED_HEAVY)
        assert heavy["hellinger_distance"] >= light["hellinger_distance"]


class TestDecompilationResistance:
    """
    TestDecompilationResistance
    
    Positive test cases for decompilationresistance.
    """
    def test_returns_expected_keys(self):
        result = measure_decompilation_resistance(OBFUSCATED_LIGHT)
        assert "constructs" in result
        assert "score" in result

    def test_empty_code_low_resistance(self):
        result = measure_decompilation_resistance(EMPTY_SRC)
        assert result["score"] >= 0

    def test_heavy_obfuscation_higher_resistance(self):
        light = measure_decompilation_resistance(OBFUSCATED_LIGHT)
        heavy = measure_decompilation_resistance(OBFUSCATED_HEAVY)
        assert heavy["score"] >= light["score"]

    def test_decompiler_unavailable_does_not_crash(self):
        result = measure_decompilation_resistance(SIMPLE_SRC)
        assert "decompiler_available" in result


class TestComplexityImpact:
    """
    TestComplexityImpact
    
    Positive test cases for complexityimpact.
    """
    def test_returns_expected_keys(self):
        result = measure_complexity_impact(SIMPLE_SRC, OBFUSCATED_HEAVY)
        assert "original_complexity" in result
        assert "protected_complexity" in result
        assert "complexity_ratio" in result
        assert "score" in result

    def test_heavier_protection_higher_ratio(self):
        light = measure_complexity_impact(SIMPLE_SRC, OBFUSCATED_LIGHT)
        heavy = measure_complexity_impact(SIMPLE_SRC, OBFUSCATED_HEAVY)
        assert heavy["complexity_ratio"] >= light["complexity_ratio"]

    def test_identical_code_ratio_one(self):
        result = measure_complexity_impact(SIMPLE_SRC, SIMPLE_SRC)
        assert result["complexity_ratio"] >= 0.99


class TestInformationEntropy:
    """
    TestInformationEntropy
    
    Positive test cases for informationentropy.
    """
    def test_returns_expected_keys(self):
        result = measure_information_entropy(OBFUSCATED_HEAVY)
        assert "shannon_entropy" in result
        assert "score" in result

    def test_empty_code_zero_entropy(self):
        result = measure_information_entropy(EMPTY_SRC)
        assert result["shannon_entropy"] == 0.0

    def test_longer_code_higher_entropy(self):
        short = measure_information_entropy(TRIVIAL_SRC)
        long = measure_information_entropy(OBFUSCATED_HEAVY)
        assert long["shannon_entropy"] >= short["shannon_entropy"]


class TestScoring:
    """
    TestScoring
    
    Positive test cases for scoring.
    """
    def test_compute_protection_score_returns_float(self):
        results = {
            "naming_recovery": {"score": 0.5},
            "semantic_leakage": {"score": 0.5},
            "decompilation_resistance": {"score": 0.5},
            "complexity_impact": {"score": 0.5},
            "entropy": {"score": 0.5},
            "static_confusion": {"score": 0.5},
        }
        score = compute_protection_score(results)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_protected_scores_higher_than_unprotected(self):
        orig = {
            "naming_recovery": {"score": 0.0},
            "semantic_leakage": {"score": 0.0},
            "decompilation_resistance": {"score": 0.0},
            "complexity_impact": {"score": 0.0},
            "entropy": {"score": 0.0},
            "static_confusion": {"score": 0.0},
        }
        prot = {
            "naming_recovery": {"score": 0.8},
            "semantic_leakage": {"score": 0.7},
            "decompilation_resistance": {"score": 0.9},
            "complexity_impact": {"score": 0.6},
            "entropy": {"score": 0.5},
            "static_confusion": {"score": 0.4},
        }
        assert compute_protection_score(prot) > compute_protection_score(orig)


# =========================================================================
# Integration Tests
# =========================================================================

class TestAIBenchmark:
    """
    TestAIBenchmark
    
    Positive test cases for aibenchmark.
    """
    def test_full_evaluation_returns_all_metrics(self, ai_benchmark, temp_simple, temp_light):
        results = ai_benchmark.evaluate(temp_simple, temp_light)
        for metric in AIBenchmark.METRICS:
            assert metric in results, f"Missing metric: {metric}"
        for key in ("naming_recovery", "semantic_leakage", "static_confusion",
                     "decompilation_resistance", "complexity_impact", "entropy", "overall"):
            assert key in results, f"Missing key: {key}"

    def test_heavier_protection_yields_higher_score(self, ai_benchmark, temp_simple, temp_light, temp_heavy):
        light_results = ai_benchmark.evaluate(temp_simple, temp_light)
        heavy_results = ai_benchmark.evaluate(temp_simple, temp_heavy)
        assert heavy_results["overall"] >= light_results["overall"]

    def test_unprotected_code_low_score(self, ai_benchmark, temp_simple):
        results = ai_benchmark.evaluate(temp_simple, temp_simple)
        assert results["overall"] < 0.5

    def test_edge_empty_code(self, ai_benchmark):
        fd, orig = tempfile.mkstemp(suffix=".py", text=True)
        os.close(fd)
        fd2, prot = tempfile.mkstemp(suffix=".py", text=True)
        os.close(fd2)
        try:
            results = ai_benchmark.evaluate(orig, prot)
            assert "overall" in results
        finally:
            os.unlink(orig)
            os.unlink(prot)

    def test_edge_trivial_code(self, ai_benchmark):
        fd, orig = tempfile.mkstemp(suffix=".py", text=True)
        os.close(fd)
        with open(orig, "w") as f:
            f.write(TRIVIAL_SRC)
        fd2, prot = tempfile.mkstemp(suffix=".py", text=True)
        os.close(fd2)
        with open(prot, "w") as f:
            f.write(TRIVIAL_SRC)
        try:
            results = ai_benchmark.evaluate(orig, prot)
            assert "overall" in results
        finally:
            os.unlink(orig)
            os.unlink(prot)


class TestReport:
    """
    TestReport
    
    Positive test cases for report.
    """
    def test_html_generation(self):
        results = {
            "naming_recovery": {"score": 0.8, "recovery_rate": 0.2},
            "semantic_leakage": {"score": 0.7, "hellinger_distance": 0.3},
            "static_confusion": {"score": 0.6, "total_warnings": 12},
            "decompilation_resistance": {"score": 0.9, "constructs": {"exec_eval": 0, "nested_decorators": 5, "exception_control_flow": 3}},
            "complexity_impact": {"score": 0.5, "complexity_ratio": 3.2},
            "entropy": {"score": 0.4, "shannon_entropy": 3.5},
            "overall": 0.68,
            "_original_path": "/tmp/orig.py",
            "_protected_path": "/tmp/prot.py",
            "_llm_results": {
                "gpt4": {"decompilation_success": 0.6, "logic_recovery": 0.4},
                "claude3": {"decompilation_success": 0.5, "logic_recovery": 0.5},
            },
        }
        report = BenchmarkReport()
        html = report.generate_html(results)
        assert "<!DOCTYPE html>" in html
        assert "0.68" in html
        assert "Radar Chart" in html
        assert "gpt4" in html

    def test_text_summary(self):
        results = {
            "naming_recovery": {"score": 0.8},
            "semantic_leakage": {"score": 0.7},
            "static_confusion": {"score": 0.6},
            "decompilation_resistance": {"score": 0.9},
            "complexity_impact": {"score": 0.5},
            "entropy": {"score": 0.4},
            "overall": 0.68,
        }
        report = BenchmarkReport()
        text = report.generate_text_summary(results)
        assert "Overall Protection Score" in text
        assert "0.68" in text

    def test_report_empty_results_does_not_crash(self):
        report = BenchmarkReport()
        html = report.generate_html({"overall": 0.0})
        assert html


class TestLLMEvaluator:
    """
    TestLLMEvaluator
    
    Positive test cases for llmevaluator.
    """
    def test_evaluate_returns_dict(self):
        evaluator = LLMEvaluator()
        result = evaluator.evaluate(OBFUSCATED_HEAVY, "nemotron-3-ultra-free")
        assert isinstance(result, dict)
        assert all(0.0 <= v <= 1.0 for v in result.values())

    def test_evaluate_all_returns_all_models(self):
        evaluator = LLMEvaluator()
        results = evaluator.evaluate_all(OBFUSCATED_HEAVY)
        assert set(results.keys()) == {"nemotron-3-ultra-free", "north-mini-code-free", "deepseek-v4-flash-free", "mimo-v2.5-free"}

    def test_invalid_model_raises(self):
        evaluator = LLMEvaluator()
        with pytest.raises(ValueError):
            evaluator.evaluate(OBFUSCATED_HEAVY, "nonexistent")

    def test_longer_code_returns_valid_scores(self):
        evaluator = LLMEvaluator()
        result = evaluator.evaluate(OBFUSCATED_HEAVY, "nemotron-3-ultra-free")
        assert all(0.0 <= v <= 1.0 for v in result.values())
