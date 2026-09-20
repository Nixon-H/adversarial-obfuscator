"""
bench_runtime_truth.py

Benchmarks for Runtime Truth Monitoring (Feature 193).

Measures intended execution parsing and actual evidence collection performance.
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.runtime_truth.monitor import RuntimeTruthMonitor


def bench_full_runtime_truth() -> dict:
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
    monitor = RuntimeTruthMonitor(scripts_dir=scripts_dir)

    timings = []
    for _ in range(5):
        start = time.perf_counter()
        result = monitor.record_runtime_truth()
        elapsed = time.perf_counter() - start
        timings.append(elapsed)

    avg_time = round(sum(timings) / len(timings), 4)
    result = monitor.record_runtime_truth()
    return {
        "avg_time_seconds": avg_time,
        "min_time_seconds": round(min(timings), 4),
        "max_time_seconds": round(max(timings), 4),
        "num_runs": len(timings),
        "intended_phases": len(result["intended_execution"]),
        "actual_evidence": len(result["actual_evidence"]),
        "gaps": len(result["gaps"]),
        "truth_score": result["truth_score"],
    }


def bench_empty_directory() -> dict:
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        monitor = RuntimeTruthMonitor(scripts_dir=str(tmpdir))
        start = time.perf_counter()
        result = monitor.record_runtime_truth()
        elapsed = time.perf_counter() - start
        return {
            "scan_time_seconds": round(elapsed, 4),
            "intended_phases": len(result["intended_execution"]),
            "truth_score": result["truth_score"],
        }


def bench_large_build_file() -> dict:
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        phases_dir = os.path.join(tmpdir, "phases")
        os.makedirs(phases_dir, exist_ok=True)
        build_path = os.path.join(tmpdir, "build.py")
        imports = []
        calls = []
        for i in range(200):
            pname = f"phase_test_{i}"
            imports.append(f"    {pname},")
            calls.append(f"    {pname}(opts)")
            phase_path = os.path.join(phases_dir, f"{pname}.py")
            with open(phase_path, "w") as f:
                f.write(
                    f"def {pname}(opts):\n"
                    f"    assert True\n"
                    f"    return None\n"
                )
        build_code = (
            "import sys\n"
            "from scripts.phases import (\n"
            f"{chr(10).join(imports)}\n"
            ")\n"
            "def main():\n"
            f"{chr(10).join(calls)}\n"
            "    pass\n"
        )
        with open(build_path, "w") as f:
            f.write(build_code)

        monitor = RuntimeTruthMonitor(scripts_dir=str(tmpdir))
        start = time.perf_counter()
        result = monitor.record_runtime_truth()
        elapsed = time.perf_counter() - start
        return {
            "scan_time_seconds": round(elapsed, 4),
            "num_phases": len(imports),
            "intended_phases": len(result["intended_execution"]),
            "actual_evidence": len(result["actual_evidence"]),
            "truth_score": result["truth_score"],
        }


if __name__ == "__main__":
    print("=" * 60)
    print("  RUNTIME TRUTH MONITOR — BENCHMARKS")
    print("=" * 60)

    print("\n  [1] Full runtime truth analysis:")
    ft = bench_full_runtime_truth()
    print(f"    avg: {ft['avg_time_seconds']:.4f}s, "
          f"intended: {ft['intended_phases']}, "
          f"evidence: {ft['actual_evidence']}, "
          f"gaps: {ft['gaps']}, "
          f"score: {ft['truth_score']}")

    print("\n  [2] Empty directory:")
    em = bench_empty_directory()
    print(f"    scan: {em['scan_time_seconds']:.4f}s, "
          f"score: {em['truth_score']}")

    print("\n  [3] Large build file (200 phases):")
    lg = bench_large_build_file()
    print(f"    scan: {lg['scan_time_seconds']:.4f}s, "
          f"{lg['intended_phases']} phases, "
          f"{lg['actual_evidence']} evidence items, "
          f"score: {lg['truth_score']}")

    print("=" * 60)
    print("  BENCHMARKS COMPLETE")
    print("=" * 60)
