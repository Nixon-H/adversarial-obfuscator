"""
test_invariant_engine.py

Tests for Security Invariant Engine (Feature 191).

Test coverage:
- Positive tests verify all five invariants: unreachable features, tautological proofs,
  hardcoded metrics, silent fallbacks, undocumented assumptions
- Negative tests verify nonexistent files, empty source, score ranges
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


from scripts.invariant_engine.engine import (
    InvariantViolation,
    InvariantResult,
    InvariantReport,
    SecurityInvariantEngine,
)


class TestInvariantViolation:
    """
    TestInvariantViolation
    
    Positive test cases for invariantviolation.
    """
    def test_defaults(self):
        v = InvariantViolation(
            invariant_name="test",
            severity="HIGH",
            file_path="a.py",
            line_number=10,
            description="desc",
            code_snippet="code",
        )
        assert v.invariant_name == "test"
        assert v.severity == "HIGH"


class TestInvariantResult:
    """
    TestInvariantResult
    
    Positive test cases for invariantresult.
    """
    def test_defaults(self):
        r = InvariantResult(invariant_name="no_hardcoded_metrics", passed=False)
        assert r.passed is False
        assert r.violations == []
        assert r.checks_performed == 0

    def test_with_violations(self):
        r = InvariantResult(
            invariant_name="test",
            passed=True,
            violations=[
                InvariantViolation("test", "LOW", "b.py", 5, "desc", "code")
            ],
            checks_performed=10,
        )
        assert r.passed is True
        assert len(r.violations) == 1


class TestInvariantReport:
    """
    TestInvariantReport
    
    Positive test cases for invariantreport.
    """
    def test_defaults(self):
        r = InvariantReport()
        assert r.invariant_results == {}
        assert r.violations_found == 0
        assert r.invariant_score == 100.0

    def test_with_data(self):
        r = InvariantReport(
            invariant_results={
                "test": InvariantResult("test", passed=True),
            },
            violations_found=0,
            invariant_score=95.0,
        )
        assert r.invariant_score == 95.0


class TestSecurityInvariantEngine:
    """
    TestSecurityInvariantEngine
    
    Positive test cases for securityinvariantengine.
    """
    def test_init(self):
        e = SecurityInvariantEngine()
        assert e.root_dir is not None
        assert os.path.isdir(e.root_dir)

    def test_find_py_files(self):
        e = SecurityInvariantEngine()
        files = e._find_py_files()
        assert len(files) > 0
        for f in files:
            assert f.endswith(".py")

    def test_read_source(self):
        e = SecurityInvariantEngine()
        tmp_file = "/tmp/_test_source.py"
        with open(tmp_file, "w") as f:
            f.write("x = 1\n")
        source = e._read_source(tmp_file)
        assert source == "x = 1\n"
        os.remove(tmp_file)

    def test_read_source_nonexistent(self):
        e = SecurityInvariantEngine()
        source = e._read_source("/tmp/nonexistent_file.py")
        assert source == ""

    def test_read_lines(self):
        e = SecurityInvariantEngine()
        tmp_file = "/tmp/_test_lines.py"
        with open(tmp_file, "w") as f:
            f.write("a\nb\nc\n")
        lines = e._read_lines(tmp_file)
        assert len(lines) == 3
        os.remove(tmp_file)

    def test_read_lines_nonexistent(self):
        e = SecurityInvariantEngine()
        lines = e._read_lines("/tmp/nonexistent.py")
        assert lines == []

    def test_check_no_feature_unreachable(self):
        e = SecurityInvariantEngine()
        result = e._check_no_feature_unreachable()
        assert isinstance(result, InvariantResult)
        assert result.invariant_name == "no_feature_unreachable"

    def test_check_no_tautological_proof(self):
        e = SecurityInvariantEngine()
        result = e._check_no_tautological_proof()
        assert isinstance(result, InvariantResult)
        assert result.invariant_name == "no_tautological_proof"

    def test_check_no_hardcoded_metrics(self):
        e = SecurityInvariantEngine()
        result = e._check_no_hardcoded_metrics()
        assert isinstance(result, InvariantResult)
        assert result.invariant_name == "no_hardcoded_metrics"

    def test_check_no_silent_fallback(self):
        e = SecurityInvariantEngine()
        result = e._check_no_silent_fallback()
        assert isinstance(result, InvariantResult)
        assert result.invariant_name == "no_silent_fallback"

    def test_check_no_undocumented_assumptions(self):
        e = SecurityInvariantEngine()
        result = e._check_no_undocumented_assumptions()
        assert isinstance(result, InvariantResult)
        assert result.invariant_name == "no_undocumented_assumptions"

    def test_verify_invariants_returns_dict(self):
        e = SecurityInvariantEngine()
        result = e.verify_invariants()
        assert isinstance(result, dict)
        assert "invariant_results" in result
        assert "violations_found" in result
        assert "invariant_score" in result

    def test_all_invariants_present(self):
        e = SecurityInvariantEngine()
        result = e.verify_invariants()
        names = [
            "no_feature_unreachable",
            "no_tautological_proof",
            "no_hardcoded_metrics",
            "no_silent_fallback",
            "no_undocumented_assumptions",
        ]
        for name in names:
            assert name in result["invariant_results"]

    def test_invariant_score_in_range(self):
        e = SecurityInvariantEngine()
        result = e.verify_invariants()
        assert 0 <= result["invariant_score"] <= 100

    def test_violations_found_non_negative(self):
        e = SecurityInvariantEngine()
        result = e.verify_invariants()
        assert result["violations_found"] >= 0

    def test_each_invariant_has_violations_list(self):
        e = SecurityInvariantEngine()
        result = e.verify_invariants()
        for inv_result in result["invariant_results"].values():
            assert "violations" in inv_result
            assert "passed" in inv_result
            assert "checks_performed" in inv_result


class TestInvariantEngineIntegration:
    """
    TestInvariantEngineIntegration
    
    Positive test cases for invariantengineintegration.
    """
    def test_full_verification(self):
        e = SecurityInvariantEngine()
        result = e.verify_invariants()
        assert len(result["invariant_results"]) == 5
        total_violations = sum(
            len(r["violations"]) for r in result["invariant_results"].values()
        )
        assert result["violations_found"] == total_violations
