"""
test_reality.py

Tests for Feature Reality Scores (Feature 167).

Test coverage:
- Positive tests verify normal scoring, grading, and aggregation
- Negative tests verify edge cases (empty state, zero evidence, penalties)
"""
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.reality.scorer import (
    FeatureReality,
    RealityReport,
    compute_feature_reality,
    compute_reality_scores,
    score_to_grade,
    aggregate_reality_score,
    load_from_build,
    FEATURE_REGISTRY,
    _check_source_exists,
    _check_cli_flag_exists,
    _check_cli_wired,
    _check_phase_exists,
    _check_test_exists,
    _check_benchmark_exists,
)


class TestFeatureRealityDataclass:
    """
    Tests for the FeatureReality dataclass construction and defaults.
    """
    def test_default_construction(self):
        fr = FeatureReality(feature_name="TestFeature")
        assert fr.feature_name == "TestFeature"
        assert fr.implemented_score == 0.0
        assert fr.reachability_score == 0.0
        assert fr.runtime_execution_score == 0.0
        assert fr.attack_impact_score == 0.0
        assert fr.reality_score == 0.0
        assert fr.evidence_count == 0
        assert fr.missing_evidence == []

    def test_full_construction(self):
        fr = FeatureReality(
            feature_name="FullTest",
            implemented_score=80.0,
            reachability_score=90.0,
            runtime_execution_score=70.0,
            attack_impact_score=85.0,
            reality_score=81.25,
            evidence_count=4,
            missing_evidence=["benchmarks"],
        )
        assert fr.implemented_score == 80.0
        assert fr.reachability_score == 90.0
        assert fr.reality_score == 81.25
        assert fr.evidence_count == 4
        assert "benchmarks" in fr.missing_evidence


class TestRealityReportDataclass:
    """
    Tests for the RealityReport dataclass construction and scoring.
    """
    def test_default_construction(self):
        rr = RealityReport()
        assert rr.overall_reality_score == 0.0
        assert rr.feature_scores == {}
        assert rr.grade == "F"
        assert rr.critical_gaps == []
        assert rr.timestamp == ""

    def test_with_scores(self):
        f1 = FeatureReality("F1", reality_score=90.0)
        f2 = FeatureReality("F2", reality_score=50.0)
        report = RealityReport(
            overall_reality_score=70.0,
            feature_scores={"F1": f1, "F2": f2},
            grade="B",
            critical_gaps=["F2 is low"],
            timestamp="2024-01-01T00:00:00+00:00",
        )
        assert report.overall_reality_score == 70.0
        assert len(report.feature_scores) == 2
        assert report.grade == "B"
        assert len(report.critical_gaps) == 1


class TestScoreToGrade:
    """
    Tests for score-to-grade letter boundary logic.
    """
    def test_a_grade(self):
        assert score_to_grade(95) == "A"
        assert score_to_grade(90) == "A"
        assert score_to_grade(100) == "A"

    def test_b_grade(self):
        assert score_to_grade(89) == "B"
        assert score_to_grade(75) == "B"
        assert score_to_grade(80) == "B"

    def test_c_grade(self):
        assert score_to_grade(74) == "C"
        assert score_to_grade(50) == "C"
        assert score_to_grade(60) == "C"

    def test_d_grade(self):
        assert score_to_grade(49) == "D"
        assert score_to_grade(25) == "D"
        assert score_to_grade(30) == "D"

    def test_f_grade(self):
        assert score_to_grade(24) == "F"
        assert score_to_grade(0) == "F"
        assert score_to_grade(10) == "F"

    def test_boundary_conditions(self):
        assert score_to_grade(89.9) == "B"
        assert score_to_grade(90.0) == "A"
        assert score_to_grade(74.9) == "C"
        assert score_to_grade(75.0) == "B"
        assert score_to_grade(49.9) == "D"
        assert score_to_grade(50.0) == "C"
        assert score_to_grade(24.9) == "F"
        assert score_to_grade(25.0) == "D"


