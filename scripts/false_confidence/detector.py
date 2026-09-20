"""
false_confidence/detector.py — False confidence pattern definitions and scanner (F173)

Purpose:
    Defines KNOWN_PATTERNS: a library of regex-based patterns that indicate
    false confidence (e.g. "always true", "empty verifier", "hardcoded proof").
    The FalseConfidenceDetector walks Python files and flags matches.

Architectural Role:
    Scanning layer. Each pattern includes a severity, description, and
    suggested fix, enabling automated remediation guidance.

Security Relevance:
    Automates detection of verification code that provides no actual
    verification, preventing silent security degradation.
"""

from __future__ import annotations

import ast
import os
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ConfidencePattern:
    """A single false-confidence pattern definition.

    Attributes:
        pattern_name: Short label (e.g. "always true").
        pattern_regex: Regular expression to search for.
        severity: critical / major / minor.
        description: Why this pattern is problematic.
        suggested_fix: Actionable remediation advice.
        file_match: Populated at scan time with the matching file path.
        line_number: Populated at scan time with the matching line number.
    """
    pattern_name: str
    pattern_regex: str
    severity: str
    description: str
    suggested_fix: str
    file_match: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class DetectionResult:
    """Result of a false-confidence scan.

    Attributes:
        patterns_found: All matched pattern instances.
        total_count / critical_count / major_count / minor_count: Severity tallies.
        scan_path: Directory that was scanned.
        timestamp: Scan timestamp.
    """

    patterns_found: List[ConfidencePattern]
    total_count: int
    critical_count: int
    major_count: int
    minor_count: int
    scan_path: str
    timestamp: str


