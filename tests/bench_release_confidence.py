"""
bench_release_confidence.py

Benchmarks for Release Confidence Scoring (Feature 198).

Measures scoring across proof coverage, evidence, attacks, and audit dimensions.
"""
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestReleaseConfidenceBenchmarks:
    @pytest.fixture
    def report_dir(self):
        tmpdir = tempfile.mkdtemp()
        with open(os.path.join(tmpdir, "proof_coverage_report.json"), "w") as f:
            json.dump({"overall_coverage": 85.0}, f)
        with open(os.path.join(tmpdir, "evidence_report.json"), "w") as f:
            json.dump({"claim_coverage_pct": 80.0, "coverage_pct": 75.0}, f)
        with open(os.path.join(tmpdir, "attack_corpus_report.json"), "w") as f:
            json.dump({"severity_distribution": {"high": 2, "low": 3}}, f)
        with open(os.path.join(tmpdir, "regression_report.md"), "w") as f:
            f.write("✅ PASS a\n✅ PASS b\n")
        with open(os.path.join(tmpdir, "security_audit.json"), "w") as f:
            json.dump({"overall_score": 70.0}, f)
        yield tmpdir
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_bench_compute(self, report_dir, benchmark):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer

        def run():
            scorer = ReleaseConfidenceScorer(report_dir)
            return scorer.compute()

        result = benchmark(run)
        assert result.confidence_score > 0

    def test_bench_score_proof_coverage(self, report_dir, benchmark):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer

        scorer = ReleaseConfidenceScorer(report_dir)

        def run():
            return scorer.score_proof_coverage()

        score = benchmark(run)
        assert score > 0

    def test_bench_score_attack_results(self, report_dir, benchmark):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer

        scorer = ReleaseConfidenceScorer(report_dir)

        def run():
            return scorer.score_attack_results()

        score = benchmark(run)
        assert 0.0 <= score <= 1.0

    def test_bench_empty_dir(self, benchmark):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer

        def run():
            scorer = ReleaseConfidenceScorer("/tmp/nonexistent_bench_dir")
            return scorer.compute()

        result = benchmark(run)
        assert result.confidence_score >= 0
