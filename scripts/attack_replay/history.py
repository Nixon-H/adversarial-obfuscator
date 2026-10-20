"""
history.py

Purpose:
Tracks the historical record of attack replay comparisons. Maintains
a time-ordered log of replay results with match status, similarity
scores, and metadata. Provides trend analysis and regression detection.

Architectural Role:
Analytics layer for the attack replay framework. AttackHistory
persists a JSON log of all replay comparisons. The get_trend() and
get_regression_report() methods provide historical analysis.

Execution Context:
Instantiated per build directory. Entries are added by the security
regression checker after each replay comparison. The history file
(history.json) persists across builds for longitudinal analysis.

Dependencies:
- capture (AttackCaptureStore)
- Standard library (json, os, time, datetime, typing)

Security Relevance:
Historical trend analysis reveals gradual degradation of protections
that might be invisible in a single build comparison. A slowly
declining match rate indicates that attackers are adapting to
the protection scheme.

Maintenance Notes:
- get_regression_report() compares the match rate of the last N
  entries (window_size) against the preceding entries. A drop of
  more than 10% is flagged as a regression.
- The history file is a simple JSON list. For large histories,
  consider a database-backed store.
"""

import json
import os
import time  # noqa: F401 (this line binds a name used by an embedded template)
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .capture import AttackCaptureStore  # noqa: F401 (this line binds a name used by an embedded template)


class AttackHistory:
    def __init__(self, store_dir: str):
        self.store_dir = store_dir
        self._history_path = os.path.join(store_dir, "history.json")
        os.makedirs(store_dir, exist_ok=True)
        self._entries: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if os.path.exists(self._history_path):
            try:
                with open(self._history_path) as f:
                    data = json.load(f)
                self._entries = data if isinstance(data, list) else []
            except (json.JSONDecodeError, OSError):
                self._entries = []

    def _save(self):
        with open(self._history_path, "w") as f:
            json.dump(self._entries, f, indent=2, default=str)

    def add_entry(
        self,
        attack_type: str,
        results: Dict[str, Any],
        match: bool,
        similarity_score: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        entry = {
            "attack_type": attack_type,
            "results": results,
            "match": match,
            "similarity_score": similarity_score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        self._entries.append(entry)
        self._save()

    def get_trend(self, attack_type: str, metric_key: str) -> List[Dict[str, Any]]:
        entries = [e for e in self._entries if e.get("attack_type") == attack_type]
        trend = []
        for entry in entries:
            results = entry.get("results", {})
            if isinstance(results, dict):
                value = results.get(metric_key)
                if value is not None:
                    trend.append({
                        "timestamp": entry["timestamp"],
                        "value": value,
                        "match": entry.get("match", False),
                        "similarity_score": entry.get("similarity_score", 1.0),
                    })
        return trend

    def get_regression_report(self, window_size: int = 5) -> Dict[str, Any]:
        if len(self._entries) < 2:
            return {"regression_detected": False, "message": "insufficient history"}

        recent = self._entries[-window_size:] if window_size > 0 else self._entries
        older = self._entries[:-window_size] if len(self._entries) > window_size else []

        if not older:
            return {"regression_detected": False, "message": "no baseline for comparison"}

        recent_match_rate = sum(1 for e in recent if e.get("match", False)) / max(len(recent), 1)
        older_match_rate = sum(1 for e in older if e.get("match", False)) / max(len(older), 1)

        regression_detected = recent_match_rate < older_match_rate - 0.1
        regressed_types = []
        types_in_recent = set(e.get("attack_type", "") for e in recent)
        for atype in types_in_recent:
            recent_type = [e for e in recent if e.get("attack_type") == atype]
            older_type = [e for e in older if e.get("attack_type") == atype]
            if older_type:
                r_rate = sum(1 for e in recent_type if e.get("match", False)) / max(len(recent_type), 1)
                o_rate = sum(1 for e in older_type if e.get("match", False)) / max(len(older_type), 1)
                if r_rate < o_rate - 0.1:
                    regressed_types.append(atype)

        return {
            "regression_detected": regression_detected,
            "recent_match_rate": recent_match_rate,
            "older_match_rate": older_match_rate,
            "total_entries": len(self._entries),
            "recent_entries": len(recent),
            "older_entries": len(older),
            "regressed_attack_types": regressed_types,
        }

    def get_statistics(self) -> Dict[str, Any]:
        if not self._entries:
            return {"total_entries": 0, "attack_types": {}, "overall_match_rate": 0.0}

        by_type: Dict[str, List[Dict[str, Any]]] = {}
        for entry in self._entries:
            atype = entry.get("attack_type", "unknown")
            by_type.setdefault(atype, []).append(entry)

        type_stats = {}
        for atype, entries in by_type.items():
            match_count = sum(1 for e in entries if e.get("match", False))
            avg_sim = sum(e.get("similarity_score", 0) for e in entries) / max(len(entries), 1)
            type_stats[atype] = {
                "count": len(entries),
                "matches": match_count,
                "match_rate": match_count / max(len(entries), 1),
                "avg_similarity": avg_sim,
            }

        total_match = sum(1 for e in self._entries if e.get("match", False))
        return {
            "total_entries": len(self._entries),
            "attack_types": type_stats,
            "overall_match_rate": total_match / max(len(self._entries), 1),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "store_dir": self.store_dir,
            "history_path": self._history_path,
            "total_entries": len(self._entries),
            "entries": self._entries,
        }