# Known false-confidence patterns with severity and remediation guidance.
KNOWN_PATTERNS: List[ConfidencePattern] = [
    ConfidencePattern(
        pattern_name="always true",
        pattern_regex=r"assert.*or\s+True|True\s+or\s+assert|return\s+True\s*#.*placeholder",
        severity="critical",
        description="Code that always evaluates to True, making assertions meaningless",
        suggested_fix="Replace with actual condition that verifies the intended invariant",
    ),
    ConfidencePattern(
        pattern_name="empty pass",
        pattern_regex=r"^\s+pass\s*$",
        severity="major",
        description="Empty pass statement in function body — no real logic",
        suggested_fix="Implement the function body or raise NotImplementedError explicitly",
    ),
    ConfidencePattern(
        pattern_name="TODO/FIXME",
        pattern_regex=r"TODO|FIXME|HACK|XXX",
        severity="minor",
        description="Unresolved development marker left in code",
        suggested_fix="Address the TODO/FIXME before considering this code complete",
    ),
    ConfidencePattern(
        pattern_name="NotImplemented",
        pattern_regex=r"NotImplemented|raise\s+NotImplementedError",
        severity="critical",
        description="Function raises NotImplementedError — not actually implemented",
        suggested_fix="Implement the function or remove the call site",
    ),
    ConfidencePattern(
        pattern_name="hardcoded success",
        pattern_regex=r"return\s+True\s*#.*success|result\s*.*=\s*.*True\s*#.*proof",
        severity="critical",
        description="Hardcoded success return with comment claiming proof or verification",
        suggested_fix="Replace with actual proof or verification logic",
    ),
    ConfidencePattern(
        pattern_name="return True unconditionally",
        pattern_regex=r"def\s+\w+.*:[\s\S]*?return\s+True",
        severity="critical",
        description="Verification function returns True unconditionally with no real check",
        suggested_fix="Add actual verification logic before returning True",
    ),
    ConfidencePattern(
        pattern_name="empty verifier",
        pattern_regex=r"def\s+verify\w*.*:[\s\S]*?pass",
        severity="critical",
        description="Empty verifier function — no actual verification performed",
        suggested_fix="Implement verification logic or remove the function",
    ),
    ConfidencePattern(
        pattern_name="hardcoded benchmark",
        pattern_regex=r"benchmark\s*.*=\s*.*\{.*\"mean\":\s*\d+",
        severity="major",
        description="Hardcoded benchmark mean value — not from actual measurement",
        suggested_fix="Run actual benchmark and record the real value",
    ),
    ConfidencePattern(
        pattern_name="mock security",
        pattern_regex=r"#.*mock|#.*simulated|SIMULATION|simulation\s*.*=\s*.*True",
        severity="critical",
        description="Security feature is mocked or simulated, not real",
        suggested_fix="Replace mock with actual security implementation",
    ),
    ConfidencePattern(
        pattern_name="empty except",
        pattern_regex=r"except\s*.*:[\s\S]*?pass",
        severity="major",
        description="Bare except catches all exceptions and silently ignores them",
        suggested_fix="Catch specific exceptions and handle or re-raise",
    ),
    ConfidencePattern(
        pattern_name="always valid",
        pattern_regex=r"if\s*.*:[\s\S]*?return\s+True\s*else\s*:[\s\S]*?return\s+True",
        severity="critical",
        description="Both branches return True — condition is meaningless",
        suggested_fix="Make at least one branch return a different value",
    ),
    ConfidencePattern(
        pattern_name="commented out code",
        pattern_regex=r"#\s*def\s+|#\s*class\s+|#\s*import\s+",
        severity="major",
        description="Commented out code left in source — dead code",
        suggested_fix="Remove commented code if unused, or uncomment if needed",
    ),
    ConfidencePattern(
        pattern_name="fake assertion",
        pattern_regex=r"assert\s+True\s*#|assert\s+True\s*$",
        severity="critical",
        description="Assert True is always a no-op — provides false confidence",
        suggested_fix="Assert an actual condition that must be true",
    ),
    ConfidencePattern(
        pattern_name="empty function body",
        pattern_regex=r"def\s+\w+\s*\([\s\S]*?\)\s*:\s*\n\s+pass\s*$",
        severity="major",
        description="Function has empty body — no implementation",
        suggested_fix="Implement the function or mark with a decorator",
    ),
    ConfidencePattern(
        pattern_name="stub return",
        pattern_regex=r"return\s+None\s*#.*stub|return\s+0\s*#.*TODO|return\s+\"\"\s*#.*TODO",
        severity="major",
        description="Stub return value left as placeholder",
        suggested_fix="Return a real computed value",
    ),
    ConfidencePattern(
        pattern_name="hardcoded proof",
        pattern_regex=r"proof\s*.*=\s*.*True|verified\s*.*=\s*.*True|passed\s*.*=\s*.*True\s*$",
        severity="critical",
        description="Proof or verification status hardcoded to True",
        suggested_fix="Compute the proof/verification status from actual checks",
    ),
    ConfidencePattern(
        pattern_name="placeholder docstring",
        pattern_regex=r"TODO.*docstring|FIXME.*docstring|placeholder.*docstring",
        severity="minor",
        description="Placeholder docstring marker left in code",
        suggested_fix="Write a meaningful docstring describing the function",
    ),
    ConfidencePattern(
        pattern_name="empty test",
        pattern_regex=r"def\s+test\w*\s*\([\s\S]*?\)\s*:\s*\n\s+pass\s*$",
        severity="critical",
        description="Empty test function — no assertions",
        suggested_fix="Add actual test assertions",
    ),
    ConfidencePattern(
        pattern_name="skip test",
        pattern_regex=r"@unittest\.skip|@pytest\.mark\.skip|skip.*test",
        severity="major",
        description="Test has been skipped — not actually running",
        suggested_fix="Fix the test and remove the skip decorator",
    ),
    ConfidencePattern(
        pattern_name="mock all",
        pattern_regex=r"unittest\.mock\.patch|@mock\.patch|patch\.object",
        severity="minor",
        description="Extensive use of mocking may hide real integration issues",
        suggested_fix="Consider integration tests alongside mocks",
    ),
    ConfidencePattern(
        pattern_name="constant result",
        pattern_regex=r"return\s+\"success\"|return\s+\"ok\"|return\s+\"pass\"",
        severity="major",
        description="Hardcoded success string returned regardless of actual logic",
        suggested_fix="Return dynamic result based on actual computation",
    ),
    ConfidencePattern(
        pattern_name="unconditional except",
        pattern_regex=r"except\s+[A-Za-z]*:\s*[\s\S]*?return\s+True",
        severity="critical",
        description="Exception handler unconditionally returns True — hides failures",
        suggested_fix="Log the exception and re-raise or handle appropriately",
    ),
    ConfidencePattern(
        pattern_name="false security check",
        pattern_regex=r"if\s+True\s*:[\s\S]*?check|if\s+False\s*:[\s\S]*?verify",
        severity="critical",
        description="Security check is guarded by a constant condition — never runs",
        suggested_fix="Remove the constant guard or make it conditional on real input",
    ),
    ConfidencePattern(
        pattern_name="empty benchmark",
        pattern_regex=r"def\s+bench\w*\s*\([\s\S]*?\)\s*:\s*\n\s+pass\s*$",
        severity="major",
        description="Empty benchmark function — no timing or measurement",
        suggested_fix="Add actual benchmark timing logic",
    ),
    ConfidencePattern(
        pattern_name="hardcoded score",
        pattern_regex=r"(?:score|security|resilience|coverage|leakage|survivability)\s*[=:]\s*\d+",
        severity="major",
        description="Security score hardcoded to maximum — not computed",
        suggested_fix="Compute security score from actual measurements",
    ),
    ConfidencePattern(
        pattern_name="commented test",
        pattern_regex=r"#\s*def\s+test|#\s*\.test_|#\s*test_case",
        severity="major",
        description="Test has been commented out — not running",
        suggested_fix="Remove or re-enable the test",
    ),
    ConfidencePattern(
        pattern_name="always None",
        pattern_regex=r"return\s+None\s*$",
        severity="minor",
        description="Function always returns None — verify this is intentional",
        suggested_fix="Add explicit return type annotation and verify None is correct",
    ),
]


