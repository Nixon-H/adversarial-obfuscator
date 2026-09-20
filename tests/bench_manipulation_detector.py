"""
bench_manipulation_detector.py

Benchmarks for Metric Manipulation Detector (Feature 183).

Measures full scan time for manipulation pattern detection.
"""

from __future__ import annotations

import os
import sys
import time
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.manipulation_detector.detector import MetricManipulationDetector


def _generate_bench_files(tmpdir: str, num_files: int, num_hardcoded: int) -> None:
    for i in range(num_files):
        if i < num_hardcoded:
            code = (
                "def compute_coverage():\n"
                "    return 100\n"
                "proof_score = 100\n"
                "survivability = 99\n"
            )
        else:
            code = (
                "def add(a, b):\n"
                "    return a + b\n"
                "x = 42\n"
            )
        path = os.path.join(tmpdir, f"file_{i}.py")
        with open(path, "w") as f:
            f.write(code)


def bench_full_scan() -> dict:
    results: dict = {}
    for num_files, label in [(50, "50files"), (200, "200files")]:
        with tempfile.TemporaryDirectory() as tmpdir:
            _generate_bench_files(tmpdir, num_files, num_files // 5)
            detector = MetricManipulationDetector(scripts_dir=tmpdir)
            start = time.perf_counter()
            result = detector.scan_all()
            elapsed = time.perf_counter() - start
            results[label] = {
                "num_files": num_files,
                "time_seconds": round(elapsed, 4),
                "findings": result["total_findings"],
                "mutations": result["total_mutations"],
                "files_per_second": round(num_files / elapsed, 2) if elapsed > 0 else 0,
            }
    return results


def bench_clean_directory() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(100):
            path = os.path.join(tmpdir, f"clean_{i}.py")
            with open(path, "w") as f:
                f.write(f"x_{i} = {i}\n")
        detector = MetricManipulationDetector(scripts_dir=tmpdir)
        start = time.perf_counter()
        result = detector.scan_all()
        elapsed = time.perf_counter() - start
        return {
            "time_seconds": round(elapsed, 4),
            "findings": result["total_findings"],
            "files_per_second": round(100 / elapsed, 2) if elapsed > 0 else 0,
        }


if __name__ == "__main__":
    print("=" * 60)
    print("  METRIC MANIPULATION DETECTOR — BENCHMARKS")
    print("=" * 60)

    print("\n  [1] Full scan (mixed files):")
    fs = bench_full_scan()
    for label, data in fs.items():
        print(f"    {label}: {data['time_seconds']:.4f}s, "
              f"{data['findings']} findings, {data['files_per_second']:.0f} files/s")

    print("\n  [2] Clean directory (100 files):")
    cd = bench_clean_directory()
    print(f"    scan: {cd['time_seconds']:.4f}s, "
          f"{cd['findings']} findings, {cd['files_per_second']:.0f} files/s")

    print("=" * 60)
    print("  BENCHMARKS COMPLETE")
    print("=" * 60)
