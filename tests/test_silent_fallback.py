"""
test_silent_fallback.py

Tests for Silent Fallback Detection (Feature 192).

Test coverage:
- Positive tests verify detection of bare except, logged, reported, and printed fallbacks
- Negative tests verify clean files, specific exceptions, syntax errors are ignored
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.silent_fallback.detector import (
    Classification,
    SilentFallbackDetector,
    SilentFallbackFinding,
)


def _make_file(tmpdir: str, name: str, content: str) -> str:
    path = os.path.join(tmpdir, name)
    with open(path, "w") as f:
        f.write(content)
    return path


class TestClassification:
    """
    TestClassification
    
    Positive test cases for classification.
    """
    def test_enum_values(self):
        assert Classification.SILENT.value == "silent"
        assert Classification.LOGGED.value == "logged"
        assert Classification.REPORTED.value == "reported"

    def test_enum_distinct(self):
        assert len(set(Classification)) == 3


class TestSilentFallbackFinding:
    """
    TestSilentFallbackFinding
    
    Positive test cases for silentfallbackfinding.
    """
    def test_dataclass_defaults(self):
        f = SilentFallbackFinding(
            file_path="/a.py", line_number=10, classification=Classification.SILENT,
            try_line=5, except_line=10, exception_type="bare",
            has_logging=False,
        )
        assert f.file_path == "/a.py"
        assert f.line_number == 10
        assert f.classification == Classification.SILENT
        assert f.snippet == ""

    def test_dataclass_with_snippet(self):
        f = SilentFallbackFinding(
            file_path="/a.py", line_number=10, classification=Classification.LOGGED,
            try_line=5, except_line=10, exception_type="Exception",
            has_logging=True, snippet="except: log('err')",
        )
        assert f.snippet == "except: log('err')"


class TestSilentFallbackDetectorPositive:
    """
    TestSilentFallbackDetectorPositive
    
    Positive test cases for silentfallbackdetectorpositive.
    """
    def test_detect_bare_except_silent(self, tmpdir):
        code = (
            "def foo():\n"
            "    try:\n"
            "        secure_path()\n"
            "    except:\n"
            "        insecure_path()\n"
        )
        _make_file(tmpdir, "test_silent.py", code)
        detector = SilentFallbackDetector(str(tmpdir))
        result = detector.detect_silent_fallbacks()
        assert result["total_silent"] >= 1
        assert result["total_findings"] >= 1

    def test_detect_except_exception_silent(self, tmpdir):
        code = (
            "def foo():\n"
            "    try:\n"
            "        secure_path()\n"
            "    except Exception:\n"
            "        insecure_path()\n"
        )
        _make_file(tmpdir, "test_except_exc.py", code)
        detector = SilentFallbackDetector(str(tmpdir))
        result = detector.detect_silent_fallbacks()
        assert result["total_silent"] >= 1

    def test_detect_logged_fallback(self, tmpdir):
        code = (
            "def foo():\n"
            "    try:\n"
            "        secure_path()\n"
            "    except Exception:\n"
            "        log('fallback triggered')\n"
            "        insecure_path()\n"
        )
        _make_file(tmpdir, "test_logged.py", code)
        detector = SilentFallbackDetector(str(tmpdir))
        result = detector.detect_silent_fallbacks()
        assert result["classification_stats"].get("logged", 0) >= 1
        assert result["total_silent"] == 0

    def test_detect_reported_fallback(self, tmpdir):
        code = (
            "def foo():\n"
            "    try:\n"
            "        secure_path()\n"
            "    except Exception:\n"
            "        raise RuntimeError('fallback failed')\n"
        )
        _make_file(tmpdir, "test_reported.py", code)
        detector = SilentFallbackDetector(str(tmpdir))
        result = detector.detect_silent_fallbacks()
        assert result["classification_stats"].get("reported", 0) >= 1

    def test_detect_printed_fallback(self, tmpdir):
        code = (
            "def foo():\n"
            "    try:\n"
            "        secure_path()\n"
            "    except:\n"
            "        print('warning: using insecure path')\n"
            "        insecure_path()\n"
        )
        _make_file(tmpdir, "test_printed.py", code)
        detector = SilentFallbackDetector(str(tmpdir))
        result = detector.detect_silent_fallbacks()
        assert result["classification_stats"].get("logged", 0) >= 1

    def test_multiple_files(self, tmpdir):
        code1 = (
            "def a():\n"
            "    try:\n"
            "        safe()\n"
            "    except:\n"
            "        unsafe()\n"
        )
        code2 = (
            "def b():\n"
            "    try:\n"
            "        safe()\n"
            "    except Exception:\n"
            "        log('fallback')\n"
            "        unsafe()\n"
        )
        _make_file(tmpdir, "a.py", code1)
        _make_file(tmpdir, "b.py", code2)
        detector = SilentFallbackDetector(str(tmpdir))
        result = detector.detect_silent_fallbacks()
        assert result["total_findings"] >= 2
        assert "a.py" in str(result["findings"]) or str(tmpdir) in str(result["findings"])

    def test_classification_stats(self, tmpdir):
        code = (
            "def foo():\n"
            "    try:\n"
            "        secure_path()\n"
            "    except:\n"
            "        insecure_path()\n"
        )
        _make_file(tmpdir, "stat.py", code)
        detector = SilentFallbackDetector(str(tmpdir))
        result = detector.detect_silent_fallbacks()
        assert "silent" in result["classification_stats"]

    def test_silent_fallback_score_zero(self, tmpdir):
        code = (
            "def foo():\n"
            "    try:\n"
            "        secure_path()\n"
            "    except Exception:\n"
            "        log('logged')\n"
            "        fallback()\n"
        )
        _make_file(tmpdir, "log.py", code)
        detector = SilentFallbackDetector(str(tmpdir))
        result = detector.detect_silent_fallbacks()
        assert result["silent_fallback_score"] == 0.0


class TestSilentFallbackDetectorNegative:
    """
    TestSilentFallbackDetectorNegative
    
    Negative test cases — exercises error handling and edge cases for silentfallbackdetectornegative.
    """
    def test_clean_file_no_findings(self, tmpdir):
        code = "def foo(x):\n    return x + 1\n"
        _make_file(tmpdir, "clean.py", code)
        detector = SilentFallbackDetector(str(tmpdir))
        result = detector.detect_silent_fallbacks()
        assert result["total_findings"] == 0

    def test_empty_directory(self, tmpdir):
        detector = SilentFallbackDetector(str(tmpdir))
        result = detector.detect_silent_fallbacks()
        assert result["total_findings"] == 0

    def test_non_python_files_ignored(self, tmpdir):
        path = os.path.join(tmpdir, "data.txt")
        with open(path, "w") as f:
            f.write("try:\n    pass\nexcept:\n    pass\n")
        detector = SilentFallbackDetector(str(tmpdir))
        result = detector.detect_silent_fallbacks()
        assert result["total_findings"] == 0

    def test_specific_exception_not_flagged(self, tmpdir):
        code = (
            "def foo():\n"
            "    try:\n"
            "        secure_path()\n"
            "    except ValueError:\n"
            "        insecure_path()\n"
        )
        _make_file(tmpdir, "specific.py", code)
        detector = SilentFallbackDetector(str(tmpdir))
        result = detector.detect_silent_fallbacks()
        assert result["total_silent"] == 0

    def test_syntax_error_file_skipped(self, tmpdir):
        _make_file(tmpdir, "bad.py", "this is not python {{{")
        detector = SilentFallbackDetector(str(tmpdir))
        result = detector.detect_silent_fallbacks()
        assert result["total_findings"] == 0

    def test_multiple_exception_tuple_not_flagged(self, tmpdir):
        code = (
            "def foo():\n"
            "    try:\n"
            "        secure_path()\n"
            "    except (ValueError, TypeError):\n"
            "        insecure_path()\n"
        )
        _make_file(tmpdir, "tuple.py", code)
        detector = SilentFallbackDetector(str(tmpdir))
        result = detector.detect_silent_fallbacks()
        assert result["total_silent"] == 0

    def test_per_file_output_format(self, tmpdir):
        code = (
            "def foo():\n"
            "    try:\n"
            "        safe()\n"
            "    except:\n"
            "        unsafe()\n"
        )
        _make_file(tmpdir, "fmt.py", code)
        detector = SilentFallbackDetector(str(tmpdir))
        result = detector.detect_silent_fallbacks()
        assert isinstance(result["findings"], dict)
        for fpath, findings in result["findings"].items():
            assert isinstance(fpath, str)
            for f in findings:
                assert "classification" in f
                assert "line_number" in f
                assert "has_logging" in f


class TestPhaseIntegration:
    """
    TestPhaseIntegration
    
    Positive test cases for phaseintegration.
    """
    def test_phase_module_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "phase_silent_fallback",
            "scripts/phases/phase_silent_fallback.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "phase_silent_fallback")
        assert callable(mod.phase_silent_fallback)

    def test_detector_can_scan_self(self):
        detector = SilentFallbackDetector(
            os.path.join(os.path.dirname(__file__), "..", "scripts", "silent_fallback")
        )
        result = detector.detect_silent_fallbacks()
        assert isinstance(result, dict)
        assert "findings" in result
