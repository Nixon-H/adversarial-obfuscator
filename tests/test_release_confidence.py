"""
test_release_confidence.py

Tests for Release Confidence Scoring (Feature 198).

Test coverage:
- Positive tests verify proof coverage, evidence completeness, attack results, regression, audit scoring
- Negative tests verify empty build dir, corrupted JSON, missing files
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestReleaseConfidenceScorer:
    """
    TestReleaseConfidenceScorer
    
    Positive test cases for releaseconfidencescorer.
    """
    def test_score_proof_coverage(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        with tempfile.TemporaryDirectory() as td:
            data = {"overall_coverage": 85.0}
            with open(os.path.join(td, "proof_coverage_report.json"), "w") as f:
                json.dump(data, f)
            scorer = ReleaseConfidenceScorer(td)
            score = scorer.score_proof_coverage()
            assert score == 0.85

    def test_score_proof_coverage_missing_file(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        with tempfile.TemporaryDirectory() as td:
            scorer = ReleaseConfidenceScorer(td)
            score = scorer.score_proof_coverage()
            assert score == 0.0

    def test_score_evidence_completeness(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        with tempfile.TemporaryDirectory() as td:
            data = {"claim_coverage_pct": 80.0, "coverage_pct": 70.0}
            with open(os.path.join(td, "evidence_report.json"), "w") as f:
                json.dump(data, f)
            scorer = ReleaseConfidenceScorer(td)
            score = scorer.score_evidence_completeness()
            assert score == 0.75

    def test_score_evidence_completeness_alt_file(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        with tempfile.TemporaryDirectory() as td:
            data = {"claim_coverage_pct": 100.0, "coverage_pct": 100.0}
            with open(os.path.join(td, "evidence_ledger.json"), "w") as f:
                json.dump(data, f)
            scorer = ReleaseConfidenceScorer(td)
            score = scorer.score_evidence_completeness()
            assert score == 1.0

    def test_score_attack_results_from_corpus(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        with tempfile.TemporaryDirectory() as td:
            data = {"severity_distribution": {"critical": 1, "low": 2}}
            with open(os.path.join(td, "attack_corpus_report.json"), "w") as f:
                json.dump(data, f)
            scorer = ReleaseConfidenceScorer(td)
            score = scorer.score_attack_results()
            assert 0.0 <= score <= 1.0

    def test_score_attack_results_from_markdown(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "attack_report.md"), "w") as f:
                f.write("**CRITICAL** issue\n**HIGH** risk\n")
            scorer = ReleaseConfidenceScorer(td)
            score = scorer.score_attack_results()
            assert 0.0 <= score <= 1.0

    def test_score_regression_from_markdown(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "regression_report.md"), "w") as f:
                f.write("✅ PASS test1\n✅ PASS test2\n❌ FAIL test3\n")
            scorer = ReleaseConfidenceScorer(td)
            score = scorer.score_regression()
            assert score == 2.0 / 3.0

    def test_score_regression_from_gates(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        with tempfile.TemporaryDirectory() as td:
            data = {
                "all_passed": False,
                "gates": [
                    {"passed": True},
                    {"passed": False},
                    {"passed": True},
                ],
            }
            with open(os.path.join(td, "security_gate_report.json"), "w") as f:
                json.dump(data, f)
            scorer = ReleaseConfidenceScorer(td)
            score = scorer.score_regression()
            assert score == 2.0 / 3.0

    def test_score_audit_quality(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        with tempfile.TemporaryDirectory() as td:
            data = {"overall_score": 80.0}
            with open(os.path.join(td, "security_audit.json"), "w") as f:
                json.dump(data, f)
            scorer = ReleaseConfidenceScorer(td)
            score = scorer.score_audit_quality()
            assert score == 0.8

    def test_score_audit_quality_missing(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        with tempfile.TemporaryDirectory() as td:
            scorer = ReleaseConfidenceScorer(td)
            score = scorer.score_audit_quality()
            assert score == 0.0

    def test_compute_full(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "proof_coverage_report.json"), "w") as f:
                json.dump({"overall_coverage": 100.0}, f)
            with open(os.path.join(td, "evidence_report.json"), "w") as f:
                json.dump({"claim_coverage_pct": 100.0, "coverage_pct": 100.0}, f)
            with open(os.path.join(td, "attack_corpus_report.json"), "w") as f:
                json.dump({"severity_distribution": {}}, f)
            with open(os.path.join(td, "regression_report.md"), "w") as f:
                f.write("✅ PASS test\n")
            with open(os.path.join(td, "security_audit.json"), "w") as f:
                json.dump({"overall_score": 100.0}, f)
            scorer = ReleaseConfidenceScorer(td)
            result = scorer.compute()
            assert result.confidence_score > 0
            assert result.confidence_grade in ("A", "B", "C", "D", "F")

    def test_grade_boundaries(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        scorer = ReleaseConfidenceScorer("/tmp")
        assert scorer._grade(95) == "A"
        assert scorer._grade(85) == "B"
        assert scorer._grade(75) == "C"
        assert scorer._grade(65) == "D"
        assert scorer._grade(55) == "F"

    def test_compute_release_confidence_function(self):
        from scripts.release_confidence.scorer import compute_release_confidence
        with tempfile.TemporaryDirectory() as td:
            result = compute_release_confidence(td)
            assert "confidence_score" in result
            assert "confidence_interval" in result
            assert "confidence_grade" in result


class TestReleaseConfidenceNegative:
    """
    TestReleaseConfidenceNegative
    
    Negative test cases — exercises error handling and edge cases for releaseconfidencenegative.
    """
    def test_empty_build_dir(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        with tempfile.TemporaryDirectory() as td:
            scorer = ReleaseConfidenceScorer(td)
            result = scorer.compute()
            assert result.confidence_score >= 0
            assert isinstance(result.confidence_grade, str)

    def test_corrupted_json_handling(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "proof_coverage_report.json"), "w") as f:
                f.write("not json")
            scorer = ReleaseConfidenceScorer(td)
            score = scorer.score_proof_coverage()
            assert score == 0.0

    def test_zero_attack_severity_returns_one(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        with tempfile.TemporaryDirectory() as td:
            data = {"severity_distribution": {}}
            with open(os.path.join(td, "attack_corpus_report.json"), "w") as f:
                json.dump(data, f)
            scorer = ReleaseConfidenceScorer(td)
            score = scorer.score_attack_results()
            assert score == 1.0

    def test_no_regression_passes_default(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        with tempfile.TemporaryDirectory() as td:
            scorer = ReleaseConfidenceScorer(td)
            score = scorer.score_regression()
            assert score == 0.5

    def test_malformed_security_audit(self):
        from scripts.release_confidence.scorer import ReleaseConfidenceScorer
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "security_audit.json"), "w") as f:
                f.write("{broken")
            scorer = ReleaseConfidenceScorer(td)
            score = scorer.score_audit_quality()
            assert score == 0.0
