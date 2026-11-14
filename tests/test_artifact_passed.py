"""The verification report's "passed" flag must follow the test results."""
from scripts.artifacts.builder import _normalize_test_results, _tests_passed
from scripts.artifacts.report_generator import generate_verification_report


def test_summary_shape_all_passed():
    summary = {"total": 10, "passed": 10, "failed": 0, "skipped": 0,
               "failed_tests": []}
    assert _tests_passed(summary) is True
    md = generate_verification_report({"test_results": summary,
                                       "passed": _tests_passed(summary)})
    assert "ALL PASSED" in md


def test_summary_shape_failure():
    summary = {"total": 10, "passed": 9, "failed": 1, "skipped": 0,
               "failed_tests": [{"name": "x", "error": "boom"}]}
    assert _tests_passed(summary) is False
    md = generate_verification_report({"test_results": summary,
                                       "passed": _tests_passed(summary)})
    assert "NOT ALL PASSED" in md


def test_per_test_shape():
    assert _tests_passed({"a": {"status": "PASS"},
                          "b": {"status": "PASS"}}) is True
    assert _tests_passed({"a": {"status": "PASS"},
                          "b": {"status": "FAIL"}}) is False


def test_per_test_shape_is_normalized_for_the_report():
    summary = _normalize_test_results({"a": {"status": "PASS"},
                                       "b": {"status": "PASS"}})
    assert summary["total"] == 2 and summary["passed"] == 2
    md = generate_verification_report({"test_results": summary,
                                       "passed": True})
    assert "ALL PASSED" in md
    assert "**Total:** 2" in md


def test_empty_is_not_passed():
    assert _tests_passed({}) is False
    assert _tests_passed(None) is False
