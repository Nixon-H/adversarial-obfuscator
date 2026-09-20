"""
bench_trust_boundary.py

Benchmarks for Trust Boundary Mapping (Feature 187).

Measures boundary mapping, enforcement status, and trust graph performance.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.trust_boundary.mapper import TrustBoundaryMapper


def bench_full_mapping():
    mapper = TrustBoundaryMapper()
    start = time.perf_counter()
    result = mapper.map_trust_boundaries()
    elapsed = time.perf_counter() - start
    total_entries = sum(len(v) for v in result["boundary_entries"].values())
    print(f"\n  Full trust boundary mapping: {elapsed:.4f}s")
    print(f"  Total domains: {len(result['boundary_entries'])}")
    print(f"  Total entries: {total_entries}")
    print(f"  Throughput: {total_entries / elapsed:.1f} entries/s")
    return elapsed


def bench_single_domain_mapping():
    mapper = TrustBoundaryMapper()
    start = time.perf_counter()
    iterations = 20
    domain_info = {
        "directories": ["scripts/trust_boundary"],
        "entry_patterns": ["map", "scan"],
    }
    for i in range(iterations):
        mapper.map_domain("test", domain_info)
    elapsed = time.perf_counter() - start
    print(f"\n  Single domain mapping ({iterations}x): {elapsed:.4f}s")
    print(f"  Per call: {elapsed / iterations * 1000:.4f}ms")
    return elapsed


def bench_detect_entry_points():
    mapper = TrustBoundaryMapper()
    functions = [("compile_fn", i, f"def compile_fn_{i}():\n    pass") for i in range(100)]
    domain_info = {"entry_patterns": ["compile", "build", "run"]}
    start = time.perf_counter()
    iterations = 100
    for i in range(iterations):
        mapper._detect_entry_points(functions, domain_info)
    elapsed = time.perf_counter() - start
    print(f"\n  Entry point detection ({iterations}x): {elapsed:.4f}s")
    print(f"  Per call: {elapsed / iterations * 1000:.4f}ms")
    return elapsed


if __name__ == "__main__":
    print("=" * 60)
    print("  TRUST BOUNDARY MAPPING BENCHMARKS")
    print("=" * 60)
    t1 = bench_full_mapping()
    t2 = bench_single_domain_mapping()
    t3 = bench_detect_entry_points()
    total = t1 + t2 + t3
    print(f"\n  Total benchmark time: {total:.4f}s")
    print("=" * 60)
