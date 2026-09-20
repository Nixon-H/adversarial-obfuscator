"""
phase_benchmark_integrity.py

Purpose:
Verifies the integrity of benchmark data — checks file hashes against
baselines, detects tampering, and validates the environment fingerprint
to ensure benchmarks are reproducible and untampered.

Architectural Role:
Integrity verification phase — protects benchmark trustworthiness.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.benchmark_integrity.*

Security Relevance:
Benchmark integrity is essential for tracking protection effectiveness
over time; compromised benchmarks invalidate trend analysis.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.benchmark_integrity.integrity import verify_benchmark_integrity



def phase_benchmark_integrity(args: Any) -> dict | None:
    """
    Verify the integrity of benchmark data.

    Args:
        args: argparse.Namespace

    Returns:
        dict with integrity_score and detection entries, or None if disabled
    """
    enabled = getattr(args, "benchmark_integrity", False)
    if not enabled:
        log("INTEGRITY", "Benchmark integrity verifier disabled (use --benchmark-integrity)")
        return None
    log("INTEGRITY", "Verifying benchmark integrity...")
    result = verify_benchmark_integrity()
    os.makedirs(BUILD_DIR, exist_ok=True)
    atomic_write(os.path.join(BUILD_DIR, "benchmark_integrity.json"), json.dumps(result, indent=2))
    print("\n" + "=" * 60 + "\n  BENCHMARK INTEGRITY\n" + "=" * 60)
    print(f"  Integrity Score:      {result.get('integrity_score', 0):.1f}/100")
    print(f"  Benchmark files:      {len(result.get('file_hashes', {}))}")
    print(f"  Tamper entries:       {len(result.get('tamper_detection', []))}")
    print(f"  Replay entries:       {len(result.get('replay_detection', []))}")
    print(f"  Environment baseline: {'set' if result.get('env_fingerprint') else 'missing'}")
    print("=" * 60)
    return result
