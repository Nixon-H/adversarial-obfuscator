"""
phase_trust_boundary.py

Purpose:
Maps trust boundaries across all execution domains — identifies where
data crosses between trust levels (user space, kernel, TEE, enclave)
and verifies that each boundary is enforced.

Architectural Role:
Security architecture audit phase.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.trust_boundary.*

Security Relevance:
Trust boundaries define where security guarantees must be enforced;
unmapped boundaries are unguarded attack surfaces.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.trust_boundary.mapper import TrustBoundaryMapper


def phase_trust_boundary(args: Any) -> dict:
    """
    Map trust boundaries across all execution domains.

    Args:
        args: argparse.Namespace

    Returns:
        dict with boundary entries and enforcement status
    """
    log("TRUST_BOUNDARY", "Mapping trust boundaries across all domains...")

    mapper = TrustBoundaryMapper()
    result = mapper.map_trust_boundaries()

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "trust_boundary_report.json")
    atomic_write(report_path, json.dumps(result, indent=2))
    log("TRUST_BOUNDARY", f"Report saved to {report_path}")

    print()
    print("=" * 60)
    print("  TRUST BOUNDARY MAP")
    print("=" * 60)
    for domain, entries in result["boundary_entries"].items():
        print(f"  [{domain}] {len(entries)} boundary entries")
        status = result["enforcement_status"].get(domain, {})
        enforced = status.get("enforced", False)
        print(f"    Enforced: {enforced}")
        total = status.get("total_entries", 0)
        enforced_count = status.get("enforced_entries", 0)
        print(f"    Entries: {total}, Validated: {enforced_count}")
    print(f"  Total domains: {len(result['boundary_entries'])}")
    print(f"  Trust graph edges: {sum(len(v) for v in result['trust_graph'].values())}")
    print("=" * 60)
    print()

    return result
