"""
test_security_debt.py

Tests for Security Debt Index (Feature 170).

Test coverage:
- Positive tests verify debt item creation, tracking, querying, scoring, report generation
- Negative tests verify empty tracker, malformed data, edge case handling
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.security_debt import SecurityDebtItem, SecurityDebtTracker, SecurityDebtScorer, SecurityDebtReport
from scripts.security_debt.tracker import DebtCategory, DebtSeverity


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture
def tracker():
    return SecurityDebtTracker()


@pytest.fixture
def populated_tracker(tracker):
    tracker.record(
        category=DebtCategory.UNPROTECTED_FUNCTION,
        severity=DebtSeverity.CRITICAL,
        description="Function 'main' has no obfuscation protection",
        location="payload::main",
        feature="main_entry",
        impact_score=8.0,
    )
    tracker.record(
        category=DebtCategory.WEAK_PROTECTION,
        severity=DebtSeverity.HIGH,
        description="CFG flattening uses minimal depth",
        location="protection::cfg_flatten",
        feature="control_flow",
        impact_score=6.0,
    )
    return tracker


# =========================================================================
# Test SecurityDebtItem
# =========================================================================

class TestSecurityDebtItem:
    """
    TestSecurityDebtItem
    
    Positive test cases for securitydebtitem.
    """
    def test_default_timestamp(self):
        item = SecurityDebtItem(
            category=DebtCategory.UNPROTECTED_FUNCTION,
            severity=DebtSeverity.CRITICAL,
            description="test",
            location="test",
            feature="test",
        )
        assert item.timestamp_ns > 0

    def test_auto_hash(self):
        item = SecurityDebtItem(
            category=DebtCategory.UNPROTECTED_FUNCTION,
            severity=DebtSeverity.CRITICAL,
            description="desc",
            location="loc",
            feature="feat",
        )
        assert len(item.item_hash) == 16

    def test_deterministic_hash(self):
        item1 = SecurityDebtItem(
            category=DebtCategory.UNPROTECTED_FUNCTION,
            severity=DebtSeverity.CRITICAL,
            description="desc",
            location="loc",
            feature="feat",
        )
        item2 = SecurityDebtItem(
            category=DebtCategory.UNPROTECTED_FUNCTION,
            severity=DebtSeverity.CRITICAL,
            description="desc",
            location="loc",
            feature="feat",
        )
        assert item1.item_hash == item2.item_hash

    def test_to_dict(self):
        item = SecurityDebtItem(
            category=DebtCategory.WEAK_PROTECTION,
            severity=DebtSeverity.HIGH,
            description="weak desc",
            location="path::to",
            feature="feat",
            impact_score=5.0,
            effort_to_fix="medium",
        )
        d = item.to_dict()
        assert d["category"] == "weak_protection"
        assert d["severity"] == "high"
        assert d["description"] == "weak desc"
        assert d["location"] == "path::to"
        assert d["impact_score"] == 5.0
        assert d["effort_to_fix"] == "medium"

    def test_all_severities(self):
        for sev in DebtSeverity:
            item = SecurityDebtItem(
                category=DebtCategory.CONFIG_WEAKNESS,
                severity=sev,
                description="test",
                location="test",
                feature="test",
            )
            assert item.severity == sev

    def test_all_categories(self):
        for cat in DebtCategory:
            item = SecurityDebtItem(
                category=cat,
                severity=DebtSeverity.INFO,
                description="test",
                location="test",
                feature="test",
            )
            assert item.category == cat


# =========================================================================
# Test SecurityDebtTracker — Recording
# =========================================================================

class TestSecurityDebtTrackerRecord:
    """
    TestSecurityDebtTrackerRecord
    
    Positive test cases for securitydebttrackerrecord.
    """
    def test_record_item(self, tracker):
        item = SecurityDebtItem(
            category=DebtCategory.UNPROTECTED_FUNCTION,
            severity=DebtSeverity.CRITICAL,
            description="test",
            location="test",
            feature="test",
        )
        result = tracker.record_item(item)
        assert result is item
        assert tracker.count() == 1

    def test_record(self, tracker):
        item = tracker.record(
            category=DebtCategory.MISSING_COVERAGE,
            severity=DebtSeverity.MEDIUM,
            description="no coverage for X",
            location="tests::X",
            feature="test_feature",
            impact_score=4.0,
            effort_to_fix="high",
        )
        assert isinstance(item, SecurityDebtItem)
        assert tracker.count() == 1
        assert item.category == DebtCategory.MISSING_COVERAGE
        assert item.impact_score == 4.0

    def test_multiple_records(self, tracker):
        for i in range(5):
            tracker.record(
                category=DebtCategory.UNPROTECTED_FUNCTION,
                severity=DebtSeverity.LOW,
                description=f"item_{i}",
                location=f"loc_{i}",
                feature="test",
            )
        assert tracker.count() == 5


# =========================================================================
# Test SecurityDebtTracker — Querying
# =========================================================================

class TestSecurityDebtTrackerQuery:
    """
    TestSecurityDebtTrackerQuery
    
    Positive test cases for securitydebttrackerquery.
    """
    def test_get_items(self, populated_tracker):
        items = populated_tracker.get_items()
        assert len(items) == 2

    def test_get_items_by_severity(self, populated_tracker):
        critical = populated_tracker.get_items_by_severity(DebtSeverity.CRITICAL)
        high = populated_tracker.get_items_by_severity(DebtSeverity.HIGH)
        assert len(critical) == 1
        assert len(high) == 1
        assert populated_tracker.get_items_by_severity(DebtSeverity.INFO) == []

    def test_get_items_by_category(self, populated_tracker):
        unprotected = populated_tracker.get_items_by_category(DebtCategory.UNPROTECTED_FUNCTION)
        weak = populated_tracker.get_items_by_category(DebtCategory.WEAK_PROTECTION)
        assert len(unprotected) == 1
        assert len(weak) == 1

    def test_get_items_by_feature(self, populated_tracker):
        items = populated_tracker.get_items_by_feature("main_entry")
        assert len(items) == 1
        assert items[0].description == "Function 'main' has no obfuscation protection"

    def test_count_by_severity(self, populated_tracker):
        counts = populated_tracker.count_by_severity()
        assert counts.get("critical") == 1
        assert counts.get("high") == 1
        assert counts.get("info", 0) == 0

    def test_count_by_category(self, populated_tracker):
        counts = populated_tracker.count_by_category()
        assert counts.get("unprotected_function") == 1
        assert counts.get("weak_protection") == 1


# =========================================================================
# Test SecurityDebtTracker — Clear
# =========================================================================

class TestSecurityDebtTrackerClear:
    """
    TestSecurityDebtTrackerClear
    
    Negative test cases — exercises error handling and edge cases for securitydebttrackerclear.
    """
    def test_clear_resets(self, populated_tracker):
        assert populated_tracker.count() > 0
        populated_tracker.clear()
        assert populated_tracker.count() == 0

    def test_clear_then_record(self, tracker):
        tracker.record(
            category=DebtCategory.UNPROTECTED_FUNCTION,
            severity=DebtSeverity.CRITICAL,
            description="test",
            location="test",
            feature="test",
        )
        tracker.clear()
        assert tracker.count() == 0
        tracker.record(
            category=DebtCategory.UNPROTECTED_FUNCTION,
            severity=DebtSeverity.CRITICAL,
            description="test2",
            location="test2",
            feature="test2",
        )
        assert tracker.count() == 1

    def test_clear_empty_tracker(self, tracker):
        tracker.clear()
        assert tracker.count() == 0

    def test_to_dict_after_clear(self, populated_tracker):
        populated_tracker.clear()
        d = populated_tracker.to_dict()
        assert d["total_items"] == 0
        assert d["by_severity"] == {}


# =========================================================================
# Test SecurityDebtScorer — Score Computation
# =========================================================================

class TestSecurityDebtScorer:
    """
    TestSecurityDebtScorer
    
    Positive test cases for securitydebtscorer.
    """
    def test_scorer_empty_tracker(self, tracker):
        scorer = SecurityDebtScorer(tracker)
        assert scorer.compute_raw_debt() == 0.0
        assert scorer.compute_normalized_index(0.0) == 0.0

    def test_scorer_positive_raw(self, populated_tracker):
        scorer = SecurityDebtScorer(populated_tracker)
        raw = scorer.compute_raw_debt()
        assert raw > 0.0

    def test_scorer_normalized_index(self, populated_tracker):
        scorer = SecurityDebtScorer(populated_tracker)
        raw = scorer.compute_raw_debt()
        idx = scorer.compute_normalized_index(raw)
        assert 0.0 <= idx <= 100.0

    def test_category_breakdown(self, populated_tracker):
        scorer = SecurityDebtScorer(populated_tracker)
        breakdown = scorer.compute_category_breakdown()
        assert "unprotected_function" in breakdown
        assert "weak_protection" in breakdown
        total_pct = sum(breakdown.values())
        assert abs(total_pct - 100.0) < 0.01

    def test_top_items(self, populated_tracker):
        scorer = SecurityDebtScorer(populated_tracker)
        top = scorer.get_top_items(n=5)
        assert len(top) == 2
        assert top[0].severity == DebtSeverity.CRITICAL

    def test_top_items_empty(self, tracker):
        scorer = SecurityDebtScorer(tracker)
        assert scorer.get_top_items() == []

    def test_recommendations_empty(self, tracker):
        scorer = SecurityDebtScorer(tracker)
        assert scorer.generate_recommendations() == []

    def test_recommendations_populated(self, populated_tracker):
        scorer = SecurityDebtScorer(populated_tracker)
        recs = scorer.generate_recommendations()
        assert len(recs) > 0
        assert any("critical" in r for r in recs)

    def test_generate_report(self, populated_tracker):
        scorer = SecurityDebtScorer(populated_tracker)
        report = scorer.generate_report()
        assert isinstance(report, SecurityDebtReport)
        assert report.total_items == 2
        assert report.critical_count == 1
        assert report.high_count == 1
        assert report.overall_index > 0.0
        assert len(report.recommendations) > 0

    def test_report_to_dict(self, populated_tracker):
        scorer = SecurityDebtScorer(populated_tracker)
        report = scorer.generate_report()
        d = report.to_dict()
        assert "overall_index" in d
        assert "total_items" in d
        assert "category_breakdown" in d
        assert "recommendations" in d
        json.dumps(d)

    def test_report_to_json(self, populated_tracker):
        scorer = SecurityDebtScorer(populated_tracker)
        report = scorer.generate_report()
        s = report.to_json()
        assert isinstance(s, str)
        parsed = json.loads(s)
        assert parsed["total_items"] == 2


# =========================================================================
# Negative Tests
# =========================================================================

class TestEmptyTrackerNegative:
    """
    TestEmptyTrackerNegative
    
    Negative test cases — exercises error handling and edge cases for emptytrackernegative.
    """
    def test_empty_tracker_count(self, tracker):
        assert tracker.count() == 0

    def test_empty_tracker_get_items(self, tracker):
        assert tracker.get_items() == []

    def test_empty_tracker_by_severity(self, tracker):
        assert tracker.get_items_by_severity(DebtSeverity.CRITICAL) == []

    def test_empty_tracker_by_category(self, tracker):
        assert tracker.get_items_by_category(DebtCategory.UNPROTECTED_FUNCTION) == []

    def test_empty_tracker_by_feature(self, tracker):
        assert tracker.get_items_by_feature("nonexistent") == []

    def test_empty_tracker_count_by_severity(self, tracker):
        assert tracker.count_by_severity() == {}

    def test_empty_tracker_count_by_category(self, tracker):
        assert tracker.count_by_category() == {}

    def test_empty_scorer_raw(self, tracker):
        scorer = SecurityDebtScorer(tracker)
        assert scorer.compute_raw_debt() == 0.0

    def test_empty_scorer_index(self, tracker):
        scorer = SecurityDebtScorer(tracker)
        assert scorer.compute_normalized_index(0.0) == 0.0

    def test_empty_scorer_breakdown(self, tracker):
        scorer = SecurityDebtScorer(tracker)
        assert scorer.compute_category_breakdown() == {}

    def test_empty_scorer_report(self, tracker):
        scorer = SecurityDebtScorer(tracker)
        report = scorer.generate_report()
        assert report.overall_index == 0.0
        assert report.total_items == 0
        assert report.critical_count == 0
        assert report.recommendations == []

    def test_empty_tracker_to_dict(self, tracker):
        d = tracker.to_dict()
        assert d["total_items"] == 0
        assert d["by_severity"] == {}
        assert d["items"] == []


class TestMalformedData:
    """
    TestMalformedData
    
    Negative test cases — exercises error handling and edge cases for malformeddata.
    """
    def test_item_empty_description(self):
        item = SecurityDebtItem(
            category=DebtCategory.UNPROTECTED_FUNCTION,
            severity=DebtSeverity.INFO,
            description="",
            location="test",
            feature="test",
        )
        assert item.item_hash is not None
        assert len(item.item_hash) == 16

    def test_item_negative_impact(self):
        item = SecurityDebtItem(
            category=DebtCategory.UNPROTECTED_FUNCTION,
            severity=DebtSeverity.LOW,
            description="negative",
            location="test",
            feature="test",
            impact_score=-1.0,
        )
        assert item.impact_score == -1.0

    def test_item_max_impact(self):
        item = SecurityDebtItem(
            category=DebtCategory.UNPROTECTED_FUNCTION,
            severity=DebtSeverity.CRITICAL,
            description="max",
            location="test",
            feature="test",
            impact_score=1e6,
        )
        assert item.impact_score == 1e6

    def test_severity_enum_values(self):
        assert DebtSeverity.CRITICAL.value == "critical"
        assert DebtSeverity.HIGH.value == "high"
        assert DebtSeverity.MEDIUM.value == "medium"
        assert DebtSeverity.LOW.value == "low"
        assert DebtSeverity.INFO.value == "info"

    def test_category_enum_values(self):
        assert DebtCategory.UNPROTECTED_FUNCTION.value == "unprotected_function"
        assert DebtCategory.WEAK_PROTECTION.value == "weak_protection"
        assert DebtCategory.MISSING_COVERAGE.value == "missing_coverage"
        assert DebtCategory.OUTDATED_MECHANISM.value == "outdated_mechanism"
        assert DebtCategory.CONFIG_WEAKNESS.value == "config_weakness"
        assert DebtCategory.KNOWN_VULNERABILITY.value == "known_vulnerability"
        assert DebtCategory.EXPOSURE_RISK.value == "exposure_risk"
        assert DebtCategory.COMPLEXITY_RISK.value == "complexity_risk"


# =========================================================================
# Integration Tests
# =========================================================================

class TestIntegration:
    """
    TestIntegration
    
    Positive test cases for integration.
    """
    def test_full_workflow(self):
        tracker = SecurityDebtTracker()
        for i in range(3):
            tracker.record(
                category=DebtCategory.UNPROTECTED_FUNCTION,
                severity=DebtSeverity.CRITICAL if i == 0 else DebtSeverity.HIGH,
                description=f"item_{i}",
                location=f"loc_{i}",
                feature="test",
                impact_score=float(10 - i),
            )
        scorer = SecurityDebtScorer(tracker)
        report = scorer.generate_report()
        assert report.total_items == 3
        assert report.critical_count == 1
        assert report.high_count == 2
        assert 0.0 < report.overall_index <= 100.0
        assert len(report.category_breakdown) > 0
        assert len(report.recommendations) > 0

    def test_multiple_categories(self):
        tracker = SecurityDebtTracker()
        for cat in [DebtCategory.UNPROTECTED_FUNCTION, DebtCategory.WEAK_PROTECTION,
                     DebtCategory.MISSING_COVERAGE, DebtCategory.CONFIG_WEAKNESS]:
            tracker.record(
                category=cat,
                severity=DebtSeverity.MEDIUM,
                description=f"test_{cat.value}",
                location="test",
                feature="test",
            )
        assert tracker.count() == 4
        scorer = SecurityDebtScorer(tracker)
        report = scorer.generate_report()
        assert len(report.category_breakdown) == 4
        total_pct = sum(report.category_breakdown.values())
        assert abs(total_pct - 100.0) < 0.01

    def test_to_dict_roundtrip(self, populated_tracker):
        d = populated_tracker.to_dict()
        assert d["total_items"] == 2
        assert len(d["items"]) == 2
        for item_dict in d["items"]:
            assert "category" in item_dict
            assert "severity" in item_dict
            assert "description" in item_dict
            assert "item_hash" in item_dict
