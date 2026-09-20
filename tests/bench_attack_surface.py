"""
bench_attack_surface.py

Benchmarks for Attack Surface Enumeration (Feature 190).

Measures enumeration speed across CLI, runtime, VM, proof, and filesystem vectors.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.attack_surface.enumerator import AttackSurfaceEnumerator


def bench_full_enumeration():
    enumerator = AttackSurfaceEnumerator()
    start = time.perf_counter()
    result = enumerator.enumerate_attack_surfaces()
    elapsed = time.perf_counter() - start
    print(f"\n  Full attack surface enumeration: {elapsed:.4f}s")
    print(f"  Total entry points: {result['total_entry_points']}")
    risk = result["risk_summary"]
    print(f"  CRITICAL: {risk.get('CRITICAL', 0)}, HIGH: {risk.get('HIGH', 0)}, "
          f"MEDIUM: {risk.get('MEDIUM', 0)}, LOW: {risk.get('LOW', 0)}")
    return elapsed


def bench_single_category():
    enumerator = AttackSurfaceEnumerator()
    categories = [
        enumerator._enumerate_cli_attack_surface,
        enumerator._enumerate_runtime_attack_surface,
        enumerator._enumerate_network_attack_surface,
    ]
    start = time.perf_counter()
    iterations = 20
    for i in range(iterations):
        for cat_fn in categories:
            cat_fn()
    elapsed = time.perf_counter() - start
    print(f"\n  Single category enumeration ({iterations * len(categories)}x): {elapsed:.4f}s")
    print(f"  Per call: {elapsed / (iterations * len(categories)) * 1000:.4f}ms")
    return elapsed


def bench_find_py_files():
    enumerator = AttackSurfaceEnumerator()
    start = time.perf_counter()
    iterations = 30
    for i in range(iterations):
        enumerator._find_py_files()
    elapsed = time.perf_counter() - start
    print(f"\n  Find Python files ({iterations}x): {elapsed:.4f}s")
    print(f"  Per call: {elapsed / iterations * 1000:.4f}ms")
    return elapsed


if __name__ == "__main__":
    print("=" * 60)
    print("  ATTACK SURFACE ENUMERATION BENCHMARKS")
    print("=" * 60)
    t1 = bench_full_enumeration()
    t2 = bench_single_category()
    t3 = bench_find_py_files()
    total = t1 + t2 + t3
    print(f"\n  Total benchmark time: {total:.4f}s")
    print("=" * 60)
