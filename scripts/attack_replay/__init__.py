"""
__init__.py

Purpose:
Package initializer for the attack replay framework. Enables capture,
storage, replay, comparison, and history tracking of red-team attack
results for regression detection and reproducibility analysis.

Architectural Role:
Quality assurance layer for the red-team pipeline. Attack captures
are compared across builds to detect regressions (protections that
became less effective). The replay framework allows independent
verification of past results.

Execution Context:
Captures are created automatically during red-team execution. Replay
and comparison are triggered by the security regression checker when
comparing builds.

Dependencies:
- capture (AttackCapture, AttackCaptureStore, capture_attack)
- replay (AttackReplay, ReplayResult, replay_attack)
- comparator (compare_results, fuzzy_match, compare_reports)
- history (AttackHistory)

Security Relevance:
Attack replay detects security regressions: if a protection that
previously thwarted angr/Ghidra/Binary Ninja suddenly becomes less
effective, the replay framework will flag the delta. This prevents
silent degradation of protection quality.

Maintenance Notes:
- Captures are stored as JSON files in the build directory under
  attack_replay/captures/.
- Each capture includes binary and source SHA-256 hashes for
  input-matching across builds.
"""

from .capture import AttackCapture, AttackCaptureStore, capture_attack
from .replay import AttackReplay, ReplayResult, replay_attack
from .comparator import compare_results, fuzzy_match, compare_reports
from .history import AttackHistory

__all__ = [
    "AttackCapture", "AttackCaptureStore", "capture_attack",
    "AttackReplay", "ReplayResult", "replay_attack",
    "compare_results", "fuzzy_match", "compare_reports",
    "AttackHistory",
]
