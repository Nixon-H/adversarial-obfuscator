"""
bench_verification_diversity.py

Benchmarks for Verification Diversity Analysis (Feature 185).

Measures full analysis time across all verification methods.
"""

from __future__ import annotations

import os
import sys
import time
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.verification_diversity.diversity import VerificationDiversityAnalyzer


def _make_phase_dir(tmpdir: str, num_phases: int) -> str:
    phases_dir = os.path.join(tmpdir, "phases")
    os.makedirs(phases_dir)
    init_lines = []
    for i in range(num_phases):
        name = f"phase_{i}"
        init_lines.append(f"from .{name} import {name}\n")
        with open(os.path.join(phases_dir, f"{name}.py"), "w") as f:
            f.write(
                f"def {name}(args):\n"
                f"    if args is not None:\n"
                f"        return {i}\n"
                f"    else:\n"
                f"        return 0\n"
            )
    with open(os.path.join(phases_dir, "__init__.py"), "w") as f:
        f.writelines(init_lines)
    return phases_dir


def bench_full_analysis() -> dict:
    results: dict = {}
    for count, label in [(10, "10phases"), (50, "50phases")]:
        with tempfile.TemporaryDirectory() as tmpdir:
            phases_dir = _make_phase_dir(tmpdir, count)
            analyzer = VerificationDiversityAnalyzer()
            analyzer.phases_dir = phases_dir
            start = time.perf_counter()
            report = analyzer.run_all()
            elapsed = time.perf_counter() - start
            results[label] = {
                "num_phases": count,
                "time_seconds": round(elapsed, 4),
                "diversity_score": report["diversity_score"],
                "disagreements": len(report["disagreements"]),
            }
    return results


def bench_single_strategy() -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        phases_dir = _make_phase_dir(tmpdir, 30)
        analyzer = VerificationDiversityAnalyzer()
        analyzer.phases_dir = phases_dir
        start = time.perf_counter()
        analyzer.static_verify()
        t_static = time.perf_counter() - start
        start = time.perf_counter()
        analyzer.symbolic_verify()
        t_symbolic = time.perf_counter() - start
        return {
            "static_time": round(t_static, 4),
            "symbolic_time": round(t_symbolic, 4),
            "num_phases": 30,
        }


if __name__ == "__main__":
    print("=" * 60)
    print("  VERIFICATION DIVERSITY — BENCHMARKS")
    print("=" * 60)

    print("\n  [1] Full analysis:")
    fa = bench_full_analysis()
    for label, data in fa.items():
        print(f"    {label}: {data['time_seconds']:.4f}s, "
              f"score={data['diversity_score']:.1f}, disagr={data['disagreements']}")

    print("\n  [2] Single strategy (30 phases):")
    ss = bench_single_strategy()
    print(f"    static:   {ss['static_time']:.4f}s")
    print(f"    symbolic: {ss['symbolic_time']:.4f}s")

    print("=" * 60)
    print("  BENCHMARKS COMPLETE")
    print("=" * 60)
