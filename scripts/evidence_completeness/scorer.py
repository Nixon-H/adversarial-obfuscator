"""
evidence_completeness/scorer.py

Purpose:
Evaluates the completeness of evidence backing security claims found in the
codebase. For each claim (detected via keyword matching), the scorer checks
for corresponding source implementation, tests, benchmarks, runtime traces,
and audit reports.

Architectural Role:
Produced by the meta-assurance pipeline. Its output feeds the release
confidence scorer (F197) and the self-critique engine (F200).

Security Relevance:
Claims without complete evidence chains (source + test + trace + audit) are
untrustworthy. This scorer quantifies the gap.
"""
from __future__ import annotations

import json  # noqa: F401 (this line binds a name used by an embedded template)
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

# Keywords that indicate a strong security claim requiring evidence backing.
CLAIM_PATTERNS = [
    "unbreakable",
    "provably",
    "secure",
    "tamper-proof",
    "tamperproof",
    "impossible",
    "guaranteed",
    "unconditionally",
    "perfect",
    "absolutely",
    "invulnerable",
    "unhackable",
    "incapable",
    "cannot be broken",
    "cannot be reversed",
]

# Precompiled claim matchers — compiled once at import time instead of
# calling re.search(re.escape(...)) per pattern per line during scans.
_CLAIM_REGEXES = [re.compile(re.escape(p)) for p in CLAIM_PATTERNS]

# Files larger than this are skipped during scans. Generated artifacts such
# as archive/artifacts/invariant_engine_report.json (~81MB, ~1.9M lines)
# otherwise make full-repo scans hang.
_MAX_SCAN_FILE_BYTES = 5 * 1024 * 1024


def _is_too_large(file_path: str) -> bool:
    """Return True if a file should be skipped for being oversized."""
    try:
        return os.path.getsize(file_path) > _MAX_SCAN_FILE_BYTES
    except OSError:
        return True


@dataclass
class ClaimEvidence:
    """
    ClaimEvidence

    Purpose:
    Stores the evidence chain for a single security claim — whether it has
    source implementation, tests, benchmarks, traces, and audit reports.

    Lifecycle:
    Created by compute_evidence_completeness() for each unique claim found.

    Security:
    The score property (0-100) quantifies how well a claim is backed.
    """
    claim_text: str
    source_file: str
    line_number: int
    source_exists: bool = False
    test_exists: bool = False
    benchmark_exists: bool = False
    trace_exists: bool = False
    audit_exists: bool = False
    source_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    benchmark_files: list[str] = field(default_factory=list)
    trace_files: list[str] = field(default_factory=list)
    audit_files: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        numerator = sum([self.source_exists, self.test_exists, self.benchmark_exists, self.trace_exists, self.audit_exists])
        return numerator / 5.0 * 100

    @property
    def missing_links(self) -> list[str]:
        missing = []
        if not self.source_exists:
            missing.append("source_implementation")
        if not self.test_exists:
            missing.append("tests")
        if not self.benchmark_exists:
            missing.append("benchmarks")
        if not self.trace_exists:
            missing.append("runtime_traces")
        if not self.audit_exists:
            missing.append("audit_report")
        return missing