class FalseConfidenceDetector:
    """Walks a directory tree and flags false-confidence patterns in Python files."""

    def __init__(self, scan_root: str):
        self.scan_root = scan_root
        self.results: List[ConfidencePattern] = []

    def scan_for_pattern(self, pattern: ConfidencePattern) -> List[ConfidencePattern]:
        """Search all .py files under scan_root for a single ConfidencePattern."""
        matches: List[ConfidencePattern] = []
        compiled = re.compile(pattern.pattern_regex, re.MULTILINE)
        for dirpath, _, filenames in os.walk(self.scan_root):
            for fname in filenames:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception as _fe:
                    import logging as _lg
                    _lg.warning(f"Cannot scan {fpath} for false confidence: {_fe}")
                    continue
                for m in compiled.finditer(content):
                    line_num = content[: m.start()].count("\n") + 1
                    matches.append(ConfidencePattern(
                        pattern_name=pattern.pattern_name,
                        pattern_regex=pattern.pattern_regex,
                        severity=pattern.severity,
                        description=pattern.description,
                        suggested_fix=pattern.suggested_fix,
                        file_match=fpath,
                        line_number=line_num,
                    ))
        return matches

    def scan_all(self) -> DetectionResult:
        """Run all known false-confidence patterns against the scan root; return a DetectionResult."""
        all_patterns: List[ConfidencePattern] = []
        for known in KNOWN_PATTERNS:
            all_patterns.extend(self.scan_for_pattern(known))
        total = len(all_patterns)
        critical = sum(1 for p in all_patterns if p.severity == "critical")
        major = sum(1 for p in all_patterns if p.severity == "major")
        minor = sum(1 for p in all_patterns if p.severity == "minor")
        self.results = all_patterns
        return DetectionResult(
            patterns_found=all_patterns,
            total_count=total,
            critical_count=critical,
            major_count=major,
            minor_count=minor,
            scan_path=self.scan_root,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

    def generate_report(self) -> str:
        """Format a human-readable audit report from the current scan results."""
        lines: list[str] = []
        lines.append("=" * 72)
        lines.append("  FALSE CONFIDENCE DETECTOR — AUDIT REPORT")
        lines.append("=" * 72)
        lines.append(f"  Scan root: {self.scan_root}")
        lines.append(f"  Timestamp: {time.strftime('%Y-%m-%dT%H:%M:%S')}")
        lines.append("=" * 72)

        if not self.results:
            lines.append("  No false confidence patterns detected.")
            lines.append("=" * 72)
            return "\n".join(lines)

        criticals = [p for p in self.results if p.severity == "critical"]
        majors = [p for p in self.results if p.severity == "major"]
        minors = [p for p in self.results if p.severity == "minor"]

        for severity, group in [("CRITICAL", criticals), ("MAJOR", majors), ("MINOR", minors)]:
            if not group:
                continue
            lines.append(f"\n  [{severity}] — {len(group)} findings")
            lines.append("  " + "-" * 68)
            for p in group:
                fname = os.path.relpath(p.file_match, self.scan_root) if p.file_match else "?"
                lines.append(f"  {p.pattern_name:30s}  {fname}:{p.line_number or '?'}")
                lines.append(f"  {'':30s}  {p.description}")
                lines.append(f"  {'':30s}  Fix: {p.suggested_fix}")
                lines.append("")

        lines.append("=" * 72)
        lines.append(f"  SUMMARY: {len(self.results)} total | "
                     f"{len(criticals)} critical | {len(majors)} major | {len(minors)} minor")
        lines.append("=" * 72)
        return "\n".join(lines)


def scan_for_false_confidence(scan_root: str) -> DetectionResult:
    """Convenience: create a FalseConfidenceDetector, scan all patterns, return result."""
    detector = FalseConfidenceDetector(scan_root)
    return detector.scan_all()
