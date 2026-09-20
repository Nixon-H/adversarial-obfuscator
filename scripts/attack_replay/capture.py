"""
capture.py

Purpose:
Captures and persists red-team attack results with metadata (binary
hash, source hash, build ID, timestamps) for later replay and
comparison. Provides an indexed store for managing captures.

Architectural Role:
Persistence layer for the attack replay framework. Each attack run
produces an AttackCapture that is stored as JSON and indexed in a
store. The store supports load, list, delete, and latest queries.

Execution Context:
AttackCaptureStore is instantiated per build directory. Captures
are created by the red-team pipeline after each attack tool runs.
The store is consumed by AttackReplay for replay operations.

Dependencies:
- Standard library (hashlib, json, os, time, uuid, dataclasses, datetime)

Security Relevance:
Each capture includes SHA-256 hashes of both the binary and source,
enabling precise input matching across builds. Without these hashes,
comparing results between builds would be unreliable (different
inputs would produce different results).

Maintenance Notes:
- Captures are stored as individual JSON files in a captures/
  subdirectory. An index.json tracks all captures for fast listing.
- The CAPTURE_VERSION field enables future schema migration.
- SHA-256 hashing uses 64KB chunks for memory efficiency on large
  binaries.
"""

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

CAPTURE_VERSION = "1.0.0"


@dataclass
class AttackCapture:
    attack_id: str
    attack_type: str
    capture_time: str
    binary_hash: str
    source_hash: str
    build_id: str
    results: Dict[str, Any]
    debug_trace: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    capture_version: str = CAPTURE_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AttackCapture":
        return cls(**data)


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_data(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class AttackCaptureStore:
    def __init__(self, store_dir: str):
        self.store_dir = store_dir
        self._captures_dir = os.path.join(store_dir, "captures")
        self._index_path = os.path.join(store_dir, "index.json")
        os.makedirs(self._captures_dir, exist_ok=True)
        self._index: Dict[str, Dict[str, Any]] = {}
        self._load_index()

    def _load_index(self):
        if os.path.exists(self._index_path):
            try:
                with open(self._index_path) as f:
                    self._index = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._index = {}

    def _save_index(self):
        os.makedirs(os.path.dirname(self._index_path), exist_ok=True)
        with open(self._index_path, "w") as f:
            json.dump(self._index, f, indent=2, default=str)

    def _capture_path(self, attack_id: str) -> str:
        return os.path.join(self._captures_dir, f"{attack_id}.json")

    def capture(
        self,
        attack_type: str,
        results: Dict[str, Any],
        binary_path: str,
        source_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        debug_trace: Optional[str] = None,
        build_id: Optional[str] = None,
    ) -> AttackCapture:
        attack_id = str(uuid.uuid4())
        capture_time = datetime.now(timezone.utc).isoformat()
        binary_hash = _sha256_file(binary_path) if os.path.exists(binary_path) else ""
        source_hash = _sha256_file(source_path) if os.path.exists(source_path) else ""
        build_id = build_id or f"build_{int(time.time())}"

        cap = AttackCapture(
            attack_id=attack_id,
            attack_type=attack_type,
            capture_time=capture_time,
            binary_hash=binary_hash,
            source_hash=source_hash,
            build_id=build_id,
            results=results,
            debug_trace=debug_trace,
            metadata=metadata or {},
            capture_version=CAPTURE_VERSION,
        )

        path = self._capture_path(attack_id)
        with open(path, "w") as f:
            json.dump(cap.to_dict(), f, indent=2, default=str)

        self._index[attack_id] = {
            "attack_id": attack_id,
            "attack_type": attack_type,
            "capture_time": capture_time,
            "binary_hash": binary_hash,
            "source_hash": source_hash,
            "build_id": build_id,
            "capture_version": CAPTURE_VERSION,
        }
        self._save_index()

        return cap

    def load(self, attack_id: str) -> Optional[AttackCapture]:
        path = self._capture_path(attack_id)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)
        return AttackCapture.from_dict(data)

    def load_latest(self, attack_type: str) -> Optional[AttackCapture]:
        captures = self.list_captures(attack_type=attack_type)
        if not captures:
            return None
        captures.sort(key=lambda x: x.get("capture_time", ""), reverse=True)
        latest_id = captures[0]["attack_id"]
        return self.load(latest_id)

    def list_captures(self, attack_type: Optional[str] = None) -> List[Dict[str, Any]]:
        entries = list(self._index.values())
        if attack_type:
            entries = [e for e in entries if e.get("attack_type") == attack_type]
        return entries

    def delete(self, attack_id: str) -> bool:
        path = self._capture_path(attack_id)
        removed = False
        if os.path.exists(path):
            os.remove(path)
            removed = True
        if attack_id in self._index:
            del self._index[attack_id]
            self._save_index()
            removed = True
        return removed

    def count(self) -> int:
        return len(self._index)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "store_dir": self.store_dir,
            "total_captures": self.count(),
            "captures": self._index,
        }


def capture_attack(
    store_dir: str,
    attack_type: str,
    results: Dict[str, Any],
    binary_path: str,
    source_path: str,
    metadata: Optional[Dict[str, Any]] = None,
    debug_trace: Optional[str] = None,
) -> AttackCapture:
    store = AttackCaptureStore(store_dir)
    return store.capture(attack_type, results, binary_path, source_path, metadata, debug_trace)
