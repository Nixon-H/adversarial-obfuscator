"""
manipulation_detector/detector.py

Purpose:
Detects manipulation of security metrics in the codebase — hardcoded scores,
inflated coverage, fake survivability, fake proof coverage, and fake resistance
values. Generates adversarial mutations for each finding to demonstrate impact.

Architectural Role:
Runs as a static analysis pass over the scripts/ tree. Produces a manipulation
score and a list of findings consumed by meta-assurance features (F193, F194).

Security Relevance:
Prevents security theatre by flagging metrics that are fabricated rather than
computed. Adversarial mutations provide concrete evidence of manipulation.
"""
from __future__ import annotations

import ast
import os
import random
import re
import sys
from dataclasses import dataclass, field
from typing import Any


_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class ManipulationFinding:
    """
    ManipulationFinding

    Purpose:
    Captures a single instance of suspected metric manipulation found during
    static analysis — e.g., a hardcoded score or an always-100 coverage return.

    Lifecycle:
    Created by detector check methods; consumed by _build_report().

    Security:
    Each finding contributes to the aggregate manipulation score.
    """
    file: str
    line: int
    metric_type: str
    pattern: str
    snippet: str
    score_contribution: float


@dataclass
class AdversarialMutation:
    """
    AdversarialMutation

    Purpose:
    Records a concrete code transformation that exposes a manipulated metric —
    e.g., replacing `return 100` with `return random.randint(0, 100)`.

    Lifecycle:
    Created by _generate_mutation() alongside a ManipulationFinding.

    Security:
    Provides reproducible evidence that a metric is fragile under adversarial
    perturbation.
    """
    original_file: str
    original_line: int
    original_code: str
    mutated_code: str
    metric_type: str


