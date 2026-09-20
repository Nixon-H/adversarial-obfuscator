"""
bench_benchmark_integrity.py

Benchmarks for Benchmark Integrity Verification (Feature 184).

Measures hashing, tamper detection, and verification performance.
"""

from __future__ import annotations

import os
import sys
import time
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.benchmark_integrity.integrity import BenchmarkIntegrityVerifier


def _make_bench_files(tmpdir: str, count: int, size_kb: int = 1) -> None:
    for i in range(count):
        line = "x = " + str(i) + "\n"
        chunk = (line * (size_kb * 1024 // len(line)))[:size_kb * 1024]
        path = os.path.join(tmpdir, f"bench_{i}.py")
        with open(path, "w") as f:
            f.write(chunk)


def bench_hashing() -> dict:
    results: dict = {}
    for count, label in [(10, "10files"), (100, "100files")]:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_bench_files(tmpdir, count)
            verifier = BenchmarkIntegrityVerifier(root_dir=tmpdir)
            verifier.tests_dir = tmpdir
            start = time.perf_counter()
            hashes = verifier.hash_benchmark_files()
            elapsed = time.perf_counter() - start
            results[label] = {
                "file_count": count,
                "time_seconds": round(elapsed, 4),
                "files_per_second": round(count / elapsed, 2) if elapsed > 0 else 0,
            }
    return results


def bench_full_verification() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        _make_bench_files(tmpdir, 50)
        verifier = BenchmarkIntegrityVerifier(root_dir=tmpdir)
        verifier.tests_dir = tmpdir
        previous = {}
        for fname in sorted(os.listdir(tmpdir)):
            if fname.endswith(".py"):
                previous[fname] = "0" * 64
        start = time.perf_counter()
        verifier.hash_benchmark_files()
        verifier.detect_tampering(previous)
        verifier.detect_replay()
        verifier.detect_modification()
        score = verifier.compute_integrity_score()
        elapsed = time.perf_counter() - start
        return {
            "time_seconds": round(elapsed, 4),
            "file_count": 50,
            "integrity_score": score,
        }


if __name__ == "__main__":
    print("=" * 60)
    print("  BENCHMARK INTEGRITY — BENCHMARKS")
    print("=" * 60)

    print("\n  [1] Hashing benchmarks:")
    hs = bench_hashing()
    for label, data in hs.items():
        print(f"    {label}: {data['time_seconds']:.4f}s, {data['files_per_second']:.0f} files/s")

    print("\n  [2] Full verification (50 files):")
    fv = bench_full_verification()
    print(f"    {fv['time_seconds']:.4f}s, score={fv['integrity_score']:.1f}")

    print("=" * 60)
    print("  BENCHMARKS COMPLETE")
    print("=" * 60)
