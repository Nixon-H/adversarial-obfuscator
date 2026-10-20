"""
claim_auditor/detector.py — Claim pattern definitions and regex scanner (F172)

Purpose:
    Defines a library of common overclaiming patterns (CLAIM_PATTERNS) and the
    ClaimDetector that walks source trees, matches patterns, and produces a
    ClaimAuditResult.

Architectural Role:
    Scanning layer. The pattern list is the "rule book" of banned or suspicious
    security language. Each pattern includes severity, description, and evidence
    hints for remediation.

Security Relevance:
    Automated detection of unsubstantiated claims provides a safety net against
    accidental or intentional over-promising in documentation and code comments.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ClaimPattern:
    """A pattern definition for a type of unsupported security claim.

    Attributes:
        claim_text: Short label (e.g. "unbreakable").
        pattern_regex: Regular expression to search for.
        category: Classification (false_security, overpromise, formal_claim, marketing).
        severity: critical / high / medium / low.
        description: Human-readable explanation of why this pattern is concerning.
        evidence_hint: Suggestion for what evidence would substantiate the claim.
    """
    claim_text: str
    pattern_regex: str
    category: str
    severity: str
    description: str
    evidence_hint: str


@dataclass
class ClaimMatch:
    """A single match of a claim pattern in a source file.

    Attributes same as ClaimPattern, plus the file, line number, and line content.
    """

    claim_text: str
    pattern_regex: str
    category: str
    severity: str
    description: str
    evidence_hint: str
    file_match: Optional[str] = None
    line_number: Optional[int] = None
    line_content: Optional[str] = None


@dataclass
class ClaimAuditResult:
    """Aggregate result of a claim-audit scan.

    Attributes:
        scan_path: Directory that was scanned.
        timestamp: Scan timestamp.
        total_claims / critical_count / high_count / medium_count / low_count: Severity counts.
        supported_count / unsupported_count: How many claims have supporting evidence.
        score: 0-100 composite score (higher = fewer unsupported claims).
        matches: All individual ClaimMatch instances.
        evidence_summary: Mapping from match index to evidence booleans.
    """

    scan_path: str
    timestamp: str
    total_claims: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    supported_count: int
    unsupported_count: int
    score: float
    matches: List[ClaimMatch]
    evidence_summary: Optional[dict] = None


# Registry of known overclaiming / unsupported security claim patterns.
# Each entry includes severity, description, and an evidence hint.
CLAIM_PATTERNS: List[ClaimPattern] = [
    ClaimPattern(
        claim_text="secure",
        pattern_regex=r"(?i)\bsecure\b",
        category="false_security",
        severity="high",
        description="Claims the software is 'secure' without specifying threat model or scope",
        evidence_hint="Look for security audit reports, penetration test results, or formal verification",
    ),
    ClaimPattern(
        claim_text="unbreakable",
        pattern_regex=r"(?i)\bunbreakable\b",
        category="overpromise",
        severity="critical",
        description="Claims the software is 'unbreakable' — no software is unbreakable",
        evidence_hint="Requires formal proof of security properties under well-defined adversary model",
    ),
    ClaimPattern(
        claim_text="tamper-proof",
        pattern_regex=r"(?i)\btamper[-\s]?(proof|resistant|protected)\b",
        category="false_security",
        severity="critical",
        description="Claims tamper-proof capability without evidence of anti-tamper mechanisms",
        evidence_hint="Look for integrity checks, attestation, or secure enclave usage",
    ),
    ClaimPattern(
        claim_text="AI resistant",
        pattern_regex=r"(?i)\b(AI|artificial\s+intelligence)[-\s]?(resistant|proof|immune|protected)\b",
        category="overpromise",
        severity="critical",
        description="Claims resistance to AI analysis without supporting adversarial evaluation",
        evidence_hint="Requires published AI-deobfuscation benchmark results",
    ),
    ClaimPattern(
        claim_text="military grade",
        pattern_regex=r"(?i)\bmilitary[-\s]?grade\b",
        category="marketing",
        severity="high",
        description="Vague 'military grade' claim with no specific standard reference",
        evidence_hint="Should reference specific standard (FIPS 140-2/3, Common Criteria EAL, etc.)",
    ),
    ClaimPattern(
        claim_text="unhackable",
        pattern_regex=r"(?i)\bunhackable\b",
        category="overpromise",
        severity="critical",
        description="Claims the software is 'unhackable' — no system is unhackable",
        evidence_hint="Requires formal proofs, bounty program results, and independent audits",
    ),
    ClaimPattern(
        claim_text="uncrackable",
        pattern_regex=r"(?i)\buncrackable\b",
        category="overpromise",
        severity="critical",
        description="Claims the software is 'uncrackable' without supporting evidence",
        evidence_hint="Requires cryptanalysis results and formal verification",
    ),
    ClaimPattern(
        claim_text="100% protection",
        pattern_regex=r"(?i)100\s*%\s*(protection|secure|safe|coverage|guaranteed)",
        category="overpromise",
        severity="critical",
        description="Claims 100% effectiveness — no protection is perfect",
        evidence_hint="Should report actual measured protection rates with confidence intervals",
    ),
    ClaimPattern(
        claim_text="guaranteed",
        pattern_regex=r"(?i)\b(guaranteed?|guarantee)\s+(secure|protection|safe|unbreakable)",
        category="overpromise",
        severity="high",
        description="Guarantees security outcomes without qualification",
        evidence_hint="Look for formal guarantees with well-defined security properties",
    ),
    ClaimPattern(
        claim_text="impossible to reverse",
        pattern_regex=r"(?i)\bimpossible\b.*\breverse\b|\breverse\b.*\bimpossible\b",
        category="overpromise",
        severity="critical",
        description="Claims reverse engineering is impossible — it is merely harder",
        evidence_hint="Should cite specific obfuscation strength metrics and analyst-time estimates",
    ),
    ClaimPattern(
        claim_text="invulnerable",
        pattern_regex=r"(?i)\binvulnerable\b",
        category="overpromise",
        severity="critical",
        description="Claims invulnerability without defining attack surface",
        evidence_hint="Requires comprehensive threat model coverage and penetration testing",
    ),
    ClaimPattern(
        claim_text="bulletproof",
        pattern_regex=r"(?i)\bbulletproof\b",
        category="overpromise",
        severity="high",
        description="Casual 'bulletproof' security claim without substantiation",
        evidence_hint="Should reference specific attack vectors that were tested and mitigated",
    ),
    ClaimPattern(
        claim_text="provably secure",
        pattern_regex=r"(?i)\bprovably\s+secure\b",
        category="formal_claim",
        severity="high",
        description="Claims provable security — requires formal proof in a defined model",
        evidence_hint="Look for formal verification artifacts, proof certificates, or published proofs",
    ),
    ClaimPattern(
        claim_text="mathematically proven",
        pattern_regex=r"(?i)\bmathematically\s+proven?\b",
        category="formal_claim",
        severity="critical",
        description="Claims mathematical proof of security property without evidence",
        evidence_hint="Should cite specific theorem, proof assistant (Coq/Isabelle/Z3), or paper",
    ),
    ClaimPattern(
        claim_text="zero-day resistant",
        pattern_regex=r"(?i)\bzero[-\s]?day[-\s]?(resistant|proof|immune)\b",
        category="false_security",
        severity="high",
        description="Claims zero-day resistance — impossible to guarantee against unknown vulns",
        evidence_hint="Look for exploit mitigation techniques: ASLR, CFG, sandboxing, etc.",
    ),
    ClaimPattern(
        claim_text="undetectable",
        pattern_regex=r"(?i)\bundetectable\b",
        category="overpromise",
        severity="high",
        description="Claims the software or its protection is undetectable",
        evidence_hint="Should provide evasion test results against specific detection tools",
    ),
    ClaimPattern(
        claim_text="fully protected",
        pattern_regex=r"(?i)\bfully\s+protected\b",
        category="false_security",
        severity="medium",
        description="Vague 'fully protected' claim with no scope definition",
        evidence_hint="Should enumerate what protections are applied and what threats they cover",
    ),
    ClaimPattern(
        claim_text="immune to analysis",
        pattern_regex=r"(?i)\bimmune\b.*\b(analysis|reverse|decompil|debug)\b",
        category="overpromise",
        severity="critical",
        description="Claims immunity to analysis techniques — no code is immune",
        evidence_hint="Requires empirical evaluation against multiple analysis approaches",
    ),
    ClaimPattern(
        claim_text="impregnable",
        pattern_regex=r"(?i)\bimpregnable\b",
        category="overpromise",
        severity="high",
        description="Archaic 'impregnable' security claim with no substantiation",
        evidence_hint="Should reference specific security architecture reviews",
    ),
    ClaimPattern(
        claim_text="absolute protection",
        pattern_regex=r"(?i)\babsolute\s+(protection|security|safety)\b",
        category="overpromise",
        severity="critical",
        description="Claims absolute protection — no defense is absolute",
        evidence_hint="Should qualify with specific threat model boundaries",
    ),
    ClaimPattern(
        claim_text="perfect security",
        pattern_regex=r"(?i)\bperfect\s+security\b",
        category="overpromise",
        severity="critical",
        description="Claims perfect security — information-theoretic security is rarely achieved",
        evidence_hint="Requires information-theoretic proof or reference to one-time pad level guarantees",
    ),
    ClaimPattern(
        claim_text="cannot be broken",
        pattern_regex=r"(?i)\bcannot?\s+be\s+broken?\b",
        category="overpromise",
        severity="high",
        description="Claims the system cannot be broken — no system is unbreakable",
        evidence_hint="Should reference cryptanalytic results and security margins",
    ),
    ClaimPattern(
        claim_text="no known vulnerabilities",
        pattern_regex=r"(?i)\bno\s+known\s+(vulnerabilit|weakness|flaw)\b",
        category="false_security",
        severity="high",
        description="Claims no known vulnerabilities — absence of evidence is not evidence of absence",
        evidence_hint="Should reference specific vulnerability scanning and disclosure process",
    ),
    ClaimPattern(
        claim_text="patented security",
        pattern_regex=r"(?i)\bpatented\s+security\b",
        category="marketing",
        severity="medium",
        description="Marketing claim of patented security without reference to patent numbers",
        evidence_hint="Should cite specific patent numbers and their relevance to security claims",
    ),
    ClaimPattern(
        claim_text="certified secure",
        pattern_regex=r"(?i)\bcertified\s+(secure|safe|protected)\b",
        category="marketing",
        severity="high",
        description="Claims security certification without naming the standard",
        evidence_hint="Look for specific certification: Common Criteria, FIPS 140, SOC 2, ISO 27001",
    ),
]


class ClaimDetector:
    """Walks a directory tree and matches CLAIM_PATTERNS against all source files.

    Scans .py, .rs, .c, .cpp, .h, .hpp, .md, .rst, .txt, .json, .yaml, .yml files.
    """

    def __init__(self, scan_root: str):
        self.scan_root = scan_root
        self.matches: List[ClaimMatch] = []

    def scan_for_pattern(self, pattern: ClaimPattern) -> List[ClaimMatch]:
        """Search all eligible files for a single ClaimPattern; return matching ClaimMatch list."""
        matches: List[ClaimMatch] = []
        try:
            compiled = re.compile(pattern.pattern_regex, re.MULTILINE)
        except re.error:
            return matches
        for dirpath, _, filenames in os.walk(self.scan_root):
            for fname in filenames:
                if not fname.endswith((".py", ".rs", ".c", ".cpp", ".h", ".hpp",
                                      ".md", ".rst", ".txt", ".json", ".yaml", ".yml")):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception:
                    continue
                for m in compiled.finditer(content):
                    line_num = content[: m.start()].count("\n") + 1
                    line_start = content.rfind("\n", 0, m.start())
                    line_end = content.find("\n", m.end())
                    if line_start == -1:
                        line_start = 0
                    if line_end == -1:
                        line_end = len(content)
                    line_content = content[line_start:line_end].strip()
                    matches.append(ClaimMatch(
                        claim_text=pattern.claim_text,
                        pattern_regex=pattern.pattern_regex,
                        category=pattern.category,
                        severity=pattern.severity,
                        description=pattern.description,
                        evidence_hint=pattern.evidence_hint,
                        file_match=fpath,
                        line_number=line_num,
                        line_content=line_content,
                    ))
        return matches

    def scan_all(self) -> ClaimAuditResult:
        """Run all claim patterns against the scan root and return a ClaimAuditResult with severity counts."""
        all_matches: List[ClaimMatch] = []
        for pattern in CLAIM_PATTERNS:
            all_matches.extend(self.scan_for_pattern(pattern))
        total = len(all_matches)
        critical = sum(1 for m in all_matches if m.severity == "critical")
        high = sum(1 for m in all_matches if m.severity == "high")
        medium = sum(1 for m in all_matches if m.severity == "medium")
        low = sum(1 for m in all_matches if m.severity == "low")
        self.matches = all_matches
        return ClaimAuditResult(
            scan_path=self.scan_root,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            total_claims=total,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            supported_count=0,
            unsupported_count=total,
            score=0.0,
            matches=all_matches,
        )

    def generate_report(self) -> str:
        """Format a human-readable audit report string from the current scan results."""
        lines: list[str] = []
        lines.append("=" * 72)
        lines.append("  CLAIM AUDITOR — AUDIT REPORT")
        lines.append("=" * 72)
        lines.append(f"  Scan root: {self.scan_root}")
        lines.append(f"  Timestamp: {time.strftime('%Y-%m-%dT%H:%M:%S')}")
        lines.append("=" * 72)

        if not self.matches:
            lines.append("  No unsupported claims detected.")
            lines.append("=" * 72)
            return "\n".join(lines)

        for severity, label in [("critical", "CRITICAL"), ("high", "HIGH"),
                                 ("medium", "MEDIUM"), ("low", "LOW")]:
            group = [m for m in self.matches if m.severity == severity]
            if not group:
                continue
            lines.append(f"\n  [{label}] — {len(group)} claims")
            lines.append("  " + "-" * 68)
            for m in group:
                relpath = os.path.relpath(m.file_match, self.scan_root) if m.file_match else "?"
                lines.append(f"  [{m.claim_text:24s}] {relpath}:{m.line_number or '?'}")
                lines.append(f"  {'':28s}{m.description}")
                lines.append(f"  {'':28s}Evidence: {m.evidence_hint}")
                lines.append("")

        lines.append("=" * 72)
        lines.append(f"  SUMMARY: {len(self.matches)} total | "
                     f"{len([m for m in self.matches if m.severity == 'critical'])} critical | "
                     f"{len([m for m in self.matches if m.severity == 'high'])} high | "
                     f"{len([m for m in self.matches if m.severity == 'medium'])} medium | "
                     f"{len([m for m in self.matches if m.severity == 'low'])} low")
        lines.append("=" * 72)
        return "\n".join(lines)


def scan_for_claims(scan_root: str) -> ClaimAuditResult:
    """Convenience: create a ClaimDetector, run scan_all, and return the result."""
    detector = ClaimDetector(scan_root)
    return detector.scan_all()
