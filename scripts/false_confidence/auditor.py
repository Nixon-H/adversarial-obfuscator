"""
false_confidence/auditor.py — Focused auditing functions for false confidence (F173)

TWIN: scripts/claim_auditor/auditor.py (per-claim evidence scoring, F172) —
that module scores whether a claim has supporting evidence; this module
detects vacuous-pattern shapes (assert-nothing, 100-on-empty) in source,
tests, and benchmarks. Different signal; do not merge.

Purpose:
    Provides targeted audit functions (audit_source, audit_tests,
    audit_benchmarks, audit_all) that run a subset of false-confidence
    patterns relevant to a specific domain, plus deduplication and
    formatting utilities.

Architectural Role:
    Domain-specific audit layer on top of the generic FalseConfidenceDetector.
    Test-focused and benchmark-focused audits filter the pattern library.

Security Relevance:
    Enables CI/CD gates that reject PRs introducing false-confidence patterns
    in tests or benchmarks specifically.
"""

from __future__ import annotations

import os
import time
from typing import Dict, List, Set, Tuple

from .detector import ConfidencePattern, DetectionResult, FalseConfidenceDetector, KNOWN_PATTERNS


def audit_source(path: str) -> DetectionResult:
    """Run the full false-confidence scan on a source path (file or directory)."""
    detector = FalseConfidenceDetector(path)
    return detector.scan_all()


def audit_tests(path: str) -> DetectionResult:
    """Run a targeted false-confidence scan focused on test-specific patterns (empty test, skip, etc.)."""
    test_patterns = [
        p for p in KNOWN_PATTERNS
        if p.pattern_name in ("empty test", "skip test", "commented test", "TODO/FIXME")
    ]
    detector = FalseConfidenceDetector(path)
    matches: List[ConfidencePattern] = []
    for pat in test_patterns:
        matches.extend(detector.scan_for_pattern(pat))
    total = len(matches)
    critical = sum(1 for p in matches if p.severity == "critical")
    major = sum(1 for p in matches if p.severity == "major")
    minor = sum(1 for p in matches if p.severity == "minor")
    return DetectionResult(
        patterns_found=matches,
        total_count=total,
        critical_count=critical,
        major_count=major,
        minor_count=minor,
        scan_path=path,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )


def audit_benchmarks(path: str) -> DetectionResult:
    """Run a targeted false-confidence scan focused on benchmark-specific patterns (hardcoded scores, empty benchmarks)."""
    bench_patterns = [
        p for p in KNOWN_PATTERNS
        if p.pattern_name in ("hardcoded benchmark", "empty benchmark", "hardcoded score")
    ]
    detector = FalseConfidenceDetector(path)
    matches: List[ConfidencePattern] = []
    for pat in bench_patterns:
        matches.extend(detector.scan_for_pattern(pat))
    total = len(matches)
    critical = sum(1 for p in matches if p.severity == "critical")
    major = sum(1 for p in matches if p.severity == "major")
    minor = sum(1 for p in matches if p.severity == "minor")
    return DetectionResult(
        patterns_found=matches,
        total_count=total,
        critical_count=critical,
        major_count=major,
        minor_count=minor,
        scan_path=path,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )


def audit_all(paths: List[str]) -> Dict[str, DetectionResult]:
    """Audit multiple paths; results keyed by path."""
    results: Dict[str, DetectionResult] = {}
    for path in paths:
        if os.path.isfile(path):
            results[path] = audit_source(os.path.dirname(path))
        elif os.path.isdir(path):
            results[path] = audit_source(path)
    return results


def deduplicate_patterns(results: List[ConfidencePattern]) -> List[ConfidencePattern]:
    """Remove duplicate ConfidencePattern entries based on (name, file, line) key."""
    seen: Set[Tuple[str, str, int]] = set()
    deduped: List[ConfidencePattern] = []
    for p in results:
        key = (p.pattern_name, p.file_match or "", p.line_number or 0)
        if key not in seen:
            seen.add(key)
            deduped.append(p)
    return deduped


def format_audit_report(result: DetectionResult) -> str:
    """Format a DetectionResult into a human-readable audit report string."""
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("  FALSE CONFIDENCE AUDIT REPORT")
    lines.append("=" * 72)
    lines.append(f"  Scan path:  {result.scan_path}")
    lines.append(f"  Timestamp:  {result.timestamp}")
    lines.append(f"  Total:      {result.total_count}")
    lines.append(f"  Critical:   {result.critical_count}")
    lines.append(f"  Major:      {result.major_count}")
    lines.append(f"  Minor:      {result.minor_count}")
    lines.append("=" * 72)

    for severity, label, color in [("critical", "CRITICAL", "!"), ("major", "MAJOR", "*"), ("minor", "MINOR", "-")]:
        group = [p for p in result.patterns_found if p.severity == severity]
        if not group:
            continue
        lines.append(f"\n  [{label}]")
        lines.append("  " + "-" * 68)
        for p in group:
            relpath = os.path.relpath(p.file_match, result.scan_path) if p.file_match else "?"
            lines.append(f"  {color} {p.pattern_name:28s}  {relpath}:{p.line_number or '?'}")
            lines.append(f"    {p.description}")
            lines.append(f"    Fix: {p.suggested_fix}")
            lines.append("")

    lines.append("=" * 72)
    return "\n".join(lines)


def generate_audit_report(path: str) -> DetectionResult:
    """Convenience: run a full false-confidence audit on a path and return the result."""
    return audit_source(path)
