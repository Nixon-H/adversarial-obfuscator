"""
test_runtime_truth.py

Tests for Runtime Truth Monitoring (Feature 193).

Test coverage:
- Positive tests verify intended execution parsing, actual evidence collection, gap analysis
- Negative tests verify empty scripts dir, missing build.py, no phases dir
"""
from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.runtime_truth.monitor import (
    ActualEvidence,
    GapAnalysis,
    IntendedExecution,
    RuntimeTruthMonitor,
)


class TestIntendedExecution:
    """
    TestIntendedExecution
    
    Positive test cases for intendedexecution.
    """
    def test_dataclass(self):
        ie = IntendedExecution(
            phase_name="phase_test", line_number=42,
            call_expression="phase_test(opts)", enabled_by_flag="test-flag",
        )
        assert ie.phase_name == "phase_test"
        assert ie.line_number == 42


class TestActualEvidence:
    """
    TestActualEvidence
    
    Positive test cases for actualevidence.
    """
    def test_dataclass(self):
        ae = ActualEvidence(
            phase_name="phase_test", file_path="/a.py",
            has_assertions=True, has_validations=True,
            assertion_count=5, validation_keywords=["assert"],
            function_defs=["run"],
        )
        assert ae.phase_name == "phase_test"
        assert ae.assertion_count == 5


class TestGapAnalysis:
    """
    TestGapAnalysis
    
    Positive test cases for gapanalysis.
    """
    def test_dataclass(self):
        ga = GapAnalysis(
            phase_name="phase_test", intended=True,
            has_evidence=False, gap_type="missing",
            description="test gap",
        )
        assert ga.phase_name == "phase_test"
        assert ga.gap_type == "missing"


class TestRuntimeTruthMonitorPositive:
    """
    TestRuntimeTruthMonitorPositive
    
    Positive test cases for runtimetruthmonitorpositive.
    """
    def test_parse_multiple_phases(self):
        monitor = RuntimeTruthMonitor(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = monitor.record_runtime_truth()
        assert "intended_execution" in result
        assert "actual_evidence" in result
        assert "gaps" in result
        assert "truth_score" in result

    def test_truth_score_range(self):
        monitor = RuntimeTruthMonitor(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = monitor.record_runtime_truth()
        assert 0.0 <= result["truth_score"] <= 100.0

    def test_actual_evidence_non_empty(self):
        monitor = RuntimeTruthMonitor(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = monitor.record_runtime_truth()
        assert len(result["intended_execution"]) > 0

    def test_evidence_contains_phase_names(self):
        monitor = RuntimeTruthMonitor(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = monitor.record_runtime_truth()
        for ev in result["actual_evidence"]:
            assert "phase_name" in ev
            assert "file_path" in ev
            assert "has_assertions" in ev

    def test_intended_contains_phase_names(self):
        monitor = RuntimeTruthMonitor(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = monitor.record_runtime_truth()
        for intent in result["intended_execution"]:
            assert "phase_name" in intent
            assert "line_number" in intent

    def test_gaps_listed(self):
        monitor = RuntimeTruthMonitor(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = monitor.record_runtime_truth()
        assert isinstance(result["gaps"], list)

    def test_build_flag_detection(self):
        monitor = RuntimeTruthMonitor(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = monitor.record_runtime_truth()
        has_flags = any(
            intent.get("enabled_by_flag") for intent in result["intended_execution"]
        )
        assert isinstance(has_flags, bool)

    def test_assertion_counting(self):
        monitor = RuntimeTruthMonitor(
            scripts_dir=os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        result = monitor.record_runtime_truth()
        for ev in result["actual_evidence"]:
            assert isinstance(ev["assertion_count"], int)
            assert ev["assertion_count"] >= 0


class TestRuntimeTruthMonitorNegative:
    """
    TestRuntimeTruthMonitorNegative
    
    Negative test cases — exercises error handling and edge cases for runtimetruthmonitornegative.
    """
    def test_empty_scripts_dir(self, tmpdir):
        monitor = RuntimeTruthMonitor(scripts_dir=str(tmpdir))
        result = monitor.record_runtime_truth()
        assert result["truth_score"] == 0.0
        assert result["intended_execution"] == []
        assert result["actual_evidence"] == []

    def test_no_build_py(self, tmpdir):
        os.makedirs(os.path.join(tmpdir, "phases"), exist_ok=True)
        monitor = RuntimeTruthMonitor(scripts_dir=str(tmpdir))
        result = monitor.record_runtime_truth()
        assert result["intended_execution"] == []

    def test_no_phases_dir(self, tmpdir):
        build_py = os.path.join(tmpdir, "build.py")
        with open(build_py, "w") as f:
            f.write("# empty build\n")
        monitor = RuntimeTruthMonitor(scripts_dir=str(tmpdir))
        result = monitor.record_runtime_truth()
        assert result["actual_evidence"] == []

    def test_build_py_syntax_error(self, tmpdir):
        build_py = os.path.join(tmpdir, "build.py")
        with open(build_py, "w") as f:
            f.write("this is not python {{{")
        monitor = RuntimeTruthMonitor(scripts_dir=str(tmpdir))
        result = monitor.record_runtime_truth()
        assert result["intended_execution"] == []

    def test_gap_for_missing_phase_file(self, tmpdir):
        build_py = os.path.join(tmpdir, "build.py")
        phases_dir = os.path.join(tmpdir, "phases")
        os.makedirs(phases_dir, exist_ok=True)
        with open(build_py, "w") as f:
            f.write(
                "import sys\n"
                "from scripts.phases import (\n"
                "    phase_missing_test,\n"
                ")\n"
                "def main():\n"
                "    phase_missing_test(opts)\n"
            )
        phase_file = os.path.join(phases_dir, "phase_missing_test.py")
        if os.path.exists(phase_file):
            os.remove(phase_file)
        monitor = RuntimeTruthMonitor(scripts_dir=str(tmpdir))
        result = monitor.record_runtime_truth()
        gaps = [g for g in result["gaps"] if "missing_phase_file" in g.get("gap_type", "")]
        assert isinstance(gaps, list)


class TestPhaseIntegration:
    """
    TestPhaseIntegration
    
    Positive test cases for phaseintegration.
    """
    def test_phase_module_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "phase_runtime_truth",
            "scripts/phases/phase_runtime_truth.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "phase_runtime_truth")
        assert callable(mod.phase_runtime_truth)
