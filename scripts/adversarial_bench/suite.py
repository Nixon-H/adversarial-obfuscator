"""
adversarial_bench/suite.py — Adversarial test execution and reporting (F175)

Purpose:
    Executes a collection of AdversarialTest cases against an optional pipeline
    callable (or via built-in compile/exec), records pass/fail/vulnerability
    status, and produces a report.

Architectural Role:
    Execution layer. Consumes AdversarialTest cases from the generator and
    produces an AdversarialSuite with results.

Security Relevance:
    Automated execution and reporting ensures adversarial tests are repeatable
    and their results are auditable.
"""

from __future__ import annotations

import datetime
import time
import traceback
from datetime import timezone
from typing import Any, Callable, Dict, List, Optional

from .generator import AdversarialBenchGenerator, AdversarialTest, AdversarialSuite


class AdversarialTestSuite:
    """Manages adversarial test execution, recording, and report generation.

    Can execute tests via an optional pipeline callable or via the built-in
    Python compile/exec path. Records execution time, errors, and vulnerability
    detection.
    """
    def __init__(self):
        self.tests: List[AdversarialTest] = []
        self.results: List[Dict[str, Any]] = []
        self._start_time: float = 0.0

    def load_tests(self, generator: AdversarialBenchGenerator, count: int = 20) -> None:
        """Load tests from a generator into this suite."""
        self.tests = generator.generate_all(count=count)

    def run_test(self, test: AdversarialTest, pipeline: Optional[Callable] = None) -> Dict[str, Any]:
        """Execute a single adversarial test via the pipeline (or built-in exec) and record results."""
        start = time.perf_counter()
        error = None
        result = None
        vulnerability_detected = False

        if pipeline is not None:
            try:
                result = pipeline(test.source_code)
                test.actual_result = result
            except Exception as e:
                error = str(e)
                test.actual_result = error
                vulnerability_detected = True
        else:
            try:
                compiled = compile(test.source_code, f"<{test.test_id}>", "exec")
                namespace = {}
                exec(compiled, namespace)
                test.actual_result = "executed"
            except Exception as e:
                error = str(e)
                test.actual_result = error
                vulnerability_detected = True

        elapsed = time.perf_counter() - start

        record = {
            "test_id": test.test_id,
            "target_system": test.target_system,
            "attack_type": test.attack_type,
            "expected_failure": test.expected_failure,
            "actual_result": str(test.actual_result),
            "error": error,
            "vulnerability_detected": vulnerability_detected,
            "elapsed_ms": round(elapsed * 1000, 2),
            "severity": test.severity,
        }
        return record

    def run_all(self, pipeline: Optional[Callable] = None) -> AdversarialSuite:
        """Run all loaded tests and aggregate results into an AdversarialSuite."""
        self._start_time = time.perf_counter()
        self.results = []

        for test in self.tests:
            record = self.run_test(test, pipeline)
            self.results.append(record)

        vulnerabilities = [r for r in self.results if r["vulnerability_detected"]]
        failing_targets = list(set(r["target_system"] for r in vulnerabilities))

        suite = AdversarialSuite(
            tests=self.tests,
            total=len(self.tests),
            vulnerabilities_found=len(vulnerabilities),
            failing_targets=failing_targets,
            timestamp=datetime.datetime.now(timezone.utc).isoformat(),
        )
        return suite

    def generate_report(self) -> Dict[str, Any]:
        """Generate a structured report dict from the current results."""
        if not self.results:
            return {"error": "No results to report. Run run_all() first."}

        vulnerabilities = [r for r in self.results if r["vulnerability_detected"]]
        by_system: Dict[str, List[Dict]] = {}
        for r in self.results:
            by_system.setdefault(r["target_system"], []).append(r)

        report = {
            "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
            "total_tests": len(self.results),
            "vulnerabilities_found": len(vulnerabilities),
            "vulnerability_rate": round(len(vulnerabilities) / max(len(self.results), 1) * 100, 2),
            "failing_targets": list(set(r["target_system"] for r in vulnerabilities)),
            "total_elapsed_ms": round((time.perf_counter() - self._start_time) * 1000, 2),
            "by_system": {},
        }

        for system, records in by_system.items():
            sys_vulns = [r for r in records if r["vulnerability_detected"]]
            report["by_system"][system] = {
                "total": len(records),
                "vulnerabilities": len(sys_vulns),
                "average_elapsed_ms": round(sum(r["elapsed_ms"] for r in records) / max(len(records), 1), 2),
                "tests": records,
            }

        return report

    def get_vulnerabilities(self) -> List[Dict[str, Any]]:
        """Return only the results where a vulnerability was detected."""
        if not self.results:
            return []
        return [r for r in self.results if r["vulnerability_detected"]]
