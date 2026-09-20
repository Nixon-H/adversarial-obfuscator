"""
claim_auditor — Claim Auditor (F172)

Purpose:
    Scans the codebase for potentially unsubstantiated security claims
    (e.g. "unbreakable", "provably secure", "tamper-proof") and cross-
    references them against supporting evidence (tests, benchmarks,
    proofs, documentation).

Architectural Role:
    Oversight layer. Acts as a linter for security marketing language,
    ensuring every strong claim has verifiable backing.

Security Relevance:
    Prevents overclaiming and security-washing by flagging claims that
    lack evidence, reducing the risk of misleading users or auditors.
"""

from .detector import ClaimPattern, ClaimAuditResult, ClaimDetector, CLAIM_PATTERNS, scan_for_claims
from .auditor import audit_source, audit_file, check_evidence, compute_claim_score, format_audit_report

__all__ = [
    "ClaimPattern",
    "ClaimAuditResult",
    "ClaimDetector",
    "CLAIM_PATTERNS",
    "scan_for_claims",
    "audit_source",
    "audit_file",
    "check_evidence",
    "compute_claim_score",
    "format_audit_report",
]
