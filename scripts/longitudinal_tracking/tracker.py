"""
longitudinal_tracking/tracker.py

Purpose:
Tracks security metrics over time by comparing current state against a
baseline report and historical snapshots. Computes deltas, trend analysis,
drift detection, and a trend score.

Architectural Role:
Called by the meta-assurance pipeline to produce a longitudinal security
tracking report (F195). Consumes baseline_report.json and historical
snapshots from config/history/.

Security Relevance:
Security posture is not static — it degrades over time without active
maintenance. Longitudinal tracking detects negative trends (declining
test coverage, failing builds, reducing CLI flags) before they become
critical.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)


@dataclass
class BaselineMetrics:
    """
    BaselineMetrics

    Purpose:
    Stores the initial baseline measurements for longitudinal comparison.
    """
    test_pass_rate: float
    test_count: int
    test_passed: int
    test_failed: int
    build_success: bool
    cli_flags: int
    timestamp: float | None = None


@dataclass
class CurrentMetrics:
    """
    CurrentMetrics

    Purpose:
    Stores the current state measurements for comparison against the baseline.
    """
    test_count: int
    cli_flag_count: int
    build_success: bool
    phase_count: int


@dataclass
class DeltaMetrics:
    """
    DeltaMetrics

    Purpose:
    Stores the computed differences between current and baseline metrics.
    """
    test_count_delta: int
    test_count_pct: float
    flag_count_delta: int
    flag_count_pct: float
    build_success_change: bool


@dataclass
class TrendAnalysis:
    """
    TrendAnalysis

    Purpose:
    Stores the qualitative trend assessment for each metric dimension.
    """
    test_trend: str
    flag_trend: str
    build_trend: str
    assessment: str


@dataclass
class SnapshotEntry:
    """
    SnapshotEntry

    Purpose:
    Represents a single historical data point from config/history/.
    """
    test_count: int
    cli_flags: int
    build_success: bool
    timestamp: float


class LongitudinalTracker:
    """
    LongitudinalTracker

    Purpose:
    Tracks security-relevant metrics over time by comparing current
    measurements against a stored baseline and historical snapshots.

    Lifecycle:
    Created on demand; track_longitudinal_security() drives the analysis.
    """
    def __init__(self, config_dir: str | None = None):
        self.config_dir = config_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config"
        )

    def track_longitudinal_security(self) -> dict[str, Any]:
        """
        track_longitudinal_security

        Purpose:
        Main entry point — loads baseline, loads historical snapshots,
        computes current metrics, calculates deltas and trends, detects
        drift, and produces a trend score.

        Inputs:
        None

        Outputs:
        Dict with baseline, current, deltas, trend_analysis, drift_detected,
        trend_score, historical_snapshots.
        """
        baseline = self._load_baseline()
        historical = self._load_historical_snapshots()
        current = self._compute_current_metrics()
        deltas = self._compute_deltas(baseline, current)
        trends = self._compute_trend_analysis(current, deltas, historical)
        drift = self._detect_drift(baseline, current, deltas)
        trend_score = self._compute_trend_score(current, deltas, drift)

        return {
            "baseline": {
                "test_pass_rate": baseline.test_pass_rate,
                "test_count": baseline.test_count,
                "test_passed": baseline.test_passed,
                "test_failed": baseline.test_failed,
                "build_success": baseline.build_success,
                "cli_flags": baseline.cli_flags,
                "timestamp": baseline.timestamp,
            },
            "current": {
                "test_count": current.test_count,
                "cli_flag_count": current.cli_flag_count,
                "build_success": current.build_success,
                "phase_count": current.phase_count,
            },
            "deltas": {
                "test_count_delta": deltas.test_count_delta,
                "test_count_pct_change": round(deltas.test_count_pct, 2),
                "flag_count_delta": deltas.flag_count_delta,
                "flag_count_pct_change": round(deltas.flag_count_pct, 2),
                "build_success_change": deltas.build_success_change,
            },
            "trend_analysis": {
                "test_trend": trends.test_trend,
                "flag_trend": trends.flag_trend,
                "build_trend": trends.build_trend,
                "assessment": trends.assessment,
            },
            "drift_detected": drift,
            "trend_score": round(trend_score, 2),
            "historical_snapshots": [
                {
                    "test_count": s.test_count,
                    "cli_flags": s.cli_flags,
                    "build_success": s.build_success,
                    "timestamp": s.timestamp,
                }
                for s in historical
            ],
        }

    def _load_baseline(self) -> BaselineMetrics:
        """
        _load_baseline

        Purpose:
        Loads the baseline report from config/baseline_report.json.

        Inputs:
        None

        Outputs:
        BaselineMetrics dataclass (defaults on failure).
        """
        baseline_path = os.path.join(self.config_dir, "baseline_report.json")
        try:
            with open(baseline_path, encoding="utf-8") as f:
                data = json.load(f)
            return BaselineMetrics(
                test_pass_rate=data.get("test_pass_rate", 1.0),
                test_count=data.get("test_count", 0),
                test_passed=data.get("test_passed", 0),
                test_failed=data.get("test_failed", 0),
                build_success=data.get("build_success", True),
                cli_flags=data.get("cli_flags", 0),
                timestamp=data.get("timestamp"),
            )
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return BaselineMetrics(
                test_pass_rate=1.0, test_count=0, test_passed=0,
                test_failed=0, build_success=True, cli_flags=0,
            )

    def _load_historical_snapshots(self) -> list[SnapshotEntry]:
        """
        _load_historical_snapshots

        Purpose:
        Loads historical snapshot files from config/history/ directory.

        Inputs:
        None

        Outputs:
        List of SnapshotEntry sorted by filename.
        """
        snapshots: list[SnapshotEntry] = []
        hist_dir = os.path.join(self.config_dir, "history")
        if not os.path.isdir(hist_dir):
            return snapshots
        for fname in sorted(os.listdir(hist_dir)):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(hist_dir, fname), encoding="utf-8") as f:
                    data = json.load(f)
                snapshots.append(SnapshotEntry(
                    test_count=data.get("test_count", 0),
                    cli_flags=data.get("cli_flags", 0),
                    build_success=data.get("build_success", True),
                    timestamp=data.get("timestamp", 0.0),
                ))
            except (json.JSONDecodeError, OSError):
                continue
        return snapshots

    def _compute_current_metrics(self) -> CurrentMetrics:
        """
        _compute_current_metrics

        Purpose:
        Computes current test count, CLI flag count, build success, and
        phase count from the filesystem.

        Inputs:
        None

        Outputs:
        CurrentMetrics dataclass.
        """
        scripts_dir = os.path.dirname(self.config_dir)
        test_count = self._count_tests(scripts_dir)

        cli_flag_count = self._count_cli_flags(scripts_dir)

        build_success = self._check_build_success(scripts_dir)

        phase_count = self._count_phases(scripts_dir)

        return CurrentMetrics(
            test_count=test_count,
            cli_flag_count=cli_flag_count,
            build_success=build_success,
            phase_count=phase_count,
        )

    def _count_tests(self, scripts_dir: str) -> int:
        """
        _count_tests

        Purpose:
        Counts test_*.py files in the tests/ directory.

        Inputs:
        scripts_dir — path to scripts/ directory

        Outputs:
        Integer count.
        """
        tests_dir = os.path.join(os.path.dirname(scripts_dir), "tests")
        if not os.path.isdir(tests_dir):
            return 0
        count = 0
        for root, _dirs, files in os.walk(tests_dir):
            for fname in files:
                if fname.startswith("test_") and fname.endswith(".py"):
                    count += 1
        return count

    def _count_cli_flags(self, scripts_dir: str) -> int:
        """
        _count_cli_flags

        Purpose:
        Counts parser.add_argument() calls in build.py as a proxy for
        CLI feature flags.

        Inputs:
        scripts_dir — path to scripts/ directory

        Outputs:
        Integer count.
        """
        build_path = os.path.join(scripts_dir, "build.py")
        if not os.path.exists(build_path):
            return 0
        try:
            with open(build_path, encoding="utf-8") as f:
                content = f.read()
            count = content.count("parser.add_argument(")
            count += content.count("parser.add_argument (")
            return count
        except OSError:
            return 0

    def _check_build_success(self, scripts_dir: str) -> bool:
        """
        _check_build_success

        Purpose:
        Checks build.log for error/failure indicators to determine build status.

        Inputs:
        scripts_dir — path to scripts/ directory

        Outputs:
        True if the build appears successful.
        """
        build_log = os.path.join(os.path.dirname(scripts_dir), "build.log")
        if not os.path.exists(build_log):
            return True
        try:
            with open(build_log, encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "ERROR" in content or "FAILED" in content or "Traceback" in content:
                return False
            if "Build complete" in content or "BUILD SUCCESS" in content:
                return True
            return True
        except OSError:
            return True

    def _count_phases(self, scripts_dir: str) -> int:
        """
        _count_phases

        Purpose:
        Counts phase_*.py files in the scripts/phases/ directory.

        Inputs:
        scripts_dir — path to scripts/ directory

        Outputs:
        Integer count.
        """
        phases_dir = os.path.join(scripts_dir, "phases")
        if not os.path.isdir(phases_dir):
            return 0
        return sum(
            1 for f in os.listdir(phases_dir)
            if f.startswith("phase_") and f.endswith(".py")
        )

    def _compute_deltas(
        self, baseline: BaselineMetrics, current: CurrentMetrics
    ) -> DeltaMetrics:
        """
        _compute_deltas

        Purpose:
        Computes the difference between current and baseline metrics.

        Inputs:
        baseline — BaselineMetrics from baseline_report.json
        current — CurrentMetrics from filesystem scan

        Outputs:
        DeltaMetrics with absolute and percentage changes.
        """

        test_delta = current.test_count - baseline.test_count
        test_pct = round(
            (test_delta / max(baseline.test_count, 1)) * 100, 2
        ) if baseline.test_count > 0 else 0.0

        flag_delta = current.cli_flag_count - baseline.cli_flags
        flag_pct = round(
            (flag_delta / max(baseline.cli_flags, 1)) * 100, 2
        ) if baseline.cli_flags > 0 else 0.0

        build_change = current.build_success != baseline.build_success

        return DeltaMetrics(
            test_count_delta=test_delta,
            test_count_pct=test_pct,
            flag_count_delta=flag_delta,
            flag_count_pct=flag_pct,
            build_success_change=build_change,
        )

    def _compute_trend_analysis(
        self,
        current: CurrentMetrics,
        deltas: DeltaMetrics,
        historical: list[SnapshotEntry],
    ) -> TrendAnalysis:
        """
        _compute_trend_analysis

        Purpose:
        Analyzes deltas and historical data to assign qualitative trends
        (growing/declining/stable) to each metric dimension.

        Inputs:
        current — CurrentMetrics
        deltas — DeltaMetrics
        historical — list of historical SnapshotEntry

        Outputs:
        TrendAnalysis with trend strings and assessment text.
        """

        test_trend = "stable"
        if deltas.test_count_delta > 0:
            test_trend = "growing"
        elif deltas.test_count_delta < 0:
            test_trend = "declining"

        flag_trend = "stable"
        if deltas.flag_count_delta > 0:
            flag_trend = "growing"
        elif deltas.flag_count_delta < 0:
            flag_trend = "declining"

        build_trend = "stable"
        if historical:
            previous_success = [s.build_success for s in historical]
            recent_failures = previous_success.count(False)
            if recent_failures > len(previous_success) / 2:
                build_trend = "failing"
            elif not current.build_success:
                build_trend = "currently_failing"
        elif not current.build_success:
            build_trend = "currently_failing"

        assessments = []
        if test_trend == "growing":
            assessments.append("Test coverage is improving")
        elif test_trend == "declining":
            assessments.append("Test coverage is declining")

        if flag_trend == "growing":
            assessments.append("Security feature flags are increasing")
        elif flag_trend == "declining":
            assessments.append("Security feature flags are decreasing")

        if build_trend == "failing":
            assessments.append("Build stability is degrading")
        elif build_trend == "currently_failing":
            assessments.append("Current build has errors")

        if not assessments:
            assessments.append("All security metrics are stable")

        assessment = "; ".join(assessments)

        return TrendAnalysis(
            test_trend=test_trend,
            flag_trend=flag_trend,
            build_trend=build_trend,
            assessment=assessment,
        )

    def _detect_drift(
        self,
        baseline: BaselineMetrics,
        current: CurrentMetrics,
        deltas: DeltaMetrics,
    ) -> bool:
        """
        _detect_drift

        Purpose:
        Detects significant drift from baseline: build failures, large
        changes in test count (>50%), or large changes in flag count (>50%).

        Inputs:
        baseline — BaselineMetrics
        current — CurrentMetrics
        deltas — DeltaMetrics

        Outputs:
        True if drift is detected.
        """

        if not baseline.test_count and not baseline.cli_flags:
            return False
        if deltas.build_success_change and not current.build_success:
            return True
        if abs(deltas.test_count_pct) > 50:
            return True
        if abs(deltas.flag_count_pct) > 50:
            return True
        return False

    def _compute_trend_score(
        self,
        current: CurrentMetrics,
        deltas: DeltaMetrics,
        drift: bool,
    ) -> float:
        """
        _compute_trend_score

        Purpose:
        Computes a 0-200 trend score based on build success, test count
        changes, flag count changes, drift presence, and phase count.

        Inputs:
        current — CurrentMetrics
        deltas — DeltaMetrics
        drift — whether drift was detected

        Outputs:
        Float between 0.0 and 200.0.
        """

        score = 100.0

        if current.build_success:
            score += 10
        else:
            score -= 30

        if deltas.test_count_delta > 0:
            score += min(deltas.test_count_delta * 2, 20)
        elif deltas.test_count_delta < 0:
            score -= min(abs(deltas.test_count_delta) * 5, 30)

        if deltas.flag_count_delta > 0:
            score += min(deltas.flag_count_delta, 10)
        elif deltas.flag_count_delta < 0:
            score -= min(abs(deltas.flag_count_delta) * 2, 20)

        if drift:
            score -= 20

        if current.phase_count > 0:
            score += min(current.phase_count * 0.5, 15)

        return max(0.0, min(200.0, score))
