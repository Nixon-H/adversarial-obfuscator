"""
test_adversarial_bench.py

Tests for Adversarial Benchmark Generator (Feature 175).

Test coverage:
- Positive tests verify generation for all target systems, attack types, suite execution
- Negative tests verify invalid code, failing pipelines, empty suites
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from scripts.adversarial_bench import (
    AdversarialBenchGenerator,
    AdversarialTest,
    AdversarialSuite,
    AdversarialTestSuite,
    generate_adversarial_tests,
    run_adversarial_suite,
)


class TestAdversarialTest:
    """
    TestAdversarialTest
    
    Positive test cases for adversarial.
    """
    def test_dataclass_defaults(self):
        t = AdversarialTest(
            test_id="ADV-0001",
            target_system="proof",
            attack_type="bypass",
            source_code="x = 1",
            expected_failure="test fails",
        )
        assert t.test_id == "ADV-0001"
        assert t.target_system == "proof"
        assert t.attack_type == "bypass"
        assert t.source_code == "x = 1"
        assert t.expected_failure == "test fails"
        assert t.actual_result is None
        assert t.severity == "medium"

    def test_dataclass_all_fields(self):
        t = AdversarialTest(
            test_id="ADV-0002",
            target_system="watermark",
            attack_type="overload",
            source_code="def f(): pass",
            expected_failure="wm fails",
            actual_result="vuln found",
            severity="critical",
        )
        assert t.actual_result == "vuln found"
        assert t.severity == "critical"


class TestAdversarialSuite:
    """
    TestAdversarialSuite
    
    Positive test cases for adversarialsuite.
    """
    def test_dataclass_defaults(self):
        s = AdversarialSuite()
        assert s.tests == []
        assert s.total == 0
        assert s.vulnerabilities_found == 0
        assert s.failing_targets == []
        assert s.timestamp == ""

    def test_dataclass_with_values(self):
        t = AdversarialTest(
            test_id="ADV-0001", target_system="proof",
            attack_type="bypass", source_code="x=1",
            expected_failure="fail",
        )
        s = AdversarialSuite(
            tests=[t],
            total=1,
            vulnerabilities_found=1,
            failing_targets=["proof"],
            timestamp="2025-01-01T00:00:00",
        )
        assert len(s.tests) == 1
        assert s.total == 1
        assert s.vulnerabilities_found == 1


class TestAdversarialBenchGenerator:
    """
    TestAdversarialBenchGenerator
    
    Positive test cases for adversarialbenchgenerator.
    """
    def test_generate_for_proofs(self):
        gen = AdversarialBenchGenerator(seed=42)
        tests = gen.generate_for_proofs()
        assert len(tests) >= 3
        for t in tests:
            assert t.target_system == "proof"
            assert t.test_id.startswith("PROOF")
            assert len(t.source_code) > 0
            assert len(t.expected_failure) > 0

    def test_generate_for_watermark(self):
        gen = AdversarialBenchGenerator(seed=42)
        tests = gen.generate_for_watermark()
        assert len(tests) >= 3
        for t in tests:
            assert t.target_system == "watermark"
            assert t.test_id.startswith("WM")

    def test_generate_for_coverage(self):
        gen = AdversarialBenchGenerator(seed=42)
        tests = gen.generate_for_coverage()
        assert len(tests) >= 3
        for t in tests:
            assert t.target_system == "coverage"
            assert t.test_id.startswith("COV")

    def test_generate_for_synthesis(self):
        gen = AdversarialBenchGenerator(seed=42)
        tests = gen.generate_for_synthesis()
        assert len(tests) >= 3
        for t in tests:
            assert t.target_system == "synthesis"
            assert t.test_id.startswith("SYNTH")

    def test_generate_for_leakage(self):
        gen = AdversarialBenchGenerator(seed=42)
        tests = gen.generate_for_leakage()
        assert len(tests) >= 3
        for t in tests:
            assert t.target_system == "leakage"
            assert t.test_id.startswith("LEAK")

    def test_generate_all_default(self):
        gen = AdversarialBenchGenerator(seed=42)
        tests = gen.generate_all()
        assert len(tests) == 20
        systems = set(t.target_system for t in tests)
        assert "proof" in systems
        assert "watermark" in systems
        assert "coverage" in systems
        assert "synthesis" in systems
        assert "leakage" in systems

    def test_generate_all_custom_count(self):
        gen = AdversarialBenchGenerator(seed=42)
        tests = gen.generate_all(count=10)
        assert len(tests) == 10

    def test_generate_all_large_count(self):
        gen = AdversarialBenchGenerator(seed=42)
        tests = gen.generate_all(count=100)
        assert len(tests) == 100

    def test_generate_all_all_attack_types(self):
        gen = AdversarialBenchGenerator(seed=42)
        tests = gen.generate_all(count=50)
        attack_types = set(t.attack_type for t in tests)
        expected = {"bypass", "confuse", "overload", "edge_case", "pathological"}
        for at in expected:
            assert at in attack_types, f"Missing attack type: {at}"

    def test_unique_ids(self):
        gen = AdversarialBenchGenerator(seed=42)
        tests = gen.generate_all(count=50)
        ids = [t.test_id for t in tests]
        assert len(ids) == len(set(ids))

    def test_severity_present(self):
        gen = AdversarialBenchGenerator(seed=42)
        tests = gen.generate_all(count=20)
        for t in tests:
            assert t.severity in ("low", "medium", "high", "critical")

    def test_source_code_compiles(self):
        gen = AdversarialBenchGenerator(seed=42)
        tests = gen.generate_all(count=20)
        for t in tests:
            try:
                compile(t.source_code, f"<{t.test_id}>", "exec")
            except SyntaxError as e:
                pytest.fail(f"Syntax error in {t.test_id}: {e}")

    def test_proofs_deeply_nested(self):
        gen = AdversarialBenchGenerator(seed=42)
        tests = gen.generate_for_proofs()
        nested = [t for t in tests if "deeply_nested" in t.source_code or "nested" in t.test_id]
        assert len(nested) >= 1
        code = nested[0].source_code
        assert "((" in code or "nested" in code

    def test_watermark_short_functions(self):
        gen = AdversarialBenchGenerator(seed=42)
        tests = gen.generate_for_watermark()
        short = [t for t in tests if t.attack_type == "bypass"]
        for t in short:
            assert len(t.source_code.strip()) < 200

    def test_coverage_thousand_blocks(self):
        gen = AdversarialBenchGenerator(seed=42)
        tests = gen.generate_for_coverage()
        overload = [t for t in tests if t.attack_type == "overload"]
        assert len(overload) >= 1
        assert "thousand_blocks" in overload[0].source_code or "_state" in overload[0].source_code


class TestAdversarialTestSuite:
    """
    TestAdversarialTestSuite
    
    Positive test cases for adversarialsuite.
    """
    def test_suite_load_tests(self):
        gen = AdversarialBenchGenerator(seed=42)
        suite = AdversarialTestSuite()
        suite.load_tests(gen, count=15)
        assert len(suite.tests) == 15

    def test_run_test_execution(self):
        t = AdversarialTest(
            test_id="ADV-TEST", target_system="proof",
            attack_type="bypass", source_code="x = 42",
            expected_failure="none",
        )
        suite = AdversarialTestSuite()
        result = suite.run_test(t)
        assert result["test_id"] == "ADV-TEST"
        assert result["actual_result"] is not None

    def test_run_test_with_invalid_code(self):
        t = AdversarialTest(
            test_id="ADV-BAD", target_system="proof",
            attack_type="bypass", source_code="this is not valid python {{{",
            expected_failure="syntax error",
        )
        suite = AdversarialTestSuite()
        result = suite.run_test(t)
        assert result["vulnerability_detected"] is True
        assert result["error"] is not None

    def test_run_test_with_custom_pipeline(self):
        def fake_pipeline(code):
            if "return" in code:
                return 42
            raise RuntimeError("no return")

        t = AdversarialTest(
            test_id="ADV-PIPE", target_system="synthesis",
            attack_type="bypass", source_code="return 42",
            expected_failure="none",
        )
        suite = AdversarialTestSuite()
        result = suite.run_test(t, pipeline=fake_pipeline)
        assert result["actual_result"] == "42"

    def test_run_test_with_failing_pipeline(self):
        def failing_pipeline(code):
            raise RuntimeError("pipeline crashed")

        t = AdversarialTest(
            test_id="ADV-FAIL", target_system="leakage",
            attack_type="bypass", source_code="x = 1",
            expected_failure="pipeline fails",
        )
        suite = AdversarialTestSuite()
        result = suite.run_test(t, pipeline=failing_pipeline)
        assert result["vulnerability_detected"] is True

    def test_run_all(self):
        gen = AdversarialBenchGenerator(seed=42)
        suite = AdversarialTestSuite()
        suite.load_tests(gen, count=10)
        result = suite.run_all()
        assert isinstance(result, AdversarialSuite)
        assert result.total == 10
        assert result.timestamp != ""

    def test_get_vulnerabilities_before_run(self):
        suite = AdversarialTestSuite()
        assert suite.get_vulnerabilities() == []

    def test_get_vulnerabilities_after_run(self):
        t = AdversarialTest(
            test_id="ADV-VULN", target_system="proof",
            attack_type="bypass", source_code="invalid {{{ code",
            expected_failure="syntax error",
        )
        suite = AdversarialTestSuite()
        suite.tests = [t]
        suite.run_all()
        vulns = suite.get_vulnerabilities()
        assert len(vulns) >= 1

    def test_generate_report_structure(self):
        gen = AdversarialBenchGenerator(seed=42)
        suite = AdversarialTestSuite()
        suite.load_tests(gen, count=15)
        suite.run_all()
        report = suite.generate_report()
        assert "timestamp" in report
        assert "total_tests" in report
        assert report["total_tests"] == 15
        assert "vulnerabilities_found" in report
        assert "vulnerability_rate" in report
        assert "by_system" in report
        assert "total_elapsed_ms" in report

    def test_generate_report_by_system(self):
        gen = AdversarialBenchGenerator(seed=42)
        suite = AdversarialTestSuite()
        suite.load_tests(gen, count=20)
        suite.run_all()
        report = suite.generate_report()
        for system in ("proof", "watermark", "coverage", "synthesis", "leakage"):
            assert system in report["by_system"]
            sys_data = report["by_system"][system]
            assert "total" in sys_data
            assert "vulnerabilities" in sys_data
            assert "average_elapsed_ms" in sys_data

    def test_generate_report_no_results(self):
        suite = AdversarialTestSuite()
        report = suite.generate_report()
        assert "error" in report


class TestModuleLevelFunctions:
    """
    TestModuleLevelFunctions
    
    Positive test cases for modulelevelfunctions.
    """
    def test_generate_adversarial_tests(self):
        tests = generate_adversarial_tests(count=12)
        assert len(tests) == 12

    def test_run_adversarial_suite(self):
        gen = AdversarialBenchGenerator(seed=42)
        tests = gen.generate_all(count=8)
        result = run_adversarial_suite(tests)
        assert isinstance(result, AdversarialSuite)
        assert result.total == 8

    def test_module_export(self):
        from scripts.adversarial_bench import (
            AdversarialBenchGenerator,
            AdversarialTest,
            AdversarialSuite,
            generate_adversarial_tests,
            run_adversarial_suite,
        )
        assert AdversarialBenchGenerator is not None
        assert AdversarialTest is not None
        assert AdversarialSuite is not None
        assert callable(generate_adversarial_tests)
        assert callable(run_adversarial_suite)
