"""
bench_dependency_graph.py

Benchmarks for Dependency Graph Validation (Feature 189).

Measures import extraction, cycle detection, and graph building performance.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.dependency_graph.validator import DependencyGraphValidator


def bench_full_validation():
    validator = DependencyGraphValidator()
    start = time.perf_counter()
    result = validator.validate_dependency_graph()
    elapsed = time.perf_counter() - start
    print(f"\n  Full dependency graph validation: {elapsed:.4f}s")
    print(f"  Total modules: {result['total_modules']}")
    print(f"  Cycles found: {result['total_cycles']}")
    print(f"  Circular score: {result['circular_score']:.1f}")
    return elapsed


def bench_build_graph():
    validator = DependencyGraphValidator()
    start = time.perf_counter()
    iterations = 10
    for i in range(iterations):
        validator._build_graph()
    elapsed = time.perf_counter() - start
    print(f"\n  Graph building ({iterations}x): {elapsed:.4f}s")
    print(f"  Per call: {elapsed / iterations * 1000:.4f}ms")
    return elapsed


def bench_extract_imports():
    validator = DependencyGraphValidator()
    test_content = "\n".join(
        f"import module_{i}\nfrom pkg_{i} import func_{i}" for i in range(100)
    )
    tmp_file = "/tmp/_bench_imports.py"
    with open(tmp_file, "w") as f:
        f.write(test_content)

    start = time.perf_counter()
    iterations = 100
    for i in range(iterations):
        validator._extract_imports(tmp_file)
    elapsed = time.perf_counter() - start
    print(f"\n  Import extraction ({iterations}x): {elapsed:.4f}s")
    print(f"  Per call: {elapsed / iterations * 1000:.4f}ms")
    os.remove(tmp_file)
    return elapsed


if __name__ == "__main__":
    print("=" * 60)
    print("  DEPENDENCY GRAPH VALIDATION BENCHMARKS")
    print("=" * 60)
    t1 = bench_full_validation()
    t2 = bench_build_graph()
    t3 = bench_extract_imports()
    total = t1 + t2 + t3
    print(f"\n  Total benchmark time: {total:.4f}s")
    print("=" * 60)
