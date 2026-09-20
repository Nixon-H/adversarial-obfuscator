"""
bench_adversarial_bench.py

Benchmarks for Adversarial Benchmark Generator (Feature 175).

Measures generation speed for adversarial tests across all target systems.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.adversarial_bench import (
    AdversarialBenchGenerator,
    AdversarialTestSuite,
)


def bench_generate_all_20():
    gen = AdversarialBenchGenerator(seed=42)
    start = time.perf_counter()
    for _ in range(100):
        gen.generate_all(count=20)
    elapsed = time.perf_counter() - start
    print(f"Generate all (100x20 tests): {elapsed:.4f}s ({elapsed/100*1e3:.2f}ms/run)")


def bench_generate_all_100():
    gen = AdversarialBenchGenerator(seed=42)
    start = time.perf_counter()
    for _ in range(50):
        gen.generate_all(count=100)
    elapsed = time.perf_counter() - start
    print(f"Generate all (50x100 tests): {elapsed:.4f}s ({elapsed/50*1e3:.2f}ms/run)")


def bench_suite_run_all():
    gen = AdversarialBenchGenerator(seed=42)
    suite = AdversarialTestSuite()
    suite.load_tests(gen, count=20)
    start = time.perf_counter()
    for _ in range(50):
        suite.run_all()
    elapsed = time.perf_counter() - start
    print(f"Suite run all (50x20 tests): {elapsed:.4f}s ({elapsed/50*1e3:.2f}ms/run)")


def bench_report_generation():
    gen = AdversarialBenchGenerator(seed=42)
    suite = AdversarialTestSuite()
    suite.load_tests(gen, count=20)
    suite.run_all()
    start = time.perf_counter()
    for _ in range(200):
        suite.generate_report()
    elapsed = time.perf_counter() - start
    print(f"Report generation (200 runs): {elapsed:.4f}s ({elapsed/200*1e6:.2f}µs/run)")


def bench_vulnerability_detection():
    gen = AdversarialBenchGenerator(seed=42)
    suite = AdversarialTestSuite()
    suite.load_tests(gen, count=20)
    suite.run_all()
    start = time.perf_counter()
    for _ in range(200):
        suite.get_vulnerabilities()
    elapsed = time.perf_counter() - start
    print(f"Vulnerability detection (200 runs): {elapsed:.4f}s ({elapsed/200*1e6:.2f}µs/run)")


def bench_full_suite():
    gen = AdversarialBenchGenerator(seed=42)
    suite = AdversarialTestSuite()

    start = time.perf_counter()
    for _ in range(30):
        suite.load_tests(gen, count=20)
        suite.run_all()
        suite.generate_report()
        suite.get_vulnerabilities()
    elapsed = time.perf_counter() - start
    print(f"Full suite cycle (30x): {elapsed:.4f}s ({elapsed/30*1e3:.2f}ms/cycle)")


if __name__ == "__main__":
    bench_generate_all_20()
    bench_generate_all_100()
    bench_suite_run_all()
    bench_report_generation()
    bench_vulnerability_detection()
    bench_full_suite()
