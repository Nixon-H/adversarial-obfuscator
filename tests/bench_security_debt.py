"""
bench_security_debt.py

Benchmarks for Security Debt Index (Feature 170).

Measures debt tracking, scoring, and report generation performance.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.security_debt import SecurityDebtTracker, SecurityDebtScorer
from scripts.security_debt.tracker import DebtCategory, DebtSeverity


def _populate_tracker(tracker: SecurityDebtTracker, n: int = 100) -> None:
    cats = list(DebtCategory)
    sevs = list(DebtSeverity)
    for i in range(n):
        tracker.record(
            category=cats[i % len(cats)],
            severity=sevs[i % len(sevs)],
            description=f"benchmark debt item {i}",
            location=f"bench::{i}",
            feature=f"feature_{i % 10}",
            impact_score=float(i % 10),
            effort_to_fix="medium",
        )


def test_bench_tracker_record_overhead(benchmark):
    """Measure overhead of recording 200 items."""
    def record_200():
        t = SecurityDebtTracker()
        for i in range(200):
            t.record(
                category=DebtCategory.UNPROTECTED_FUNCTION,
                severity=DebtSeverity.MEDIUM,
                description=f"item_{i}",
                location=f"loc_{i}",
                feature="test",
                impact_score=5.0,
            )
        return t.count()

    result = benchmark(record_200)
    assert result == 200


def test_bench_tracker_query_by_severity(benchmark):
    """Measure query performance on a populated tracker."""
    t = SecurityDebtTracker()
    _populate_tracker(t, 500)

    def query():
        results = []
        for sev in DebtSeverity:
            results.extend(t.get_items_by_severity(sev))
        return len(results)

    result = benchmark(query)
    assert result == 500


def test_bench_tracker_query_by_category(benchmark):
    """Measure category query performance."""
    t = SecurityDebtTracker()
    _populate_tracker(t, 500)

    def query():
        results = []
        for cat in DebtCategory:
            results.extend(t.get_items_by_category(cat))
        return len(results)

    result = benchmark(query)
    assert result == 500


def test_bench_scorer_raw_debt(benchmark):
    """Measure raw debt computation performance."""
    t = SecurityDebtTracker()
    _populate_tracker(t, 1000)
    scorer = SecurityDebtScorer(t)

    result = benchmark(scorer.compute_raw_debt)
    assert result > 0.0


def test_bench_scorer_normalized_index(benchmark):
    """Measure normalized index computation."""
    t = SecurityDebtTracker()
    _populate_tracker(t, 1000)
    scorer = SecurityDebtScorer(t)
    raw = scorer.compute_raw_debt()

    result = benchmark(scorer.compute_normalized_index, raw)
    assert 0.0 <= result <= 100.0


def test_bench_scorer_category_breakdown(benchmark):
    """Measure category breakdown computation."""
    t = SecurityDebtTracker()
    _populate_tracker(t, 1000)
    scorer = SecurityDebtScorer(t)

    result = benchmark(scorer.compute_category_breakdown)
    total = sum(result.values())
    assert abs(total - 100.0) < 0.01


def test_bench_scorer_top_items(benchmark):
    """Measure top items extraction."""
    t = SecurityDebtTracker()
    _populate_tracker(t, 1000)
    scorer = SecurityDebtScorer(t)

    result = benchmark(scorer.get_top_items, 10)
    assert len(result) == 10


def test_bench_scorer_recommendations(benchmark):
    """Measure recommendation generation."""
    t = SecurityDebtTracker()
    _populate_tracker(t, 1000)
    scorer = SecurityDebtScorer(t)

    result = benchmark(scorer.generate_recommendations)
    assert len(result) > 0


def test_bench_generate_report(benchmark):
    """Measure full report generation."""
    t = SecurityDebtTracker()
    _populate_tracker(t, 1000)
    scorer = SecurityDebtScorer(t)

    report = benchmark(scorer.generate_report)
    assert report.total_items == 1000
    assert 0.0 <= report.overall_index <= 100.0


def test_bench_large_tracker(benchmark):
    """Measure full pipeline with 5000 items."""
    def pipeline():
        t = SecurityDebtTracker()
        _populate_tracker(t, 5000)
        scorer = SecurityDebtScorer(t)
        report = scorer.generate_report()
        return report

    report = benchmark(pipeline)
    assert report.total_items == 5000
    assert report.overall_index >= 0.0


def test_bench_tracker_to_dict(benchmark):
    """Measure serialization performance."""
    t = SecurityDebtTracker()
    _populate_tracker(t, 2000)

    result = benchmark(t.to_dict)
    assert result["total_items"] == 2000
