"""
bench_longitudinal_tracking.py

Benchmarks for Longitudinal Security Tracking (Feature 196).

Measures baseline/metric comparison, delta computation, and trend analysis.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.longitudinal_tracking.tracker import LongitudinalTracker


def bench_full_tracking() -> dict:
    config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
    tracker = LongitudinalTracker(config_dir=config_dir)

    timings = []
    for _ in range(5):
        start = time.perf_counter()
        result = tracker.track_longitudinal_security()
        elapsed = time.perf_counter() - start
        timings.append(elapsed)

    avg_time = round(sum(timings) / len(timings), 4)
    return {
        "avg_time_seconds": avg_time,
        "min_time_seconds": round(min(timings), 4),
        "max_time_seconds": round(max(timings), 4),
        "num_runs": len(timings),
        "baseline_test_count": result["baseline"]["test_count"],
        "current_test_count": result["current"]["test_count"],
        "trend_score": result["trend_score"],
        "drift_detected": result["drift_detected"],
    }


def bench_empty_directory() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = LongitudinalTracker(config_dir=str(tmpdir))
        start = time.perf_counter()
        result = tracker.track_longitudinal_security()
        elapsed = time.perf_counter() - start
        return {
            "scan_time_seconds": round(elapsed, 4),
            "trend_score": result["trend_score"],
            "drift_detected": result["drift_detected"],
        }


def bench_with_historical_data() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        baseline = {
            "test_pass_rate": 1.0, "test_count": 50,
            "test_passed": 50, "test_failed": 0,
            "build_success": True, "cli_flags": 30,
            "timestamp": 1000000.0,
        }
        with open(os.path.join(tmpdir, "baseline_report.json"), "w") as f:
            json.dump(baseline, f)

        hist_dir = os.path.join(tmpdir, "history")
        os.makedirs(hist_dir, exist_ok=True)
        for i in range(20):
            snap = {
                "test_count": 50 + i * 2,
                "cli_flags": 30 + i,
                "build_success": i % 5 != 0,
                "timestamp": 2000000.0 + i * 1000,
            }
            with open(os.path.join(hist_dir, f"snapshot_{i}.json"), "w") as f:
                json.dump(snap, f)

        tracker = LongitudinalTracker(config_dir=str(tmpdir))
        start = time.perf_counter()
        result = tracker.track_longitudinal_security()
        elapsed = time.perf_counter() - start
        return {
            "scan_time_seconds": round(elapsed, 4),
            "historical_snapshots": len(result["historical_snapshots"]),
            "trend_score": result["trend_score"],
            "drift_detected": result["drift_detected"],
        }


if __name__ == "__main__":
    print("=" * 60)
    print("  LONGITUDINAL SECURITY TRACKER — BENCHMARKS")
    print("=" * 60)

    print("\n  [1] Full tracking analysis:")
    ft = bench_full_tracking()
    print(f"    avg: {ft['avg_time_seconds']:.4f}s, "
          f"baseline: {ft['baseline_test_count']} tests, "
          f"current: {ft['current_test_count']} tests, "
          f"score: {ft['trend_score']}, "
          f"drift: {ft['drift_detected']}")

    print("\n  [2] Empty directory:")
    em = bench_empty_directory()
    print(f"    scan: {em['scan_time_seconds']:.4f}s, "
          f"score: {em['trend_score']}")

    print("\n  [3] With 20 historical snapshots:")
    hs = bench_with_historical_data()
    print(f"    scan: {hs['scan_time_seconds']:.4f}s, "
          f"{hs['historical_snapshots']} snapshots, "
          f"score: {hs['trend_score']}, "
          f"drift: {hs['drift_detected']}")

    print("=" * 60)
    print("  BENCHMARKS COMPLETE")
    print("=" * 60)
