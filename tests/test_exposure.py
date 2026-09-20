"""
test_exposure.py

Tests for Plaintext Exposure Metric (Feature 151).

Test Categories:
- Positive tests verify exposure event recording, duration tracking,
  score computation, report generation, and instrumentor behavior.
- Negative tests verify empty trackers, cleared states, and malformed data handling.

Coverage:
- ExposureTracker: appearance/disappearance/encryption/decryption recording, duration
- ExposureMetric: score computation from events, component/function-level scores
- ExposureReport: generation, serialization, recommendations
- Instrumentors: MicroJIT, fragmentation, FHE, history-bound
- ExposureSimulator: plaintext flow simulation
"""

import hashlib
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.exposure.tracker import ExposureEvent, ExposureEventType, ExposureTracker
from scripts.exposure.metric import PlaintextExposureMetric, ExposureReport
from scripts.exposure.instrumentors import (
    MicroJITExposureInstrumentor,
    FragmentationExposureInstrumentor,
    HistoryBoundExposureInstrumentor,
    FHEExposureInstrumentor,
)
from scripts.exposure.simulator import ExposureSimulator


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture
def tracker():
    return ExposureTracker()


@pytest.fixture
def populated_tracker(tracker):
    tracker.record_appearance("test_component", "test_func", b"hello")
    time.sleep(0.00001)
    tracker.record_disappearance("test_component", "test_func", b"hello")
    return tracker


# =========================================================================
# Test ExposureTracker — Recording
# =========================================================================

class TestExposureTrackerRecord:
    """
    TestExposureTrackerRecord

    Positive test cases for recording exposure events: appearance,
    disappearance, encryption, decryption, and string data handling.
    """
    def test_record_appearance(self, tracker):
        tracker.record_appearance("microjit", "encrypt", b"plaintext_data")
        events = tracker.get_events()
        assert len(events) == 1
        assert events[0].component == "microjit"
        assert events[0].function == "encrypt"
        assert events[0].event_type == ExposureEventType.PLAINTEXT_APPEARS
        assert events[0].timestamp_ns > 0
        expected_hash = hashlib.sha256(b"plaintext_data").hexdigest()
        assert events[0].data_hash == expected_hash

    def test_record_disappearance(self, tracker):
        tracker.record_disappearance("frag", "frag_0", b"sensitive")
        events = tracker.get_events()
        assert len(events) == 1
        assert events[0].event_type == ExposureEventType.PLAINTEXT_DISAPPEARS

    def test_record_encryption(self, tracker):
        tracker.record_encryption("fhe", "add")
        events = tracker.get_events()
        assert len(events) == 1
        assert events[0].event_type == ExposureEventType.ENCRYPTED

    def test_record_decryption(self, tracker):
        tracker.record_decryption("fhe", "decrypt")
        events = tracker.get_events()
        assert len(events) == 1
        assert events[0].event_type == ExposureEventType.DECRYPTED

    def test_record_string_data(self, tracker):
        tracker.record_appearance("comp", "fn", "string_data")
        events = tracker.get_events()
        expected_hash = hashlib.sha256(b"string_data").hexdigest()
        assert events[0].data_hash == expected_hash

    def test_multiple_events(self, tracker):
        for i in range(5):
            tracker.record_appearance("comp", "fn", f"data_{i}".encode())
        assert len(tracker.get_events()) == 5


# =========================================================================
# Test ExposureTracker — Duration
# =========================================================================

