"""
bench_invariant_engine.py

Benchmarks for Security Invariant Engine (Feature 191).

Measures invariant checking performance across all five invariant types.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.invariant_engine.engine import SecurityInvariantEngine


def bench_full_verification():
    engine = SecurityInvariantEngine()
    start = time.perf_counter()
    result = engine.verify_invariants()
    elapsed = time.perf_counter() - start
    print(f"\n  Full invariant verification: {elapsed:.4f}s")
    print(f"  Violations found: {result['violations_found']}")
    print(f"  Invariant score: {result['invariant_score']:.1f}")
    return elapsed


def bench_single_invariant():
    engine = SecurityInvariantEngine()
    invariants = [
        engine._check_no_feature_unreachable,
        engine._check_no_tautological_proof,
        engine._check_no_hardcoded_metrics,
        engine._check_no_silent_fallback,
        engine._check_no_undocumented_assumptions,
    ]
    start = time.perf_counter()
    iterations = 10
    for i in range(iterations):
        for inv_fn in invariants:
            inv_fn()
    elapsed = time.perf_counter() - start
    print(f"\n  Single invariant ({iterations * len(invariants)}x): {elapsed:.4f}s")
    print(f"  Per call: {elapsed / (iterations * len(invariants)) * 1000:.4f}ms")
    return elapsed


def bench_find_py_files():
    engine = SecurityInvariantEngine()
    start = time.perf_counter()
    iterations = 30
    for i in range(iterations):
        engine._find_py_files()
    elapsed = time.perf_counter() - start
    print(f"\n  Find Python files ({iterations}x): {elapsed:.4f}s")
    print(f"  Per call: {elapsed / iterations * 1000:.4f}ms")
    return elapsed


if __name__ == "__main__":
    print("=" * 60)
    print("  SECURITY INVARIANT ENGINE BENCHMARKS")
    print("=" * 60)
    t1 = bench_full_verification()
    t2 = bench_single_invariant()
    t3 = bench_find_py_files()
    total = t1 + t2 + t3
    print(f"\n  Total benchmark time: {total:.4f}s")
    print("=" * 60)
