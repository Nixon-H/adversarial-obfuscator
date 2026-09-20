"""
bench_evidence_completeness.py

Benchmarks for Evidence Completeness Scoring (Feature 188).

Measures scoring, pattern detection, and directory scanning performance.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.evidence_completeness.scorer import EvidenceCompletenessScorer


def bench_full_scoring():
    scorer = EvidenceCompletenessScorer()
    start = time.perf_counter()
    result = scorer.compute_evidence_completeness()
    elapsed = time.perf_counter() - start
    print(f"\n  Full evidence completeness scoring: {elapsed:.4f}s")
    print(f"  Total claims: {result['total_claims']}")
    print(f"  Overall score: {result['overall_score']:.1f}")
    print(f"  Missing links: {len(result['missing_links'])}")
    return elapsed


def bench_scan_file():
    scorer = EvidenceCompletenessScorer()
    test_content = "\n".join(
        f"# This is a provably secure system {i}" for i in range(1000)
    )
    tmp_file = "/tmp/_bench_scan.py"
    with open(tmp_file, "w") as f:
        f.write(test_content)

    start = time.perf_counter()
    iterations = 50
    for i in range(iterations):
        scorer._scan_file_for_claims(tmp_file)
    elapsed = time.perf_counter() - start
    print(f"\n  File scanning ({iterations}x): {elapsed:.4f}s")
    print(f"  Per call: {elapsed / iterations * 1000:.4f}ms")
    os.remove(tmp_file)
    return elapsed


def bench_check_source():
    scorer = EvidenceCompletenessScorer()
    start = time.perf_counter()
    iterations = 30
    for i in range(iterations):
        scorer._check_source_exists("secure")
    elapsed = time.perf_counter() - start
    print(f"\n  Source existence check ({iterations}x): {elapsed:.4f}s")
    print(f"  Per call: {elapsed / iterations * 1000:.4f}ms")
    return elapsed


if __name__ == "__main__":
    print("=" * 60)
    print("  EVIDENCE COMPLETENESS BENCHMARKS")
    print("=" * 60)
    t1 = bench_full_scoring()
    t2 = bench_scan_file()
    t3 = bench_check_source()
    total = t1 + t2 + t3
    print(f"\n  Total benchmark time: {total:.4f}s")
    print("=" * 60)
