"""
bench_proof_coverage.py

Benchmarks for Proof Coverage Analysis.

Measures scanning, aggregation, and report generation performance.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.proof_coverage.scanner import ProofCoverageScanner
from scripts.proof_coverage.aggregator import (
    aggregate_proof_coverage,
    compute_overall_score,
    generate_recommendations,
)
from scripts.proof_coverage.coverage import ProofCoverage


def bench_full_scan():
    scanner = ProofCoverageScanner()
    start = time.perf_counter()
    for _ in range(10):
        scanner.scan_all()
    elapsed = (time.perf_counter() - start) / 10
    print(f"  ProofCoverageScanner.scan_all: {elapsed * 1000:.2f}ms avg ({10} runs)")
    return elapsed


def bench_aggregation():
    scanner = ProofCoverageScanner()
    results = scanner.scan_all()
    start = time.perf_counter()
    for _ in range(100):
        aggregated = aggregate_proof_coverage(results)
        compute_overall_score(aggregated)
        generate_recommendations(aggregated)
    elapsed = (time.perf_counter() - start) / 100
    print(f"  aggregate+score+recommend:     {elapsed * 1000:.3f}ms avg ({100} runs)")
    return elapsed


def bench_report_generation():
    scores = {
        s: ProofCoverage(
            stage=s,
            has_proof=True,
            proof_type="z3",
            functions_covered=i + 1,
            functions_total=i + 2,
            proof_validated=True,
        )
        for i, s in enumerate(["ast_ir", "ir_llvm", "llvm_vm", "watermark", "fragmentation", "mutation", "jit"])
    }
    start = time.perf_counter()
    for _ in range(200):
        compute_overall_score(scores)
        generate_recommendations(scores)
    elapsed = (time.perf_counter() - start) / 200
    print(f"  report generation (dict build): {elapsed * 1000:.3f}ms avg ({200} runs)")
    return elapsed


if __name__ == "__main__":
    print("Proof Coverage Benchmarks")
    print("=" * 50)
    t1 = bench_full_scan()
    t2 = bench_aggregation()
    t3 = bench_report_generation()
    print("=" * 50)
    print(f"  Total benchmark time: {(t1 + t2 + t3) * 1000:.2f}ms")
