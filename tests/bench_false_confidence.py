"""
bench_false_confidence.py

Benchmarks for False Confidence Detection (Feature 173).

Measures full source scan time for false confidence patterns.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.false_confidence.detector import FalseConfidenceDetector


def _generate_large_source(num_lines: int) -> str:
    lines: list[str] = []
    for i in range(num_lines):
        if i % 50 == 0:
            lines.append(f"# TODO: implement line {i}\n")
        elif i % 100 == 0:
            lines.append(f"def verify_{i}():\n    pass\n")
        elif i % 150 == 0:
            lines.append(f"return True  # success\n")
        else:
            lines.append(f"x_{i} = {i}\n")
    return "".join(lines)


def bench_full_source_scan() -> dict:
    results: dict = {}

    for size, label in [(1000, "1k"), (5000, "5k"), (10000, "10k")]:
        with tempfile.TemporaryDirectory() as tmpdir:
            src = _generate_large_source(size)
            fpath = os.path.join(tmpdir, "bench_source.py")
            with open(fpath, "w") as f:
                f.write(src)

            detector = FalseConfidenceDetector(str(tmpdir))
            start = time.perf_counter()
            result = detector.scan_all()
            elapsed = time.perf_counter() - start

            report = detector.generate_report()

            results[f"{label}_lines"] = {
                "num_lines": size,
                "scan_time_seconds": round(elapsed, 4),
                "patterns_found": result.total_count,
                "critical": result.critical_count,
                "major": result.major_count,
                "minor": result.minor_count,
                "lines_per_second": round(size / elapsed, 2) if elapsed > 0 else 0,
                "report_length_chars": len(report),
            }

    return results


def bench_multi_file_scan() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(100):
            fpath = os.path.join(tmpdir, f"file_{i}.py")
            with open(fpath, "w") as f:
                f.write(f"# TODO: file {i}\nx = {i}\n")

        detector = FalseConfidenceDetector(str(tmpdir))
        start = time.perf_counter()
        result = detector.scan_all()
        elapsed = time.perf_counter() - start

        return {
            "num_files": 100,
            "scan_time_seconds": round(elapsed, 4),
            "patterns_found": result.total_count,
            "files_per_second": round(100 / elapsed, 2) if elapsed > 0 else 0,
        }


def bench_empty_directory() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        detector = FalseConfidenceDetector(str(tmpdir))
        start = time.perf_counter()
        result = detector.scan_all()
        elapsed = time.perf_counter() - start

        return {
            "scan_time_seconds": round(elapsed, 4),
            "patterns_found": result.total_count,
        }


if __name__ == "__main__":
    print("=" * 60)
    print("  FALSE CONFIDENCE DETECTOR — BENCHMARKS")
    print("=" * 60)

    print("\n  [1] Full source scan:")
    results = bench_full_source_scan()
    for label, data in results.items():
        print(f"    {label:>10s}: {data['scan_time_seconds']:.4f}s, "
              f"{data['patterns_found']} patterns, "
              f"{data['lines_per_second']:.0f} lines/s")

    print("\n  [2] Multi-file scan (100 files):")
    mf = bench_multi_file_scan()
    print(f"    scan: {mf['scan_time_seconds']:.4f}s, "
          f"{mf['patterns_found']} patterns, "
          f"{mf['files_per_second']:.0f} files/s")

    print("\n  [3] Empty directory scan:")
    em = bench_empty_directory()
    print(f"    scan: {em['scan_time_seconds']:.4f}s, "
          f"{em['patterns_found']} patterns")

    print("=" * 60)
    print("  BENCHMARKS COMPLETE")
    print("=" * 60)
