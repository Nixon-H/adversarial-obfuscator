"""
invariant_engine/engine.py

Purpose:
Enforces security invariants across the codebase. Checks include:
- No feature is unreachable (every phase function called from build.py)
- No tautological proof (verify functions unconditionally returning True)
- No hardcoded metrics
- No silent fallbacks (try/except without logging/raising)
- No undocumented assumptions (every function documents its assumptions)

Architectural Role:
Central invariant enforcement for the meta-assurance pipeline. Each invariant
maps to a security property that the system must uphold.

Security Relevance:
Invariants are the system's self-enforced security properties. A violation
means a guarantee is broken, potentially creating an exploitable weakness.
"""
from __future__ import annotations

import ast
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)


@dataclass
class InvariantViolation:
    """
    InvariantViolation

    Purpose:
    Captures a single violation of a security invariant — the invariant name,
    severity, location, and descriptive context.

    Lifecycle:
    Created by invariant check methods; aggregated into InvariantResult.
    """
    invariant_name: str
    severity: str
    file_path: str
    line_number: int
    description: str
    code_snippet: str


@dataclass
class InvariantResult:
    """
    InvariantResult

    Purpose:
    Stores the result of a single invariant check — whether it passed, the
    list of violations found, and the number of checks performed.

    Lifecycle:
    Created by each _check_* method; stored in InvariantReport.
    """
    invariant_name: str
    passed: bool
    violations: list[InvariantViolation] = field(default_factory=list)
    checks_performed: int = 0


@dataclass
class InvariantReport:
    """
    InvariantReport

    Purpose:
    Aggregates all invariant check results, total violation count, and
    overall invariant score.

    Lifecycle:
    Populated by SecurityInvariantEngine.verify_invariants().
    """
    invariant_results: dict[str, InvariantResult] = field(default_factory=dict)
    violations_found: int = 0
    invariant_score: float = 100.0


