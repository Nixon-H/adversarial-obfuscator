"""
knowledge_base/database.py

Purpose:
Builds a security knowledge base by scanning six knowledge sources:
assumptions (scripts/assumptions/), failure patterns (tests/), fix history
(git log), attack discoveries (attack_report.md), verification history
(build/ reports), and regression data (regression_report.md).

Architectural Role:
Central repository for all security-relevant knowledge discovered during
meta-assurance. Consumed by the self-critique engine (F200) and the release
confidence scorer (F197).

Security Relevance:
A comprehensive knowledge base enables evidence-based security assessments.
Missing categories indicate knowledge gaps that could lead to blind spots.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field, asdict
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class KnowledgeEntry:
    """
    KnowledgeEntry

    Purpose:
    Stores a single piece of security knowledge — an assumption, failure
    pattern, fix record, attack discovery, verification report, or regression
    result.

    Lifecycle:
    Created by the various scan_* methods; aggregated in to_dict().
    """
    entry_id: str
    category: str
    title: str
    description: str
    source: str
    timestamp: str
    tags: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SecurityKnowledgeBase:
    """
    SecurityKnowledgeBase

    Purpose:
    Scans six knowledge sources and consolidates findings into a structured,
    queryable knowledge base.

    Lifecycle:
    Created on demand; build() runs all scans; to_dict() returns results.
    """
    def __init__(self, root: str = "") -> None:
        self.root = root or _ROOT
        self.entries: list[KnowledgeEntry] = []
        self._counter: int = 0

    def scan_assumptions(self) -> None:
        """
        scan_assumptions

        Purpose:
        Scans scripts/assumptions/ for Assumption() declarations and adds
        them as knowledge entries.

        Inputs:
        None

        Outputs:
        None (appends to self.entries)
        """
        assumptions_dir = os.path.join(self.root, "scripts", "assumptions")
        if not os.path.isdir(assumptions_dir):
            return
        for root_dir, _dirs, files in os.walk(assumptions_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root_dir, fname)
                try:
                    with open(fpath, "r") as f:
                        content = f.read()
                except OSError:
                    continue
                matches = re.findall(
                    r'Assumption\("([^"]+)",\s*"([^"]+)"', content
                )
                for feature, assumption in matches:
                    self._counter += 1
                    self.entries.append(
                        KnowledgeEntry(
                            entry_id=f"KB-{self._counter:04d}",
                            category="assumption",
                            title=f"Assumption: {feature} needs {assumption}",
                            description=f"Feature {feature} requires {assumption}",
                            source=os.path.relpath(fpath, self.root),
                            timestamp=time.strftime(
                                "%Y-%m-%dT%H:%M:%S", time.gmtime()
                            ),
                            tags=[feature, assumption],
                        )
                    )

    def scan_failures(self) -> None:
        """
        scan_failures

        Purpose:
        Scans test files for failure/error/exception keywords and adds
        entries for files containing such patterns.

        Inputs:
        None

        Outputs:
        None (appends to self.entries)
        """
        tests_dir = os.path.join(self.root, "tests")
        if not os.path.isdir(tests_dir):
            return
        for root_dir, _dirs, files in os.walk(tests_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root_dir, fname)
                try:
                    with open(fpath, "r") as f:
                        cont = f.read()
                except OSError:
                    continue
                fail_matches = list(
                    re.finditer(r"(fail|error|exception)", cont, re.IGNORECASE)
                )
                if not fail_matches:
                    continue
                self._counter += 1
                self.entries.append(
                    KnowledgeEntry(
                        entry_id=f"KB-{self._counter:04d}",
                        category="failure_pattern",
                        title=f"Failure patterns in {fname}",
                        description=f"Found {len(fail_matches)} failure/error/exception references",
                        source=os.path.relpath(fpath, self.root),
                        timestamp=time.strftime(
                            "%Y-%m-%dT%H:%M:%S", time.gmtime()
                        ),
                        tags=["failure", fname.replace(".py", "")],
                    )
                )

    def scan_fixes(self) -> None:
        """
        scan_fixes

        Purpose:
        Runs git log to find fix-related commits and adds them as knowledge
        entries with evidence from commit messages.

        Inputs:
        None

        Outputs:
        None (appends to self.entries)
        """
        git_dir = os.path.join(self.root, ".git")
        if not os.path.isdir(git_dir):
            return
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--oneline",
                    "--grep=fix",
                    "--grep=Fix",
                    "--grep=FIX",
                    "--all-match",
                    "-50",
                ],
                capture_output=True,
                text=True,
                cwd=self.root,
                timeout=30,
            )
            if result.returncode != 0:
                return
            lines = [l for l in result.stdout.strip().split("\n") if l]
            if not lines:
                return
            self._counter += 1
            self.entries.append(
                KnowledgeEntry(
                    entry_id=f"KB-{self._counter:04d}",
                    category="fix",
                    title=f"Git history: {len(lines)} fix-related commits",
                    description=f"Found {len(lines)} commits matching 'fix' pattern",
                    source="git log",
                    timestamp=time.strftime(
                        "%Y-%m-%dT%H:%M:%S", time.gmtime()
                    ),
                    tags=["fix", "git"],
                    evidence=lines[:10],
                )
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

    def scan_attack_discoveries(self) -> None:
        """
        scan_attack_discoveries

        Purpose:
        Parses the attack report for feature sections and adds entries for
        each discovered attack.

        Inputs:
        None

        Outputs:
        None (appends to self.entries)
        """
        report_path = os.path.join(self.root, "attack_report.md")
        if not os.path.isfile(report_path):
            return
        with open(report_path, "r") as f:
            content = f.read()
        feature_sections = re.findall(r"##\s+(F\d+):\s+(.+?)\n", content)
        for feature_id, feature_name in feature_sections:
            self._counter += 1
            self.entries.append(
                KnowledgeEntry(
                    entry_id=f"KB-{self._counter:04d}",
                    category="attack_discovery",
                    title=f"Attack on {feature_id}: {feature_name.strip()}",
                    description=f"Red team assessment identified attacks on {feature_id}",
                    source=os.path.basename(report_path),
                    timestamp=time.strftime(
                        "%Y-%m-%dT%H:%M:%S", time.gmtime()
                    ),
                    tags=[feature_id, "attack", "redteam"],
                )
            )

    def scan_verification_history(self) -> None:
        """
        scan_verification_history

        Purpose:
        Scans the build/ directory for verification report JSON files and
        adds entries for each found report.

        Inputs:
        None

        Outputs:
        None (appends to self.entries)
        """
        build_dir = os.path.join(self.root, "build")
        if not os.path.isdir(build_dir):
            return
        report_files = [
            "proof_coverage_report.json",
            "proof_soundness_report.json",
            "evidence_report.json",
            "security_gate_report.json",
            "confidence_interval_report.json",
        ]
        for rf in report_files:
            rpath = os.path.join(build_dir, rf)
            if not os.path.isfile(rpath):
                continue
            try:
                with open(rpath) as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            self._counter += 1
            self.entries.append(
                KnowledgeEntry(
                    entry_id=f"KB-{self._counter:04d}",
                    category="verification_history",
                    title=f"Verification report: {rf}",
                    description=f"Loaded {rf} with {len(data)} top-level keys",
                    source=rf,
                    timestamp=time.strftime(
                        "%Y-%m-%dT%H:%M:%S", time.gmtime()
                    ),
                    tags=["verification", rf.replace(".json", "")],
                )
            )

    def scan_regressions(self) -> None:
        """
        scan_regressions

        Purpose:
        Parses the regression report for pass/fail counts and adds an entry.

        Inputs:
        None

        Outputs:
        None (appends to self.entries)
        """
        regression_path = os.path.join(self.root, "build", "regression_report.md")
        if not os.path.isfile(regression_path):
            return
        with open(regression_path) as f:
            content = f.read()
        passes = len(re.findall(r"✅ PASS", content))
        fails = len(re.findall(r"❌ FAIL|❌ MISSING", content))
        if passes or fails:
            self._counter += 1
            self.entries.append(
                KnowledgeEntry(
                    entry_id=f"KB-{self._counter:04d}",
                    category="regression",
                    title=f"Regression scan: {passes} pass, {fails} fail",
                    description=f"Regression report shows {passes} passing and {fails} failing checks",
                    source="build/regression_report.md",
                    timestamp=time.strftime(
                        "%Y-%m-%dT%H:%M:%S", time.gmtime()
                    ),
                    tags=["regression", "baseline"],
                )
            )

    def build(self) -> None:
        """
        build

        Purpose:
        Runs all six knowledge scans in sequence: assumptions, failures,
        fixes, attack discoveries, verification history, regressions.

        Inputs:
        None

        Outputs:
        None (populates self.entries)
        """
        self.scan_assumptions()
        self.scan_failures()
        self.scan_fixes()
        self.scan_attack_discoveries()
        self.scan_verification_history()
        self.scan_regressions()

    def by_category(self) -> dict[str, list[KnowledgeEntry]]:
        """
        by_category

        Purpose:
        Groups knowledge entries by their category.

        Inputs:
        None

        Outputs:
        Dict mapping category -> list of KnowledgeEntry.
        """
        cats: dict[str, list[KnowledgeEntry]] = {}
        for e in self.entries:
            cats.setdefault(e.category, []).append(e)
        return cats

    def knowledge_coverage(self) -> dict[str, Any]:
        """
        knowledge_coverage

        Purpose:
        Computes what percentage of expected knowledge categories have at
        least one entry.

        Inputs:
        None

        Outputs:
        Dict with covered_categories, total_categories, coverage_pct.
        """
        cats = self.by_category()
        expected_categories = [
            "assumption",
            "failure_pattern",
            "fix",
            "attack_discovery",
            "verification_history",
            "regression",
        ]
        covered = sum(1 for c in expected_categories if c in cats)
        return {
            "covered_categories": covered,
            "total_categories": len(expected_categories),
            "coverage_pct": round(covered / len(expected_categories) * 100, 1),
        }

    def to_dict(self) -> dict[str, Any]:
        """
        to_dict

        Purpose:
        Serializes the full knowledge base to a plain dict.

        Inputs:
        None

        Outputs:
        Dict with entries, total_entries, by_category, knowledge_coverage.
        """
        return {
            "entries": [e.to_dict() for e in self.entries],
            "total_entries": len(self.entries),
            "by_category": {
                k: len(v) for k, v in self.by_category().items()
            },
            "knowledge_coverage": self.knowledge_coverage(),
        }


def build_knowledge_base(root: str = "") -> dict:
    """
    build_knowledge_base

    Purpose:
    Convenience function that creates a SecurityKnowledgeBase and runs
    the full build pipeline.

    Inputs:
    root — optional root directory override

    Outputs:
    Dict with entries, total_entries, by_category, knowledge_coverage.

    Security:
    Module entry point for F199.
    """
    kb = SecurityKnowledgeBase(root)
    kb.build()
    return {
        "entries": [e.to_dict() for e in kb.entries],
        "total_entries": len(kb.entries),
        "by_category": {k: len(v) for k, v in kb.by_category().items()},
        "knowledge_coverage": kb.knowledge_coverage(),
    }
