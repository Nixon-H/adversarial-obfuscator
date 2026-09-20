"""
bench_retirement.py

Benchmarks for Feature Retirement Analysis (Feature 176).

Measures assessment, classification, and scoring across all features.
"""
from __future__ import annotations

import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from scripts.feature_retirement.analyzer import RetirementAnalyzer


def bench_full_retirement_analysis():
    analyzer = RetirementAnalyzer()
    start = time.perf_counter()
    report = analyzer.generate_report()
    elapsed = time.perf_counter() - start
    print(f"\n  Full retirement analysis:       {elapsed:.4f}s")
    print(f"  Total features:                {report.total_features}")
    print(f"  DEPRECATE:                     {report.deprecate_count}")
    print(f"  MONITOR:                       {report.monitor_count}")
    print(f"  KEEP:                          {report.keep_count}")
    print(f"  OPTIMIZE:                      {report.optimize_count}")
    print(f"  Throughput:                    {report.total_features / elapsed:.1f} features/s")
    return elapsed


def bench_single_feature_assessment():
    analyzer = RetirementAnalyzer()
    start = time.perf_counter()
    iterations = 100
    for i in range(iterations):
        analyzer.assess_feature("obfuscation")
    elapsed = time.perf_counter() - start
    print(f"\n  Single feature assessment ({iterations}x): {elapsed:.4f}s")
    print(f"  Per call:                      {elapsed / iterations * 1000:.4f}ms")
    return elapsed


def bench_effectiveness_scoring():
    analyzer = RetirementAnalyzer()
    start = time.perf_counter()
    iterations = 200
    features = ["obfuscation", "encryption", "cfg_mutation", "watermark", "vm",
                 "jit", "diversity", "relay", "packaging", "cross_compile"]
    for i in range(iterations):
        for name in features:
            info = analyzer.feature_map.get(name, {})
            analyzer.compute_effectiveness(name, info)
            analyzer.compute_overhead(name, info)
            analyzer.compute_survivability(name, info)
    elapsed = time.perf_counter() - start
    print(f"\n  Scoring computation ({iterations * len(features)}x): {elapsed:.4f}s")
    print(f"  Per feature:                   {elapsed / (iterations * len(features)) * 1000:.4f}ms")
    return elapsed


def bench_classify_feature_type():
    analyzer = RetirementAnalyzer()
    start = time.perf_counter()
    iterations = 500
    names = ["obfuscation", "encryption", "cfg_mutation", "ssa_mutation",
             "cross_compile", "packaging", "coverage", "diversity",
             "_unknown_one", "_another_unknown"]
    for i in range(iterations):
        for name in names:
            analyzer.classify_feature_type(name)
    elapsed = time.perf_counter() - start
    print(f"\n  Feature type classification ({iterations * len(names)}x): {elapsed:.4f}s")
    print(f"  Per call:                      {elapsed / (iterations * len(names)) * 1000:.4f}ms")
    return elapsed


if __name__ == "__main__":
    print("=" * 60)
    print("  FEATURE RETIREMENT BENCHMARKS")
    print("=" * 60)
    t1 = bench_full_retirement_analysis()
    t2 = bench_single_feature_assessment()
    t3 = bench_effectiveness_scoring()
    t4 = bench_classify_feature_type()
    total = t1 + t2 + t3 + t4
    print(f"\n  Total benchmark time:          {total:.4f}s")
    print("=" * 60)