class TestExposureTrackerDuration:
    """
    TestExposureTrackerDuration

    Positive test cases for computing exposure durations from
    appearance/disappearance event pairs, including multiple events.
    """
    def test_compute_duration(self, populated_tracker):
        duration = populated_tracker.get_exposure_duration("test_component", "test_func")
        assert duration > 0

    def test_no_matching_events(self, tracker):
        duration = tracker.get_exposure_duration("nonexistent", "nonexistent")
        assert duration == 0

    def test_total_exposure_time(self, populated_tracker):
        total = populated_tracker.get_total_exposure_time()
        assert total > 0

    def test_multiple_appear_disappear(self, tracker):
        tracker.record_appearance("c", "f", b"data1")
        t1 = time.monotonic_ns()
        tracker._events[-1].timestamp_ns = t1
        tracker.record_disappearance("c", "f", b"data1")
        t2 = t1 + 1000
        tracker._events[-1].timestamp_ns = t2
        tracker.record_appearance("c", "f", b"data2")
        t3 = t2 + 500
        tracker._events[-1].timestamp_ns = t3
        tracker.record_disappearance("c", "f", b"data2")
        t4 = t3 + 2000
        tracker._events[-1].timestamp_ns = t4
        duration = tracker.get_exposure_duration("c", "f")
        assert duration == 3000

    def test_total_with_multiple_components(self, tracker):
        tracker.record_appearance("c1", "f1", b"d1")
        t1 = time.monotonic_ns()
        tracker._events[-1].timestamp_ns = t1
        tracker.record_disappearance("c1", "f1", b"d1")
        t2 = t1 + 5000
        tracker._events[-1].timestamp_ns = t2
        tracker.record_appearance("c2", "f2", b"d2")
        t3 = t2 + 100
        tracker._events[-1].timestamp_ns = t3
        tracker.record_disappearance("c2", "f2", b"d2")
        t4 = t3 + 3000
        tracker._events[-1].timestamp_ns = t4
        assert tracker.get_total_exposure_time() == 8000


# =========================================================================
# Test ExposureTracker — Accessors and Serialization
# =========================================================================

class TestExposureTrackerAccessors:
    """
    TestExposureTrackerAccessors

    Positive test cases for tracker accessors: event list immutability,
    dictionary serialization, and event-to-dict conversion.
    """
    def test_get_events_returns_copy(self, tracker):
        tracker.record_appearance("c", "f", b"d")
        events = tracker.get_events()
        events.append(ExposureEvent("x", "y", ExposureEventType.ENCRYPTED, 0, ""))
        assert len(tracker.get_events()) == 1

    def test_to_dict(self, populated_tracker):
        d = populated_tracker.to_dict()
        assert "events" in d
        assert "total_exposure_ns" in d
        assert "event_count" in d
        assert d["event_count"] == 2

    def test_event_to_dict(self):
        ev = ExposureEvent("c", "f", ExposureEventType.ENCRYPTED, 12345, "abc123")
        d = ev.to_dict()
        assert d["component"] == "c"
        assert d["function"] == "f"
        assert d["event_type"] == "encrypted"
        assert d["timestamp_ns"] == 12345
        assert d["data_hash"] == "abc123"


# =========================================================================
# Test ExposureMetric — Score Computation
# =========================================================================

class TestExposureMetricScore:
    """
    TestExposureMetricScore

    Positive and edge-case tests for PlaintextExposureMetric score
    computation with zero events, single events, and high exposure.
    """
    def test_score_zero_no_events(self, tracker):
        metric = PlaintextExposureMetric(tracker)
        score = metric.compute_exposure_score()
        assert score == 0.0

    def test_score_positive(self, populated_tracker):
        metric = PlaintextExposureMetric(populated_tracker)
        score = metric.compute_exposure_score()
        assert 0.0 <= score <= 100.0

    def test_high_exposure_score(self, tracker):
        now = time.monotonic_ns()
        for i in range(10):
            ts = now + i * 1000
            tracker._events.append(ExposureEvent(
                "c", "f", ExposureEventType.PLAINTEXT_APPEARS, ts, f"hash{i}"
            ))
            ts = now + i * 1000 + 900
            tracker._events.append(ExposureEvent(
                "c", "f", ExposureEventType.PLAINTEXT_DISAPPEARS, ts, f"hash{i}"
            ))
        metric = PlaintextExposureMetric(tracker)
        score = metric.compute_exposure_score(10000)
        assert score > 0
        assert score <= 100.0


# =========================================================================
# Test ExposureReport — Generation
# =========================================================================

