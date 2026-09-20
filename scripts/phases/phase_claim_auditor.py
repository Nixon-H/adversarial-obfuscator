"""
phase_claim_auditor.py

Purpose:
Scans the codebase for unsupported security claims — statements in
comments or documentation that claim security properties without
corresponding implementation or evidence.

Architectural Role:
Audit phase — detects security claims that cannot be substantiated.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.claim_auditor.*

Security Relevance:
Unsupported claims erode trust and can constitute false advertising —
this phase ensures every claim has backing evidence.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.claim_auditor.detector import ClaimAuditResult
from scripts.claim_auditor.auditor import audit_source, format_audit_report


def phase_claim_audit(args: Any) -> Optional[ClaimAuditResult]:
    """
    Scan source for unsupported security claims.

    Args:
        args: argparse.Namespace

    Returns:
        ClaimAuditResult or None
    """
    log("CLAIM_AUDIT", "Scanning for unsupported security claims...")

    scan_root = getattr(args, "payload", _ROOT)
    if os.path.isfile(scan_root):
        scan_root = os.path.dirname(scan_root)

    result = audit_source(scan_root)

    report = format_audit_report(result)
    print(report)

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "claim_audit_report.json")
    atomic_write(
        report_path,
        json.dumps(
            {
                "scan_path": result.scan_path,
                "timestamp": result.timestamp,
                "total_claims": result.total_claims,
                "critical_count": result.critical_count,
                "high_count": result.high_count,
                "medium_count": result.medium_count,
                "low_count": result.low_count,
                "supported_count": result.supported_count,
                "unsupported_count": result.unsupported_count,
                "score": result.score,
                "claims": [
                    {
                        "claim_text": m.claim_text,
                        "severity": m.severity,
                        "category": m.category,
                        "description": m.description,
                        "evidence_hint": m.evidence_hint,
                        "file": m.file_match,
                        "line": m.line_number,
                    }
                    for m in result.matches
                ],
            },
            indent=2,
        ),
    )
    log("CLAIM_AUDIT", f"Audit report saved to {report_path}")

    if result.critical_count > 0:
        log("CLAIM_AUDIT", f"{result.critical_count} CRITICAL unsupported security claims!")
        for m in result.matches:
            if m.severity == "critical":
                rel = os.path.relpath(m.file_match, scan_root) if m.file_match else "?"
                log("CLAIM_AUDIT", f"  CRITICAL: [{m.claim_text}] at {rel}:{m.line_number}")

    log("CLAIM_AUDIT", f"Claim score: {result.score:.1f}/100")

    return result
