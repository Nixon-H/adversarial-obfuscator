"""
claim_auditor/auditor.py — Evidence cross-referencing and scoring for claims (F172)

# TWIN AUDITORS (different scopes, do not merge): scripts/self_audit/
# auditor.py (ten-category release gate, F180 — consumes THESE scores) and
# scripts/independent_audit/auditor.py (external artifact cross-check).

Purpose:
    After claims are detected, cross-references each against the filesystem
    for supporting evidence (tests, benchmarks, implementations, proofs,
    documentation), computes a composite claim score, and formats audit reports.

Architectural Role:
    Post-processing layer on top of ClaimDetector. Transforms raw matches into
    evidence-backed scores consumed by the Self-Audit Agent (F180).

Security Relevance:
    Converts claim detection from a binary flag into a graduated score,
    enabling teams to track improvement over time.
"""

from __future__ import annotations

import os
import time
from typing import Dict, List, Optional

from .detector import CLAIM_PATTERNS, ClaimDetector, ClaimAuditResult, ClaimMatch


def check_evidence(match: ClaimMatch, scan_root: str) -> Dict[str, bool]:
    """Search scan_root for files that could serve as evidence for a given claim match.

    Returns a dict with booleans for has_test, has_benchmark, has_implementation,
    has_proof, and has_documentation.
    """
    evidence: Dict[str, bool] = {
        "has_test": False,
        "has_benchmark": False,
        "has_implementation": False,
        "has_proof": False,
        "has_documentation": False,
    }
    claim_key = match.claim_text.replace(" ", "_").replace("-", "_")
    for dirpath, _, filenames in os.walk(scan_root):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            if fname.endswith(".py") and ("test_" + claim_key in fname
                                          or claim_key in fname):
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception:
                    continue
                if any(kw in content.lower() for kw in
                       ["assert", "def test", "claim", match.claim_text.lower()]):
                    evidence["has_test"] = evidence["has_test"] or ("test_" in fname)
                    evidence["has_benchmark"] = evidence["has_benchmark"] or ("bench_" in fname)
                    evidence["has_implementation"] = evidence["has_implementation"] or (
                        "def " in content and "class " in content
                    )
                    evidence["has_proof"] = evidence["has_proof"] or (
                        "proof" in fname or "prove" in fname
                        or "z3." in content or "z3." in content
                    )
                    evidence["has_documentation"] = evidence["has_documentation"] or (
                        "README" in fname or "docs/" in fpath
                    )

    return evidence


def compute_claim_score(matches: List[ClaimMatch],
                        evidence_map: Dict[int, Dict[str, bool]]) -> float:
    """Compute a 0-100 claim score from the match list and per-match evidence map.

    Weighted by severity: critical=1.0, high=0.8, medium=0.5, low=0.3.
    Each evidence type contributes up to its weight (test 0.25, impl 0.30, etc.).
    A penalty of up to 60 points is applied for the number of matches.

    Fail-closed: no matches audited => 0.0 (no evidence, no confidence),
    never a vacuous 100.0 "perfect" score.
    """
    if not matches:
        return 0.0
    total_weight = 0.0
    weighted_score = 0.0
    severity_weights = {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.3}
    for i, m in enumerate(matches):
        w = severity_weights.get(m.severity, 0.5)
        total_weight += w
        ev = evidence_map.get(i, {})
        evidence_score = 0.0
        if ev.get("has_test"):
            evidence_score += 0.25
        if ev.get("has_benchmark"):
            evidence_score += 0.15
        if ev.get("has_implementation"):
            evidence_score += 0.30
        if ev.get("has_proof"):
            evidence_score += 0.20
        if ev.get("has_documentation"):
            evidence_score += 0.10
        claim_score = 100.0 - (100.0 * (1.0 - evidence_score) * w)
        weighted_score += claim_score * w
    base = weighted_score / total_weight if total_weight > 0 else 0.0
    penalty = min(len(matches) * 3.0, 60.0)
    return max(0.0, base - penalty)


def format_audit_report(result: ClaimAuditResult) -> str:
    """Format a ClaimAuditResult into a human-readable, monospace audit report string."""
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("  CLAIM AUDITOR — EVIDENCE-BASED AUDIT REPORT")
    lines.append("=" * 72)
    lines.append(f"  Scan path:  {result.scan_path}")
    lines.append(f"  Timestamp:  {result.timestamp}")
    lines.append(f"  Total claims: {result.total_claims}")
    lines.append(f"  Critical:   {result.critical_count}")
    lines.append(f"  High:       {result.high_count}")
    lines.append(f"  Medium:     {result.medium_count}")
    lines.append(f"  Low:        {result.low_count}")
    lines.append(f"  Supported:  {result.supported_count}")
    lines.append(f"  Unsupported: {result.unsupported_count}")
    lines.append(f"  CLAIM SCORE: {result.score:.1f}/100")
    lines.append("=" * 72)

    if not result.matches:
        lines.append("\n  No claims found — clean bill of health.")
        lines.append("=" * 72)
        return "\n".join(lines)

    for severity, label in [("critical", "CRITICAL"), ("high", "HIGH"),
                             ("medium", "MEDIUM"), ("low", "LOW")]:
        group = [m for m in result.matches if m.severity == severity]
        if not group:
            continue
        lines.append(f"\n  [{label}] — {len(group)} claims")
        lines.append("  " + "-" * 68)
        for m in group:
            relpath = os.path.relpath(m.file_match, result.scan_path) if m.file_match else "?"
            lines.append(f"  [{m.claim_text:24s}] {relpath}:{m.line_number or '?'}")
            lines.append(f"  {'':28s}{m.description}")
            lines.append(f"  {'':28s}Evidence: {m.evidence_hint}")
            lines.append("")

    lines.append("=" * 72)
    lines.append(f"  SCORE: {result.score:.1f}/100 — "
                 f"{'PASS' if result.score >= 50.0 else 'REVIEW RECOMMENDED'}")
    lines.append("=" * 72)
    return "\n".join(lines)


def audit_source(scan_root: str) -> ClaimAuditResult:
    """Run a full claim audit on a directory: detect claims, cross-reference evidence, compute score."""
    detector = ClaimDetector(scan_root)
    result = detector.scan_all()
    evidence_map: Dict[int, Dict[str, bool]] = {}
    supported = 0
    for i, m in enumerate(result.matches):
        ev = check_evidence(m, scan_root)
        evidence_map[i] = ev
        if any(ev.values()):
            supported += 1
    result.supported_count = supported
    result.unsupported_count = result.total_claims - supported
    result.evidence_summary = evidence_map
    result.score = compute_claim_score(result.matches, evidence_map)
    return result


def audit_file(file_path: str) -> ClaimAuditResult:
    """Run a claim audit on a single file (or directory if path is a dir)."""
    scan_root = os.path.dirname(os.path.abspath(file_path)) if os.path.isfile(file_path) else file_path
    return audit_source(scan_root)