class EvidenceCompletenessScorer:
    """
    EvidenceCompletenessScorer

    Purpose:
    Scans the entire codebase for security claims and evaluates the evidence
    chain supporting each one.

    Lifecycle:
    Created on demand; compute_evidence_completeness() drives the full scan.

    Security:
    Quantifies the gap between claims and their supporting evidence, enabling
    targeted remediation.
    """
    def __init__(self, root_dir: str | None = None):
        self.root_dir = root_dir or _ROOT
        self.claims: list[ClaimEvidence] = []

    def _scan_file_for_claims(self, file_path: str) -> list[tuple[int, str]]:
        """
        _scan_file_for_claims

        Purpose:
        Scans a single file for lines containing any of the CLAIM_PATTERNS keywords.

        Inputs:
        file_path — absolute path to the file

        Outputs:
        List of (line_number, text) tuples for each match.
        """
        matches = []
        if _is_too_large(file_path):
            return matches
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    line_lower = line.lower()
                    for rx in _CLAIM_REGEXES:
                        if rx.search(line_lower):
                            matches.append((i, line.strip()[:150]))
                            break
        except (UnicodeDecodeError, OSError):
            pass
        return matches

    def _skip_dir(self, dir_name: str) -> bool:
        """
        _skip_dir

        Purpose:
        Determines whether a directory should be skipped during recursive walks.

        Inputs:
        dir_name — name of the directory

        Outputs:
        True if the directory should be skipped.
        """
        skip = {".git", ".svn", "__pycache__", "node_modules", ".venv", "venv", ".tox", ".pytest_cache", ".eggs", "eggs", "dist", "build", "relay", ".agents", ".claude", "archive", "target", ".mypy_cache", ".pytest_cache", "fixtures", "test_data"}
        return dir_name in skip or dir_name.startswith(".")

    def _scan_directory_for_claims(self) -> list[tuple[str, int, str]]:
        """
        _scan_directory_for_claims

        Purpose:
        Walks the entire root directory scanning all source, config, and
        documentation files for claim keywords.

        Inputs:
        None

        Outputs:
        List of (relative_path, line_number, text) tuples.
        """
        claims_found = []
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if not self._skip_dir(d)]
            for f in files:
                if f.endswith((".py", ".rs", ".c", ".h", ".md", ".txt", ".json")):
                    file_path = os.path.join(root, f)
                    rel_path = os.path.relpath(file_path, self.root_dir)
                    for lineno, text in self._scan_file_for_claims(file_path):
                        claims_found.append((rel_path, lineno, text))
        return claims_found

    def _check_source_exists(self, claim_text: str) -> tuple[bool, list[str]]:
        """
        _check_source_exists

        Purpose:
        Searches for implementation files containing both the claim text and
        implementation keywords (def, class, impl, fn, etc.).

        Inputs:
        claim_text — the claim string to search for

        Outputs:
        Tuple of (exists, list_of_matching_file_paths).
        """
        impl_keywords = ["def ", "class ", "impl ", "fn ", "void ", "int ", "function "]
        files_found = []
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if not self._skip_dir(d)]
            for f in files:
                if f.endswith((".py", ".rs", ".c", ".h")):
                    file_path = os.path.join(root, f)
                    if _is_too_large(file_path):
                        continue
                    try:
                        with open(file_path, encoding="utf-8", errors="ignore") as fh:
                            content = fh.read()
                        if claim_text.lower() in content.lower():
                            for kw in impl_keywords:
                                if kw in content:
                                    files_found.append(os.path.relpath(file_path, self.root_dir))
                                    break
                    except (UnicodeDecodeError, OSError):
                        pass
        return len(files_found) > 0, files_found[:5]

    def _check_test_exists(self, claim_keywords: list[str]) -> tuple[bool, list[str]]:
        """
        _check_test_exists

        Purpose:
        Searches test files for references to the claim's keywords.

        Inputs:
        claim_keywords — list of relevant keywords from the claim

        Outputs:
        Tuple of (exists, list_of_matching_test_files).
        """
        test_dir = os.path.join(self.root_dir, "tests")
        if not os.path.isdir(test_dir):
            return False, []
        test_files = []
        for f in os.listdir(test_dir):
            if f.startswith("test_") and f.endswith(".py"):
                file_path = os.path.join(test_dir, f)
                try:
                    with open(file_path, encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                    for kw in claim_keywords:
                        if kw.lower() in content.lower():
                            test_files.append(f"tests/{f}")
                            break
                except (UnicodeDecodeError, OSError):
                    pass
        return len(test_files) > 0, test_files[:5]

    def _check_benchmark_exists(self, claim_keywords: list[str]) -> tuple[bool, list[str]]:
        """
        _check_benchmark_exists

        Purpose:
        Searches benchmark files for references to the claim's keywords.

        Inputs:
        claim_keywords — list of relevant keywords from the claim

        Outputs:
        Tuple of (exists, list_of_matching_benchmark_files).
        """
        test_dir = os.path.join(self.root_dir, "tests")
        if not os.path.isdir(test_dir):
            return False, []
        bench_files = []
        for f in os.listdir(test_dir):
            if f.startswith("bench_") and f.endswith(".py"):
                file_path = os.path.join(test_dir, f)
                try:
                    with open(file_path, encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                    for kw in claim_keywords:
                        if kw.lower() in content.lower():
                            bench_files.append(f"tests/{f}")
                            break
                except (UnicodeDecodeError, OSError):
                    pass
        return len(bench_files) > 0, bench_files[:5]

    def _check_trace_exists(self, claim_keywords: list[str]) -> tuple[bool, list[str]]:
        """
        _check_trace_exists

        Purpose:
        Searches for runtime trace files (.prof, .trace, .log, .csv, .json)
        that reference the claim's keywords.

        Inputs:
        claim_keywords — list of relevant keywords from the claim

        Outputs:
        Tuple of (exists, list_of_matching_trace_files).
        """
        trace_files = []
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if not self._skip_dir(d)]
            for f in files:
                if f.endswith((".prof", ".trace", ".log", ".csv", ".json")):
                    file_path = os.path.join(root, f)
                    if _is_too_large(file_path):
                        continue
                    try:
                        with open(file_path, encoding="utf-8", errors="ignore") as fh:
                            content = fh.read()
                        for kw in claim_keywords:
                            if kw.lower() in content.lower():
                                trace_files.append(os.path.relpath(file_path, self.root_dir))
                                break
                    except (UnicodeDecodeError, OSError):
                        pass
        return len(trace_files) > 0, trace_files[:5]

    def _check_audit_exists(self, claim_text: str) -> tuple[bool, list[str]]:
        """
        _check_audit_exists

        Purpose:
        Searches for audit report files containing the claim text.

        Inputs:
        claim_text — the claim string to search for

        Outputs:
        Tuple of (exists, list_of_matching_audit_files).
        """
        audit_files = []
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if not self._skip_dir(d)]
            for f in files:
                if "audit" in f.lower() or "audit" in root.lower():
                    file_path = os.path.join(root, f)
                    if _is_too_large(file_path):
                        continue
                    try:
                        with open(file_path, encoding="utf-8", errors="ignore") as fh:
                            content = fh.read()
                        if claim_text.lower() in content.lower():
                            audit_files.append(os.path.relpath(file_path, self.root_dir))
                            break
                    except (UnicodeDecodeError, OSError):
                        pass
        return len(audit_files) > 0, audit_files[:5]

    def _get_keywords(self, claim_text: str) -> list[str]:
        """
        _get_keywords

        Purpose:
        Extracts up to 5 significant alphanumeric words from a claim text
        (length > 2) for use in keyword-based file matching.

        Inputs:
        claim_text — the claim string

        Outputs:
        List of keyword strings.
        """
        words = re.findall(r"[a-zA-Z_]\w*", claim_text)
        return [w for w in words if len(w) > 2][:5]

    def compute_evidence_completeness(self) -> dict[str, Any]:
        """
        compute_evidence_completeness

        Purpose:
        Main entry point — scans all files for claims, then for each unique
        claim checks all five evidence categories and computes scores.

        Inputs:
        None

        Outputs:
        Dict with per_claim_results, overall_score, missing_links,
        total_claims.
        """
        raw_claims = self._scan_directory_for_claims()

        scripts_dir = os.path.join(self.root_dir, "scripts")
        tests_dir = os.path.join(self.root_dir, "tests")
        build_dir = os.path.join(self.root_dir, "build")

        all_py_files = []
        if os.path.isdir(scripts_dir):
            for root, dirs, files in os.walk(scripts_dir):
                dirs[:] = [d for d in dirs if not self._skip_dir(d)]
                for f in files:
                    if f.endswith(".py"):
                        all_py_files.append(os.path.join(root, f))

        all_test_files = []
        all_bench_files = []
        if os.path.isdir(tests_dir):
            for f in os.listdir(tests_dir):
                if f.startswith("test_") and f.endswith(".py"):
                    all_test_files.append(os.path.join(tests_dir, f))
                elif f.startswith("bench_") and f.endswith(".py"):
                    all_bench_files.append(os.path.join(tests_dir, f))

        all_trace_files = []
        if os.path.isdir(build_dir):
            for root, dirs, files in os.walk(build_dir):
                dirs[:] = [d for d in dirs if not self._skip_dir(d)]
                for f in files:
                    if f.endswith((".json", ".log", ".txt", ".md")):
                        all_trace_files.append(os.path.join(root, f))

        all_audit_files = []
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if not self._skip_dir(d)]
            for f in files:
                if "audit" in f.lower() or "audit" in root.lower():
                    all_audit_files.append(os.path.join(root, f))

        test_contents = {}
        for tf in all_test_files:
            try:
                with open(tf, encoding="utf-8", errors="ignore") as fh:
                    test_contents[tf] = fh.read()
            except OSError:
                pass

        bench_contents = {}
        for bf in all_bench_files:
            try:
                with open(bf, encoding="utf-8", errors="ignore") as fh:
                    bench_contents[bf] = fh.read()
            except OSError:
                pass

        trace_contents = {}
        for trf in all_trace_files:
            try:
                with open(trf, encoding="utf-8", errors="ignore") as fh:
                    trace_contents[trf] = fh.read()
            except OSError:
                pass

        audit_contents = {}
        for af in all_audit_files:
            try:
                with open(af, encoding="utf-8", errors="ignore") as fh:
                    audit_contents[af] = fh.read()
            except OSError:
                pass

        source_contents = {}
        for sf in all_py_files:
            try:
                with open(sf, encoding="utf-8", errors="ignore") as fh:
                    source_contents[sf] = fh.read()
            except OSError:
                pass

        seen_claims = set()
        for file_path, lineno, text in raw_claims:
            if text in seen_claims:
                continue
            seen_claims.add(text)
            keywords = self._get_keywords(text)

            src_files = []
            for sf, sc in source_contents.items():
                if text.lower() in sc.lower():
                    for kw in ["def ", "class ", "impl ", "fn ", "function "]:
                        if kw in sc:
                            src_files.append(os.path.relpath(sf, self.root_dir))
                            break

            if not keywords:
                logger.warning("Claim '%s' produced no keywords — falling back to raw claim text for matching (may inflate scores)", text[:80])

            test_files = []
            for tf, tc in test_contents.items():
                for kw in keywords or [text]:
                    if kw.lower() in tc.lower():
                        test_files.append(os.path.relpath(tf, self.root_dir))
                        break

            bench_files = []
            for bf, bc in bench_contents.items():
                for kw in keywords or [text]:
                    if kw.lower() in bc.lower():
                        bench_files.append(os.path.relpath(bf, self.root_dir))
                        break

            trace_files = []
            for trf, trc in trace_contents.items():
                for kw in keywords or [text]:
                    if kw.lower() in trc.lower():
                        trace_files.append(os.path.relpath(trf, self.root_dir))
                        break

            audit_files = []
            for af, ac in audit_contents.items():
                if text.lower() in ac.lower():
                    audit_files.append(os.path.relpath(af, self.root_dir))
                    break

            evidence = ClaimEvidence(
                claim_text=text,
                source_file=file_path,
                line_number=lineno,
                source_exists=len(src_files) > 0,
                test_exists=len(test_files) > 0,
                benchmark_exists=len(bench_files) > 0,
                trace_exists=len(trace_files) > 0,
                audit_exists=len(audit_files) > 0,
                source_files=src_files[:5],
                test_files=test_files[:5],
                benchmark_files=bench_files[:5],
                trace_files=trace_files[:5],
                audit_files=audit_files[:5],
            )
            self.claims.append(evidence)

        total_scores = sum(c.score for c in self.claims)
        if not self.claims:
            logger.warning("No claims found — returning overall_score=0.0 (fail-closed: no evidence, no confidence).")
        # Fail-closed: an empty claim set previously scored a perfect
        # 100.0, certifying "complete evidence" for nothing audited.
        overall_score = total_scores / len(self.claims) if self.claims else 0.0

        all_missing = {}
        for c in self.claims:
            missing = c.missing_links
            if missing:
                key = f"{c.source_file}:{c.line_number}"
                all_missing[key] = {
                    "claim": c.claim_text,
                    "missing": missing,
                    "score": round(c.score, 1),
                }

        return {
            "per_claim_results": [
                {
                    "claim_text": c.claim_text,
                    "source_file": c.source_file,
                    "line_number": c.line_number,
                    "score": round(c.score, 1),
                    "source_exists": c.source_exists,
                    "test_exists": c.test_exists,
                    "benchmark_exists": c.benchmark_exists,
                    "trace_exists": c.trace_exists,
                    "audit_exists": c.audit_exists,
                    "source_files": c.source_files,
                    "test_files": c.test_files,
                    "benchmark_files": c.benchmark_files,
                    "trace_files": c.trace_files,
                    "audit_files": c.audit_files,
                    "missing_links": c.missing_links,
                }
                for c in self.claims
            ],
            "overall_score": round(overall_score, 1),
            "missing_links": all_missing,
            "total_claims": len(self.claims),
        }