class SecurityInvariantEngine:
    """
    SecurityInvariantEngine

    Purpose:
    Verifies that the codebase satisfies a set of predefined security
    invariants. Each invariant is a property that must hold for the
    system to be considered secure.

    Lifecycle:
    Created on demand; verify_invariants() runs all checks.
    """
    def __init__(self, root_dir: str | None = None):
        self.root_dir = root_dir or _ROOT
        self.report = InvariantReport()

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
        skip = {".git", ".svn", "__pycache__", "node_modules", ".venv", "venv", ".tox", ".pytest_cache", ".eggs", "eggs", "dist", "relay", ".agents", ".claude"}
        return dir_name in skip or dir_name.startswith(".")

    def _find_py_files(self) -> list[str]:
        """
        _find_py_files

        Purpose:
        Recursively finds all .py files, skipping excluded directories.

        Inputs:
        None

        Outputs:
        List of absolute file paths.
        """
        result = []
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if not self._skip_dir(d)]
            for f in files:
                if f.endswith(".py"):
                    result.append(os.path.join(root, f))
        return result

    def _read_source(self, file_path: str) -> str:
        """
        _read_source

        Purpose:
        Reads the entire file as a single string, handling encoding errors.

        Inputs:
        file_path — absolute path to the file

        Outputs:
        File contents as a string.
        """
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                return f.read()
        except OSError:
            return ""

    def _read_lines(self, file_path: str) -> list[str]:
        """
        _read_lines

        Purpose:
        Reads a file and returns its lines, handling encoding errors.

        Inputs:
        file_path — absolute path to the file

        Outputs:
        List of strings (lines).
        """
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                return f.readlines()
        except OSError:
            return []

    def _check_no_feature_unreachable(self) -> InvariantResult:
        """
        _check_no_feature_unreachable

        Purpose:
        Verifies that every phase_* function exported from phases/__init__.py
        is actually called from build.py.

        Inputs:
        None

        Outputs:
        InvariantResult with violations for each unreachable phase function.
        """
        result = InvariantResult(
            invariant_name="no_feature_unreachable",
            passed=True,
        )

        build_py = os.path.join(self.root_dir, "scripts", "build.py")
        if not os.path.exists(build_py):
            result.passed = False
            result.violations.append(InvariantViolation(
                invariant_name="no_feature_unreachable",
                severity="CRITICAL",
                file_path="scripts/build.py",
                line_number=0,
                description="build.py not found — cannot verify reachability",
                code_snippet="",
            ))
            return result

        lines = self._read_lines(build_py)
        phase_calls = set()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("phase_") and "(" in stripped:
                fn_name = stripped.split("(")[0].strip()
                phase_calls.add(fn_name)

        phases_init = os.path.join(self.root_dir, "scripts", "phases", "__init__.py")
        if os.path.exists(phases_init):
            init_lines = self._read_lines(phases_init)
            for i, line in enumerate(init_lines, 1):
                stripped = line.strip()
                if "import" in stripped or "from" in stripped:
                    continue
                match = re.search(r"phase_(\w+)", stripped)
                if match:
                    fn_name = f"phase_{match.group(1)}"
                    if fn_name not in phase_calls:
                        result.passed = False
                        result.violations.append(InvariantViolation(
                            invariant_name="no_feature_unreachable",
                            severity="HIGH",
                            file_path="scripts/phases/__init__.py",
                            line_number=i,
                            description=f"Phase function '{fn_name}' is NOT called from build.py",
                            code_snippet=stripped[:120],
                        ))

        result.checks_performed = len(phase_calls)
        return result

    def _check_no_tautological_proof(self) -> InvariantResult:
        """
        _check_no_tautological_proof

        Purpose:
        Scans proof/validation directories for functions that unconditionally
        return True within a verification context — these are tautological
        proofs that provide no real assurance.

        Inputs:
        None

        Outputs:
        InvariantResult with violations for each tautological proof.
        """
        result = InvariantResult(
            invariant_name="no_tautological_proof",
            passed=True,
        )

        proof_dirs = ["scripts/proof", "scripts/proofs", "scripts/validation"]
        for pd in proof_dirs:
            full_dir = os.path.join(self.root_dir, pd)
            if not os.path.isdir(full_dir):
                continue
            for root, _dirs, files in os.walk(full_dir):
                for f in files:
                    if f.endswith(".py"):
                        fp = os.path.join(root, f)
                        lines = self._read_lines(fp)
                        for i, line in enumerate(lines, 1):
                            stripped = line.strip()
                            if "return True" in stripped or "return true" in stripped.lower():
                                ctx_before = lines[max(i - 3, 0):i]
                                ctx_text = "".join(ctx_before)
                                if "verify" in ctx_text.lower() or "validate" in ctx_text.lower() or "prove" in ctx_text.lower() or "check" in ctx_text.lower():
                                    result.passed = False
                                    result.violations.append(InvariantViolation(
                                        invariant_name="no_tautological_proof",
                                        severity="CRITICAL",
                                        file_path=os.path.relpath(fp, self.root_dir),
                                        line_number=i,
                                        description="Proof/validation function unconditionally returns True — tautological",
                                        code_snippet=stripped[:120],
                                    ))

        result.checks_performed = len(result.violations)
        return result

    def _check_no_hardcoded_metrics(self) -> InvariantResult:
        """
        _check_no_hardcoded_metrics

        Purpose:
        Scans for inline dict/JSON literals where score/metric/rating/resilience/
        security keys are assigned constant numeric values.

        Inputs:
        None

        Outputs:
        InvariantResult with violations for each hardcoded metric.
        """
        result = InvariantResult(
            invariant_name="no_hardcoded_metrics",
            passed=True,
        )

        for file_path in self._find_py_files():
            rel = os.path.relpath(file_path, self.root_dir)
            if rel.startswith(("tests/", ".", "relay/", "obfuscator/")):
                continue
            lines = self._read_lines(file_path)
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if re.search(r'["\'](score|metric|rating|resilience|security)[\'"]\s*:\s*\d+\.?\d*', stripped, re.IGNORECASE):
                    parts = stripped.split(":")
                    if len(parts) >= 2:
                        val_str = parts[-1].strip().rstrip(",").strip("\"'")
                        try:
                            val = float(val_str)
                            if val == int(val):
                                result.passed = False
                                result.violations.append(InvariantViolation(
                                    invariant_name="no_hardcoded_metrics",
                                    severity="MEDIUM",
                                    file_path=rel,
                                    line_number=i,
                                    description=f"Hardcoded metric value: {val}",
                                    code_snippet=stripped[:120],
                                ))
                        except ValueError:
                            pass

        result.checks_performed = len(result.violations)
        return result

    def _check_no_silent_fallback(self) -> InvariantResult:
        """
        _check_no_silent_fallback

        Purpose:
        Scans for try/except blocks that catch bare Exception or BaseException
        but have no logging, warning, or re-raise in the handler — these are
        silent fallbacks that hide errors.

        Inputs:
        None

        Outputs:
        InvariantResult with violations for each silent fallback.
        """
        result = InvariantResult(
            invariant_name="no_silent_fallback",
            passed=True,
        )

        for file_path in self._find_py_files():
            rel = os.path.relpath(file_path, self.root_dir)
            if rel.startswith(("tests/", ".", "relay/")):
                continue
            source = self._read_source(file_path)
            lines = source.split("\n")
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Try):
                    for handler in node.handlers:
                        is_bare = handler.type is None or (isinstance(handler.type, ast.Name) and handler.type.id in ("BaseException", "Exception"))
                        if not is_bare:
                            continue
                        has_reporting = False
                        for inner_node in ast.walk(handler):
                            if isinstance(inner_node, ast.Expr) and isinstance(inner_node.value, ast.Call):
                                call = inner_node.value
                                if isinstance(call.func, ast.Attribute) and call.func.attr in ("log", "warn", "error", "print"):
                                    has_reporting = True
                                elif isinstance(call.func, ast.Name) and call.func.id in ("log", "warn", "error", "print"):
                                    has_reporting = True
                        if not has_reporting:
                            hlineno = node.lineno if hasattr(node, "lineno") else 0
                            result.passed = False
                            result.violations.append(InvariantViolation(
                                invariant_name="no_silent_fallback",
                                severity="HIGH",
                                file_path=rel,
                                line_number=hlineno,
                                description="try/except block without visible fallback reporting (log/print/error)",
                                code_snippet=lines[hlineno - 1][:120] if 0 < hlineno <= len(lines) else "",
                            ))

        result.checks_performed = len(result.violations)
        return result

    def _check_no_undocumented_assumptions(self) -> InvariantResult:
        """
        _check_no_undocumented_assumptions

        Purpose:
        Checks that every function and class definition has at least one line
        mentioning "assume" in its opening docstring or first lines, or an
        inline comment containing "assume".

        Inputs:
        None

        Outputs:
        InvariantResult with violations for each undocumented assumption.
        """
        result = InvariantResult(
            invariant_name="no_undocumented_assumptions",
            passed=True,
        )

        scripts_dir = os.path.join(self.root_dir, "scripts")
        py_files = []
        if os.path.isdir(scripts_dir):
            for root, dirs, files in os.walk(scripts_dir):
                dirs[:] = [d for d in dirs if not self._skip_dir(d)]
                for f in files:
                    if f.endswith(".py"):
                        py_files.append(os.path.join(root, f))

        for file_path in py_files:
            rel = os.path.relpath(file_path, self.root_dir)
            source = self._read_source(file_path)
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    func_name = node.name
                    for stmt in node.body:
                        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                            break
                        if isinstance(stmt, ast.FunctionDef) or isinstance(stmt, ast.AsyncFunctionDef):
                            continue
                        break

                    first_line = node.lineno
                    docstring_lines = source.split("\n")[first_line:first_line + 3]
                    has_assumption_doc = any("assume" in line.lower() for line in docstring_lines)

                    func_body = source.split("\n")[first_line - 1:first_line + 10]
                    body_text = "\n".join(func_body)
                    has_assumption_comment = "assume" in body_text.lower() or "# assume" in body_text.lower()

                    if not has_assumption_doc and not has_assumption_comment:
                        for stmt in node.body[:3]:
                            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                                if "assume" in stmt.value.value.lower():
                                    has_assumption_doc = True
                                    break

                    if not has_assumption_doc and not has_assumption_comment:
                        result.passed = False
                        result.violations.append(InvariantViolation(
                            invariant_name="no_undocumented_assumptions",
                            severity="LOW",
                            file_path=rel,
                            line_number=first_line,
                            description=f"Function '{func_name}' has no documented assumptions",
                            code_snippet=source.split("\n")[first_line - 1][:120] if first_line <= len(source.split("\n")) else "",
                        ))

        result.checks_performed = len(result.violations)
        return result

    def verify_invariants(self) -> dict[str, Any]:
        """
        verify_invariants

        Purpose:
        Main entry point — runs all five invariant checks, aggregates results,
        and computes the overall invariant score.

        Inputs:
        None

        Outputs:
        Dict with invariant_results, violations_found, invariant_score.
        """
        invariants = [
            self._check_no_feature_unreachable,
            self._check_no_tautological_proof,
            self._check_no_hardcoded_metrics,
            self._check_no_silent_fallback,
            self._check_no_undocumented_assumptions,
        ]

        for check_fn in invariants:
            result = check_fn()
            self.report.invariant_results[result.invariant_name] = result

        total_violations = sum(
            len(r.violations) for r in self.report.invariant_results.values()
        )
        self.report.violations_found = total_violations

        if total_violations == 0:
            self.report.invariant_score = 100.0
        else:
            score = max(0, 100 - (total_violations * 5))
            self.report.invariant_score = float(score)

        return self._to_dict()

    def _to_dict(self) -> dict[str, Any]:
        """
        _to_dict

        Purpose:
        Serializes the InvariantReport to a plain dict for JSON output.

        Inputs:
        None

        Outputs:
        Dict with invariant_results, violations_found, invariant_score.
        """
        return {
            "invariant_results": {
                name: {
                    "invariant_name": r.invariant_name,
                    "passed": r.passed,
                    "checks_performed": r.checks_performed,
                    "violations": [
                        {
                            "invariant_name": v.invariant_name,
                            "severity": v.severity,
                            "file_path": v.file_path,
                            "line_number": v.line_number,
                            "description": v.description,
                            "code_snippet": v.code_snippet,
                        }
                        for v in r.violations
                    ],
                }
                for name, r in self.report.invariant_results.items()
            },
            "violations_found": self.report.violations_found,
            "invariant_score": self.report.invariant_score,
        }
