"""
silent_fallback/detector.py

Purpose:
Detects "silent fallbacks" — try/except blocks that catch exceptions without
logging, re-raising, or otherwise reporting the failure. Such blocks silently
swallow errors, making debugging and auditing impossible.

Architectural Role:
Consumed by the Security Invariant Engine (F190) and the Runtime Truth
Monitor (F192) to quantify error-reporting hygiene.

Security Relevance:
Silent fallbacks can hide security-relevant errors (e.g., attestation failures,
verification exceptions) from operators and auditors, creating blind spots.
"""
from __future__ import annotations

import ast
import os
import sys
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# Functions considered as logging/reporting calls for fallback classification.
LOG_FUNCTIONS = {"log", "logging", "warn", "warning", "print", "info", "error", "critical", "debug"}


class Classification(Enum):
    """
    Classification

    Purpose:
    Enumerates the three categories of try/except blocks:
    - SILENT: no logging or re-raise (dangerous)
    - LOGGED: has logging but no re-raise
    - REPORTED: re-raises the exception
    """
    SILENT = "silent"
    LOGGED = "logged"
    REPORTED = "reported"


@dataclass
class SilentFallbackFinding:
    """
    SilentFallbackFinding

    Purpose:
    Records a single silent-fallback finding — the file, line numbers,
    classification, exception type, and whether logging was present.

    Lifecycle:
    Created by _scan_file(); aggregated into the final report.
    """
    file_path: str
    line_number: int
    classification: Classification
    try_line: int
    except_line: int
    exception_type: str | None
    has_logging: bool
    snippet: str = ""


class SilentFallbackDetector:
    """
    SilentFallbackDetector

    Purpose:
    Scans Python files for try/except blocks that catch broad exceptions
    (bare or Exception) without logging or re-raising.

    Lifecycle:
    Created on demand; detect_silent_fallbacks() drives the full scan.
    """
    def __init__(self, scan_root: str):
        self.scan_root = scan_root
        self.findings: list[SilentFallbackFinding] = []

    def detect_silent_fallbacks(self) -> dict[str, Any]:
        """
        detect_silent_fallbacks

        Purpose:
        Main entry point — walks all .py files, scans for silent fallbacks,
        and produces a report with per-file findings and classification stats.

        Inputs:
        None

        Outputs:
        Dict with findings, classification_stats, total_silent,
        total_findings, silent_fallback_score.
        """
        findings = []
        py_files = sorted(
            os.path.join(root, f)
            for root, _dirs, files in os.walk(self.scan_root)
            for f in files
            if f.endswith(".py")
        )
        for file_path in py_files:
            findings.extend(self._scan_file(file_path))

        self.findings = findings
        per_file: dict[str, list[dict]] = {}
        for f in findings:
            per_file.setdefault(f.file_path, []).append({
                "line_number": f.line_number,
                "classification": f.classification.value,
                "try_line": f.try_line,
                "except_line": f.except_line,
                "exception_type": f.exception_type,
                "has_logging": f.has_logging,
                "snippet": f.snippet,
            })

        stats = dict(Counter(f.classification.value for f in findings))
        total_silent = sum(1 for f in findings if f.classification == Classification.SILENT)
        total = len(findings)
        silent_fallback_score = round((total_silent / max(total, 1)) * 100, 2)

        return {
            "findings": per_file,
            "classification_stats": stats,
            "total_silent": total_silent,
            "total_findings": total,
            "silent_fallback_score": silent_fallback_score,
        }

    def _scan_file(self, file_path: str) -> list[SilentFallbackFinding]:
        """
        _scan_file

        Purpose:
        Parses a single .py file and scans for try/except patterns.

        Inputs:
        file_path — absolute path to the .py file

        Outputs:
        List of SilentFallbackFinding for each suspicious handler found.
        """
        findings: list[SilentFallbackFinding] = []
        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                source = f.read()
            tree = ast.parse(source, filename=file_path)
        except (SyntaxError, UnicodeDecodeError, OSError):
            return findings

        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            for handler in node.handlers:
                if not isinstance(handler, ast.ExceptHandler):
                    continue
                self._inspect_handler(file_path, source, node, handler, findings)

        return findings

    def _inspect_handler(
        self,
        file_path: str,
        source: str,
        try_node: ast.Try,
        handler: ast.ExceptHandler,
        findings: list[SilentFallbackFinding],
    ) -> None:
        """
        _inspect_handler

        Purpose:
        Inspects a single ExceptHandler node, extracts exception type,
        checks for logging and re-raise, and appends a finding.

        Inputs:
        file_path — source file path
        source — raw source text
        try_node — parent Try node
        handler — the ExceptHandler node
        findings — list to append results to
        """

        except_type = None
        if handler.type is None:
            except_type = "bare"
        elif isinstance(handler.type, ast.Name):
            except_type = handler.type.id
        elif isinstance(handler.type, ast.Attribute):
            except_type = f"{handler.type.value.id}.{handler.type.attr}"
        elif isinstance(handler.type, ast.Tuple):
            types = []
            for elt in handler.type.elts:
                if isinstance(elt, ast.Name):
                    types.append(elt.id)
                elif isinstance(elt, ast.Attribute):
                    types.append(f"{elt.value.id}.{elt.attr}")
            except_type = "(" + ", ".join(types) + ")"

        if except_type not in ("bare", "Exception") and except_type is not None:
            return

        has_logging = self._handler_has_logging(handler)
        has_raise = self._handler_has_raise(handler)

        if has_raise:
            classification = Classification.REPORTED
        elif has_logging:
            classification = Classification.LOGGED
        else:
            classification = Classification.SILENT

        snippet = self._extract_snippet(source, handler.lineno, handler.end_lineno or handler.lineno)

        findings.append(SilentFallbackFinding(
            file_path=file_path,
            line_number=handler.lineno,
            classification=classification,
            try_line=try_node.lineno,
            except_line=handler.lineno,
            exception_type=except_type,
            has_logging=has_logging,
            snippet=snippet,
        ))

    def _handler_has_logging(self, handler: ast.ExceptHandler) -> bool:
        """
        _handler_has_logging

        Purpose:
        Checks whether a handler body contains any logging function calls.

        Inputs:
        handler — the ExceptHandler AST node

        Outputs:
        True if a logging call is found and no raise statement is present.
        """
        for node in ast.walk(handler):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in LOG_FUNCTIONS:
                    return True
                if isinstance(node.func, ast.Attribute) and node.func.attr in LOG_FUNCTIONS:
                    return True
            if isinstance(node, ast.Raise):
                return False
        return False

    def _handler_has_raise(self, handler: ast.ExceptHandler) -> bool:
        """
        _handler_has_raise

        Purpose:
        Checks whether a handler body contains any raise statement.

        Inputs:
        handler — the ExceptHandler AST node

        Outputs:
        True if a raise is found.
        """
        return any(isinstance(node, ast.Raise) for node in ast.walk(handler))

    def _extract_snippet(self, source: str, start: int, end: int) -> str:
        """
        _extract_snippet

        Purpose:
        Extracts a code snippet from the source spanning the given line range.

        Inputs:
        source — raw source text
        start — start line (1-indexed)
        end — end line (1-indexed)

        Outputs:
        String of the extracted lines joined by newlines.
        """
        lines = source.splitlines()
        return "\n".join(lines[max(0, start - 1):end])
