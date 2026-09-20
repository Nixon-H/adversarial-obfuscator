"""
bench_synthesis.py

Benchmarks for Protection Synthesis Engine (Feature 150).

Measures optimization algorithm performance (greedy, knapsack, genetic).
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.synthesis import (
    SynthesisEngine,
    ProtectionOptimizer,
    PROTECTION_COSTS,
)


def bench_greedy_optimization():
    engine = SynthesisEngine()
    engine.load_protection_costs()
    start = time.perf_counter()
    for _ in range(200):
        engine.solve_optimization(target_security=70.0, max_overhead=50.0, max_size=3.0)
    elapsed = time.perf_counter() - start
    print(f"Greedy optimization (200 runs): {elapsed:.4f}s ({elapsed/200*1e3:.2f}ms/run)")


def bench_knapsack_optimization():
    optimizer = ProtectionOptimizer(PROTECTION_COSTS)
    start = time.perf_counter()
    optimizer.optimize_with_knapsack({
        "target_security": 70.0,
        "max_overhead": 50.0,
        "max_size": 3.0,
    })
    elapsed = time.perf_counter() - start
    print(f"Knapsack optimization (1 run): {elapsed:.4f}s ({elapsed*1000:.2f}ms)")


def bench_score_computation():
    optimizer = ProtectionOptimizer(PROTECTION_COSTS)
    plan = optimizer.optimize_with_greedy({
        "target_security": 70.0,
        "max_overhead": 50.0,
        "max_size": 3.0,
    })
    start = time.perf_counter()
    for _ in range(2000):
        optimizer.score_plan(plan, {"target_security": 70.0, "max_overhead": 50.0, "max_size": 3.0})
    elapsed = time.perf_counter() - start
    print(f"Score computation (2000 runs): {elapsed:.4f}s ({elapsed/2000*1e6:.2f}µs/run)")


def bench_full_solve():
    engine = SynthesisEngine()
    engine.load_protection_costs()
    start = time.perf_counter()
    for _ in range(100):
        engine.solve_optimization(target_security=80.0, max_overhead=30.0, max_size=2.0)
        engine.solve_optimization(target_security=60.0, max_overhead=100.0, max_size=5.0)
        engine.solve_optimization(target_security=95.0, max_overhead=500.0, max_size=8.0)
    elapsed = time.perf_counter() - start
    print(f"Full solve (100x3 scenarios): {elapsed:.4f}s ({elapsed/(100*3)*1e3:.2f}ms/run)")


if __name__ == "__main__":
    bench_greedy_optimization()
    bench_knapsack_optimization()
    bench_score_computation()
    bench_full_solve()