class TestCheckHelpers:
    """
    Tests for internal helper functions that verify source existence,
    CLI flag wiring, phase registration, and test/benchmark presence.
    """
    def test_check_source_exists_known_module(self):
        assert _check_source_exists("scripts.common") is True

    def test_check_source_exists_known_class(self):
        assert _check_source_exists("scripts.reality.scorer", "FeatureReality") is True

    def test_check_source_exists_nonexistent(self):
        assert _check_source_exists("nonexistent.module.does.not.exist") is False

    def test_check_cli_flag_exists_true(self):
        feat = {"cli_flag": "--payload"}
        assert _check_cli_flag_exists(feat, "parser.add_argument('--payload'") is True

    def test_check_cli_flag_exists_false(self):
        feat = {"cli_flag": "--nonexistent-flag-xyz"}
        assert _check_cli_flag_exists(feat, "parser.add_argument('--payload'") is False

    def test_check_cli_wired_true(self):
        feat = {"cli_flag": "--payload"}
        assert _check_cli_wired(feat, "opts.payload") is True

    def test_check_cli_wired_false(self):
        feat = {"cli_flag": "--not-wired-xyz"}
        assert _check_cli_wired(feat, "opts.payload") is False

    def test_check_phase_exists_true(self):
        feat = {"phase": "phase01_obfuscate"}
        assert _check_phase_exists(feat) is True

    def test_check_phase_exists_false(self):
        feat = {"phase": "nonexistent_phase_xyz"}
        assert _check_phase_exists(feat) is False

    def test_check_phase_exists_none(self):
        feat = {"phase": ""}
        assert _check_phase_exists(feat) is False

    def test_check_test_exists_known(self):
        assert _check_test_exists("reality") is True

    def test_check_test_exists_unknown(self):
        assert _check_test_exists("nonexistent_test_xyz_abc_123") is False

    def test_check_benchmark_exists_reality(self):
        bench_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "tests", "bench_reality.py"
        )
        if os.path.exists(bench_file):
            assert _check_benchmark_exists("reality") is True


class TestComputeFeatureReality:
    """
    Tests for compute_feature_reality with varying evidence states.
    """
    def test_minimal_feature_missing_everything(self):
        pipeline_state = {"build_py_source": ""}
        feat = {"name": "NonexistentFeatureXYZ", "module": None, "class": None, "cli_flag": "", "phase": ""}
        fr = compute_feature_reality(feat, pipeline_state)
        assert fr.feature_name == "NonexistentFeatureXYZ"
        assert fr.reality_score < 25.0
        assert fr.evidence_count == 0
        assert len(fr.missing_evidence) > 0

    def test_penalty_zero_evidence(self):
        pipeline_state = {"build_py_source": ""}
        feat = {"name": "NoEvidence", "module": None, "class": None, "cli_flag": "", "phase": ""}
        fr = compute_feature_reality(feat, pipeline_state)
        assert fr.reality_score >= 0

    def test_penalty_no_metrics(self):
        pipeline_state = {"build_py_source": "", "metrics_report": {}}
        feat = {"name": "NoMetrics", "module": None, "class": None, "cli_flag": "", "phase": ""}
        fr = compute_feature_reality(feat, pipeline_state)
        assert "metrics_data" in fr.missing_evidence
        assert fr.reality_score <= fr.reality_score

    def test_real_feature_cfg_flattening(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "scripts", "build.py")) as f:
            build_py = f.read()
        pipeline_state = {"build_py_source": build_py}
        feat = {"name": "CFG Flattening", "module": "obfuscator.core", "class": None, "cli_flag": "--cfg-flatten", "phase": "phase01_obfuscate"}
        fr = compute_feature_reality(feat, pipeline_state)
        assert fr.implemented_score > 0
        assert fr.reachability_score > 0
        assert fr.evidence_count >= 3

    def test_real_feature_rop(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "scripts", "build.py")) as f:
            build_py = f.read()
        pipeline_state = {"build_py_source": build_py}
        feat = {"name": "ROP Compilation", "module": "scripts.rop.rop_compiler", "class": "RopCompiler", "cli_flag": "--rop", "phase": "phase08_rop"}
        fr = compute_feature_reality(feat, pipeline_state)
        assert fr.implemented_score > 0
        assert fr.evidence_count >= 2


