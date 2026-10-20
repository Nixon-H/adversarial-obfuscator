"""
pipeline_tracker.py

Purpose:
Records which protections are applied or skipped for each function
during pipeline execution. Provides a real-time audit trail of
protection decisions.

Architectural Role:
Sits between the protection pipeline and the coverage map. Each
protection pass calls record_protection() or record_skip() as it
runs. The CoverageMap later queries this data to build accurate
coverage snapshots.

Execution Context:
Instantiated at pipeline start, shared across all protection passes
via pipeline_state.globals["tracker"]. Each pass records decisions;
the tracker is serialized at build completion.

Dependencies:
- Standard library only (datetime, typing)

Security Relevance:
Without tracking, there is no way to know which protections were
skipped and why. PipelineTracker preserves the rationale for skips,
enabling post-hoc analysis of coverage gaps.

Maintenance Notes:
- Thread-safe concerns: if protection passes run in parallel, the
  tracker MUST be protected by a lock (currently not thread-safe).
- The _serialize_val recursive helper handles nested dicts/lists
  but may stack-overflow on deeply nested data.
"""

from __future__ import annotations

import datetime
from typing import Dict, Optional


class PipelineTracker:
    """
    Real-time audit trail for protection pipeline decisions.

    Each protection pass calls record_protection() or record_skip()
    as it runs, enabling the CoverageMap to include skip reasons and
    per-protection function lists.
    """

    def __init__(self):
        self._state: Dict[str, dict] = {}
        self._global_summary: Dict[str, list] = {}
        self._created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def record_protection(self, function_name: str, protection_name: str, details: Optional[Dict] = None, source=None, evidence_hash: Optional[str] = None):
        """
        Record that a protection was successfully applied to a function.

        Stores per-function application lists, detailed metadata, and
        updates the global protection-to-functions index.
        The evidence_hash should be a SHA-256 of the function body before
        and after the protection to verify actual transformation occurred.
        """
        if function_name not in self._state:
            self._state[function_name] = {
                "applied": [],
                "skipped": {},
                "details": {},
                "sources": {},
            }
        if evidence_hash is None:
            import logging as _lg
            _lg.warning(f"record_protection({function_name}, {protection_name}) called without evidence_hash — cannot verify actual application")
        if protection_name not in self._state[function_name]["applied"]:
            self._state[function_name]["applied"].append(protection_name)
            self._state[function_name]["sources"][protection_name] = source
        if details:
            self._state[function_name]["details"][protection_name] = details
        if protection_name not in self._global_summary:
            self._global_summary[protection_name] = []
        if function_name not in self._global_summary[protection_name]:
            self._global_summary[protection_name].append(function_name)

    def record_skip(self, function_name: str, protection_name: str, reason: str):
        """
        Record that a protection was skipped for a function.

        Stores the skip reason so the coverage map can explain
        why a function lacks a particular protection.
        """
        if function_name not in self._state:
            self._state[function_name] = {
                "applied": [],
                "skipped": {},
                "details": {},
            }
        self._state[function_name]["skipped"][protection_name] = reason

    def get_function_state(self, function_name: str) -> dict:
        """
        Return the recorded state for a function.

        Returns a dict with keys 'applied', 'skipped', 'details'.
        If no recordings exist, returns an empty state.
        """
        return self._state.get(function_name, {
            "applied": [],
            "skipped": {},
            "details": {},
        })

    def get_summary(self) -> dict:
        """
        Return a high-level summary of all recorded protections.

        Includes total function count, per-protection coverage
        ratios, total recordings, and total skips.
        """
        total_functions = len(self._state)
        per_protection = {}
        for pname, funcs in self._global_summary.items():
            per_protection[pname] = {
                "functions_covered": len(funcs),
                "coverage_ratio": len(funcs) / total_functions if total_functions > 0 else 0.0,
            }
        return {
            "total_functions": total_functions,
            "protections_applied": list(self._global_summary.keys()),
            "per_protection": per_protection,
            "total_recordings": sum(len(v["applied"]) for v in self._state.values()),
            "total_skips": sum(len(v["skipped"]) for v in self._state.values()),
        }

    def to_dict(self) -> dict:
        """
        Serialize the full tracker state to a JSON-compatible dict.
        """
        return {
            "created_at": self._created_at,
            "functions": {
                fname: {
                    "applied": list(state["applied"]),
                    "skipped": dict(state["skipped"]),
                    "details": {k: _serialize_val(v) for k, v in state["details"].items()},
                }
                for fname, state in self._state.items()
            },
            "summary": self.get_summary(),
        }


def _serialize_val(v):
    """
    Recursively serialize a value to a JSON-safe type.
    Dicts, lists, primitives pass through; everything else becomes str.
    """
    if isinstance(v, dict):
        return {k: _serialize_val(v2) for k, v2 in v.items()}
    if isinstance(v, list):
        return [_serialize_val(x) for x in v]
    if isinstance(v, (str, int, float, bool)):
        return v
    return str(v)
