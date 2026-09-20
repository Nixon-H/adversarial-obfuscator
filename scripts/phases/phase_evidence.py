"""
phase_evidence.py

Purpose:
Builds an evidence ledger — scans build artifacts for evidence that
supports protection claims.  Each piece of evidence is verified and
scored.  Claims without supporting evidence are flagged.

Architectural Role:
Audit/verification phase — provides empirical support for claims.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, ..common, ..evidence.*

Security Relevance:
The evidence ledger is the bridge between security claims and actual
proof — claims without evidence are just assertions.
"""

from __future__ import annotations

import json
import os

from ..common import log, BUILD_DIR
from ..evidence.ledger import EvidenceLedger, generate_evidence_report


def phase_evidence(args) -> EvidenceLedger:
    """
    Build evidence ledger from build artifacts and verify each claim.

    Args:
        args: argparse.Namespace

    Returns:
        EvidenceLedger with all claims and verification results
    """
    log("EVIDENCE", "Building evidence ledger from build artifacts...")

    build_dir = getattr(args, "build_dir", BUILD_DIR)

    ledger = EvidenceLedger()
    ledger = ledger.from_build_artifacts(build_dir)

    log("EVIDENCE", f"Registered {len(ledger.claims)} claims")

    ev_results = ledger.verify_all()
    total_verified = 0
    total_evidence = 0
    for ev_list in ev_results.values():
        total_evidence += len(ev_list)
        for ev in ev_list:
            if ev.verified:
                total_verified += 1

    log("EVIDENCE", f"Verified {total_verified}/{total_evidence} evidence entries")

    unverified = ledger.get_unverified_claims()
    if unverified:
        log("EVIDENCE", f"Claims with no evidence ({len(unverified)}):")
        for c in unverified:
            log("EVIDENCE", f"  - {c}")

    no_runtime = ledger.get_claims_without_runtime()
    if no_runtime:
        log("EVIDENCE", f"Claims missing runtime evidence ({len(no_runtime)}):")
        for c in no_runtime:
            log("EVIDENCE", f"  - {c}")

    report = generate_evidence_report(ledger)
    report_path = os.path.join(build_dir, "evidence_ledger.json")
    ledger.to_json(report_path)
    log("EVIDENCE", f"Evidence ledger written to {report_path}")

    report_path2 = os.path.join(build_dir, "evidence_report.json")
    with open(report_path2, "w") as f:
        json.dump(report, f, indent=2)
    log("EVIDENCE", f"Evidence report written to {report_path2}")

    print()
    print("=" * 60)
    print("  EVIDENCE LEDGER SUMMARY")
    print("=" * 60)
    print(f"  Total claims:           {report['total_claims']}")
    print(f"  Total evidence entries: {report['total_evidence']}")
    print(f"  Verified entries:       {report['verified_evidence']}")
    print(f"  Evidence integrity:     {report['coverage_pct']}%")
    print(f"  Claim coverage:         {report['claim_coverage_pct']}%")
    print(f"  Claims w/o evidence:    {len(report['unverified_claims'])}")
    print(f"  Claims w/o runtime:     {len(report['claims_without_runtime_evidence'])}")
    print(f"  Evidence by type:       {report['evidence_by_type']}")
    print("=" * 60)
    print()

    return ledger
