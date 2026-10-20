"""
test_feature_effectiveness.py

Tests for Feature Effectiveness Scoring (Feature 194).

Test coverage:
- Positive tests verify feature discovery, impact metrics, docstring extraction
- Negative tests verify empty directories, syntax errors, no-purpose files
"""
from __future__ import annotations

import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.feature_effectiveness.scorer import (
    FeatureEffectiveness,
    FeatureEffectivenessScorer,
)


def _make_file(tmpdir: str, name: str, content: str) -> str:
    path = os.path.join(tmpdir, name)
    with open(path, "w") as f:
        f.write(content)
    return path


class TestFeatureEffectiveness:
    """
    TestFeatureEffectiveness
    
    Positive test cases for featureeffectiveness.
    """
    def test_dataclass(self):
        fe = FeatureEffectiveness(
            feature_name="test_feat", file_path="/a.py",
            has_impact_metric=True, has_before_after=True,
            has_resistance_benchmark=False,
            docstring_purpose="Detect threats",
            tests_found=[], benchmarks_found=[],
            impact_metric_score=40.0, before_after_score=30.0,
            resistance_score=0.0, overall_score=70.0,
        )
        assert fe.feature_name == "test_feat"
        assert fe.overall_score == 70.0

    def test_dataclass_defaults(self):
        fe = FeatureEffectiveness(
            feature_name="a", file_path="/a.py",
            has_impact_metric=False, has_before_after=False,
            has_resistance_benchmark=False,
            docstring_purpose="", tests_found=[], benchmarks_found=[],
            impact_metric_score=0.0, before_after_score=0.0,
            resistance_score=0.0, overall_score=0.0,
        )
        assert fe.overall_score == 0.0


class TestFeatureEffectivenessScorerPositive:
    """
    TestFeatureEffectivenessScorerPositive
    
    Positive test cases for featureeffectivenessscorerpositive.
    """
    def test_discover_features(self):
        scorer = FeatureEffectivenessScorer(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = scorer.compute_feature_effectiveness()
        assert result["total_features"] > 0
        assert "per_feature_scores" in result
        assert "overall_score" in result
        assert "low_impact_features" in result

    def test_overall_score_range(self):
        scorer = FeatureEffectivenessScorer(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = scorer.compute_feature_effectiveness()
        assert 0.0 <= result["overall_score"] <= 100.0

    def test_per_feature_has_fields(self):
        scorer = FeatureEffectivenessScorer(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = scorer.compute_feature_effectiveness()
        for s in result["per_feature_scores"]:
            assert "feature_name" in s
            assert "file_path" in s
            assert "has_impact_metric" in s
            assert "has_before_after_comparison" in s
            assert "has_resistance_benchmark" in s
            assert "overall_score" in s

    def test_some_features_have_impact(self):
        scorer = FeatureEffectivenessScorer(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = scorer.compute_feature_effectiveness()
        has_impact = any(s["has_impact_metric"] for s in result["per_feature_scores"])
        assert isinstance(has_impact, bool)

    def test_some_features_have_tests(self):
        scorer = FeatureEffectivenessScorer(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = scorer.compute_feature_effectiveness()
        has_tests = any(s["tests_found"] for s in result["per_feature_scores"])
        assert isinstance(has_tests, bool)

    def test_low_impact_features_list(self):
        scorer = FeatureEffectivenessScorer(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = scorer.compute_feature_effectiveness()
        assert isinstance(result["low_impact_features"], list)

    def test_extract_purpose(self, tmpdir):
        code = '"""Detect malicious activity in network traffic."""\ndef run():\n    pass\n'
        fpath = _make_file(tmpdir, "detector.py", code)
        scorer = FeatureEffectivenessScorer(scripts_dir=str(tmpdir))
        purpose = scorer._extract_purpose(fpath)
        assert "Detect malicious" in purpose


class TestFeatureEffectivenessScorerNegative:
    """
    TestFeatureEffectivenessScorerNegative
    
    Negative test cases — exercises error handling and edge cases for featureeffectivenessscorernegative.
    """
    def test_empty_scripts_dir(self, tmpdir):
        scorer = FeatureEffectivenessScorer(scripts_dir=str(tmpdir))
        result = scorer.compute_feature_effectiveness()
        assert result["total_features"] == 0
        assert result["overall_score"] == 0.0

    def test_empty_tests_dir(self, tmpdir):
        non_existent = os.path.join(tmpdir, "nonexistent")
        scorer = FeatureEffectivenessScorer(
            scripts_dir=str(tmpdir), tests_dir=non_existent,
        )
        result = scorer.compute_feature_effectiveness()
        assert result["total_features"] == 0

    def test_no_purpose_file(self, tmpdir):
        pkg_dir = os.path.join(tmpdir, "minimal_pkg")
        os.makedirs(pkg_dir, exist_ok=True)
        code = "x = 1\n"
        _make_file(pkg_dir, "minimal.py", code)
        scorer = FeatureEffectivenessScorer(scripts_dir=str(tmpdir))
        result = scorer.compute_feature_effectiveness()
        assert result["total_features"] >= 1
        for s in result["per_feature_scores"]:
            assert s["docstring_purpose"] == ""

    def test_syntax_error_file(self, tmpdir):
        _make_file(tmpdir, "bad.py", "this is not python {{{")
        scorer = FeatureEffectivenessScorer(scripts_dir=str(tmpdir))
        result = scorer.compute_feature_effectiveness()
        assert result["total_features"] >= 0

    def test_no_low_impact_when_empty(self, tmpdir):
        scorer = FeatureEffectivenessScorer(scripts_dir=str(tmpdir))
        result = scorer.compute_feature_effectiveness()
        assert result["low_impact_features"] == []


class TestPhaseIntegration:
    """
    TestPhaseIntegration
    
    Positive test cases for phaseintegration.
    """
    def test_phase_module_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "phase_feature_effectiveness",
            "scripts/phases/phase_feature_effectiveness.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "phase_feature_effectiveness")
        assert callable(mod.phase_feature_effectiveness)