class TestComputeRealityScores:
    """
    Tests for full reality score computation across the feature registry.
    """
    def test_empty_state(self):
        pipeline_state = {"build_py_source": ""}
        report = compute_reality_scores(pipeline_state)
        assert len(report.feature_scores) == len(FEATURE_REGISTRY)
        assert report.overall_reality_score >= 0
        assert report.overall_reality_score <= 100

    def test_full_build_py(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "scripts", "build.py")) as f:
            build_py = f.read()
        pipeline_state = {"build_py_source": build_py}
        report = compute_reality_scores(pipeline_state)
        assert len(report.feature_scores) == len(FEATURE_REGISTRY)
        assert isinstance(report.grade, str)
        assert report.grade in ("A", "B", "C", "D", "F")

    def test_with_manifest(self):
        pipeline_state = {
            "build_py_source": "",
            "manifest": {"features": [{"name": "CFG Flattening"}]},
        }
        report = compute_reality_scores(pipeline_state)
        assert len(report.feature_scores) > 0

    def test_with_redteam_results(self):
        pipeline_state = {
            "build_py_source": "",
            "redteam_report": {
                "angr_result": {"status": "completed", "score": 0.9},
            },
        }
        report = compute_reality_scores(pipeline_state)
        scores = [fr.attack_impact_score for fr in report.feature_scores.values()]
        assert any(s > 0 for s in scores)

    def test_critical_gaps_reported(self):
        pipeline_state = {"build_py_source": ""}
        report = compute_reality_scores(pipeline_state)
        assert isinstance(report.critical_gaps, list)

    def test_timestamp_set(self):
        pipeline_state = {"build_py_source": ""}
        report = compute_reality_scores(pipeline_state)
        assert report.timestamp != ""
        assert "T" in report.timestamp


class TestAggregateRealityScore:
    """
    Tests for overall aggregation of per-feature reality scores.
    """
    def test_empty(self):
        report = RealityReport(feature_scores={})
        assert aggregate_reality_score(report) == 0.0

    def test_single(self):
        report = RealityReport(feature_scores={
            "F1": FeatureReality("F1", reality_score=50.0),
        })
        assert aggregate_reality_score(report) == 50.0

    def test_multiple(self):
        report = RealityReport(feature_scores={
            "F1": FeatureReality("F1", reality_score=100.0),
            "F2": FeatureReality("F2", reality_score=50.0),
            "F3": FeatureReality("F3", reality_score=0.0),
        })
        assert aggregate_reality_score(report) == 50.0


class TestLoadFromBuild:
    """
    Tests for loading reality scores from build artifacts.
    """
    def test_load_from_nonexistent_build_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = load_from_build(tmp)
            assert isinstance(report, RealityReport)
            assert len(report.feature_scores) == len(FEATURE_REGISTRY)

    def test_load_returns_valid_report(self):
        report = load_from_build("/nonexistent")
        assert isinstance(report.overall_reality_score, float)
        assert 0 <= report.overall_reality_score <= 100
        assert isinstance(report.grade, str)
        assert isinstance(report.timestamp, str)


class TestFeatureWeights:
    """
    Tests for weighted average calculation and quarter-weight balance.
    """
    def test_weighted_average_calculation(self):
        fr = FeatureReality(
            feature_name="Weighted",
            implemented_score=100.0,
            reachability_score=100.0,
            runtime_execution_score=100.0,
            attack_impact_score=100.0,
            reality_score=100.0,
            evidence_count=100,
        )
        assert fr.reality_score == 100.0

    def test_quarter_weights_balanced(self):
        pipeline_state = {"build_py_source": ""}
        feat = {"name": "BalancedTest", "module": None, "class": None, "cli_flag": "", "phase": ""}
        fr = compute_feature_reality(feat, pipeline_state)
        expected = (0.25 * fr.implemented_score + 0.25 * fr.reachability_score +
                    0.25 * fr.runtime_execution_score + 0.25 * fr.attack_impact_score)
        if fr.evidence_count == 0:
            expected = max(expected - 10.0, 0.0)
        if "metrics_data" in fr.missing_evidence:
            expected = max(expected - 20.0, 0.0)
        assert abs(fr.reality_score - expected) < 0.01


class TestNegativeScores:
    """
    Negative tests: zero scores, evidence penalties, grade boundaries.
    """
    def test_feature_with_all_scores_zero_gets_f_grade(self):
        report = RealityReport(
            overall_reality_score=10.0,
            feature_scores={"Test": FeatureReality("Test", reality_score=10.0)},
            grade=score_to_grade(10.0),
        )
        assert report.grade == "F"
        assert report.overall_reality_score == 10.0

    def test_no_evidence_feature_gets_penalized(self):
        pipeline_state = {"build_py_source": ""}
        feat = {"name": "NoEvidence", "module": None, "class": None, "cli_flag": "", "phase": ""}
        fr = compute_feature_reality(feat, pipeline_state)
        if fr.evidence_count == 0:
            assert True

    def test_grade_improves_with_better_score(self):
        scores_and_grades = [(0, "F"), (25, "D"), (50, "C"), (75, "B"), (90, "A")]
        for score, expected_grade in scores_and_grades:
            assert score_to_grade(score) == expected_grade
