"""
phase_proof_soundness.py

Purpose:
Runs the proof soundness harness — generates and executes tests that
verify the soundness of formal proofs across the pipeline (semantic
preservation, mutation safety, VM correctness).

Architectural Role:
Verification phase — validates formal proof quality.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.proof_soundness.*

Security Relevance:
Proof soundness ensures that formal proofs actually establish what
they claim — a critical confidence metric for the entire pipeline.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.proof_soundness.harness import (
    ProofSoundnessHarness,
    SoundnessReport,
    generate_soundness_tests,
    run_soundness_harness,
)


def phase_proof_soundness(args: Any) -> Optional[SoundnessReport]:
    """
    Run the proof soundness harness across all proof modules.

    Args:
        args: argparse.Namespace

    Returns:
        SoundnessReport or None
    """
    log("PROOF_SOUNDNESS", "Running proof soundness harness...")

    proof_modules = [
        "semantic_preservation",
        "mutation_safety",
        "vm_correctness",
    ]

    harness = ProofSoundnessHarness()
    report = harness.run_all(proof_modules)

    print()
    print("=" * 60)
    print("  PROOF SOUNDNESS REPORT")
    print("=" * 60)
    print(f"  Total tests:     {report.total}")
    print(f"  Passed:          {report.passed}")
    print(f"  Failed:          {report.failed}")
    print(f"  Soundness score: {report.soundness_score:.4f}")
    print()
    if report.failing_modules:
        print(f"  Failing modules: {', '.join(report.failing_modules)}")
    print()
    for test in report.tests:
        status = "PASS" if test.passed else "FAIL"
        print(f"  [{status}] {test.test_id} ({test.test_type} → {test.target_proof})")
        if test.error_message:
            print(f"         error: {test.error_message}")
    print("=" * 60)
    print()

    report_path = os.path.join(BUILD_DIR, "proof_soundness_report.json")
    os.makedirs(BUILD_DIR, exist_ok=True)
    atomic_write(report_path, json.dumps(report.to_dict(), indent=2))
    log("PROOF_SOUNDNESS", f"Report saved to {report_path}")

    return report
