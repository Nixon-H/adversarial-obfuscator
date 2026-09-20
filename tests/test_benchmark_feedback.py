"""Tests for Adaptive Adversarial Rewriting (Item 74)."""
import ast
import json
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.benchmark.feedback import BenchmarkFeedbackAnalyzer, WeaknessProfile
from obfuscator.adaptive_rewriter import AdaptiveRewriter


SIMPLE_SRC = """
def greet(name):
    msg = "hello " + name
    return msg

def main():
    result = greet("world")
    print(result)

main()
"""


def _execute(code: str) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp = f.name
    try:
        result = subprocess.run(
            [sys.executable, tmp], capture_output=True, text=True, timeout=10
        )
        return result.stdout
    finally:
        os.unlink(tmp)


class TestBenchmarkFeedback:
    """
    TestBenchmarkFeedback
    
    Positive test cases for benchmarkfeedback.
    """
    def test_benchmark_feedback_analysis(self):
        results = {
            "naming_recovery": {"score": 0.2},
            "semantic_leakage": {"score": 0.3},
            "decompilation_resistance": {"score": 0.4},
            "complexity_impact": {"score": 0.6},
            "entropy": {"score": 0.7},
            "static_confusion": {"score": 0.5},
            "overall": 0.45,
        }
        analyzer = BenchmarkFeedbackAnalyzer(threshold=0.5)
        profile = analyzer.analyze(results)
        assert "naming_recovery" in profile.failed_metrics
        assert "semantic_leakage" in profile.failed_metrics
        assert "decompilation_resistance" in profile.failed_metrics
        assert len(profile.recommended_actions) >= 3

    def test_adaptive_rewriter_generates_replacement(self):
        results = {
            "naming_recovery": {"score": 0.2},
            "semantic_leakage": {"score": 0.3},
            "decompilation_resistance": {"score": 0.1},
            "complexity_impact": {"score": 0.6},
            "entropy": {"score": 0.7},
            "static_confusion": {"score": 0.2},
            "overall": 0.35,
        }
        analyzer = BenchmarkFeedbackAnalyzer(threshold=0.5)
        profile = analyzer.analyze(results)
        rewriter = AdaptiveRewriter()
        result = rewriter.rewrite(profile, SIMPLE_SRC)
        try:
            ast.parse(result)
        except SyntaxError as e:
            pytest.fail(f"Invalid Python generated: {e}")

    def test_adaptive_rewriter_history_persistence(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            history_path = f.name
        try:
            results = {
                "naming_recovery": {"score": 0.2},
                "decompilation_resistance": {"score": 0.3},
                "semantic_leakage": {"score": 0.4},
                "complexity_impact": {"score": 0.6},
                "entropy": {"score": 0.7},
                "static_confusion": {"score": 0.5},
                "overall": 0.45,
            }
            analyzer = BenchmarkFeedbackAnalyzer(threshold=0.5)
            profile = analyzer.analyze(results)
            analyzer.save_history(profile, history_path)
            assert os.path.exists(history_path)
            with open(history_path) as f:
                data = json.load(f)
            assert len(data) >= 1
            assert "failed_metrics" in data[0]
        finally:
            os.unlink(history_path)

    def test_rewriter_preserves_semantics(self):
        original_stdout = _execute(SIMPLE_SRC)
        results = {
            "naming_recovery": {"score": 0.2},
            "decompilation_resistance": {"score": 0.1},
            "semantic_leakage": {"score": 0.3},
            "complexity_impact": {"score": 0.6},
            "entropy": {"score": 0.7},
            "static_confusion": {"score": 0.2},
            "overall": 0.35,
        }
        analyzer = BenchmarkFeedbackAnalyzer(threshold=0.5)
        profile = analyzer.analyze(results)
        rewriter = AdaptiveRewriter()
        result = rewriter.rewrite(profile, SIMPLE_SRC)
        obfuscated_stdout = _execute(result)
        assert original_stdout == obfuscated_stdout

    def test_profile_serialization(self):
        profile = WeaknessProfile(
            failed_metrics=["naming_recovery"],
            weak_scores={"naming_recovery": 0.2},
            recommended_actions=["strengthen_symbol_renaming"],
        )
        d = profile.to_dict()
        restored = WeaknessProfile.from_dict(d)
        assert restored.failed_metrics == ["naming_recovery"]
        assert restored.recommended_actions == ["strengthen_symbol_renaming"]

    def test_load_empty_history(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("[]")
            history_path = f.name
        try:
            analyzer = BenchmarkFeedbackAnalyzer()
            history = analyzer.load_history(history_path)
            assert history == []
        finally:
            os.unlink(history_path)

    def test_nonexistent_history(self):
        analyzer = BenchmarkFeedbackAnalyzer()
        history = analyzer.load_history("/tmp/nonexistent_history_xyz.json")
        assert history == []
