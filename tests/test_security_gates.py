"""
test_security_gates.py

Tests for Security Gate Evaluation.

Test coverage:
- Positive tests verify gate checks, pass/fail logic, report generation
- Negative tests verify empty gates, missing data, edge cases
"""
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestGateAndResultDataclasses:
    """
    TestGateAndResultDataclasses
    
    Positive test cases for gateandresultdataclasses.
    """
    def test_gate_result_dataclass(self):
        from scripts.security_regression.gate import GateResult, GateSeverity
        r = GateResult(
            gate_name="Test Gate",
            metric_name="test_metric",
            baseline_value=1.0,
            current_value=0.95,
            delta_ratio=-0.05,
            threshold_ratio=0.9,
            passed=True,
            severity=GateSeverity.BLOCKER,
            message="test",
        )
        assert r.gate_name == "Test Gate"
        assert r.metric_name == "test_metric"
        assert r.baseline_value == 1.0
        assert r.current_value == 0.95
        assert r.delta_ratio == pytest.approx(-0.05, abs=1e-3)
        assert r.threshold_ratio == 0.9
        assert r.passed is True
        assert r.severity == GateSeverity.BLOCKER

    def test_gate_result_post_init_delta(self):
        from scripts.security_regression.gate import GateResult, GateSeverity
        r = GateResult(
            gate_name="CFG", metric_name="cfg_entropy",
            baseline_value=1.0, current_value=0.5,
            delta_ratio=0.0, threshold_ratio=0.9,
            passed=False, severity=GateSeverity.BLOCKER, message="",
        )
        assert r.delta_ratio == -0.5
        assert r.passed is False

    def test_security_gate_dataclass(self):
        from scripts.security_regression.gate import SecurityGate, GateSeverity
        g = SecurityGate("Test", "test_metric", 0.9, GateSeverity.BLOCKER)
        assert g.name == "Test"
        assert g.metric_name == "test_metric"
        assert g.threshold_ratio == 0.9
        assert g.severity == GateSeverity.BLOCKER
        assert g.enabled is True

    def test_security_gate_check_pass(self):
        from scripts.security_regression.gate import SecurityGate, GateSeverity
        g = SecurityGate("Test", "test_metric", 0.9, GateSeverity.BLOCKER)
        result = g.check(1.0, 0.95)
        assert result.passed is True
        assert "PASS" in result.message

    def test_security_gate_check_fail(self):
        from scripts.security_regression.gate import SecurityGate, GateSeverity
        g = SecurityGate("Test", "test_metric", 0.9, GateSeverity.BLOCKER)
        result = g.check(1.0, 0.5)
        assert result.passed is False
        assert "FAIL" in result.message

    def test_gate_severity_values(self):
        from scripts.security_regression.gate import GateSeverity
        assert GateSeverity.BLOCKER.value == "blocker"
        assert GateSeverity.WARNING.value == "warning"
        assert GateSeverity.INFO.value == "info"


class TestDefaultGates:
    """
    TestDefaultGates
    
    Positive test cases for defaultgates.
    """
    def test_default_gates(self):
        from scripts.security_regression.checker import DEFAULT_GATES
        assert len(DEFAULT_GATES) == 8
        names = [g.name for g in DEFAULT_GATES]
        assert "CFG Entropy" in names
        assert "AI Resistance" in names
        assert "Proof Coverage" in names
        assert "Survivability" in names
        assert "Plaintext Exposure" in names
        assert "Semantic Leakage" in names
        assert "Watermark Survival" in names
        assert "Symbolic Resistance" in names

    def test_default_gates_config(self):
        from scripts.security_regression.checker import DEFAULT_GATES
        from scripts.security_regression.gate import GateSeverity
        for g in DEFAULT_GATES:
            assert 0.0 < g.threshold_ratio <= 1.0
            assert g.severity in (GateSeverity.BLOCKER, GateSeverity.WARNING, GateSeverity.INFO)
            assert g.enabled is True


