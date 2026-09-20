"""
tracker.py

Purpose:
Tracks plaintext exposure events (appearance, disappearance,
encryption, decryption) with nanosecond timestamps. Provides
the raw event stream that the exposure metric consumes.

Architectural Role:
Lowest-level data layer for the exposure metric. Each instrumentor
pushes events as protection operations happen. The tracker records
event type, component, function, and data hash for deduplication.

Execution Context:
Instantiated once per pipeline run. Shared across all instrumentors
via pipeline_state. Events are pushed synchronously as protections
execute.

Dependencies:
- Standard library only (enum, hashlib, time, dataclasses, typing)

Security Relevance:
The event stream is the ground truth for exposure analysis. Without
accurate tracking, exposure scores would be based on estimates rather
than measurements. The data hash enables detection of duplicate or
overlapping exposure windows.

Maintenance Notes:
- The ExposureEventType enum has duplicate values (PLAINTEXT_APPEARS
  and PLAINTEXT_DISAPPEARS appear twice, ENCRYPTED and DECRYPTED
  appear twice). This is benign in Python but should be cleaned up.
- timestamps use time.monotonic_ns() for monotonic nanosecond
  precision; wall-clock time is NOT used.
- The _hash_data method uses SHA-256 which is cryptographically
  expensive for large data; consider using a faster hash if throughput
  is a concern.
"""

from __future__ import annotations
import enum
import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


class ExposureEventType(enum.Enum):
    """Enumeration of event types in the exposure timeline."""
    PLAINTEXT_APPEARS = "plaintext_appears"
    PLAINTEXT_DISAPPEARS = "plaintext_disappears"
    ENCRYPTED = "encrypted"
    DECRYPTED = "decrypted"


@dataclass
class ExposureEvent:
    """
    A single event in the plaintext exposure timeline.

    Records which component/function experienced an exposure event,
    the event type (appears/disappears/encrypted/decrypted), the
    nanosecond timestamp, and a SHA-256 hash of the data involved.
    """

    component: str
    function: str
    event_type: ExposureEventType
    timestamp_ns: int
    data_hash: str

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "component": self.component,
            "function": self.function,
            "event_type": self.event_type.value,
            "timestamp_ns": self.timestamp_ns,
            "data_hash": self.data_hash,
        }


class ExposureTracker:
    """
    Records a timestamped event stream of plaintext exposure events.

    Callers (instrumentors, simulators) push events as data transitions
    between plaintext and encrypted states. The event stream is consumed
    by PlaintextExposureMetric to compute exposure scores.
    """

    def __init__(self) -> None:
        self._events: List[ExposureEvent] = []

    def _hash_data(self, data: bytes) -> str:
        """Compute a SHA-256 hash for event deduplication."""
        return hashlib.sha256(data).hexdigest()

    def _ensure_bytes(self, data: bytes | str) -> bytes:
        """Normalize str input to bytes for consistent hashing."""
        if isinstance(data, str):
            return data.encode("utf-8")
        return data

    def record_appearance(self, component: str, function: str, data: bytes | str) -> None:
        return hashlib.sha256(data).hexdigest()

    def _ensure_bytes(self, data: bytes | str) -> bytes:
        if isinstance(data, str):
            return data.encode("utf-8")
        return data

    def record_appearance(self, component: str, function: str, data: bytes | str) -> None:
        """
        Record that plaintext data appeared (was decrypted) in memory.

        Used by instrumentors when data transitions from encrypted
        to plaintext state.
        """
        raw = self._ensure_bytes(data)
        self._events.append(ExposureEvent(
            component=component,
            function=function,
            event_type=ExposureEventType.PLAINTEXT_APPEARS,
            timestamp_ns=time.monotonic_ns(),
            data_hash=self._hash_data(raw),
        ))

    def record_disappearance(self, component: str, function: str, data: bytes | str) -> None:
        """
        Record that plaintext data disappeared (was encrypted/zeroed).

        Used by instrumentors when data transitions from plaintext
        back to encrypted or wiped state.
        """
        raw = self._ensure_bytes(data)
        self._events.append(ExposureEvent(
            component=component,
            function=function,
            event_type=ExposureEventType.PLAINTEXT_DISAPPEARS,
            timestamp_ns=time.monotonic_ns(),
            data_hash=self._hash_data(raw),
        ))

    def record_encryption(self, component: str, function: str) -> None:
        """Record an encryption operation event (no data hash needed)."""
        self._events.append(ExposureEvent(
            component=component,
            function=function,
            event_type=ExposureEventType.ENCRYPTED,
            timestamp_ns=time.monotonic_ns(),
            data_hash="",
        ))

    def record_decryption(self, component: str, function: str) -> None:
        """Record a decryption operation event (no data hash needed)."""
        self._events.append(ExposureEvent(
            component=component,
            function=function,
            event_type=ExposureEventType.DECRYPTED,
            timestamp_ns=time.monotonic_ns(),
            data_hash="",
        ))

    def get_exposure_duration(self, component: str, function: str) -> int:
        """
        Compute total exposure time (nanoseconds) for a specific
        component and function pair by summing the durations
        between PLAINTEXT_APPEARS and PLAINTEXT_DISAPPEARS events.
        """
        appears: Optional[ExposureEvent] = None
        total_ns = 0
        for ev in self._events:
            if (ev.component, ev.function) != (component, function):
                continue
            if ev.event_type == ExposureEventType.PLAINTEXT_APPEARS:
                appears = ev
            elif ev.event_type == ExposureEventType.PLAINTEXT_DISAPPEARS:
                if appears is not None:
                    total_ns += ev.timestamp_ns - appears.timestamp_ns
                    appears = None
        return total_ns

    def get_total_exposure_time(self) -> int:
        """
        Compute total exposure time across all components and functions.
        """
        total = 0
        components = {(ev.component, ev.function) for ev in self._events}
        for comp, func in components:
            total += self.get_exposure_duration(comp, func)
        return total

    def get_events(self) -> List[ExposureEvent]:
        """Return a copy of all recorded events."""
        return list(self._events)

    def clear(self) -> None:
        """Clear all recorded events. Used between simulation runs."""
        self._events.clear()

    def to_dict(self) -> dict:
        """Serialize the tracker state to a JSON-compatible dict."""
        return {
            "events": [ev.to_dict() for ev in self._events],
            "total_exposure_ns": self.get_total_exposure_time(),
            "event_count": len(self._events),
        }
