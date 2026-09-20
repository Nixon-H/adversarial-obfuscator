"""
evidence — Evidence Ledger (F168)

Purpose:
    Maintains a claim-evidence ledger that associates every protection claim
    (e.g. "AST obfuscation preserves semantics") with one or more pieces of
    verifiable evidence (source code, tests, benchmarks, runtime traces,
    metrics).

Architectural Role:
    Auditability layer: the ledger is the single source of truth for "why we
    believe each claim". It is consumed by the Self-Audit Agent (F180) and
    the Claim Auditor (F172).

Security Relevance:
    Prevents unsubstantiated security claims. Every claim must link to at
    least one piece of evidence that can be hashed and independently verified.
"""

from .ledger import ClaimEntry, EvidenceEntry, EvidenceLedger, build_evidence_ledger, verify_evidence, generate_evidence_report

__all__ = [
    "EvidenceLedger",
    "EvidenceEntry",
    "ClaimEntry",
    "build_evidence_ledger",
    "verify_evidence",
    "generate_evidence_report",
]