class TestExposureReportGeneration:
    """
    TestExposureReportGeneration

    Positive test cases for ExposureReport generation, dict serialization,
    multi-component reports, and recommendation generation.
    """
    def test_report_generation(self, populated_tracker):
        metric = PlaintextExposureMetric(populated_tracker)
        report = metric.generate_report()
        assert isinstance(report, ExposureReport)
        assert 0.0 <= report.overall_score <= 100.0
        assert report.total_exposure_ns > 0
        assert report.event_count > 0
        assert isinstance(report.recommendations, list)

    def test_report_to_dict(self, populated_tracker):
        metric = PlaintextExposureMetric(populated_tracker)
        report = metric.generate_report()
        d = report.to_dict()
        assert "overall_score" in d
        assert "component_scores" in d
        assert "function_scores" in d
        assert "recommendations" in d
        json.dumps(d)

    def test_report_with_multiple_components(self, tracker):
        tracker.record_appearance("microjit", "enc", b"data")
        tracker.record_disappearance("microjit", "enc", b"data")
        tracker.record_appearance("frag", "f1", b"d2")
        tracker.record_disappearance("frag", "f1", b"d2")
        tracker.record_encryption("fhe", "add")
        metric = PlaintextExposureMetric(tracker)
        report = metric.generate_report()
        assert "microjit" in report.component_scores
        assert "frag" in report.component_scores
        assert "fhe" in report.component_scores
        assert report.event_count == 5

    def test_recommendations_high_score(self, tracker):
        now = time.monotonic_ns()
        for i in range(20):
            tracker._events.append(ExposureEvent(
                "bad_comp", "leaky_fn", ExposureEventType.PLAINTEXT_APPEARS,
                now + i * 100, f"h{i}"
            ))
            tracker._events.append(ExposureEvent(
                "bad_comp", "leaky_fn", ExposureEventType.PLAINTEXT_DISAPPEARS,
                now + i * 100 + 95, f"h{i}"
            ))
        metric = PlaintextExposureMetric(tracker)
        report = metric.generate_report(2000)
        assert len(report.recommendations) >= 1


# =========================================================================
# Test Component Scores
# =========================================================================

class TestComponentScores:
    """
    TestComponentScores

    Positive test cases for per-component and per-function exposure
    score computation.
    """
    def test_component_scores(self, tracker):
        tracker.record_appearance("microjit", "fn1", b"d1")
        tracker.record_disappearance("microjit", "fn1", b"d1")
        tracker.record_appearance("frag", "fn2", b"d2")
        tracker.record_disappearance("frag", "fn2", b"d2")
        metric = PlaintextExposureMetric(tracker)
        scores = metric.compute_component_scores()
        assert "microjit" in scores
        assert "frag" in scores

    def test_function_scores(self, tracker):
        tracker.record_appearance("c", "f1", b"d1")
        tracker.record_disappearance("c", "f1", b"d1")
        tracker.record_appearance("c", "f2", b"d2")
        tracker.record_disappearance("c", "f2", b"d2")
        metric = PlaintextExposureMetric(tracker)
        scores = metric.compute_function_scores()
        assert "c:f1" in scores
        assert "c:f2" in scores


# =========================================================================
# Test Instrumentors
# =========================================================================

class TestMicroJITInstrumentor:
    """
    TestMicroJITInstrumentor

    Positive test cases for MicroJITExposureInstrumentor event creation.
    """
    def test_instrumentor_creates_events(self, tracker):
        inst = MicroJITExposureInstrumentor(tracker)
        ir_func = type("IRFunc", (), {"name": "test_func"})()
        inst.instrument_microjit(ir_func)
        events = tracker.get_events()
        assert len(events) >= 2
        assert events[0].component == "microjit"
        assert events[0].function == "test_func"

    def test_instrumentor_none(self, tracker):
        inst = MicroJITExposureInstrumentor(tracker)
        result = inst.instrument_microjit(None)
        assert result is None


class TestFragmentInstrumentor:
    """
    TestFragmentInstrumentor

    Positive test cases for FragmentationExposureInstrumentor event creation.
    """
    def test_instrumentor_creates_events(self, tracker):
        inst = FragmentationExposureInstrumentor(tracker)
        fragment = type("Frag", (), {"id": 42})()
        inst.instrument_fragment(fragment)
        events = tracker.get_events()
        assert len(events) >= 2
        assert events[0].component == "fragmentation"

    def test_instrumentor_none(self, tracker):
        inst = FragmentationExposureInstrumentor(tracker)
        result = inst.instrument_fragment(None)
        assert result is None


class TestFHEInstrumentor:
    """
    TestFHEInstrumentor

    Positive test cases for FHEExposureInstrumentor encryption/decryption event creation.
    """
    def test_instrumentor_creates_events(self, tracker):
        inst = FHEExposureInstrumentor(tracker)
        inst.instrument_encryption("fhe_add")
        inst.instrument_decryption("fhe_decrypt")
        events = tracker.get_events()
        assert len(events) == 4
        assert events[0].component == "fhe_vm"

    def test_encryption_appearance(self, tracker):
        inst = FHEExposureInstrumentor(tracker)
        inst.instrument_encryption("enc")
        events = tracker.get_events()
        assert events[0].event_type == ExposureEventType.PLAINTEXT_APPEARS
        assert events[1].event_type == ExposureEventType.ENCRYPTED


