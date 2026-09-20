"""
bench_security_gates.py

Benchmarks for security regression gates.

Measures gate checking, metrics collection, and report generation performance.
"""
import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_BASELINE_METRICS = {
    "cfg_entropy": 0.95,
    "ai_resistance": 0.90,
    "proof_coverage": 0.92,
    "survivability": 0.88,
    "plaintext_exposure": 0.85,
    "semantic_leakage": 0.90,
    "watermark_survival": 0.93,
    "symbolic_resistance": 0.87,
}


class TestSecurityGatesBenchmarks:
    @pytest.fixture
    def baseline_file(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(_BASELINE_METRICS, f)
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def empty_build_dir(self):
        d = tempfile.mkdtemp()
        yield d
        import shutil
        shutil.rmtree(d, ignore_errors=True)

    def test_gate_check_time_single(self, benchmark):
        from scripts.security_regression.checker import RegressionChecker
        from scripts.security_regression.gate import SecurityGate, GateSeverity
        checker = RegressionChecker()
        gate = SecurityGate("CFG Entropy", "cfg_entropy", 0.9, GateSeverity.BLOCKER)

        def run():
            return checker.check_gate(gate, 0.95)

        result = benchmark(run)
        assert result.passed is True

    def test_full_gate_check_all_gates(self, baseline_file, benchmark):
        from scripts.security_regression.checker import RegressionChecker
        checker = RegressionChecker(baseline_file)

        def run():
            return checker.check_all_gates(_BASELINE_METRICS)

        results = benchmark(run)
        assert len(results) == 8
        assert all(r.passed for r in results)

    def test_metrics_collection_time(self, empty_build_dir, benchmark):
        from scripts.security_regression.metrics_collector import MetricsCollector
        collector = MetricsCollector(build_dir=empty_build_dir)

        def run():
            return collector.collect_with_fallback()

        metrics = benchmark(run)
        assert isinstance(metrics, dict)
        assert len(metrics) >= 8

    def test_report_generation_time(self, benchmark):
        from scripts.security_regression.report import generate_gate_report
        from scripts.security_regression.gate import GateResult, GateSeverity

        results = [
            GateResult(f"G{i}", f"m{i}", 1.0, 0.95, -0.05, 0.9, True, GateSeverity.BLOCKER, "")
            for i in range(8)
        ]

        def run():
            return generate_gate_report(results, tempfile.mkdtemp())

        report = benchmark(run)
        assert report.all_passed is True

    def test_regression_checker_init_time(self, baseline_file, benchmark):
        from scripts.security_regression.checker import RegressionChecker

        def run():
            return RegressionChecker(baseline_file)

        checker = benchmark(run)
        assert len(checker.baseline) > 0

    def test_metrics_collector_to_dict_time(self, benchmark):
        from scripts.security_regression.metrics_collector import MetricsCollector
        collector = MetricsCollector()
        collector.collect_all_metrics()

        def run():
            return collector.to_dict()

        d = benchmark(run)
        assert isinstance(d, dict)