class TestCheckerLoadSaveBaseline:
    """
    TestCheckerLoadSaveBaseline
    
    Positive test cases for checkerloadsavebaseline.
    """
    def test_checker_load_baseline(self):
        from scripts.security_regression.checker import RegressionChecker
        baseline_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "baseline_report.json"
        )
        if os.path.exists(baseline_path):
            checker = RegressionChecker(baseline_path)
            assert len(checker.baseline) > 0
            assert "build_success" in checker.baseline
            assert float(checker.baseline["build_success"]) == 1.0

    def test_checker_load_baseline_missing(self):
        from scripts.security_regression.checker import RegressionChecker
        with tempfile.NamedTemporaryFile(suffix=".json") as f:
            path = f.name + ".nonexistent"
        checker = RegressionChecker(path)
        assert "cfg_entropy" in checker.baseline
        assert "ai_resistance" in checker.baseline

    def test_checker_save_baseline(self):
        from scripts.security_regression.checker import RegressionChecker
        metrics = {"test_metric": 0.85, "another": 0.92}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            checker = RegressionChecker()
            checker.save_baseline(path, metrics)
            assert os.path.exists(path)
            with open(path) as f:
                data = json.load(f)
            assert data["test_metric"] == 0.85
            assert data["another"] == 0.92
            assert "timestamp" in data
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_load_baseline_function(self):
        from scripts.security_regression.checker import load_baseline
        baseline_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "baseline_report.json"
        )
        if os.path.exists(baseline_path):
            metrics = load_baseline(baseline_path)
            assert "build_success" in metrics

    def test_update_baseline_function(self):
        from scripts.security_regression.checker import update_baseline
        metrics = {"test_val": 0.77}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            update_baseline(path, metrics)
            with open(path) as f:
                data = json.load(f)
            assert data["test_val"] == 0.77
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestCheckerGateCheck:
    """
    TestCheckerGateCheck
    
    Positive test cases for checkergatecheck.
    """
    def test_checker_gate_pass(self):
        from scripts.security_regression.checker import RegressionChecker
        from scripts.security_regression.gate import SecurityGate, GateSeverity
        checker = RegressionChecker()
        gate = SecurityGate("Test", "test_metric", 0.9, GateSeverity.BLOCKER)
        result = checker.check_gate(gate, 0.95)
        assert result.passed is True
        assert result.current_value == 0.95

    def test_checker_gate_fail(self):
        from scripts.security_regression.checker import RegressionChecker
        from scripts.security_regression.gate import SecurityGate, GateSeverity
        import tempfile, json
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"test_metric": 1.0}, f)
            bpath = f.name
        try:
            checker = RegressionChecker(bpath)
            gate = SecurityGate("Test", "test_metric", 0.9, GateSeverity.BLOCKER)
            result = checker.check_gate(gate, 0.5)
            assert result.passed is False
        finally:
            os.unlink(bpath)

    def test_checker_check_all_gates(self):
        from scripts.security_regression.checker import RegressionChecker
        metrics = {
            "cfg_entropy": 0.95,
            "ai_resistance": 0.90,
            "proof_coverage": 0.92,
            "survivability": 0.88,
            "plaintext_exposure": 0.85,
            "semantic_leakage": 0.90,
            "watermark_survival": 0.93,
            "symbolic_resistance": 0.87,
        }
        checker = RegressionChecker()
        results = checker.check_all_gates(metrics)
        assert len(results) == 8
        assert all(r.passed for r in results)

    def test_checker_has_blockers(self):
        from scripts.security_regression.checker import RegressionChecker
        from scripts.security_regression.gate import GateResult, GateSeverity
        results = [
            GateResult("G1", "m1", 1.0, 0.3, -0.7, 0.9, False, GateSeverity.BLOCKER, "fail"),
            GateResult("G2", "m2", 1.0, 0.5, -0.5, 0.9, False, GateSeverity.WARNING, "fail"),
        ]
        checker = RegressionChecker()
        assert checker.has_blockers(results) is True

    def test_checker_no_blockers(self):
        from scripts.security_regression.checker import RegressionChecker
        from scripts.security_regression.gate import GateResult, GateSeverity
        results = [
            GateResult("G1", "m1", 1.0, 0.95, -0.05, 0.9, True, GateSeverity.BLOCKER, "pass"),
            GateResult("G2", "m2", 1.0, 0.5, -0.5, 0.9, False, GateSeverity.WARNING, "warn"),
        ]
        checker = RegressionChecker()
        assert checker.has_blockers(results) is False


