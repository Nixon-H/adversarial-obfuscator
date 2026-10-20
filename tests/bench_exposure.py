"""
bench_exposure.py

Benchmarks for Plaintext Exposure Metric (Feature 151).

Measures event recording, score computation, and report generation.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.exposure.tracker import ExposureTracker
from scripts.exposure.metric import PlaintextExposureMetric
from scripts.exposure.simulator import ExposureSimulator


class TestExposureBenchmarks:
    def test_bench_tracker_overhead_per_event(self, benchmark):
        def record_events():
            tracker = ExposureTracker()
            for i in range(100):
                tracker.record_appearance("microjit", f"fn_{i}", f"data_{i}".encode())
                tracker.record_disappearance("microjit", f"fn_{i}", f"data_{i}".encode())
            return len(tracker.get_events())

        result = benchmark(record_events)
        assert result == 200

    def test_bench_score_computation(self, benchmark):
        from scripts.exposure.tracker import ExposureEvent, ExposureEventType

        def compute():
            tracker = ExposureTracker()
            for i in range(50):
                ts = time.monotonic_ns() + i * 1000
                tracker._events.append(ExposureEvent("c", "f", ExposureEventType.PLAINTEXT_APPEARS, ts, f"h{i}"))
                tracker._events.append(ExposureEvent("c", "f", ExposureEventType.PLAINTEXT_DISAPPEARS, ts + 500, f"h{i}"))
            metric = PlaintextExposureMetric(tracker)
            return metric.compute_exposure_score()

        result = benchmark(compute)
        assert 0.0 <= result <= 100.0

    def test_bench_simulator_execution(self, benchmark):
        sim = ExposureSimulator()
        config = {
            "microjit": True,
            "fragmentation": True,
            "history_bound": True,
            "fhe_vm": True,
        }

        def run_sim():
            events, score = sim.simulate_plaintext_flow(None, config)
            return len(events), score

        result = benchmark(run_sim)
        assert result[0] > 0

    def test_bench_full_pipeline_overhead(self, benchmark):
        def run_pipeline():
            t = ExposureTracker()
            for i in range(20):
                t.record_appearance("microjit", f"fn_{i}", f"data_{i}".encode())
                t.record_encryption("microjit", f"fn_{i}")
                t.record_disappearance("microjit", f"fn_{i}", f"data_{i}".encode())
            metric = PlaintextExposureMetric(t)
            report = metric.generate_report()
            return report

        result = benchmark(run_pipeline)
        assert result.overall_score >= 0.0
        assert result.event_count == 60
