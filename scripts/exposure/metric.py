"""
metric.py

Purpose:
Computes the plaintext exposure metric from an event stream. The
exposure score represents the percentage of execution time during
which sensitive data is exposed in plaintext memory.

Architectural Role:
Core metric computation for the exposure module. Reads events from
ExposureTracker, computes component-level and function-level scores,
and generates an ExposureReport with remediation recommendations.

Execution Context:
Instantiated with an ExposureTracker that has been populated by
instrumentors during pipeline execution. The generate_report() method
is called at build completion to produce the final exposure assessment.

Dependencies:
- tracker (ExposureEventType, ExposureTracker)
- Standard library (math, dataclasses, typing)

Security Relevance:
The exposure score directly quantifies one of the most critical attack
surfaces: memory disclosure. A score of 0 means data is never in
plaintext; 100 means data is always in plaintext. Security regression
gates use this score to enforce exposure budgets.

Maintenance Notes:
- The score formula (time_ratio * 0.5 + contiguity_ratio * 0.3 +
  appearance_frequency * 0.2) is heuristic; adjust weights based on
  empirical correlation with real-world attacks.
- The max_contiguous_exposure calculation assumes that PLAINTEXT_APPEARS
  and PLAINTEXT_DISAPPEARS events are properly matched. Unmatched
  events will cause incorrect contiguity measurements.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .tracker import ExposureEventType, ExposureTracker


@dataclass
class ExposureReport:
    """
    Complete plaintext exposure analysis report.

    Contains the overall exposure score (0-100), per-component and
    per-function breakdowns, total exposure/execution times, event
    count, and human-readable remediation recommendations.
    """

    overall_score: float
    component_scores: Dict[str, float]
    function_scores: Dict[str, float]
    total_exposure_ns: int
    total_execution_ns: int
    event_count: int
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize the report to a JSON-compatible dict."""
        return {
            "overall_score": self.overall_score,
            "component_scores": self.component_scores,
            "function_scores": self.function_scores,
            "total_exposure_ns": self.total_exposure_ns,
            "total_execution_ns": self.total_execution_ns,
            "event_count": self.event_count,
            "recommendations": self.recommendations,
        }


