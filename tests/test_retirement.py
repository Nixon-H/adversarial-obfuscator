"""
test_retirement.py

Tests for Feature Retirement Analysis (Feature 176).

Test coverage:
- Positive tests verify assessment, classification, and scoring
- Negative tests verify empty features, orphan features, score ranges
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


from scripts.feature_retirement.analyzer import (
    RetirementAnalyzer,
    RetirementAssessment,
    RetirementReport,
    RetirementStatus,
)
from scripts.feature_retirement import analyze_feature_retirement, generate_retirement_report
from scripts.reachability.feature_map import ALL_FEATURES


class TestRetirementStatus:
    """
    Tests for RetirementStatus enum values and membership.
    """
    def test_enum_values(self):
        assert RetirementStatus.DEPRECATE.value == "DEPRECATE"
        assert RetirementStatus.MONITOR.value == "MONITOR"
        assert RetirementStatus.KEEP.value == "KEEP"
        assert RetirementStatus.OPTIMIZE.value == "OPTIMIZE"

    def test_enum_members(self):
        assert len(RetirementStatus) == 4


class TestRetirementAssessment:
    """
    Tests for RetirementAssessment dataclass defaults and full fields.
    """
    def test_dataclass_defaults(self):
        a = RetirementAssessment(
            feature_name="test_feature",
            effectiveness_score=0.8,
            overhead_score=0.3,
            survivability_score=0.7,
            overall_score=0.65,
            recommendation=RetirementStatus.KEEP,
            reason="Good value",
        )
        assert a.feature_name == "test_feature"
        assert a.effectiveness_score == 0.8
        assert a.overhead_score == 0.3
        assert a.survivability_score == 0.7
        assert a.overall_score == 0.65
        assert a.recommendation == RetirementStatus.KEEP
        assert a.reason == "Good value"
        assert a.has_tests is False
        assert a.has_runtime is False
        assert a.has_implementation is False
        assert a.cli_flag_present is False
        assert a.phase_present is False

    def test_dataclass_with_all_fields(self):
        a = RetirementAssessment(
            feature_name="full_feature",
            effectiveness_score=0.9,
            overhead_score=0.1,
            survivability_score=0.85,
            overall_score=0.88,
            recommendation=RetirementStatus.KEEP,
            reason="Excellent value",
            has_tests=True,
            has_runtime=True,
            has_implementation=True,
            cli_flag_present=True,
            phase_present=True,
        )
        assert a.feature_name == "full_feature"
        assert a.has_tests is True
        assert a.has_runtime is True
        assert a.has_implementation is True
        assert a.cli_flag_present is True
        assert a.phase_present is True


class TestRetirementReport:
    """
    Tests for RetirementReport counts and dict serialization.
    """
    def test_report_counts(self):
        assessments = {
            "a": RetirementAssessment("a", 0.8, 0.3, 0.7, 0.65, RetirementStatus.KEEP, "good"),
            "b": RetirementAssessment("b", 0.3, 0.7, 0.2, 0.15, RetirementStatus.DEPRECATE, "bad"),
            "c": RetirementAssessment("c", 0.5, 0.5, 0.5, 0.40, RetirementStatus.MONITOR, "meh"),
            "d": RetirementAssessment("d", 0.7, 0.8, 0.6, 0.45, RetirementStatus.OPTIMIZE, "heavy"),
        }
        report = RetirementReport(
            assessments=assessments,
            deprecate_count=1,
            monitor_count=1,
            keep_count=1,
            optimize_count=1,
            total_features=4,
            timestamp="2026-01-01T00:00:00+00:00",
        )
        assert report.deprecate_count == 1
        assert report.monitor_count == 1
        assert report.keep_count == 1
        assert report.optimize_count == 1
        assert report.total_features == 4

    def test_report_to_dict(self):
        assessments = {
            "test": RetirementAssessment(
                "test", 0.8, 0.3, 0.7, 0.65, RetirementStatus.KEEP, "good",
            ),
        }
        report = RetirementReport(
            assessments=assessments,
            deprecate_count=0,
            monitor_count=0,
            keep_count=1,
            optimize_count=0,
            total_features=1,
            timestamp="2026-01-01T00:00:00+00:00",
        )
        d = report.to_dict()
        assert d["total_features"] == 1
        assert d["keep_count"] == 1
        assert "test" in d["assessments"]
        assert d["assessments"]["test"]["recommendation"] == "KEEP"
        assert d["assessments"]["test"]["effectiveness_score"] == 0.8


class TestRetirementAnalyzer:
    """
    Tests for RetirementAnalyzer: classification, effectiveness, overhead,
    survivability scoring, assessment, and report generation.
    """
    def test_init(self):
        analyzer = RetirementAnalyzer()
        assert len(analyzer.feature_map) >= 50

    def test_classify_feature_type_high(self):
        analyzer = RetirementAnalyzer()
        assert analyzer.classify_feature_type("obfuscation") == "high"
        assert analyzer.classify_feature_type("encryption") == "high"
        assert analyzer.classify_feature_type("cfg_mutation") == "high"

    def test_classify_feature_type_medium(self):
        analyzer = RetirementAnalyzer()
        assert analyzer.classify_feature_type("diversity") == "medium"
        assert analyzer.classify_feature_type("hpc") == "medium"

    def test_classify_feature_type_low(self):
        analyzer = RetirementAnalyzer()
        assert analyzer.classify_feature_type("cross_compile") == "low"
        assert analyzer.classify_feature_type("compile") == "low"
        assert analyzer.classify_feature_type("metrics") == "low"

    def test_classify_feature_type_fallback(self):
        analyzer = RetirementAnalyzer()
        result = analyzer.classify_feature_type("_unknown_feature_xyz")
        assert result == "medium"

    def test_compute_effectiveness_high(self):
        analyzer = RetirementAnalyzer()
        info = {"cli_flag": "--obfuscate", "phase_name": "phase_obfuscate", "impl_module": "obfuscator.core"}
        score = analyzer.compute_effectiveness("obfuscation", info)
        assert 0.85 <= score <= 1.0

    def test_compute_effectiveness_low(self):
        analyzer = RetirementAnalyzer()
        info = {"cli_flag": None, "phase_name": None, "impl_module": None}
        score = analyzer.compute_effectiveness("cross_compile", info)
        assert 0.20 <= score <= 0.35

    def test_compute_effectiveness_empty(self):
        analyzer = RetirementAnalyzer()
        info = {}
        score = analyzer.compute_effectiveness("_nonexistent", info)
        assert 0.0 < score <= 1.0

    def test_compute_overhead_runtime_present(self):
        analyzer = RetirementAnalyzer()
        info = {"runtime_file": "decrypt.rs", "impl_module": "scripts.phases.phase04_encrypt"}
        score = analyzer.compute_overhead("encryption", info)
        assert score > 0.50

    def test_compute_overhead_minimal(self):
        analyzer = RetirementAnalyzer()
        info = {}
        score = analyzer.compute_overhead("packaging", info)
        assert 0.0 < score <= 0.40

    def test_compute_overhead_clamped(self):
        analyzer = RetirementAnalyzer()
        info = {"runtime_file": "heavy.rs", "impl_module": "vm.heavy"}
        score = analyzer.compute_overhead("vm_heavy", info)
        assert score <= 1.0

    def test_compute_survivability_high(self):
        analyzer = RetirementAnalyzer()
        info = {
            "cli_flag": "--obfuscate", "phase_name": "phase_obfuscate",
            "impl_module": "obfuscator.core", "test_file": "test_obfuscator.py",
            "runtime_file": "obfuscate.rs",
        }
        score = analyzer.compute_survivability("obfuscation", info)
        assert score >= 0.50

    def test_compute_survivability_low(self):
        analyzer = RetirementAnalyzer()
        info = {}
        score = analyzer.compute_survivability("_orphan_feature", info)
        assert score <= 0.40

    def test_assess_feature_known_good(self):
        analyzer = RetirementAnalyzer()
        a = analyzer.assess_feature("obfuscation")
        assert a.feature_name == "obfuscation"
        assert isinstance(a.effectiveness_score, float)
        assert isinstance(a.overhead_score, float)
        assert isinstance(a.survivability_score, float)
        assert isinstance(a.overall_score, float)
        assert isinstance(a.recommendation, RetirementStatus)
        assert isinstance(a.reason, str)

    def test_assess_feature_empty_map(self):
        analyzer = RetirementAnalyzer(feature_map={"_dummy": {}})
        a = analyzer.assess_feature("_dummy")
        assert a.feature_name == "_dummy"
        assert a.recommendation in (RetirementStatus.DEPRECATE, RetirementStatus.MONITOR)

    def test_assess_all_features(self):
        analyzer = RetirementAnalyzer()
        results = analyzer.assess_all_features()
        assert len(results) >= 50
        for name, a in results.items():
            assert isinstance(a, RetirementAssessment)
            assert a.feature_name == name
            assert 0.0 <= a.effectiveness_score <= 1.0
            assert 0.0 <= a.overhead_score <= 1.0
            assert 0.0 <= a.survivability_score <= 1.0
            assert 0.0 <= a.overall_score <= 1.0

    def test_generate_report(self):
        analyzer = RetirementAnalyzer()
        report = analyzer.generate_report()
        assert isinstance(report, RetirementReport)
        assert report.total_features >= 50
        total = report.deprecate_count + report.monitor_count + report.keep_count + report.optimize_count
        assert total == report.total_features


class TestRetirementIntegration:
    """
    Integration tests for retirement analysis functions and report file output.
    """
    def test_analyze_feature_retirement_function(self):
        result = analyze_feature_retirement("obfuscation")
        assert isinstance(result, dict)
        assert result["feature_name"] == "obfuscation"
        assert "recommendation" in result
        assert "effectiveness_score" in result
        assert "overhead_score" in result
        assert "survivability_score" in result

    def test_generate_retirement_report_function(self):
        report = generate_retirement_report()
        assert isinstance(report, RetirementReport)
        assert report.total_features >= 50

    def test_phase_retirement_output_files(self):
        from scripts.feature_retirement.analyzer import RetirementAnalyzer
        from scripts.common import BUILD_DIR, atomic_write
        analyzer = RetirementAnalyzer()
        report = analyzer.generate_report()
        report_path = os.path.join(BUILD_DIR, "retirement_report.json")
        os.makedirs(BUILD_DIR, exist_ok=True)
        atomic_write(report_path, json.dumps(report.to_dict(), indent=2))
        summary_path = os.path.join(BUILD_DIR, "retirement_summary.txt")
        lines = [
            f"Total features:   {report.total_features}",
            f"DEPRECATE:        {report.deprecate_count}",
            f"MONITOR:          {report.monitor_count}",
            f"KEEP:             {report.keep_count}",
            f"OPTIMIZE:         {report.optimize_count}",
        ]
        atomic_write(summary_path, "\n".join(lines))
        assert os.path.exists(report_path)
        assert os.path.exists(summary_path)
        with open(report_path) as f:
            data = json.load(f)
        assert "assessments" in data
        assert data["total_features"] >= 50

    def test_phase_retirement_with_tempdir(self):
        from scripts.feature_retirement.analyzer import RetirementAnalyzer
        import scripts.common as _sc
        with tempfile.TemporaryDirectory() as tmpdir:
            orig = _sc.BUILD_DIR
            try:
                _sc.BUILD_DIR = tmpdir
                analyzer = RetirementAnalyzer()
                report = analyzer.generate_report()
                report_path = os.path.join(tmpdir, "retirement_report.json")
                with open(report_path, "w") as f:
                    f.write(json.dumps(report.to_dict(), indent=2))
                assert os.path.exists(report_path)
                with open(report_path) as f:
                    data = json.load(f)
                assert "assessments" in data
            finally:
                _sc.BUILD_DIR = orig


class TestRetirementPositiveNegative:
    """
    Positive and negative tests: popular features should keep, empty features deprecate.
    """
    def test_popular_features_should_keep_or_monitor(self):
        analyzer = RetirementAnalyzer()
        for name in ("obfuscation", "encryption", "cfg_mutation", "watermark"):
            a = analyzer.assess_feature(name)
            assert a.recommendation in (
                RetirementStatus.KEEP, RetirementStatus.MONITOR, RetirementStatus.OPTIMIZE
            ), f"{name} unexpectedly recommended for deprecation: {a.reason}"

    def test_negative_empty_feature_deprecates(self):
        analyzer = RetirementAnalyzer(feature_map={
            "_dead_compile": {},
            "_no_value_metrics": {},
        })
        for name in ("_dead_compile", "_no_value_metrics"):
            a = analyzer.assess_feature(name)
            assert a.effectiveness_score < 0.50
            assert a.survivability_score < 0.50

    def test_report_consistency(self):
        report = generate_retirement_report()
        feature_names = set(report.assessments.keys())
        map_names = set(ALL_FEATURES.keys())
        assert feature_names == map_names

    def test_all_scores_in_range(self):
        analyzer = RetirementAnalyzer()
        for name in ("obfuscation", "encryption", "ir_compilation", "packaging"):
            a = analyzer.assess_feature(name)
            assert 0.0 <= a.effectiveness_score <= 1.0
            assert 0.0 <= a.overhead_score <= 1.0
            assert 0.0 <= a.survivability_score <= 1.0
            assert 0.0 <= a.overall_score <= 1.0