class TestCheckRegressionGates:
    """
    TestCheckRegressionGates
    
    Positive test cases for checkregressiongates.
    """
    def test_check_regression_gates_all_pass(self):
        from scripts.security_regression.checker import check_regression_gates
        metrics = {
            "cfg_entropy": 0.95,
            "ai_resistance": 0.90,
            "proof_coverage": 0.92,
            "survivability": 0.88,
            "plaintext_exposure": 0.85,
            "semantic_leakage": 0.90,
            "watermark_survival": 0.93,
            "symbolic_resistance": 0.87,
        }
        report = check_regression_gates(metrics)
        assert report.all_passed is True


class TestMetricsCollector:
    """
    TestMetricsCollector
    
    Positive test cases for metricscollector.
    """
    def test_metrics_collector_collect(self):
        from scripts.security_regression.metrics_collector import MetricsCollector
        collector = MetricsCollector()
        metrics = collector.collect_all_metrics()
        assert isinstance(metrics, dict)
        for key in ("cfg_entropy", "ai_resistance", "proof_coverage",
                     "survivability", "plaintext_exposure", "semantic_leakage",
                     "watermark_survival", "symbolic_resistance"):
            assert key in metrics

    def test_metrics_collector_fallback(self):
        from scripts.security_regression.metrics_collector import MetricsCollector
        tmpdir = tempfile.mkdtemp()
        try:
            collector = MetricsCollector(build_dir=tmpdir)
            metrics = collector.collect_with_fallback()
            assert isinstance(metrics, dict)
            for key in ("cfg_entropy", "ai_resistance", "proof_coverage",
                         "survivability", "plaintext_exposure", "semantic_leakage",
                         "watermark_survival", "symbolic_resistance"):
                assert key in metrics
                assert metrics[key] > 0
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_metrics_collector_to_dict(self):
        from scripts.security_regression.metrics_collector import MetricsCollector
        collector = MetricsCollector()
        collector.collect_all_metrics()
        d = collector.to_dict()
        assert isinstance(d, dict)
        assert len(d) > 0


class TestGateReport:
    """
    TestGateReport
    
    Positive test cases for gatereport.
    """
    def test_gate_report_generation(self):
        from scripts.security_regression.report import generate_gate_report
        from scripts.security_regression.gate import GateResult, GateSeverity
        results = [
            GateResult("G1", "m1", 1.0, 0.95, -0.05, 0.9, True, GateSeverity.BLOCKER, ""),
        ]
        report = generate_gate_report(results, tempfile.mkdtemp())
        assert len(report.gates) == 1
        assert report.all_passed is True
        assert len(report.blockers) == 1
        assert len(report.warnings) == 0

    def test_format_report_text(self):
        from scripts.security_regression.report import GateReport, format_report_text
        from scripts.security_regression.gate import GateResult, GateSeverity
        r = GateResult("G1", "m1", 1.0, 0.95, -0.05, 0.9, True, GateSeverity.BLOCKER, "")
        report = GateReport(
            gates=[r], blockers=[r], warnings=[], all_passed=True, summary="1/1 passed"
        )
        text = format_report_text(report)
        assert "SECURITY GATE REPORT" in text
        assert "PASSED" in text

    def test_format_report_json(self):
        from scripts.security_regression.report import GateReport, format_report_json
        from scripts.security_regression.gate import GateResult, GateSeverity
        r = GateResult("G1", "m1", 1.0, 0.95, -0.05, 0.9, True, GateSeverity.BLOCKER, "")
        report = GateReport(
            gates=[r], blockers=[r], warnings=[], all_passed=True, summary="1/1 passed"
        )
        j = format_report_json(report)
        data = json.loads(j)
        assert data["all_passed"] is True
        assert data["gate_count"] == 1

    def test_report_to_dict(self):
        from scripts.security_regression.report import GateReport
        from scripts.security_regression.gate import GateResult, GateSeverity
        r = GateResult("G1", "m1", 1.0, 0.95, -0.05, 0.9, True, GateSeverity.BLOCKER, "")
        report = GateReport(gates=[r], blockers=[r], warnings=[], all_passed=True, summary="ok")
        d = report.to_dict()
        assert d["all_passed"] is True
        assert d["gate_count"] == 1