class TestHistoryBoundInstrumentor:
    """
    TestHistoryBoundInstrumentor

    Positive test cases for HistoryBoundExposureInstrumentor event creation.
    """
    def test_instrumentor_creates_events(self, tracker):
        inst = HistoryBoundExposureInstrumentor(tracker)
        inst.instrument_decryption("check_history")
        events = tracker.get_events()
        assert len(events) == 2

    def test_decryption_encryption_roundtrip(self, tracker):
        inst = HistoryBoundExposureInstrumentor(tracker)
        inst.instrument_decryption("fn")
        inst.instrument_encryption("fn")
        events = tracker.get_events()
        assert len(events) == 4


# =========================================================================
# Test ExposureSimulator
# =========================================================================

class TestExposureSimulator:
    """
    TestExposureSimulator

    Positive test cases for plaintext flow simulation across
    configured components.
    """
    def test_simulate_plaintext_flow(self):
        sim = ExposureSimulator()
        config = {
            "microjit": True,
            "fragmentation": True,
            "history_bound": True,
            "fhe_vm": True,
        }
        events, score = sim.simulate_plaintext_flow(None, config)
        assert len(events) > 0
        assert 0.0 <= score <= 100.0

    def test_simulator_empty_config(self):
        sim = ExposureSimulator()
        events, score = sim.simulate_plaintext_flow(None, {})
        assert len(events) > 0
        assert 0.0 <= score <= 100.0


# =========================================================================
# Negative Tests
# =========================================================================

class TestEmptyTracker:
    """
    TestEmptyTracker

    Negative test cases — empty tracker returns zero scores and empty reports.
    """
    def test_no_events_score_zero(self, tracker):
        metric = PlaintextExposureMetric(tracker)
        score = metric.compute_exposure_score()
        assert score == 0.0

    def test_no_events_component_scores(self, tracker):
        metric = PlaintextExposureMetric(tracker)
        scores = metric.compute_component_scores()
        assert scores == {}

    def test_no_events_function_scores(self, tracker):
        metric = PlaintextExposureMetric(tracker)
        scores = metric.compute_function_scores()
        assert scores == {}

    def test_no_events_no_exposure_time(self, tracker):
        assert tracker.get_total_exposure_time() == 0

    def test_no_events_report(self, tracker):
        metric = PlaintextExposureMetric(tracker)
        report = metric.generate_report()
        assert report.overall_score == 0.0
        assert report.total_exposure_ns == 0
        assert report.event_count == 0


class TestClearTracker:
    """
    TestClearTracker

    Negative test cases — clearing the tracker resets all events and exposure time.
    """
    def test_clear_resets_events(self, populated_tracker):
        assert len(populated_tracker.get_events()) > 0
        populated_tracker.clear()
        assert len(populated_tracker.get_events()) == 0

    def test_clear_resets_exposure_time(self, populated_tracker):
        populated_tracker.clear()
        assert populated_tracker.get_total_exposure_time() == 0

    def test_clear_then_record(self, tracker):
        tracker.record_appearance("c", "f", b"d")
        tracker.clear()
        tracker.record_appearance("c", "f", b"d")
        assert len(tracker.get_events()) == 1


class TestMalformedData:
    """
    TestMalformedData

    Negative test cases — exercises edge cases with empty bytes, strings,
    large data, and unicode data.
    """
    def test_empty_bytes(self, tracker):
        tracker.record_appearance("c", "f", b"")
        assert len(tracker.get_events()) == 1
        expected = hashlib.sha256(b"").hexdigest()
        assert tracker.get_events()[0].data_hash == expected

    def test_empty_string(self, tracker):
        tracker.record_appearance("c", "f", "")
        assert len(tracker.get_events()) == 1

    def test_large_data(self, tracker):
        large = bytes(1024 * 1024)
        tracker.record_appearance("c", "f", large)
        assert len(tracker.get_events()) == 1

    def test_unicode_string_data(self, tracker):
        tracker.record_appearance("c", "f", "\u00e9\u00e0\u00fc\u00f1")
        events = tracker.get_events()
        expected = hashlib.sha256("\u00e9\u00e0\u00fc\u00f1".encode("utf-8")).hexdigest()
        assert events[0].data_hash == expected
