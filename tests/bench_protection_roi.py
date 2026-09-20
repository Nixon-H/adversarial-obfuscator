"""
bench_protection_roi.py

Benchmarks for Protection ROI Analysis (Feature 195).

Measures ROI computation, feature metrics, and top ROI sorting performance.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.protection_roi.engine import ProtectionROIEngine


def bench_full_roi_analysis() -> dict:
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
    tests_dir = os.path.join(os.path.dirname(__file__))
    engine = ProtectionROIEngine(scripts_dir=scripts_dir, tests_dir=tests_dir)

    timings = []
    for _ in range(3):
        start = time.perf_counter()
        result = engine.compute_protection_roi()
        elapsed = time.perf_counter() - start
        timings.append(elapsed)

    avg_time = round(sum(timings) / len(timings), 4)
    return {
        "avg_time_seconds": avg_time,
        "min_time_seconds": round(min(timings), 4),
        "max_time_seconds": round(max(timings), 4),
        "num_runs": len(timings),
        "total_features": result["total_features"],
        "overall_roi": result["overall_roi"],
        "net_negative_count": len(result["net_negative_features"]),
    }


def bench_empty_directory() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ProtectionROIEngine(scripts_dir=str(tmpdir))
        start = time.perf_counter()
        result = engine.compute_protection_roi()
        elapsed = time.perf_counter() - start
        return {
            "scan_time_seconds": round(elapsed, 4),
            "total_features": result["total_features"],
            "overall_roi": result["overall_roi"],
        }


def bench_large_feature_set() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(100):
            fpath = os.path.join(tmpdir, f"feature_{i}.py")
            imports = "import os, sys\n" if i % 2 == 0 else "import os\n"
            classes = f"class Handler{i}: pass\n" if i % 3 == 0 else ""
            funcs = "\n".join(
                f"def func_{i}_{j}():\n    pass\n" for j in range(i % 5 + 1)
            )
            with open(fpath, "w") as f:
                f.write(f'"""Feature {i}: Protect data."""\n{imports}{classes}{funcs}\n')

        engine = ProtectionROIEngine(scripts_dir=str(tmpdir))
        start = time.perf_counter()
        result = engine.compute_protection_roi()
        elapsed = time.perf_counter() - start
        return {
            "scan_time_seconds": round(elapsed, 4),
            "total_features": result["total_features"],
            "overall_roi": result["overall_roi"],
        }


if __name__ == "__main__":
    print("=" * 60)
    print("  PROTECTION ROI ENGINE — BENCHMARKS")
    print("=" * 60)

    print("\n  [1] Full ROI analysis:")
    ft = bench_full_roi_analysis()
    print(f"    avg: {ft['avg_time_seconds']:.4f}s, "
          f"features: {ft['total_features']}, "
          f"overall ROI: {ft['overall_roi']}, "
          f"net-negative: {ft['net_negative_count']}")

    print("\n  [2] Empty directory:")
    em = bench_empty_directory()
    print(f"    scan: {em['scan_time_seconds']:.4f}s")

    print("\n  [3] Large feature set (100 features):")
    lg = bench_large_feature_set()
    print(f"    scan: {lg['scan_time_seconds']:.4f}s, "
          f"{lg['total_features']} features, "
          f"ROI: {lg['overall_roi']}")

    print("=" * 60)
    print("  BENCHMARKS COMPLETE")
    print("=" * 60)