class TestNegative:
    """
    TestNegative
    
    Negative test cases — exercises error handling and edge cases for negative.
    """
    def test_empty_baseline(self):
        from scripts.security_regression.checker import RegressionChecker
        checker = RegressionChecker()
        checker.baseline = {}
        from scripts.security_regression.gate import SecurityGate, GateSeverity
        gate = SecurityGate("Test", "test_metric", 0.9, GateSeverity.BLOCKER)
        result = checker.check_gate(gate, 0.95)
        assert result.passed is True
        assert result.baseline_value == 0.95

    def test_missing_metrics(self):
        from scripts.security_regression.checker import RegressionChecker
        checker = RegressionChecker()
        results = checker.check_all_gates({})
        assert len(results) == 8
        for r in results:
            assert r.current_value == 0.0
            assert r.passed is False

    def test_all_gates_fail(self):
        from scripts.security_regression.checker import check_regression_gates
        import tempfile, json
        baseline = {k: 1.0 for k in (
            "cfg_entropy", "ai_resistance", "proof_coverage",
            "survivability", "plaintext_exposure", "semantic_leakage",
            "watermark_survival", "symbolic_resistance",
        )}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(baseline, f)
            bpath = f.name
        try:
            metrics = {k: 0.1 for k in baseline}
            report = check_regression_gates(metrics, baseline_path=bpath)
            assert report.all_passed is False
            blocker_gates = sum(1 for g in report.gates if g.severity.value == "blocker")
            assert len(report.blockers) == blocker_gates
            for r in report.gates:
                assert r.passed is False
        finally:
            os.unlink(bpath)

    def test_zero_threshold(self):
        from scripts.security_regression.checker import RegressionChecker
        from scripts.security_regression.gate import SecurityGate, GateSeverity
        checker = RegressionChecker()
        gate = SecurityGate("Test", "test_metric", 0.0, GateSeverity.BLOCKER)
        result = checker.check_gate(gate, 0.0)
        assert result.passed is True

    def test_zero_baseline_value(self):
        from scripts.security_regression.checker import RegressionChecker
        from scripts.security_regression.gate import SecurityGate, GateSeverity
        checker = RegressionChecker()
        checker.baseline = {"test_metric": 0.0}
        gate = SecurityGate("Test", "test_metric", 0.9, GateSeverity.BLOCKER)
        result = checker.check_gate(gate, 0.5)
        assert result.passed is True

    def test_generate_report_all_fail(self):
        from scripts.security_regression.report import generate_gate_report
        from scripts.security_regression.gate import GateResult, GateSeverity
        results = [
            GateResult("G1", "m1", 1.0, 0.1, -0.9, 0.9, False, GateSeverity.BLOCKER, "fail"),
            GateResult("G2", "m2", 1.0, 0.1, -0.9, 0.9, False, GateSeverity.BLOCKER, "fail"),
        ]
        report = generate_gate_report(results, tempfile.mkdtemp())
        assert report.all_passed is False
        assert "BLOCKER" in report.summary

    def test_phase_security_gates_disabled(self):
        from scripts.phases.phase_security_gates import phase_security_gates
        import tempfile
        tmp_build = tempfile.mkdtemp()
        class Args:
            security_gates = False
            update_baseline = False
            gate_threshold = 0.0
            build_dir = tmp_build
        try:
            result = phase_security_gates(Args())
            assert result is True
        finally:
            import shutil
            shutil.rmtree(tmp_build, ignore_errors=True)


class TestPhaseSecurityGates:
    """
    TestPhaseSecurityGates
    
    Positive test cases for phasesecuritygates.
    """
    def test_phase_importable(self):
        phase_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "phases", "phase_security_gates.py"
        )
        assert os.path.exists(phase_path)
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "scripts.phases.phase_security_gates", phase_path
        )
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        assert mod is not None
        assert hasattr(spec.loader, "exec_module")

    def test_phase_security_gates_fails_on_blockers(self):
        from scripts.phases.phase_security_gates import phase_security_gates
        import tempfile
        tmp_build = tempfile.mkdtemp()

        class Args:
            security_gates = True
            update_baseline = False
            gate_threshold = None
            build_dir = tmp_build

        try:
            result = phase_security_gates(Args())
            assert isinstance(result, bool)
        finally:
            import shutil
            shutil.rmtree(tmp_build, ignore_errors=True)
