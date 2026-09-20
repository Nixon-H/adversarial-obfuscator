"""
test_longitudinal_tracking.py

Tests for Longitudinal Security Tracking (Feature 196).

Test coverage:
- Positive tests verify baseline/current metrics, delta computation, trend analysis
- Negative tests verify no baseline, empty JSON, invalid JSON, missing directories
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.longitudinal_tracking.tracker import (
    BaselineMetrics,
    CurrentMetrics,
    DeltaMetrics,
    LongitudinalTracker,
    SnapshotEntry,
    TrendAnalysis,
)


def _make_file(tmpdir: str, name: str, content: str) -> str:
    path = os.path.join(tmpdir, name)
    with open(path, "w") as f:
        f.write(content)
    return path


class TestBaselineMetrics:
    """
    TestBaselineMetrics
    
    Positive test cases for baselinemetrics.
    """
    def test_dataclass(self):
        bm = BaselineMetrics(
            test_pass_rate=0.95, test_count=100, test_passed=95,
            test_failed=5, build_success=True, cli_flags=50,
            timestamp=1234567890.0,
        )
        assert bm.test_count == 100
        assert bm.test_pass_rate == 0.95


class TestCurrentMetrics:
    """
    TestCurrentMetrics
    
    Positive test cases for currentmetrics.
    """
    def test_dataclass(self):
        cm = CurrentMetrics(
            test_count=120, cli_flag_count=60,
            build_success=True, phase_count=30,
        )
        assert cm.test_count == 120
        assert cm.phase_count == 30


class TestDeltaMetrics:
    """
    TestDeltaMetrics
    
    Positive test cases for deltametrics.
    """
    def test_dataclass(self):
        dm = DeltaMetrics(
            test_count_delta=20, test_count_pct=20.0,
            flag_count_delta=10, flag_count_pct=20.0,
            build_success_change=False,
        )
        assert dm.test_count_delta == 20


class TestTrendAnalysis:
    """
    TestTrendAnalysis
    
    Positive test cases for trendanalysis.
    """
    def test_dataclass(self):
        ta = TrendAnalysis(
            test_trend="growing", flag_trend="stable",
            build_trend="stable",
            assessment="Test coverage is improving",
        )
        assert ta.test_trend == "growing"


class TestSnapshotEntry:
    """
    TestSnapshotEntry
    
    Positive test cases for snapshotentry.
    """
    def test_dataclass(self):
        se = SnapshotEntry(
            test_count=50, cli_flags=25,
            build_success=True, timestamp=1000.0,
        )
        assert se.test_count == 50


class TestLongitudinalTrackerPositive:
    """
    TestLongitudinalTrackerPositive
    
    Positive test cases for longitudinaltrackerpositive.
    """
    def test_track_with_baseline(self, tmpdir):
        baseline = {
            "test_pass_rate": 1.0, "test_count": 50,
            "test_passed": 50, "test_failed": 0,
            "build_success": True, "cli_flags": 30,
            "timestamp": 1000000.0,
        }
        _make_file(tmpdir, "baseline_report.json", json.dumps(baseline))
        tracker = LongitudinalTracker(config_dir=str(tmpdir))
        result = tracker.track_longitudinal_security()
        assert "baseline" in result
        assert "current" in result
        assert "deltas" in result
        assert "trend_analysis" in result
        assert "drift_detected" in result
        assert "trend_score" in result

    def test_delta_computation(self, tmpdir):
        baseline = {
            "test_pass_rate": 1.0, "test_count": 50,
            "test_passed": 50, "test_failed": 0,
            "build_success": True, "cli_flags": 30,
            "timestamp": 1000000.0,
        }
        _make_file(tmpdir, "baseline_report.json", json.dumps(baseline))
        tracker = LongitudinalTracker(config_dir=str(tmpdir))
        result = tracker.track_longitudinal_security()
        d = result["deltas"]
        assert isinstance(d["test_count_delta"], int)
        assert isinstance(d["flag_count_delta"], int)

    def test_trend_analysis_fields(self, tmpdir):
        baseline = {
            "test_pass_rate": 1.0, "test_count": 10,
            "test_passed": 10, "test_failed": 0,
            "build_success": True, "cli_flags": 20,
            "timestamp": 1000000.0,
        }
        _make_file(tmpdir, "baseline_report.json", json.dumps(baseline))
        tracker = LongitudinalTracker(config_dir=str(tmpdir))
        result = tracker.track_longitudinal_security()
        t = result["trend_analysis"]
        assert "test_trend" in t
        assert "flag_trend" in t
        assert "build_trend" in t
        assert "assessment" in t

    def test_trend_score_range(self, tmpdir):
        baseline = {
            "test_pass_rate": 1.0, "test_count": 10,
            "test_passed": 10, "test_failed": 0,
            "build_success": True, "cli_flags": 20,
            "timestamp": 1000000.0,
        }
        _make_file(tmpdir, "baseline_report.json", json.dumps(baseline))
        tracker = LongitudinalTracker(config_dir=str(tmpdir))
        result = tracker.track_longitudinal_security()
        assert 0.0 <= result["trend_score"] <= 200.0

    def test_historical_snapshots(self, tmpdir):
        baseline = {"test_pass_rate": 1.0, "test_count": 10,
                     "test_passed": 10, "test_failed": 0,
                     "build_success": True, "cli_flags": 20,
                     "timestamp": 1000000.0}
        _make_file(tmpdir, "baseline_report.json", json.dumps(baseline))
        hist_dir = os.path.join(tmpdir, "history")
        os.makedirs(hist_dir, exist_ok=True)
        for i in range(3):
            snap = {"test_count": 10 + i, "cli_flags": 20 + i,
                     "build_success": True, "timestamp": 2000000.0 + i}
            _make_file(hist_dir, f"snapshot_{i}.json", json.dumps(snap))
        tracker = LongitudinalTracker(config_dir=str(tmpdir))
        result = tracker.track_longitudinal_security()
        assert len(result["historical_snapshots"]) == 3

    def test_drift_detected_false(self, tmpdir):
        baseline = {"test_pass_rate": 1.0, "test_count": 100,
                     "test_passed": 100, "test_failed": 0,
                     "build_success": True, "cli_flags": 50,
                     "timestamp": 1000000.0}
        _make_file(tmpdir, "baseline_report.json", json.dumps(baseline))
        tracker = LongitudinalTracker(config_dir=str(tmpdir))
        result = tracker.track_longitudinal_security()
        assert isinstance(result["drift_detected"], bool)


class TestLongitudinalTrackerNegative:
    """
    TestLongitudinalTrackerNegative
    
    Negative test cases — exercises error handling and edge cases for longitudinaltrackernegative.
    """
    def test_no_baseline_file(self, tmpdir):
        tracker = LongitudinalTracker(config_dir=str(tmpdir))
        result = tracker.track_longitudinal_security()
        assert result["baseline"]["test_count"] == 0
        assert result["baseline"]["cli_flags"] == 0

    def test_baseline_empty_json(self, tmpdir):
        _make_file(tmpdir, "baseline_report.json", "{}")
        tracker = LongitudinalTracker(config_dir=str(tmpdir))
        result = tracker.track_longitudinal_security()
        assert result["baseline"]["test_count"] == 0

    def test_baseline_invalid_json(self, tmpdir):
        _make_file(tmpdir, "baseline_report.json", "not json")
        tracker = LongitudinalTracker(config_dir=str(tmpdir))
        result = tracker.track_longitudinal_security()
        assert result["baseline"]["test_count"] == 0

    def test_no_historical_dir(self, tmpdir):
        baseline = {"test_pass_rate": 1.0, "test_count": 10,
                     "test_passed": 10, "test_failed": 0,
                     "build_success": True, "cli_flags": 20,
                     "timestamp": 1000000.0}
        _make_file(tmpdir, "baseline_report.json", json.dumps(baseline))
        tracker = LongitudinalTracker(config_dir=str(tmpdir))
        result = tracker.track_longitudinal_security()
        assert result["historical_snapshots"] == []

    def test_no_build_py(self, tmpdir):
        baseline = {"test_pass_rate": 1.0, "test_count": 10,
                     "test_passed": 10, "test_failed": 0,
                     "build_success": True, "cli_flags": 20,
                     "timestamp": 1000000.0}
        _make_file(tmpdir, "baseline_report.json", json.dumps(baseline))
        tracker = LongitudinalTracker(config_dir=str(tmpdir))
        result = tracker.track_longitudinal_security()
        assert result["current"]["cli_flag_count"] == 0

    def test_no_tests_dir(self, tmpdir):
        baseline = {"test_pass_rate": 1.0, "test_count": 10,
                     "test_passed": 10, "test_failed": 0,
                     "build_success": True, "cli_flags": 20,
                     "timestamp": 1000000.0}
        _make_file(tmpdir, "baseline_report.json", json.dumps(baseline))
        tracker = LongitudinalTracker(config_dir=str(tmpdir))
        result = tracker.track_longitudinal_security()
        assert result["current"]["test_count"] == 0


class TestPhaseIntegration:
    """
    TestPhaseIntegration
    
    Positive test cases for phaseintegration.
    """
    def test_phase_module_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "phase_longitudinal_tracking",
            "scripts/phases/phase_longitudinal_tracking.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "phase_longitudinal_tracking")
        assert callable(mod.phase_longitudinal_tracking)