class MetricManipulationDetector:
    """
    MetricManipulationDetector

    Purpose:
    Scans Python files in the scripts/ tree for five categories of metric
    manipulation: hardcoded scores, inflated coverage, fake survivability,
    fake proof coverage, and fake resistance.

    Lifecycle:
    Instantiated by detect_metric_manipulation(); scan_all() drives analysis.

    Security:
    Directly detects security theatre — metrics that look good but are
    fabricated rather than computed from real measurements.
    """
    def __init__(self, scripts_dir: str | None = None):
        self.scripts_dir = scripts_dir or os.path.join(_ROOT, "scripts")
        self.findings: list[ManipulationFinding] = []
        self.adversarial_mutations: list[AdversarialMutation] = []
        self._manipulation_score = 0.0

    def scan_all(self) -> dict:
        """
        scan_all

        Purpose:
        Walks the scripts/ directory, scans every .py file, computes the
        aggregate manipulation score, and returns the full report.

        Inputs:
        None

        Outputs:
        Dict with findings_per_file, manipulation_score, adversarial_mutations,
        total_findings, total_mutations.

        Security:
        Main entry point for metric manipulation detection (F182).
        """
        self.findings.clear()
        self.adversarial_mutations.clear()
        if not os.path.isdir(self.scripts_dir):
            return {
                "findings_per_file": {},
                "manipulation_score": 0.0,
                "adversarial_mutations": [],
            }
        for root, dirs, files in os.walk(self.scripts_dir):
            dirs[:] = [d for d in dirs if not d.startswith("__") and not d.startswith(".")]
            for fname in files:
                if fname.endswith(".py"):
                    fpath = os.path.join(root, fname)
                    self._scan_file(fpath)
        self._compute_score()
        return self._build_report()

    def _scan_file(self, fpath: str) -> None:
        """
        _scan_file

        Purpose:
        Parses a single .py file into an AST and dispatches to all five
        manipulation checks.

        Inputs:
        fpath — absolute path to the .py file

        Outputs:
        None (appends to self.findings)

        Security:
        Internal dispatch — each check targets a different manipulation vector.
        """
        with open(fpath, encoding="utf-8", errors="ignore") as f:
            content = f.read()
        tree = ast.parse(content)
        rel = os.path.relpath(fpath, self.scripts_dir)
        self._check_hardcoded_scores(rel, tree, content)
        self._check_inflated_coverage(rel, tree, content)
        self._check_fake_survivability(rel, tree, content)
        self._check_fake_proof_coverage(rel, tree, content)
        self._check_fake_resistance(rel, tree, content)

    def _check_hardcoded_scores(self, rel: str, tree: ast.AST, content: str) -> None:
        """
        _check_hardcoded_scores

        Purpose:
        Finds assignments where a variable named score/coverage/survivability/
        resistance/metric is set to a constant >= 90.

        Inputs:
        rel — relative file path
        tree — parsed AST
        content — raw source text

        Outputs:
        None (appends ManipulationFinding to self.findings)
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                        name_lower = target.id.lower()
                        val = node.value.value
                        if isinstance(val, (int, float)):
                            if any(kw in name_lower for kw in ["score", "coverage", "survivability", "resistance", "metric"]):
                                if val >= 90:
                                    self.findings.append(ManipulationFinding(
                                        file=rel,
                                        line=node.lineno,
                                        metric_type="hardcoded_score",
                                        pattern=f"Hardcoded {target.id} = {val}",
                                        snippet=content.splitlines()[node.lineno - 1].strip()[:120],
                                        score_contribution=0.4,
                                    ))

    def _check_inflated_coverage(self, rel: str, tree: ast.AST, content: str) -> None:
        """
        _check_inflated_coverage

        Purpose:
        Finds functions named *coverage* that unconditionally return 100.

        Inputs:
        rel — relative file path
        tree — parsed AST
        content — raw source text

        Outputs:
        None (appends ManipulationFinding and may call _generate_mutation)
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                returns = [n for n in ast.walk(node) if isinstance(n, ast.Return)]
                if len(returns) == 1 and isinstance(returns[0].value, ast.Constant):
                    val = returns[0].value.value
                    if val == 100 and any(kw in node.name.lower() for kw in ["coverage", "cover"]):
                        self.findings.append(ManipulationFinding(
                            file=rel,
                            line=returns[0].lineno,
                            metric_type="inflated_coverage",
                            pattern="Coverage always returns 100",
                            snippet=content.splitlines()[returns[0].lineno - 1].strip()[:120],
                            score_contribution=0.5,
                        ))
                        self._generate_mutation(rel, returns[0].lineno, content, "coverage")

    def _check_fake_survivability(self, rel: str, tree: ast.AST, content: str) -> None:
        """
        _check_fake_survivability

        Purpose:
        Finds functions named *survivability* that unconditionally return >= 90.

        Inputs:
        rel — relative file path
        tree — parsed AST
        content — raw source text

        Outputs:
        None (appends ManipulationFinding and may call _generate_mutation)
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if "survivability" in node.name.lower():
                    returns = [n for n in ast.walk(node) if isinstance(n, ast.Return)]
                    if len(returns) == 1 and isinstance(returns[0].value, ast.Constant):
                        val = returns[0].value.value
                        if isinstance(val, (int, float)) and val >= 90:
                            self.findings.append(ManipulationFinding(
                                file=rel,
                                line=returns[0].lineno,
                                metric_type="fake_survivability",
                                pattern=f"Survivability always returns {val}",
                                snippet=content.splitlines()[returns[0].lineno - 1].strip()[:120],
                                score_contribution=0.5,
                            ))
                            self._generate_mutation(rel, returns[0].lineno, content, "survivability")

    def _check_fake_proof_coverage(self, rel: str, tree: ast.AST, content: str) -> None:
        """
        _check_fake_proof_coverage

        Purpose:
        Finds functions named *proof*cover* that unconditionally return 100
        or 1.0.

        Inputs:
        rel — relative file path
        tree — parsed AST
        content — raw source text

        Outputs:
        None (appends ManipulationFinding to self.findings)
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if "proof" in node.name.lower() and "cover" in node.name.lower():
                    returns = [n for n in ast.walk(node) if isinstance(n, ast.Return)]
                    if len(returns) == 1 and isinstance(returns[0].value, ast.Constant):
                        val = returns[0].value.value
                        if val == 100 or val == 1.0:
                            self.findings.append(ManipulationFinding(
                                file=rel,
                                line=returns[0].lineno,
                                metric_type="fake_proof_coverage",
                                pattern=f"Proof coverage always returns {val}",
                                snippet=content.splitlines()[returns[0].lineno - 1].strip()[:120],
                                score_contribution=0.6,
                            ))

    def _check_fake_resistance(self, rel: str, tree: ast.AST, content: str) -> None:
        """
        _check_fake_resistance

        Purpose:
        Finds functions named *resistance* that unconditionally return >= 90.

        Inputs:
        rel — relative file path
        tree — parsed AST
        content — raw source text

        Outputs:
        None (appends ManipulationFinding to self.findings)
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if "resistance" in node.name.lower():
                    returns = [n for n in ast.walk(node) if isinstance(n, ast.Return)]
                    if len(returns) == 1 and isinstance(returns[0].value, ast.Constant):
                        val = returns[0].value.value
                        if isinstance(val, (int, float)) and val >= 90:
                            self.findings.append(ManipulationFinding(
                                file=rel,
                                line=returns[0].lineno,
                                metric_type="fake_resistance",
                                pattern=f"Resistance always returns {val}",
                                snippet=content.splitlines()[returns[0].lineno - 1].strip()[:120],
                                score_contribution=0.6,
                            ))

    def _generate_mutation(self, rel: str, lineno: int, content: str, metric_type: str) -> None:
        """
        _generate_mutation

        Purpose:
        Creates an adversarial mutation of the offending line by replacing the
        hardcoded return value with a random range, demonstrating the metric's
        fragility.

        Inputs:
        rel — relative file path
        lineno — line number of the original return
        content — raw source text
        metric_type — the category of manipulation

        Outputs:
        None (appends AdversarialMutation to self.adversarial_mutations)
        """
        lines = content.splitlines()
        if lineno - 1 < len(lines):
            original = lines[lineno - 1]
            mutated = re.sub(
                r"return\s+(\d+(?:\.\d+)?)",
                lambda m: f"return random.randint(0, {int(float(m.group(1)))})",
                original,
            )
            if mutated != original:
                self.adversarial_mutations.append(AdversarialMutation(
                    original_file=rel,
                    original_line=lineno,
                    original_code=original.strip(),
                    mutated_code=mutated.strip(),
                    metric_type=metric_type,
                ))

    def _compute_score(self) -> None:
        """
        _compute_score

        Purpose:
        Aggregates individual score_contribution values into a single
        manipulation_score (0-100).

        Inputs:
        None (reads self.findings)

        Outputs:
        None (sets self._manipulation_score)
        """
        if not self.findings:
            self._manipulation_score = 0.0
            return
        raw = sum(f.score_contribution for f in self.findings)
        self._manipulation_score = min(100.0, raw * 20.0)

    def _build_report(self) -> dict:
        """
        _build_report

        Purpose:
        Transforms internal findings and mutations into a serializable dict.

        Inputs:
        None

        Outputs:
        Dict with findings_per_file, manipulation_score, adversarial_mutations,
        total_findings, total_mutations.
        """
        findings_per_file: dict[str, list[dict]] = {}
        for f in self.findings:
            findings_per_file.setdefault(f.file, []).append({
                "line": f.line,
                "metric_type": f.metric_type,
                "pattern": f.pattern,
                "snippet": f.snippet,
                "score_contribution": f.score_contribution,
            })
        return {
            "findings_per_file": findings_per_file,
            "manipulation_score": round(self._manipulation_score, 2),
            "adversarial_mutations": [
                {
                    "original_file": m.original_file,
                    "original_line": m.original_line,
                    "original_code": m.original_code,
                    "mutated_code": m.mutated_code,
                    "metric_type": m.metric_type,
                }
                for m in self.adversarial_mutations
            ],
            "total_findings": len(self.findings),
            "total_mutations": len(self.adversarial_mutations),
        }


def detect_metric_manipulation(scripts_dir: str | None = None) -> dict:
    """
    detect_metric_manipulation

    Purpose:
    Convenience function that creates a MetricManipulationDetector and runs
    scan_all().

    Inputs:
    scripts_dir — optional override for the scripts directory path

    Outputs:
    Dict containing manipulation analysis results.

    Security:
    Module entry point for F182.
    """
    detector = MetricManipulationDetector(scripts_dir=scripts_dir)
    return detector.scan_all()
