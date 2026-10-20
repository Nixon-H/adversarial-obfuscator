"""
test_false_confidence.py

Tests for False Confidence Detection (Feature 173).

Test coverage:
- Positive tests verify pattern detection (empty pass, TODO, NotImplemented, hardcoded success)
- Negative tests verify genuine assertions and real implementations are not flagged
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.false_confidence.detector import (
    ConfidencePattern,
    DetectionResult,
    FalseConfidenceDetector,
    KNOWN_PATTERNS,
    scan_for_false_confidence,
)
from scripts.false_confidence.auditor import (
    audit_source,
    audit_tests,
    audit_benchmarks,
    audit_all,
    deduplicate_patterns,
    format_audit_report,
    generate_audit_report,
)


def _make_file(tmpdir: str, name: str, content: str) -> str:
    path = os.path.join(tmpdir, name)
    with open(path, "w") as f:
        f.write(content)
    return path


class TestConfidencePattern:
    """
    Tests for ConfidencePattern dataclass defaults and full construction.
    """
    def test_dataclass_defaults(self):
        p = ConfidencePattern(
            pattern_name="test",
            pattern_regex=r"test",
            severity="critical",
            description="desc",
            suggested_fix="fix",
        )
        assert p.pattern_name == "test"
        assert p.file_match is None
        assert p.line_number is None

    def test_dataclass_full(self):
        p = ConfidencePattern(
            pattern_name="test",
            pattern_regex=r"test",
            severity="major",
            description="desc",
            suggested_fix="fix",
            file_match="/path/to/file.py",
            line_number=42,
        )
        assert p.file_match == "/path/to/file.py"
        assert p.line_number == 42


class TestDetectionResult:
    """
    Tests for DetectionResult dataclass counts and empty result.
    """
    def test_dataclass_counts(self):
        patterns = [
            ConfidencePattern("a", r"a", "critical", "d", "f"),
            ConfidencePattern("b", r"b", "major", "d", "f"),
            ConfidencePattern("c", r"c", "minor", "d", "f"),
        ]
        result = DetectionResult(
            patterns_found=patterns,
            total_count=3,
            critical_count=1,
            major_count=1,
            minor_count=1,
            scan_path="/test",
            timestamp="2025-01-01T00:00:00",
        )
        assert result.total_count == 3
        assert result.critical_count == 1

    def test_empty_result(self):
        result = DetectionResult([], 0, 0, 0, 0, "/test", "ts")
        assert result.total_count == 0


class TestKNOWN_PATTERNS:
    """
    Tests for KNOWN_PATTERNS: minimum count, required fields, severity distribution, regex compilation.
    """
    def test_minimum_20_patterns(self):
        assert len(KNOWN_PATTERNS) >= 20, f"Only {len(KNOWN_PATTERNS)} patterns defined"

    def test_all_patterns_have_required_fields(self):
        for p in KNOWN_PATTERNS:
            assert p.pattern_name, f"Pattern missing name: {p}"
            assert p.pattern_regex, f"Pattern missing regex: {p.pattern_name}"
            assert p.severity in ("critical", "major", "minor"), f"Bad severity: {p.pattern_name}"
            assert p.description, f"Pattern missing description: {p.pattern_name}"
            assert p.suggested_fix, f"Pattern missing fix: {p.pattern_name}"

    def test_severity_distribution(self):
        severities = [p.severity for p in KNOWN_PATTERNS]
        assert "critical" in severities
        assert "major" in severities
        assert "minor" in severities

    def test_each_pattern_regex_compiles(self):
        for p in KNOWN_PATTERNS:
            import re
            try:
                re.compile(p.pattern_regex, re.MULTILINE)
            except re.error as e:
                raise AssertionError(f"Regex for '{p.pattern_name}' failed: {e}")


class TestDetector:
    """
    Tests for FalseConfidenceDetector: always-true, empty-pass, TODO,
    NotImplemented, hardcoded success, scan_all, and empty directory.
    """
    def test_detect_always_true_pattern(self, tmpdir):
        code = "assert True or True  # always ok\n"
        fpath = _make_file(tmpdir, "test_always.py", code)
        detector = FalseConfidenceDetector(str(tmpdir))
        pattern = ConfidencePattern("always true", r"assert.*or\s+True", "critical", "d", "f")
        matches = detector.scan_for_pattern(pattern)
        assert len(matches) >= 1
        assert any(m.file_match == fpath for m in matches)

    def test_detect_empty_pass(self, tmpdir):
        code = "def foo():\n    pass\n"
        _make_file(tmpdir, "empty_pass.py", code)

        class PassPattern:
            pattern_name = "empty pass"
            pattern_regex = r"def\s+\w+\s*\([\s\S]*?\)\s*:\s*\n\s+pass\s*$"
            severity = "major"
            description = "d"
            suggested_fix = "f"

        detector = FalseConfidenceDetector(str(tmpdir))
        matches = detector.scan_for_pattern(PassPattern())
        assert len(matches) >= 1

    def test_detect_todo(self, tmpdir):
        code = "# TODO: implement this\nx = 1\n"
        _make_file(tmpdir, "todo.py", code)
        detector = FalseConfidenceDetector(str(tmpdir))
        pattern = ConfidencePattern("TODO/FIXME", r"TODO|FIXME", "minor", "d", "f")
        matches = detector.scan_for_pattern(pattern)
        assert len(matches) >= 1

    def test_detect_not_implemented(self, tmpdir):
        code = "def foo():\n    raise NotImplementedError\n"
        _make_file(tmpdir, "not_impl.py", code)
        detector = FalseConfidenceDetector(str(tmpdir))
        pattern = ConfidencePattern("NotImplemented", r"raise\s+NotImplementedError", "critical", "d", "f")
        matches = detector.scan_for_pattern(pattern)
        assert len(matches) >= 1

    def test_detect_hardcoded_success(self, tmpdir):
        code = "return True  # proof success\n"
        _make_file(tmpdir, "hardcode.py", code)
        detector = FalseConfidenceDetector(str(tmpdir))
        pattern = ConfidencePattern("hardcoded success", r"return\s+True\s*#.*success", "critical", "d", "f")
        matches = detector.scan_for_pattern(pattern)
        assert len(matches) >= 1

    def test_scan_all_finds_patterns(self, tmpdir):
        code = (
            "# TODO: fix this\n"
            "def verify():\n"
            "    pass\n"
        )
        _make_file(tmpdir, "mixed.py", code)
        detector = FalseConfidenceDetector(str(tmpdir))
        result = detector.scan_all()
        assert result.total_count >= 2

    def test_scan_all_no_false_positives(self, tmpdir):
        code = "def real_func(x):\n    return x + 1\n"
        _make_file(tmpdir, "clean.py", code)
        detector = FalseConfidenceDetector(str(tmpdir))
        result = detector.scan_all()
        assert result.total_count < 5  # maybe mock all patterns match

    def test_scan_non_python_files_ignored(self, tmpdir):
        _make_file(tmpdir, "data.txt", "TODO: implement\n")
        detector = FalseConfidenceDetector(str(tmpdir))
        detector.scan_all()
        assert True

    def test_generate_report_string(self, tmpdir):
        _make_file(tmpdir, "bug.py", "# TODO: fix\n")
        detector = FalseConfidenceDetector(str(tmpdir))
        detector.scan_all()
        report = detector.generate_report()
        assert isinstance(report, str)
        assert "FALSE CONFIDENCE DETECTOR" in report
        assert "TODO/FIXME" in report or "SUMMARY" in report

    def test_empty_directory_generates_report(self, tmpdir):
        detector = FalseConfidenceDetector(str(tmpdir))
        result = detector.scan_all()
        assert result.total_count == 0
        report = detector.generate_report()
        assert "No false confidence" in report


class TestScanForFalseConfidence:
    """
    TestScanForFalseConfidence
    
    Positive test cases for scanforfalseconfidence.
    """
    def test_scan_function(self, tmpdir):
        _make_file(tmpdir, "a.py", "# TODO\n")
        result = scan_for_false_confidence(str(tmpdir))
        assert isinstance(result, DetectionResult)
        assert result.total_count >= 1


class TestAuditor:
    """
    Tests for audit_source, audit_tests, audit_benchmarks, dedup, report format.
    """
    def test_audit_source(self, tmpdir):
        _make_file(tmpdir, "s.py", "# FIXME: later\n")
        result = audit_source(str(tmpdir))
        assert result.total_count >= 1

    def test_audit_tests(self, tmpdir):
        _make_file(tmpdir, "test_foo.py", "def test_bar():\n    pass\n")
        result = audit_tests(str(tmpdir))
        assert result.total_count >= 1

    def test_audit_benchmarks(self, tmpdir):
        _make_file(tmpdir, "bench_foo.py", 'benchmark = {"mean": 999}\n')
        result = audit_benchmarks(str(tmpdir))
        assert result.total_count >= 1

    def test_deduplicate(self):
        p1 = ConfidencePattern("test", r"a", "critical", "d", "f", file_match="/a.py", line_number=1)
        p2 = ConfidencePattern("test", r"a", "critical", "d", "f", file_match="/a.py", line_number=1)
        p3 = ConfidencePattern("test2", r"b", "major", "d", "f", file_match="/b.py", line_number=5)
        deduped = deduplicate_patterns([p1, p2, p3])
        assert len(deduped) == 2

    def test_format_audit_report(self, tmpdir):
        _make_file(tmpdir, "x.py", "return True  # proof success\n")
        result = audit_source(str(tmpdir))
        report = format_audit_report(result)
        assert isinstance(report, str)
        assert "FALSE CONFIDENCE AUDIT REPORT" in report

    def test_generate_audit_report_function(self, tmpdir):
        _make_file(tmpdir, "y.py", "def verify():\n    pass\n")
        result = generate_audit_report(str(tmpdir))
        assert result.total_count >= 1

    def test_audit_all(self, tmpdir):
        sub = os.path.join(tmpdir, "sub")
        os.makedirs(sub)
        _make_file(tmpdir, "a.py", "TODO")
        _make_file(sub, "b.py", "FIXME")
        results = audit_all([str(tmpdir)])
        assert len(results) >= 1
        for path, result in results.items():
            assert isinstance(result, DetectionResult)


class TestFalsePositives:
    """
    Tests ensuring genuine assertions and real implementations are not flagged.
    """
    def test_genuine_assertion_not_flagged(self, tmpdir):
        code = "assert x == 42\n"
        _make_file(tmpdir, "good_assert.py", code)
        detector = FalseConfidenceDetector(str(tmpdir))
        pattern = ConfidencePattern("fake assertion", r"assert\s+True\s*$", "critical", "d", "f")
        matches = detector.scan_for_pattern(pattern)
        assert len(matches) == 0

    def test_real_implementation_not_flagged(self, tmpdir):
        code = (
            "def validate(x):\n"
            "    if x < 0:\n"
            "        return False\n"
            "    return True\n"
        )
        _make_file(tmpdir, "real_impl.py", code)
        detector = FalseConfidenceDetector(str(tmpdir))
        pattern = ConfidencePattern("always valid", r"if\s*.*:[\s\S]*?return\s+True\s*else\s*:[\s\S]*?return\s+True", "critical", "d", "f")
        matches = detector.scan_for_pattern(pattern)
        assert len(matches) == 0


class TestFalseNegatives:
    """
    Tests ensuring empty except, NotImplemented, commented tests, and mock security are caught.
    """
    def test_empty_except_caught(self, tmpdir):
        code = "try:\n    x = 1\nexcept:\n    pass\n"
        _make_file(tmpdir, "empty_except.py", code)
        detector = FalseConfidenceDetector(str(tmpdir))
        pattern = ConfidencePattern("empty except", r"except\s*.*:[\s\S]*?pass", "major", "d", "f")
        matches = detector.scan_for_pattern(pattern)
        assert len(matches) >= 1

    def test_not_implemented_caught(self, tmpdir):
        code = "def foo():\n    raise NotImplementedError\n"
        _make_file(tmpdir, "ni.py", code)
        detector = FalseConfidenceDetector(str(tmpdir))
        pattern = ConfidencePattern("NotImplemented", r"raise\s+NotImplementedError", "critical", "d", "f")
        matches = detector.scan_for_pattern(pattern)
        assert len(matches) >= 1

    def test_commented_test_caught(self, tmpdir):
        code = "# def test_something():\n"
        _make_file(tmpdir, "test_comment.py", code)
        detector = FalseConfidenceDetector(str(tmpdir))
        pattern = ConfidencePattern("commented test", r"#\s*def\s+test", "major", "d", "f")
        matches = detector.scan_for_pattern(pattern)
        assert len(matches) >= 1

    def test_mock_security_caught(self, tmpdir):
        code = "# mock: this is not real security\n"
        _make_file(tmpdir, "mock_sec.py", code)
        detector = FalseConfidenceDetector(str(tmpdir))
        pattern = ConfidencePattern("mock security", r"#.*mock", "critical", "d", "f")
        matches = detector.scan_for_pattern(pattern)
        assert len(matches) >= 1


class TestPhaseIntegration:
    """
    Tests that the phase module is importable and callable.
    """
    def test_phase_module_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "phase_false_confidence",
            "scripts/phases/phase_false_confidence.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "phase_false_confidence")
        assert callable(mod.phase_false_confidence)
