"""
self_critique/engine.py

Purpose:
Performs an honest, introspective self-critique of the entire security
pipeline by answering six hard questions:
1. What assumptions could be wrong?
2. Which evidence is weakest?
3. Which metrics are least trustworthy?
4. Which proofs are least convincing?
5. Which features have lowest confidence?
6. Which claims have weakest support?

Architectural Role:
Final meta-assurance feature (F200) — acts as the conscience of the pipeline.
Produces an honesty score and a critique report consumed by engineers for
remediation planning.

Security Relevance:
Self-critique is the ultimate defense against overconfidence. It explicitly
calls out the pipeline's own weaknesses, preventing the system from making
stronger claims than its evidence supports.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class CritiqueFinding:
    """
    CritiqueFinding

    Purpose:
    Stores a single critique finding — the question asked, the answer found,
    severity level, and supporting references.

    Lifecycle:
    Created by each question_* method; aggregated into CritiqueReport.
    """
    question: str
    answer: str
    severity: str
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CritiqueReport:
    """
    CritiqueReport

    Purpose:
    Aggregates all six critique findings, an evidence summary, an honesty
    score, and a timestamp.

    Lifecycle:
    Created by generate_report().
    """
    critiques: list[CritiqueFinding]
    evidence_summary: str
    honesty_score: float
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "critiques": [c.to_dict() for c in self.critiques],
            "evidence_summary": self.evidence_summary,
            "honesty_score": self.honesty_score,
            "timestamp": self.timestamp,
        }


class SelfCritiqueEngine:
    """
    SelfCritiqueEngine

    Purpose:
    Asks six critical questions about the security pipeline's own outputs
    and produces an honest assessment with an honesty score (0.0-1.0).

    Lifecycle:
    Created on demand; generate_report() runs all questions and returns
    a CritiqueReport.
    """
    def __init__(self, root: str = "") -> None:
        self.root = root or _ROOT
        self.findings: list[CritiqueFinding] = []

    def question1_assumptions_without_evidence(self) -> CritiqueFinding:
        """
        question1_assumptions_without_evidence

        Purpose:
        Scans scripts/assumptions/ for Assumption() declarations and reports
        how many lack explicit evidence verification.

        Inputs:
        None

        Outputs:
        CritiqueFinding with severity "high".
        """
        assumptions_dir = os.path.join(self.root, "scripts", "assumptions")
        refs: list[str] = []
        count = 0
        if os.path.isdir(assumptions_dir):
            for root_dir, _dirs, files in os.walk(assumptions_dir):
                for fname in files:
                    if not fname.endswith(".py"):
                        continue
                    fpath = os.path.join(root_dir, fname)
                    rel = os.path.relpath(fpath, self.root)
                    try:
                        with open(fpath) as f:
                            content = f.read()
                    except OSError:
                        continue
                    assumptions = re.findall(
                        r'Assumption\("([^"]+)",\s*"([^"]+)"', content
                    )
                    for feature, assumption in assumptions:
                        count += 1
                        refs.append(f"{rel}: assumption '{assumption}' for {feature}")
                    if not assumptions:
                        refs.append(f"{rel}: no assumptions documented")

        msg = f"Found {count} documented assumptions; "
        if count == 0:
            msg += "NONE have evidence backing. Any unvalidated assumption could be wrong."
        else:
            msg += f"all {count} lack explicit evidence verification in the scanned files."
        return CritiqueFinding(
            question="What assumptions could be wrong?",
            answer=f"Scanned {len(refs)} assumption references. {msg}",
            severity="high",
            references=refs[:10],
        )

    def question2_weakest_evidence(self) -> CritiqueFinding:
        """
        question2_weakest_evidence

        Purpose:
        Loads the evidence report from build/ and identifies gaps in
        evidence coverage, especially claims without runtime traces.

        Inputs:
        None

        Outputs:
        CritiqueFinding with severity "medium".
        """
        evidence_path = os.path.join(self.root, "build", "evidence_report.json")
        alt_path = os.path.join(self.root, "build", "evidence_ledger.json")
        refs: list[str] = []
        msg = ""
        fpath = evidence_path if os.path.isfile(evidence_path) else (
            alt_path if os.path.isfile(alt_path) else ""
        )
        if fpath:
            with open(fpath) as f:
                data = json.load(f)
            claim_cov = float(data.get("claim_coverage_pct", 0))
            ev_cov = float(data.get("coverage_pct", 0))
            claims_no_runtime = data.get("claims_without_runtime_evidence", [])
            refs.append(f"claim_coverage: {claim_cov}%")
            refs.append(f"evidence_coverage: {ev_cov}%")
            refs.append(
                f"claims without runtime evidence: {len(claims_no_runtime)}"
            )
            for c in claims_no_runtime[:5]:
                refs.append(f"  - {c}")
            if claim_cov < 50 or ev_cov < 50:
                msg = "Evidence coverage is critically low."
            elif claims_no_runtime:
                msg = f"{len(claims_no_runtime)} claims lack runtime trace evidence."
            else:
                msg = "Evidence appears comprehensive but may contain unverified entries."
        else:
            msg = "No evidence report found — weakest evidence cannot be determined."
        return CritiqueFinding(
            question="Which evidence is weakest?",
            answer=msg,
            severity="medium",
            references=refs[:10],
        )

    def question3_least_trustworthy_metrics(self) -> CritiqueFinding:
        """
        question3_least_trustworthy_metrics

        Purpose:
        Scans scripts/metrics/ for files that return hardcoded/constant
        values vs. computed values and reports the least trustworthy.

        Inputs:
        None

        Outputs:
        CritiqueFinding with severity "high".
        """
        metrics_dir = os.path.join(self.root, "scripts", "metrics")
        refs: list[str] = []
        hardcoded_count = 0
        computed_count = 0
        if os.path.isdir(metrics_dir):
            for root_dir, _dirs, files in os.walk(metrics_dir):
                for fname in files:
                    if not fname.endswith(".py"):
                        continue
                    fpath = os.path.join(root_dir, fname)
                    rel = os.path.relpath(fpath, self.root)
                    try:
                        with open(fpath) as f:
                            content = f.read()
                    except OSError:
                        continue
                    if re.search(
                        r"return\s+True\b|#\s*mock|#\s*harcod", content, re.IGNORECASE
                    ):
                        hardcoded_count += 1
                        refs.append(f"{rel}: contains hardcoded/mock return")
                    elif re.search(
                        r"def\s+\w+.*:[\s\S]*?return\s+\d+\.?\d*\s*$",
                        content,
                    ):
                        hardcoded_count += 1
                        refs.append(f"{rel}: returns literal constant")
                    else:
                        computed_count += 1
        msg = (
            f"Found {hardcoded_count} metric files with hardcoded/constant returns "
            f"vs {computed_count} with computed values. "
            f"Hardcoded metrics are least trustworthy."
        )
        return CritiqueFinding(
            question="Which metrics are least trustworthy?",
            answer=msg,
            severity="high",
            references=refs[:10],
        )

    def question4_least_convincing_proofs(self) -> CritiqueFinding:
        """
        question4_least_convincing_proofs

        Purpose:
        Scans scripts/proofs/ for files without verification test or check
        functions — these are the least convincing proofs.

        Inputs:
        None

        Outputs:
        CritiqueFinding with severity "critical".
        """
        proofs_dir = os.path.join(self.root, "scripts", "proofs")
        refs: list[str] = []
        has_verification = 0
        no_verification = 0
        if os.path.isdir(proofs_dir):
            for root_dir, _dirs, files in os.walk(proofs_dir):
                for fname in files:
                    if not fname.endswith(".py"):
                        continue
                    fpath = os.path.join(root_dir, fname)
                    rel = os.path.relpath(fpath, self.root)
                    try:
                        with open(fpath) as f:
                            content = f.read()
                    except OSError:
                        continue
                    if re.search(
                        r"def\s+test_|def\s+verify|def\s+check", content
                    ):
                        has_verification += 1
                    else:
                        no_verification += 1
                        refs.append(f"{rel}: no verification test/check function")
        msg = (
            f"Of proof files scanned, {no_verification} have no verification tests. "
            f"These are the least convincing."
        )
        return CritiqueFinding(
            question="Which proofs are least convincing?",
            answer=msg,
            severity="critical",
            references=refs[:10],
        )

    def question5_lowest_confidence_features(self) -> CritiqueFinding:
        """
        question5_lowest_confidence_features

        Purpose:
        Counts test classes per feature and identifies the features with
        the fewest — these have the lowest confidence.

        Inputs:
        None

        Outputs:
        CritiqueFinding with severity "medium".
        """
        tests_dir = os.path.join(self.root, "tests")
        refs: list[str] = []
        test_counts: dict[str, int] = {}
        if os.path.isdir(tests_dir):
            for fname in os.listdir(tests_dir):
                if fname.startswith("test_") and fname.endswith(".py"):
                    fpath = os.path.join(tests_dir, fname)
                    try:
                        with open(fpath) as f:
                            content = f.read()
                    except OSError:
                        continue
                    test_classes = re.findall(
                        r"class\s+(Test\w+)", content
                    )
                    feature = fname.replace("test_", "").replace(".py", "")
                    test_counts[feature] = len(test_classes)
        sorted_features = sorted(test_counts.items(), key=lambda x: x[1])
        lowest = sorted_features[:5] if sorted_features else []
        for feat, count in lowest:
            refs.append(f"{feat}: {count} test classes")
        msg = (
            "Features with fewest test classes: "
            + ", ".join(f"{f}({c})" for f, c in lowest)
            if lowest
            else "No test files found."
        )
        return CritiqueFinding(
            question="Which features have lowest confidence?",
            answer=msg,
            severity="medium",
            references=refs,
        )

    def question6_weakest_claims(self) -> CritiqueFinding:
        """
        question6_weakest_claims

        Purpose:
        Parses claim_validation.md for claim headers and reports on the
        support strength of each claim.

        Inputs:
        None

        Outputs:
        CritiqueFinding with severity "medium".
        """
        claim_path = os.path.join(self.root, "claim_validation.md")
        refs: list[str] = []
        msg = ""
        if os.path.isfile(claim_path):
            with open(claim_path) as f:
                content = f.read()
            claims = re.findall(r"##\s+(.+)", content)
            for c in claims[:10]:
                refs.append(f"Claim: {c}")
            msg = f"Found {len(claims)} claims in claim_validation.md. "
            msg += "Each claim's support strength depends on implementation evidence."
        else:
            msg = "No claim_validation.md found to analyze."
        return CritiqueFinding(
            question="Which claims have weakest support?",
            answer=msg,
            severity="medium",
            references=refs,
        )

    def evaluate(self) -> list[CritiqueFinding]:
        """
        evaluate

        Purpose:
        Runs all six critique questions and stores the findings.

        Inputs:
        None

        Outputs:
        List of CritiqueFinding (also stored in self.findings).
        """
        self.findings = [
            self.question1_assumptions_without_evidence(),
            self.question2_weakest_evidence(),
            self.question3_least_trustworthy_metrics(),
            self.question4_least_convincing_proofs(),
            self.question5_lowest_confidence_features(),
            self.question6_weakest_claims(),
        ]
        return self.findings

    def evidence_summary(self) -> str:
        """
        evidence_summary

        Purpose:
        Produces a qualitative summary of the overall critique severity.

        Inputs:
        None (reads self.findings)

        Outputs:
        String: "Strong", "Moderate", or "Weak".
        """
        severity_scores = {"critical": 3, "high": 2, "medium": 1, "low": 0}
        total = sum(severity_scores.get(f.severity, 0) for f in self.findings)
        if total <= 2:
            return "Strong: most critiques are low-severity"
        if total <= 6:
            return "Moderate: several medium-severity critiques"
        return "Weak: multiple high/critical severity critiques identified"

    def honesty_score(self) -> float:
        """
        honesty_score

        Purpose:
        Computes a 0.0-1.0 honesty score based on finding severities.
        Higher severity = lower honesty score.

        Inputs:
        None (reads self.findings)

        Outputs:
        Float between 0.0 and 1.0.
        """
        sev_map = {"critical": 0.0, "high": 0.25, "medium": 0.5, "low": 0.75}
        if not self.findings:
            return 0.0
        total = sum(sev_map.get(f.severity, 0.5) for f in self.findings)
        return round(total / len(self.findings), 2)

    def generate_report(self) -> CritiqueReport:
        """
        generate_report

        Purpose:
        Main entry point — runs evaluation, computes evidence summary and
        honesty score, and returns a CritiqueReport.

        Inputs:
        None

        Outputs:
        CritiqueReport with findings, summary, score, and timestamp.
        """
        self.evaluate()
        return CritiqueReport(
            critiques=self.findings,
            evidence_summary=self.evidence_summary(),
            honesty_score=self.honesty_score(),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        )

    def generate_markdown(self) -> str:
        """
        generate_markdown

        Purpose:
        Generates a human-readable markdown critique report.

        Inputs:
        None

        Outputs:
        Markdown string.
        """
        report = self.generate_report()
        lines = []
        lines.append("# Self-Critique Report")
        lines.append("")
        lines.append("## Honest Assessment of the Security Pipeline")
        lines.append("")
        lines.append(f"**Honesty Score:** {report.honesty_score}")
        lines.append(f"**Evidence Summary:** {report.evidence_summary}")
        lines.append("")
        for c in report.critiques:
            lines.append(f"## {c.question}")
            lines.append("")
            lines.append(f"**Severity:** {c.severity}")
            lines.append("")
            lines.append(c.answer)
            lines.append("")
            if c.references:
                lines.append("### References")
                for r in c.references:
                    lines.append(f"- `{r}`")
                lines.append("")
        lines.append("---")
        lines.append(f"*Generated at {report.timestamp}*")
        return "\n".join(lines)


def generate_self_critique(root: str = "") -> dict:
    """
    generate_self_critique

    Purpose:
    Convenience function that creates a SelfCritiqueEngine and generates the
    full critique report.

    Inputs:
    root — optional root directory override

    Outputs:
    Dict with critiques, evidence_summary, honesty_score, timestamp.

    Security:
    Module entry point for F200.
    """
    engine = SelfCritiqueEngine(root)
    report = engine.generate_report()
    return report.to_dict()
