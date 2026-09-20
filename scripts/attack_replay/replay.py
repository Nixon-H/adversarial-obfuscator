"""
replay.py

Purpose:
Replays captured red-team attacks against current build artifacts
and compares results to detect regressions. Supports single-attack,
latest-attack, and all-attacks replay modes.

Architectural Role:
Execution layer for the attack replay framework. AttackReplay loads
a previous capture, re-runs the same attack tool against the current
binary/source, and compares the results using fuzzy comparison.

Execution Context:
Instantiated with a store_dir (path to capture index) and optional
redteam_config (provides current binary/source paths). Called by
the security regression checker when comparing builds.

Dependencies:
- capture (AttackCaptureStore, _sha256_file)
- comparator (compare_results)
- scripts.redteam.*_runner (attack runner modules)
- Standard library (json, os, time, dataclasses, datetime, typing)

Security Relevance:
Replay detects when protections degrade between builds. If an attack
that previously failed now succeeds, the replay will flag a low
similarity score, triggering the security regression gates.

Maintenance Notes:
- The _run_attack method uses dynamic imports (import inside function)
  so that missing runner modules don't break other attack types.
- If the binary or source files are missing at replay time, a failure
  result is returned without running the attack.
- The replay relies on the redteam_config to provide the current
  binary and source paths; these must match the build layout.
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .capture import AttackCaptureStore, _sha256_file
from .comparator import compare_results


@dataclass
class ReplayResult:
    attack_id: str
    attack_type: str
    original_results: Dict[str, Any]
    replayed_results: Dict[str, Any]
    match: bool
    similarity_score: float
    delta: Dict[str, Any]
    replayed_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AttackReplay:
    def __init__(self, store_dir: str, redteam_config: Any = None):
        self.store = AttackCaptureStore(store_dir)
        self.redteam_config = redteam_config

    def _run_attack(self, attack_type: str, binary_path: str, source_path: str) -> Dict[str, Any]:
        try:
            if attack_type == "angr":
                from scripts.redteam.angr_runner import run_angr_attack
                result = run_angr_attack(binary_path, self.store.store_dir)
                return result or {"status": "failed", "error": "angr returned None"}
            elif attack_type == "ghidra":
                from scripts.redteam.ghidra_runner import run_ghidra_attack
                result = run_ghidra_attack(binary_path, self.store.store_dir)
                return result or {"status": "failed", "error": "ghidra returned None"}
            elif attack_type == "bninja":
                from scripts.redteam.bninja_runner import run_binaryninja_attack
                result = run_binaryninja_attack(binary_path, self.store.store_dir)
                return result or {"status": "failed", "error": "bninja returned None"}
            elif attack_type == "llm":
                from scripts.redteam.llm_runner import run_llm_attack
                result = run_llm_attack(source_path, self.store.store_dir)
                return result or {"status": "failed", "error": "llm returned None"}
            elif attack_type == "symbolic":
                from scripts.redteam.symbolic_runner import run_symbolic_attack
                result = run_symbolic_attack(binary_path, self.store.store_dir)
                return result or {"status": "failed", "error": "symbolic returned None"}
            else:
                return {"status": "failed", "error": f"unknown attack type: {attack_type}"}
        except ImportError as e:
            return {"status": "failed", "error": f"module not available: {e}"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def replay(self, attack_id: str) -> Optional[ReplayResult]:
        capture = self.store.load(attack_id)
        if capture is None:
            return None

        binary_path = (
            self.redteam_config.binary_path
            if self.redteam_config and hasattr(self.redteam_config, "binary_path")
            else None
        )
        source_path = (
            self.redteam_config.source_path
            if self.redteam_config and hasattr(self.redteam_config, "source_path")
            else None
        )

        if binary_path is None or not os.path.exists(binary_path):
            return ReplayResult(
                attack_id=attack_id,
                attack_type=capture.attack_type,
                original_results=capture.results,
                replayed_results={"status": "failed", "error": "binary_path not available"},
                match=False,
                similarity_score=0.0,
                delta={"error": "binary not found for replay"},
                replayed_at=datetime.now(timezone.utc).isoformat(),
            )

        if source_path is None or not os.path.exists(source_path):
            return ReplayResult(
                attack_id=attack_id,
                attack_type=capture.attack_type,
                original_results=capture.results,
                replayed_results={"status": "failed", "error": "source_path not available"},
                match=False,
                similarity_score=0.0,
                delta={"error": "source not found for replay"},
                replayed_at=datetime.now(timezone.utc).isoformat(),
            )

        replayed_results = self._run_attack(capture.attack_type, binary_path, source_path)
        match, similarity, deltas = compare_results(capture.results, replayed_results)

        return ReplayResult(
            attack_id=attack_id,
            attack_type=capture.attack_type,
            original_results=capture.results,
            replayed_results=replayed_results,
            match=match,
            similarity_score=similarity,
            delta=deltas,
            replayed_at=datetime.now(timezone.utc).isoformat(),
        )

    def replay_latest(self, attack_type: str) -> Optional[ReplayResult]:
        capture = self.store.load_latest(attack_type)
        if capture is None:
            return None
        return self.replay(capture.attack_id)

    def replay_all(self) -> List[ReplayResult]:
        captures = self.store.list_captures()
        results = []
        for entry in captures:
            aid = entry.get("attack_id")
            if aid:
                result = self.replay(aid)
                if result is not None:
                    results.append(result)
        return results


def replay_attack(
    store_dir: str,
    attack_id: str,
    redteam_config: Any = None,
) -> Optional[ReplayResult]:
    replay = AttackReplay(store_dir, redteam_config)
    return replay.replay(attack_id)
