"""
false_confidence — False Confidence Detector (F173)

Purpose:
    Scans Python source code for patterns that create "false confidence":
    hardcoded True returns, empty verifiers, placeholder assertions, mocked
    security features, and other code that appears to verify but does nothing.

Architectural Role:
    Anti-pattern detection layer. Complements the Claim Auditor by focusing
    on code-level issues rather than documentation-level overclaiming.

Security Relevance:
    False confidence in verification code is dangerous: it creates an illusion
    of safety while providing zero actual protection. Detection enables
    remediation before release.
"""

from .detector import FalseConfidenceDetector, DetectionResult, ConfidencePattern, KNOWN_PATTERNS, scan_for_false_confidence
from .auditor import audit_source, audit_tests, audit_benchmarks, audit_all, deduplicate_patterns, format_audit_report, generate_audit_report

__all__ = [
    "FalseConfidenceDetector",
    "DetectionResult",
    "ConfidencePattern",
    "KNOWN_PATTERNS",
    "scan_for_false_confidence",
    "generate_audit_report",
    "audit_source",
    "audit_tests",
    "audit_benchmarks",
    "audit_all",
    "deduplicate_patterns",
    "format_audit_report",
]
