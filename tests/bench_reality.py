"""
bench_reality.py

Benchmarks for Feature Reality Scores (Feature 167).

Measures reality score computation, grading, and aggregation across all features.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestRealityScoreBenchmarks:
    @pytest.fixture
    def full_build_py_state(self):
        build_py_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "build.py"
        )
        with open(build_py_path) as f:
            build_py_source = f.read()
        return {"build_py_source": build_py_source}

    def test_bench_all_features_computation(self, benchmark, full_build_py_state):
        from scripts.reality.scorer import compute_reality_scores
        report = benchmark(compute_reality_scores, full_build_py_state)
        assert report is not None
        assert len(report.feature_scores) > 0

    def test_bench_single_feature_computation(self, benchmark, full_build_py_state):
        from scripts.reality.scorer import compute_feature_reality
        feat = {
            "name": "CFG Flattening",
            "module": "obfuscator.core",
            "class": None,
            "cli_flag": "--cfg-flatten",
            "phase": "phase01_obfuscate",
        }
        fr = benchmark(compute_feature_reality, feat, full_build_py_state)
        assert fr is not None
        assert fr.feature_name == "CFG Flattening"

    def test_bench_aggregate_score(self, benchmark):
        from scripts.reality.scorer import (
            RealityReport,
            FeatureReality,
            aggregate_reality_score,
        )
        scores = {f"F{i}": FeatureReality(f"F{i}", reality_score=float(i * 10 % 100))
                  for i in range(50)}
        report = RealityReport(feature_scores=scores)
        result = benchmark(aggregate_reality_score, report)
        assert 0 <= result <= 100

    def test_bench_grade_conversion(self, benchmark):
        from scripts.reality.scorer import score_to_grade
        def run_grades():
            for s in range(0, 101):
                score_to_grade(float(s))
            return True
        result = benchmark(run_grades)
        assert result is True

    def test_bench_load_from_build_empty(self, benchmark):
        from scripts.reality.scorer import load_from_build
        report = benchmark(load_from_build, "/tmp/nonexistent_build_dir_xyz")
        assert report is not None
        assert len(report.feature_scores) > 0
