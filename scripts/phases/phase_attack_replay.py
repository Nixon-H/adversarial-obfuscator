"""
phase_attack_replay.py

Purpose:
Captures attack results from the red team phase and replays them
across builds to detect regressions in protection effectiveness.
Maintains an attack history for trend analysis.

Architectural Role:
Regression testing phase — ensures protection doesn't degrade over time.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.attack_replay.*

Security Relevance:
Attack replay guarantees that protections that worked in the past
continue to work in the current build.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.attack_replay.capture import AttackCaptureStore, capture_attack
from scripts.attack_replay.replay import AttackReplay, ReplayResult
from scripts.attack_replay.history import AttackHistory


def phase_attack_replay(args: Any) -> Optional[List[ReplayResult]]:
    """
    Capture and replay attack results to detect protection regressions.

    Args:
        args: argparse.Namespace

    Returns:
        list of ReplayResult, or None if no capture/replay enabled
    """
    store_dir = getattr(args, "attack_store", os.path.join(BUILD_DIR, "attacks"))
    capture_flag = getattr(args, "capture_attacks", False)
    replay_flag = getattr(args, "replay_attacks", False)

    if not capture_flag and not replay_flag:
        log("ATTACK_REPLAY", "Neither --capture-attacks nor --replay-attacks enabled, skipping")
        return None

    binary_path = getattr(args, "binary_path", None)
    source_path = getattr(args, "payload", None)
    redteam_output = getattr(args, "red_team_output", None)

    if binary_path is None:
        obfuscated_name = (
            os.path.splitext(os.path.basename(source_path))[0] + "_obfuscated.py"
            if source_path else None
        )
        if obfuscated_name:
            candidate = os.path.join(BUILD_DIR, obfuscated_name)
            if os.path.exists(candidate):
                binary_path = candidate

    store = AttackCaptureStore(store_dir)
    history = AttackHistory(store_dir)
    results: List[ReplayResult] = []

    if capture_flag:
        log("ATTACK_REPLAY", "Capturing attack results from red team...")
        redteam_report_path = os.path.join(
            redteam_output or os.path.join(BUILD_DIR, "redteam"),
            "attack_report.json",
        )

        if os.path.exists(redteam_report_path):
            with open(redteam_report_path) as f:
                redteam_data = json.load(f)
        else:
            redteam_data = {}
            log("ATTACK_REPLAY", f"Red team report not found at {redteam_report_path}, capturing empty results")

        attack_types = ["angr", "ghidra", "bninja", "llm", "symbolic"]
        result_keys = {
            "angr": "angr_result",
            "ghidra": "ghidra_result",
            "bninja": "bninja_result",
            "llm": "llm_result",
            "symbolic": "symbolic_result",
        }

        for atype in attack_types:
            res_key = result_keys[atype]
            attack_results = redteam_data.get(res_key, {})
            if not attack_results:
                attack_results = {"status": "not_available", "note": f"No {atype} result in red team report"}

            cap = capture_attack(
                store_dir=store_dir,
                attack_type=atype,
                results=attack_results,
                binary_path=binary_path or "",
                source_path=source_path or "",
                metadata={
                    "redteam_source": redteam_report_path,
                    "build_id": redteam_data.get("timestamp", ""),
                },
            )
            log("ATTACK_REPLAY", f"  Captured {atype}: {cap.attack_id}")
        log("ATTACK_REPLAY", f"Capture complete. Total captures: {store.count()}")

    if replay_flag:
        log("ATTACK_REPLAY", "Replaying captured attacks...")
        replay = AttackReplay(store_dir, args)
        results = replay.replay_all()

        if not results:
            log("ATTACK_REPLAY", "  No captures to replay")
        else:
            total = len(results)
            passed = sum(1 for r in results if r.match)
            avg_sim = sum(r.similarity_score for r in results) / max(total, 1)

            print()
            print("=" * 60)
            print("  ATTACK REPLAY REPORT")
            print("=" * 60)
            for r in results:
                status = "PASS" if r.match else "FAIL"
                print(f"  [{status:4s}] {r.attack_type:12s} sim={r.similarity_score:.4f}  id={r.attack_id[:12]}...")
            print(f"  {'─' * 40}")
            print(f"  Total: {total}  Passed: {passed}  Failed: {total - passed}")
            print(f"  Average similarity: {avg_sim:.4f}")
            print("=" * 60)
            print()

        for r in results:
            history.add_entry(
                attack_type=r.attack_type,
                results={"match": r.match, "similarity_score": r.similarity_score},
                match=r.match,
                similarity_score=r.similarity_score,
                metadata={"attack_id": r.attack_id},
            )

    report_path = os.path.join(BUILD_DIR, "attack_replay_report.json")
    os.makedirs(BUILD_DIR, exist_ok=True)
    atomic_write(
        report_path,
        json.dumps(
            {
                "results": [r.to_dict() for r in results],
                "store_summary": store.to_dict(),
                "history_summary": history.get_statistics(),
            },
            indent=2,
            default=str,
        ),
    )
    log("ATTACK_REPLAY", f"Report saved to {report_path}")

    return results if results else None
