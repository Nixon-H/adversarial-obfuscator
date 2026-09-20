"""
phase_independent_audit.py

Purpose:
Runs an independent auditor that verifies the pipeline's outputs without
relying on the pipeline's own tooling — performs reachability, proof,
benchmark, evidence, and claim audits from an external perspective.

Architectural Role:
External verification phase — provides a second-opinion audit.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.independent_audit.*

Security Relevance:
Independent audits catch blind spots that internal tooling would miss,
providing critical defense-in-depth for verification claims.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.independent_audit.auditor import independent_audit



def phase_independent_audit(args: Any) -> dict | None:
    """
    Run an independent audit of pipeline outputs.

    Args:
        args: argparse.Namespace

    Returns:
        dict with audit results, or None if disabled
    """
    enabled = getattr(args, "independent_audit", False)
    if not enabled:
        log("AUDIT", "Independent auditor disabled (use --independent-audit)")
        return None
    result = independent_audit()
    os.makedirs(BUILD_DIR, exist_ok=True)
    atomic_write(os.path.join(BUILD_DIR, "independent_audit.json"), json.dumps(result, indent=2))
    print("\n" + "=" * 60 + "\n  INDEPENDENT AUDIT\n" + "=" * 60)
    print(f"  Reachability checks: {len(result.get('reachability_audit', []))}")
    print(f"  Proof checks: {len(result.get('proof_audit', []))}")
    print(f"  Benchmark checks: {len(result.get('benchmark_audit', []))}")
    print(f"  Evidence checks: {len(result.get('evidence_audit', []))}")
    print(f"  Claim checks: {len(result.get('claim_audit', []))}")
    print("=" * 60)
    return result
