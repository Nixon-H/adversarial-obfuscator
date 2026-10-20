"""
bench_assumptions.py

Benchmarks for Assumption Tracking (Feature 171).

Measures assumption registration, checking, and report building performance.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


from scripts.assumptions import AssumptionTracker, build_assumption_report
from scripts.assumptions.registry import register_all


class TestBenchAssumptions:
    def test_bench_tracker_init(self, benchmark):
        benchmark(AssumptionTracker)

    def test_bench_register_all(self, benchmark):
        def _run():
            t = AssumptionTracker()
            register_all(t)
            return t
        benchmark(_run)

    def test_bench_build_report(self, benchmark):
        def _run():
            return build_assumption_report({
                "os": {"system": "linux", "machine": "x86_64"},
                "python3": True,
            })
        benchmark(_run)

    def test_bench_check_all_assumptions(self, benchmark):
        def _run():
            t = AssumptionTracker()
            register_all(t)
            caps = {
                "os": {"system": "linux", "machine": "x86_64"},
                "python3": True,
                "z3": True,
                "numpy": False,
                "hashlib": True,
                "angr": False,
                "gpu_hardware": False,
            }
            t.check_assumptions(caps)
            return t
        benchmark(_run)

    def test_bench_get_critical(self, benchmark):
        t = AssumptionTracker()
        register_all(t)
        t.check_assumptions({"os": {"system": "linux", "machine": "x86_64"}})
        benchmark(t.get_critical_assumptions)

    def test_bench_to_dict(self, benchmark):
        t = AssumptionTracker()
        register_all(t)
        benchmark(t.to_dict)

    def test_bench_build_report_json(self, benchmark):
        t = AssumptionTracker()
        register_all(t)
        t.check_assumptions({"os": {"system": "linux", "machine": "x86_64"}})
        r = t.build_report()
        benchmark(r.to_json)
