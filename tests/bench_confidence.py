"""
bench_confidence.py

Benchmarks for Security Confidence Interval Computation (Feature 179).

Measures confidence interval computation across sample sizes.
"""

import math
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from scripts.confidence import compute_confidence_interval, SecurityConfidenceInterval
from scripts.confidence.interval import _t_critical, _normal_critical


def _bench(fn, *args, iterations=1000, label="bench"):
    start = time.perf_counter()
    for _ in range(iterations):
        fn(*args)
    elapsed = time.perf_counter() - start
    ops = iterations / elapsed
    print(f"  {label:45s} {elapsed * 1000:.2f}ms total  {ops:.0f} ops/s  "
          f"{elapsed / iterations * 1e6:.1f} us/op")
    return elapsed


def bench_small_sample():
    samples = [85, 87, 86, 88, 84]
    _bench(compute_confidence_interval, samples, iterations=5000, label="t-distribution n=5")
    return True


def bench_large_sample():
    samples = [float(x) for x in range(100)]
    _bench(compute_confidence_interval, samples, iterations=5000, label="normal n=100")
    return True


def bench_medium_sample():
    samples = [float(x) for x in range(30)]
    _bench(compute_confidence_interval, samples, iterations=5000, label="normal n=30")
    return True


def bench_t_critical():
    samples = [float(x) for x in range(10)]
    _bench(compute_confidence_interval, samples, iterations=2000, label="t-critical n=10")
    return True


def bench_very_large_sample():
    samples = [float(x) for x in range(10000)]
    _bench(compute_confidence_interval, samples, iterations=100, label="normal n=10000")
    return True


def bench_identical_values():
    samples = [80] * 50
    _bench(compute_confidence_interval, samples, iterations=5000, label="zero-variance n=50")
    return True


def bench_single_value():
    samples = [87]
    _bench(compute_confidence_interval, samples, iterations=10000, label="degenerate n=1")
    return True


def bench_many_intervals():
    datasets = [
        [float(x) for x in range(5)],
        [float(x) for x in range(30)],
        [float(x) for x in range(100)],
        [85, 87, 86, 88, 84],
        [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
    ]
    def run():
        for d in datasets:
            compute_confidence_interval(d)
    _bench(run, iterations=2000, label="5 intervals mixed sizes")
    return True


def bench_normal_critical():
    _bench(_normal_critical, 0.05, iterations=50000, label="normal_critical(0.05)")
    return True


def main():
    print()
    print("=" * 60)
    print("  CONFIDENCE INTERVAL BENCHMARKS (Feature 179)")
    print("=" * 60)

    results = []
    for name, fn in sorted(globals().items()):
        if name.startswith("bench_") and callable(fn):
            try:
                fn()
                results.append((name, "PASS"))
            except Exception as e:
                print(f"  {name:45s} FAIL: {e}")
                results.append((name, "FAIL"))

    print("-" * 60)
    passed = sum(1 for _, s in results if s == "PASS")
    total = len(results)
    print(f"  Results: {passed}/{total} benchmarks passed")
    print("=" * 60)
    print()

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
