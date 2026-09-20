"""
attack_corpus/corpus.py

Purpose:
Builds a corpus of known attack vectors by scanning the codebase for attack
patterns (bypass, deobfuscation, proof failure, replay, symbolic failure),
identifying attack-related test files, and parsing an external attack report.

Architectural Role:
Consumed by the release confidence scorer (F197) and the formal threat
coverage mapper (F198) to quantify attack coverage and severity distribution.

Security Relevance:
An up-to-date attack corpus is essential for understanding which attack
vectors are covered by existing protections and which remain unaddressed.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class CorpusEntry:
    """
    CorpusEntry

    Purpose:
    Represents a single attack vector in the corpus with its ID, category,
    severity, affected features, and reproduction steps.

    Lifecycle:
    Created by scan_codebase(), scan_test_files(), or scan_attack_report().
    """
    attack_id: str
    category: str
    description: str
    severity: str
    affected_features: list[str] = field(default_factory=list)
    reproduction_steps: list[str] = field(default_factory=list)
    file_path: str = ""
    line_number: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Directories to skip during codebase scanning.
_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox", ".pytest_cache", ".eggs", "eggs", "dist", "relay", ".agents", ".claude"}

class AttackCorpus:
    """
    AttackCorpus

    Purpose:
    Builds and manages a corpus of attack vectors discovered by scanning
    the codebase, test files, and the attack report.

    Lifecycle:
    Created on demand; scanned via scan_codebase(), scan_test_files(),
    scan_attack_report(). Results serialized via to_dict().
    """
    def __init__(self) -> None:
        self.entries: list[CorpusEntry] = []
        self._entry_counter: int = 0

    def _should_skip(self, dir_name: str) -> bool:
        """
        _should_skip

        Purpose:
        Determines whether a directory should be skipped during scanning.

        Inputs:
        dir_name — name of the directory

        Outputs:
        True if the directory should be skipped.
        """
        return dir_name in _SKIP_DIRS or dir_name.startswith(".")

    def scan_codebase(self, root: str = "") -> None:
        """
        scan_codebase

        Purpose:
        Scans the codebase for attack patterns (bypass, deobfuscation, proof
        failure, replay, symbolic failure) and creates corpus entries.

        Inputs:
        root — optional root directory override

        Outputs:
        None (appends to self.entries)
        """
        root = root or _ROOT
        categories = [
            ("bypass", r"bypass|evade|circumvent", "Bypass"),
            ("deobfuscation", r"deobfuscat|unpack|decompress", "Deobfuscation"),
            ("proof_failure", r"proof.*fail|soundness.*violat", "Proof Failure"),
            ("replay", r"replay|capture.*attack", "Replay Attack"),
            ("symbolic_failure", r"symbolic.*fail|z3.*fail", "Symbolic Failure"),
        ]

        for root_dir, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if not self._should_skip(d)]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root_dir, fname)
                matched_cats = set()
                try:
                    with open(fpath, "r", errors="ignore") as f:
                        lines = f.readlines()
                except (OSError, UnicodeDecodeError):
                    continue
                for i, line in enumerate(lines, 1):
                    line_lower = line.lower()
                    for cat_key, pattern, cat_label in categories:
                        if cat_label in matched_cats:
                            continue
                        if re.search(pattern, line_lower):
                            matched_cats.add(cat_label)
                            self._entry_counter += 1
                            attack_id = f"AC-{self._entry_counter:04d}"
                            rel = os.path.relpath(fpath, root)
                            entry = CorpusEntry(
                                attack_id=attack_id,
                                category=cat_label,
                                description=f"Found '{cat_key}' pattern in {rel}",
                                severity=self._infer_severity(cat_key, line),
                                file_path=rel,
                                line_number=i,
                                reproduction_steps=[
                                    f"Review {rel}:{i}",
                                ],
                            )
                            self.entries.append(entry)

    def scan_test_files(self, root: str = "") -> None:
        """
        scan_test_files

        Purpose:
        Scans the tests/ directory for files containing attack-related keywords
        (adversarial, attack, bypass, soundness, replay).

        Inputs:
        root — optional root directory override

        Outputs:
        None (appends to self.entries)
        """
        root = root or _ROOT
        test_root = os.path.join(root, "tests")
        if not os.path.isdir(test_root):
            return
        attack_patterns = [
            ("adversarial", r"adversarial", "Adversarial Test"),
            ("attack", r"attack", "Attack Test"),
            ("bypass", r"bypass|evade", "Bypass Test"),
            ("soundness", r"soundness|proof.*attack", "Soundness Test"),
            ("replay", r"replay", "Replay Test"),
        ]
        for root_dir, dirs, files in os.walk(test_root):
            dirs[:] = [d for d in dirs if not self._should_skip(d)]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root_dir, fname)
                try:
                    with open(fpath, "r", errors="ignore") as f:
                        content = f.read()
                except OSError:
                    continue
                matched = set()
                for cat_key, pattern, cat_label in attack_patterns:
                    if cat_label in matched:
                        continue
                    if re.search(pattern, content, re.IGNORECASE):
                        matched.add(cat_label)
                        self._entry_counter += 1
                        attack_id = f"AC-{self._entry_counter:04d}"
                        rel = os.path.relpath(fpath, root)
                        entry = CorpusEntry(
                            attack_id=attack_id,
                            category=cat_label,
                            description=f"Attack-related test in {rel}",
                            severity="medium",
                            file_path=rel,
                            reproduction_steps=[
                                f"Run tests in {rel}",
                            ],
                        )
                        self.entries.append(entry)

    def scan_attack_report(self, report_path: str = "") -> None:
        """
        scan_attack_report

        Purpose:
        Parses the attack report markdown (attack_report.md) and creates
        corpus entries for each attack type found under each feature section.

        Inputs:
        report_path — optional path to the attack report

        Outputs:
        None (appends to self.entries)
        """
        if not report_path:
            report_path = os.path.join(_ROOT, "attack_report.md")
        if not os.path.isfile(report_path):
            return
        with open(report_path, "r") as f:
            content = f.read()

        feature_pattern = re.compile(r"##\s+(F\d+):\s+(.+)")
        severity_pattern = re.compile(r"\*\*(HIGH|CRITICAL|MEDIUM|LOW)\*\*")
        attack_pattern = re.compile(r"\*\*(BYPASS|TAMPER|CONFUSE|MISCONFIGURE)")
        fix_pattern = re.compile(r"\*\*Fix:\*\*\s*(.+)")

        current_feature: str = ""
        current_title: str = ""
        for line in content.split("\n"):
            fm = feature_pattern.search(line)
            if fm:
                current_feature = fm.group(1)
                current_title = fm.group(2).strip()
                continue
            am = attack_pattern.search(line)
            sm = severity_pattern.search(line)
            if am:
                self._entry_counter += 1
                attack_id = f"AC-{self._entry_counter:04d}"
                cat_label = am.group(1).capitalize() + " Attack"
                sev = sm.group(1) if sm else "unknown"
                entry = CorpusEntry(
                    attack_id=attack_id,
                    category=cat_label,
                    description=f"{am.group(1)} on {current_feature}: {current_title}",
                    severity=sev.lower(),
                    affected_features=[current_feature],
                    file_path=os.path.basename(report_path),
                    reproduction_steps=[
                        f"Review {current_feature} in attack_report.md",
                        f"Attack type: {am.group(1)}",
                    ],
                )
                self.entries.append(entry)

    def _infer_severity(self, category: str, line: str) -> str:
        """
        _infer_severity

        Purpose:
        Infers severity from a line of code using keyword matching.

        Inputs:
        category — attack category
        line — the source line

        Outputs:
        Severity string: critical, high, medium, or low.
        """
        sev_keywords = {
            "critical": r"critical|severe|vulnerab",
            "high": r"high|major|danger",
            "medium": r"medium|moderate",
            "low": r"low|minor|info",
        }
        for sev, pat in sev_keywords.items():
            if re.search(pat, line, re.IGNORECASE):
                return sev
        return "medium"

    def classify_entries(self) -> dict[str, list[CorpusEntry]]:
        """
        classify_entries

        Purpose:
        Groups corpus entries by category.

        Inputs:
        None

        Outputs:
        Dict mapping category -> list of CorpusEntry.
        """
        categories: dict[str, list[CorpusEntry]] = {}
        for e in self.entries:
            categories.setdefault(e.category, []).append(e)
        return categories

    def severity_distribution(self) -> dict[str, int]:
        """
        severity_distribution

        Purpose:
        Computes the severity distribution across all corpus entries.

        Inputs:
        None

        Outputs:
        Dict mapping severity level -> count.
        """
        dist: dict[str, int] = {}
        for e in self.entries:
            dist[e.severity] = dist.get(e.severity, 0) + 1
        return dist

    def to_dict(self) -> dict[str, Any]:
        """
        to_dict

        Purpose:
        Serializes the corpus to a plain dict for JSON output.

        Inputs:
        None

        Outputs:
        Dict with total_attacks, categories, severity_distribution, entries.
        """
        return {
            "total_attacks": len(self.entries),
            "categories": {k: len(v) for k, v in self.classify_entries().items()},
            "severity_distribution": self.severity_distribution(),
            "entries": [e.to_dict() for e in self.entries],
        }


def build_attack_corpus(root: str = "") -> dict:
    """
    build_attack_corpus

    Purpose:
    Convenience function that builds a full attack corpus by scanning the
    codebase, test files, and the attack report.

    Inputs:
    root — optional root directory override

    Outputs:
    Dict with corpus entries, categories, total_attacks, severity_distribution.

    Security:
    Module entry point for F196.
    """
    corpus = AttackCorpus()
    corpus.scan_codebase(root)
    corpus.scan_test_files(root)
    corpus.scan_attack_report()
    return {
        "corpus_entries": len(corpus.entries),
        "categories": {k: len(v) for k, v in corpus.classify_entries().items()},
        "total_attacks": len(corpus.entries),
        "severity_distribution": corpus.severity_distribution(),
        "entries": [e.to_dict() for e in corpus.entries],
    }
