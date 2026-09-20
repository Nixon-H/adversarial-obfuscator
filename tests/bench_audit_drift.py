"""
bench_audit_drift.py

Benchmarks for Audit Drift Detection (Feature 186).

Measures source hashing, report inventory, and drift detection performance.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.audit_drift.detector import AuditDriftDetector


def _make_scripts(tmpdir: str, count: int) -> str:
    scripts_dir = os.path.join(tmpdir, "scripts")
    os.makedirs(scripts_dir)
    for i in range(count):
        path = os.path.join(scripts_dir, f"module_{i}.py")
        with open(path, "w") as f:
            f.write(f"x_{i} = {i}\ndef func_{i}():\n    return {i}\n")
    return scripts_dir


def _make_reports(tmpdir: str, count: int) -> str:
    build_dir = os.path.join(tmpdir, "build")
    os.makedirs(build_dir)
    for i in range(count):
        path = os.path.join(build_dir, f"scripts_module_{i}.py_report.json")
        with open(path, "w") as f:
            json.dump({"source_hash": hashlib.sha256(f"content{i}".encode()).hexdigest()}, f)
    return build_dir


def bench_full_drift_detection() -> dict:
    results: dict = {}
    for count, label in [(50, "50files"), (200, "200files")]:
        with tempfile.TemporaryDirectory() as tmpdir:
            scripts_dir = _make_scripts(tmpdir, count)
            build_dir = _make_reports(tmpdir, count)
            detector = AuditDriftDetector(root_dir=tmpdir)
            detector.scripts_dir = scripts_dir
            detector.build_dir = build_dir
            start = time.perf_counter()
            detector.hash_source_files()
            detector.inventory_reports()
            detector.detect_drift()
            score = detector.compute_staleness_score()
            elapsed = time.perf_counter() - start
            results[label] = {
                "file_count": count,
                "time_seconds": round(elapsed, 4),
                "staleness_score": score,
            }
    return results


def bench_hashing_alone() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        scripts_dir = _make_scripts(tmpdir, 100)
        detector = AuditDriftDetector(root_dir=tmpdir)
        detector.scripts_dir = scripts_dir
        start = time.perf_counter()
        snapshot = detector.hash_source_files()
        elapsed = time.perf_counter() - start
        return {
            "file_count": 100,
            "time_seconds": round(elapsed, 4),
            "files_per_second": round(100 / elapsed, 2) if elapsed > 0 else 0,
        }


if __name__ == "__main__":
    print("=" * 60)
    print("  AUDIT DRIFT DETECTOR — BENCHMARKS")
    print("=" * 60)

    print("\n  [1] Full drift detection:")
    fd = bench_full_drift_detection()
    for label, data in fd.items():
        print(f"    {label}: {data['time_seconds']:.4f}s, "
              f"score={data['staleness_score']:.1f}")

    print("\n  [2] Hashing (100 files):")
    hs = bench_hashing_alone()
    print(f"    {hs['time_seconds']:.4f}s, {hs['files_per_second']:.0f} files/s")

    print("=" * 60)
    print("  BENCHMARKS COMPLETE")
    print("=" * 60)
