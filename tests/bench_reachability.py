"""
bench_reachability.py

Benchmarks for Feature Reachability Analysis (Feature 169).

Measures CLI tracing, phase tracing, import chain resolution, and full analysis.
"""
from __future__ import annotations

import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from scripts.reachability.analyzer import ReachabilityAnalyzer


def bench_full_reachability_analysis():
    analyzer = ReachabilityAnalyzer()
    start = time.perf_counter()
    report = analyzer.generate_report()
    elapsed = time.perf_counter() - start
    print(f"\n  Full reachability analysis: {elapsed:.4f}s")
    print(f"  Total features:  {report.total_features}")
    print(f"  REACHABLE:       {report.reachable_count}")
    print(f"  PARTIALLY:       {report.partially_reachable_count}")
    print(f"  UNREACHABLE:     {report.unreachable_count}")
    print(f"  Throughput:      {report.total_features / elapsed:.1f} features/s")
    return elapsed


def bench_single_feature_analysis():
    analyzer = ReachabilityAnalyzer()
    start = time.perf_counter()
    iterations = 50
    for i in range(iterations):
        analyzer.analyze_feature("obfuscation")
    elapsed = time.perf_counter() - start
    print(f"\n  Single feature analysis ({iterations}x): {elapsed:.4f}s")
    print(f"  Per call: {elapsed / iterations * 1000:.4f}ms")
    return elapsed


def bench_cli_flag_tracing():
    analyzer = ReachabilityAnalyzer()
    start = time.perf_counter()
    iterations = 100
    flags = ["--payload", "--cfg-mutation", "--obfuscate", "--skip-irgen", "--rop"]
    for i in range(iterations):
        for flag in flags:
            analyzer.trace_cli_flag(flag)
    elapsed = time.perf_counter() - start
    print(f"\n  CLI flag tracing ({iterations * len(flags)}x): {elapsed:.4f}s")
    print(f"  Per call: {elapsed / (iterations * len(flags)) * 1000:.4f}ms")
    return elapsed


def bench_phase_tracing():
    analyzer = ReachabilityAnalyzer()
    start = time.perf_counter()
    iterations = 100
    phases = ["phase_obfuscate", "phase_ir_compile", "phase_llvm_codegen", "phase_package"]
    for i in range(iterations):
        for phase in phases:
            analyzer.trace_phase(phase)
    elapsed = time.perf_counter() - start
    print(f"\n  Phase tracing ({iterations * len(phases)}x): {elapsed:.4f}s")
    print(f"  Per call: {elapsed / (iterations * len(phases)) * 1000:.4f}ms")
    return elapsed


if __name__ == "__main__":
    print("=" * 60)
    print("  REACHABILITY ANALYSIS BENCHMARKS")
    print("=" * 60)
    t1 = bench_full_reachability_analysis()
    t2 = bench_single_feature_analysis()
    t3 = bench_cli_flag_tracing()
    t4 = bench_phase_tracing()
    total = t1 + t2 + t3 + t4
    print(f"\n  Total benchmark time: {total:.4f}s")
    print("=" * 60)
