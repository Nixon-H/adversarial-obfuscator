"""
test_evidence_completeness.py

Tests for Evidence Completeness Scoring (Feature 188).

Test coverage:
- Positive tests verify claim scoring, pattern detection, directory scanning
- Negative tests verify empty files, no-tests-dir, no claims found
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from scripts.evidence_completeness.scorer import (
    CLAIM_PATTERNS,
    ClaimEvidence,
    EvidenceCompletenessScorer,
)


class TestClaimEvidence:
    """
    TestClaimEvidence
    
    Positive test cases for claimevidence.
    """
    def test_score_all_present(self):
        ce = ClaimEvidence(
            claim_text="secure",
            source_file="a.py",
            line_number=1,
            source_exists=True,
            test_exists=True,
            benchmark_exists=True,
            trace_exists=True,
            audit_exists=True,
        )
        assert ce.score == 100.0
        assert ce.missing_links == []

    def test_score_none_present(self):
        ce = ClaimEvidence(
            claim_text="unbreakable",
            source_file="b.py",
            line_number=5,
        )
        assert ce.score == 0.0
        assert len(ce.missing_links) == 5

    def test_score_partial(self):
        ce = ClaimEvidence(
            claim_text="tamper-proof",
            source_file="c.py",
            line_number=10,
            source_exists=True,
            test_exists=True,
        )
        assert ce.score == 40.0
        assert len(ce.missing_links) == 3

    def test_missing_links_correct(self):
        ce = ClaimEvidence(
            claim_text="provably",
            source_file="d.py",
            line_number=3,
            source_exists=True,
            audit_exists=True,
        )
        missing = ce.missing_links
        assert "tests" in missing
        assert "benchmarks" in missing
        assert "runtime_traces" in missing
        assert "source_implementation" not in missing
        assert "audit_report" not in missing


class TestClaimPatterns:
    """
    TestClaimPatterns
    
    Positive test cases for claimpatterns.
    """
    def test_patterns_defined(self):
        assert len(CLAIM_PATTERNS) > 0
        assert "unbreakable" in CLAIM_PATTERNS
        assert "secure" in CLAIM_PATTERNS
        assert "tamper-proof" in CLAIM_PATTERNS

    def test_all_patterns_are_strings(self):
        for p in CLAIM_PATTERNS:
            assert isinstance(p, str)


class TestEvidenceCompletenessScorer:
    """
    TestEvidenceCompletenessScorer
    
    Positive test cases for evidencecompletenessscorer.
    """
    def test_init(self):
        scorer = EvidenceCompletenessScorer()
        assert scorer.root_dir is not None
        assert scorer.claims == []

    def test_scan_file_for_claims_found(self):
        scorer = EvidenceCompletenessScorer()
        tmp_file = "/tmp/_test_claims.py"
        with open(tmp_file, "w") as f:
            f.write("# This is an unbreakable system\n")
            f.write("# It is provably secure\n")
        matches = scorer._scan_file_for_claims(tmp_file)
        assert len(matches) >= 1
        os.remove(tmp_file)

    def test_scan_file_for_claims_not_found(self):
        scorer = EvidenceCompletenessScorer()
        tmp_file = "/tmp/_test_no_claims.py"
        with open(tmp_file, "w") as f:
            f.write("# just a harmless comment\n")
            f.write("x = 42\n")
        matches = scorer._scan_file_for_claims(tmp_file)
        assert matches == []
        os.remove(tmp_file)

    def test_scan_file_for_claims_empty(self):
        scorer = EvidenceCompletenessScorer()
        tmp_file = "/tmp/_test_empty.py"
        with open(tmp_file, "w") as f:
            pass
        matches = scorer._scan_file_for_claims(tmp_file)
        assert matches == []
        os.remove(tmp_file)

    def test_get_keywords(self):
        scorer = EvidenceCompletenessScorer()
        keywords = scorer._get_keywords("the system is provably secure")
        assert len(keywords) > 0
        assert all(len(k) > 2 for k in keywords)

    def test_get_keywords_short(self):
        scorer = EvidenceCompletenessScorer()
        keywords = scorer._get_keywords("a b c")
        assert keywords == []

    def test_check_source_exists_found(self):
        scorer = EvidenceCompletenessScorer()
        tmp_file = "/tmp/_test_src.py"
        with open(tmp_file, "w") as f:
            f.write("def secure_function():\n    pass\n")
        found, files = scorer._check_source_exists("secure_function")
        assert isinstance(found, bool)
        assert isinstance(files, list)
        os.remove(tmp_file)

    def test_check_test_exists_no_tests_dir(self):
        scorer = EvidenceCompletenessScorer(root_dir="/tmp/nonexistent_test_xyz")
        found, files = scorer._check_test_exists(["secure"])
        assert found is False
        assert files == []

    def test_check_benchmark_exists_no_tests_dir(self):
        scorer = EvidenceCompletenessScorer(root_dir="/tmp/nonexistent_bench_xyz")
        found, files = scorer._check_benchmark_exists(["secure"])
        assert found is False
        assert files == []

    def test_check_trace_exists(self):
        scorer = EvidenceCompletenessScorer()
        found, files = scorer._check_trace_exists(["secure"])
        assert isinstance(found, bool)
        assert isinstance(files, list)

    def test_check_audit_exists(self):
        scorer = EvidenceCompletenessScorer()
        found, files = scorer._check_audit_exists("secure")
        assert isinstance(found, bool)
        assert isinstance(files, list)

    def test_compute_evidence_completeness_returns_dict(self):
        scorer = EvidenceCompletenessScorer()
        result = scorer.compute_evidence_completeness()
        assert isinstance(result, dict)
        assert "per_claim_results" in result
        assert "overall_score" in result
        assert "missing_links" in result
        assert "total_claims" in result

    def test_overall_score_is_float(self):
        scorer = EvidenceCompletenessScorer()
        result = scorer.compute_evidence_completeness()
        assert isinstance(result["overall_score"], float)

    def test_total_claims_is_non_negative(self):
        scorer = EvidenceCompletenessScorer()
        result = scorer.compute_evidence_completeness()
        assert result["total_claims"] >= 0

    def test_scan_directory_for_claims(self):
        scorer = EvidenceCompletenessScorer()
        claims = scorer._scan_directory_for_claims()
        assert isinstance(claims, list)


class TestEvidenceCompletenessIntegration:
    """
    TestEvidenceCompletenessIntegration
    
    Positive test cases for evidencecompletenessintegration.
    """
    def test_full_scoring_in_own_directory(self):
        scorer = EvidenceCompletenessScorer()
        result = scorer.compute_evidence_completeness()
        assert 0 <= result["overall_score"] <= 100

    def test_per_claim_structure(self):
        scorer = EvidenceCompletenessScorer()
        result = scorer.compute_evidence_completeness()
        for claim in result["per_claim_results"]:
            assert "claim_text" in claim
            assert "score" in claim
            assert "missing_links" in claim
            assert isinstance(claim["score"], (int, float))