class PlaintextExposureMetric:
    """
    Computes the plaintext exposure score from an exposure event stream.

    The score factors in three dimensions:
    - Time ratio: how much of total execution time data is in plaintext
    - Contiguity: how long the longest continuous exposure window is
    - Frequency: how many separate exposure events occur
    """

    def __init__(self, tracker: ExposureTracker) -> None:
        """
        Initialize the metric with a reference to an ExposureTracker.
        The tracker must already contain the events to analyze.
        """
        self._tracker = tracker

    def compute_exposure_score(self, total_execution_ns: Optional[int] = None) -> float:
        """
        Compute the overall exposure score (0-100).

        Higher values indicate more exposure (worse security). The
        score combines time ratio (50% weight), contiguity ratio
        (30% weight), and appearance frequency (20% weight).
        """
        events = self._tracker.get_events()
        if not events:
            return 0.0  # No plaintext ever exposed -> zero exposure

        total_exposure = self._tracker.get_total_exposure_time()
        if total_execution_ns is None:
            if events:
                total_execution_ns = events[-1].timestamp_ns - events[0].timestamp_ns
            else:
                total_execution_ns = 1
        if total_execution_ns <= 0:
            total_execution_ns = 1

        time_ratio = total_exposure / total_execution_ns
        appearances = sum(
            1 for ev in events if ev.event_type == ExposureEventType.PLAINTEXT_APPEARS
        )
        max_contiguous = self._compute_max_contiguous_exposure()
        max_possible = total_execution_ns
        contiguity_ratio = max_contiguous / max_possible if max_possible > 0 else 0.0

        raw_score = (time_ratio * 0.5 + contiguity_ratio * 0.3 + min(appearances / 100.0, 1.0) * 0.2) * 100.0
        return max(0.0, min(100.0, raw_score))

    def _compute_max_contiguous_exposure(self) -> int:
        """Find the longest continuous plaintext exposure window in nanoseconds."""
        events = self._tracker.get_events()
        active_starts: Dict[str, int] = {}
        max_duration = 0
        for ev in events:
            if ev.event_type == ExposureEventType.PLAINTEXT_APPEARS:
                active_starts[ev.data_hash] = ev.timestamp_ns
            elif ev.event_type == ExposureEventType.PLAINTEXT_DISAPPEARS:
                start = active_starts.pop(ev.data_hash, None)
                if start is not None:
                    duration = ev.timestamp_ns - start
                    if duration > max_duration:
                        max_duration = duration
        return max_duration

    def compute_component_scores(self) -> Dict[str, float]:
        """Compute per-component exposure scores (e.g., 'microjit', 'fragmentation')."""
        events = self._tracker.get_events()
        if not events:
            return {}

        components = {ev.component for ev in events}
        scores: Dict[str, float] = {}
        for comp in components:
            comp_events = [ev for ev in events if ev.component == comp]
            if not comp_events:
                scores[comp] = 0.0
                continue
            comp_time_range = comp_events[-1].timestamp_ns - comp_events[0].timestamp_ns
            if comp_time_range <= 0:
                comp_time_range = 1
            appears = sum(
                1 for ev in comp_events
                if ev.event_type == ExposureEventType.PLAINTEXT_APPEARS
            )
            raw = (min(appears / 20.0, 1.0)) * 100.0
            scores[comp] = max(0.0, min(100.0, raw))
        return scores

    def compute_function_scores(self) -> Dict[str, float]:
        """Compute per-function exposure scores across all components."""
        events = self._tracker.get_events()
        if not events:
            return {}

        functions = {(ev.component, ev.function) for ev in events}
        scores: Dict[str, float] = {}
        for comp, func in functions:
            fn_events = [ev for ev in events if ev.component == comp and ev.function == func]
            if not fn_events:
                scores[f"{comp}:{func}"] = 0.0
                continue
            fn_time_range = fn_events[-1].timestamp_ns - fn_events[0].timestamp_ns
            if fn_time_range <= 0:
                fn_time_range = 1
            appears = sum(
                1 for ev in fn_events
                if ev.event_type == ExposureEventType.PLAINTEXT_APPEARS
            )
            raw = (min(appears / 10.0, 1.0)) * 100.0
            scores[f"{comp}:{func}"] = max(0.0, min(100.0, raw))
        return scores

    def generate_report(self, total_execution_ns: Optional[int] = None) -> ExposureReport:
        """
        Generate a complete ExposureReport with scores and recommendations.

        Recommendations are generated from the scores: high component
        scores suggest component-level issues, high function scores
        suggest specific function-level problems.
        """
        events = self._tracker.get_events()
        total_exposure = self._tracker.get_total_exposure_time()
        if total_execution_ns is None:
            if events:
                total_execution_ns = events[-1].timestamp_ns - events[0].timestamp_ns
            else:
                total_execution_ns = 1
        if total_execution_ns <= 0:
            total_execution_ns = 1

        overall = self.compute_exposure_score(total_execution_ns)
        component_scores = self.compute_component_scores()
        function_scores = self.compute_function_scores()

        recommendations: List[str] = []
        if overall > 50:
            recommendations.append("Plaintext exposure score is high (>50). Consider encrypting data earlier.")
        if total_exposure > total_execution_ns // 2:
            recommendations.append("Data is in plaintext for more than half the execution time.")
        for comp, score in component_scores.items():
            if score > 60:
                recommendations.append(f"Component '{comp}' has high exposure ({score:.1f}). Review encryption boundaries.")
        for fn_key, score in function_scores.items():
            if score > 70:
                recommendations.append(f"Function '{fn_key}' has critical exposure ({score:.1f}). Consider re-encrypting immediately after use.")

        return ExposureReport(
            overall_score=round(overall, 2),
            component_scores=component_scores,
            function_scores=function_scores,
            total_exposure_ns=total_exposure,
            total_execution_ns=total_execution_ns,
            event_count=len(events),
            recommendations=recommendations,
        )

    def to_dict(self) -> dict:
        return self.generate_report().to_dict()


def compute_exposure_score(tracker: ExposureTracker) -> float:
    metric = PlaintextExposureMetric(tracker)
    return metric.compute_exposure_score()
