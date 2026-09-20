"""
phase_silent_fallback.py

Purpose:
Scans for silent fallback patterns — try/except blocks that silently
degrade security (e.g., "if crypto fails, skip it") without logs or
alerts.  Classifies findings as silent, logged, or safe.

Architectural Role:
Quality/security audit phase — prevents silent degradation.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.silent_fallback.*

Security Relevance:
Silent fallbacks are among the most dangerous security anti-patterns —
they disable protections without anyone noticing.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, ROOT, atomic_write, log
from scripts.silent_fallback.detector import SilentFallbackDetector



def phase_silent_fallback(args: Any) -> Optional[dict]:
    """
    Scan for silent fallback patterns in the codebase.

    Args:
        args: argparse.Namespace

    Returns:
        dict with total_findings, silent_fallback_score, and findings, or None if disabled
    """
    enabled = getattr(args, "silent_fallback", False)
    if not enabled:
        log("SILENT_FALLBACK", "Silent fallback detector disabled (use --silent-fallback)")
        return None

    log("SILENT_FALLBACK", "Scanning for silent fallback patterns...")

    scan_root = getattr(args, "payload", ROOT)
    if os.path.isfile(scan_root):
        scan_root = os.path.dirname(scan_root)
    if not scan_root:
        scan_root = os.path.join(ROOT, "scripts")

    detector = SilentFallbackDetector(scan_root)
    result = detector.detect_silent_fallbacks()

    print()
    print("=" * 60)
    print("  SILENT FALLBACK DETECTOR REPORT")
    print("=" * 60)
    print(f"  Total findings:                 {result['total_findings']}")
    print(f"  Silent fallbacks:               {result['total_silent']}")
    print(f"  Silent fallback score:          {result['silent_fallback_score']:.2f}%")
    print(f"  Classification stats:           {result['classification_stats']}")
    print()

    if result["findings"]:
        print("  Silent fallback findings:")
        for file_path, findings in result["findings"].items():
            rel_path = os.path.relpath(file_path, scan_root)
            for finding in findings:
                if finding["classification"] == "silent":
                    print(f"    {rel_path}:{finding['line_number']} "
                          f"(try@{finding['try_line']}, except@{finding['except_line']})")
        print()

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "silent_fallback_report.json")
    atomic_write(report_path, json.dumps(result, indent=2))
    log("SILENT_FALLBACK", f"Report saved to {report_path}")

    return result
