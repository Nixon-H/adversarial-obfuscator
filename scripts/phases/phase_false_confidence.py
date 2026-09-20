"""
phase_false_confidence.py

Purpose:
Scans the codebase for false confidence patterns — code constructs that
give a false sense of security (e.g., ineffective cryptography, dead
checks, placebo protections).  Produces a prioritized list for remediation.

Architectural Role:
Audit phase — identifies security theater in the pipeline.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.false_confidence.*

Security Relevance:
False confidence is arguably worse than no protection — it creates a
blind spot where attackers operate undetected.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.false_confidence.detector import FalseConfidenceDetector, DetectionResult
from scripts.false_confidence.auditor import deduplicate_patterns, format_audit_report


def phase_false_confidence(args: Any) -> Optional[DetectionResult]:
    """
    Scan codebase for false confidence patterns.

    Args:
        args: argparse.Namespace

    Returns:
        DetectionResult or None
    """
    log("FALSE_CONFIDENCE", "Scanning for false confidence patterns...")

    scan_root = getattr(args, "payload", _ROOT)
    if os.path.isfile(scan_root):
        scan_root = os.path.dirname(scan_root)

    detector = FalseConfidenceDetector(scan_root)
    result = detector.scan_all()

    deduped = deduplicate_patterns(result.patterns_found)
    result.patterns_found = deduped
    result.total_count = len(deduped)
    result.critical_count = sum(1 for p in deduped if p.severity == "critical")
    result.major_count = sum(1 for p in deduped if p.severity == "major")
    result.minor_count = sum(1 for p in deduped if p.severity == "minor")

    report = format_audit_report(result)
    print(report)

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "false_confidence_audit.json")
    atomic_write(
        report_path,
        json.dumps(
            {
                "scan_path": result.scan_path,
                "timestamp": result.timestamp,
                "total_count": result.total_count,
                "critical_count": result.critical_count,
                "major_count": result.major_count,
                "minor_count": result.minor_count,
                "patterns_found": [
                    {
                        "pattern_name": p.pattern_name,
                        "severity": p.severity,
                        "description": p.description,
                        "suggested_fix": p.suggested_fix,
                        "file": p.file_match,
                        "line": p.line_number,
                    }
                    for p in deduped
                ],
            },
            indent=2,
        ),
    )
    log("FALSE_CONFIDENCE", f"Audit report saved to {report_path}")

    if result.critical_count > 0:
        log("FALSE_CONFIDENCE", f"⚠  {result.critical_count} CRITICAL false confidence patterns detected!")
        for p in deduped:
            if p.severity == "critical":
                rel = os.path.relpath(p.file_match, scan_root) if p.file_match else "?"
                log("FALSE_CONFIDENCE", f"  CRITICAL: {p.pattern_name} at {rel}:{p.line_number}")

    return result
