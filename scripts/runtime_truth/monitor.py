"""
runtime_truth/monitor.py

Purpose:
Monitors "runtime truth" — the gap between what the build pipeline intends to
execute (phase calls in build.py) and what each phase actually does (its
assertions, validations, and function definitions). Produces a truth score.

Architectural Role:
Consumed by the release confidence scorer (F197) and the self-critique
engine (F200) to quantify execution integrity.

Security Relevance:
If intended execution paths lack runtime evidence (assertions, validations),
the pipeline may produce false confidence. The truth score measures how well
intent matches reality.
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
class IntendedExecution:
    """
    IntendedExecution

    Purpose:
    Captures an intended phase execution — the phase function call as declared
    in build.py, including its line number and optional flag gating.

    Lifecycle:
    Created during _parse_intended_execution().
    """
    phase_name: str
    line_number: int
    call_expression: str
    enabled_by_flag: str | None = None


@dataclass
class ActualEvidence:
    """
    ActualEvidence

    Purpose:
    Captures the actual evidence found in a phase file — assertions,
    validation patterns, and function definitions.

    Lifecycle:
    Created during _gather_actual_evidence().
    """
    phase_name: str
    file_path: str
    has_assertions: bool
    has_validations: bool
    assertion_count: int
    validation_keywords: list[str] = field(default_factory=list)
    function_defs: list[str] = field(default_factory=list)


@dataclass
class GapAnalysis:
    """
    GapAnalysis

    Purpose:
    Describes a gap between intended execution and actual evidence — a
    missing phase file, lack of validation, or low assertion count.

    Lifecycle:
    Created during _compute_gaps().
    """
    phase_name: str
    intended: bool
    has_evidence: bool
    gap_type: str
    description: str


# Keywords that indicate assertion/validation logic in phase files.
ASSERTION_KEYWORDS = {"assert", "verify", "validate", "check", "ensure", "confirm", "test"}
VALIDATION_PATTERNS = [
    r"assert\s+",
    r"if\s+not\s+\w+\s*:",
    r"raise\s+\w+Error",
    r"logging\.\w+",
    r"log\s*\(",
    r"print\s*\(.*err",
    r"print\s*\(.*fail",
    r"print\s*\(.*warn",
]


class RuntimeTruthMonitor:
    """
    RuntimeTruthMonitor

    Purpose:
    Compares intended pipeline execution (phase calls from build.py) against
    actual runtime evidence (assertions/validations in phase files) to produce
    a truth score.

    Lifecycle:
    Created on demand; record_runtime_truth() drives the full analysis.
    """
    def __init__(self, scripts_dir: str | None = None):
        self.scripts_dir = scripts_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
        )

    def record_runtime_truth(self, build_dir: str | None = None) -> dict[str, Any]:
        """
        record_runtime_truth

        Purpose:
        Main entry point — parses intended execution, gathers actual evidence,
        computes gaps, and produces a truth score.

        Inputs:
        build_dir — optional build directory override (unused, kept for API)

        Outputs:
        Dict with intended_execution, actual_evidence, gaps, truth_score.
        """
        intended = self._parse_intended_execution()
        actual = self._gather_actual_evidence(intended)
        gaps = self._compute_gaps(intended, actual)
        truth_score = self._compute_truth_score(intended, actual, gaps)

        return {
            "intended_execution": [
                {
                    "phase_name": i.phase_name,
                    "line_number": i.line_number,
                    "call_expression": i.call_expression,
                    "enabled_by_flag": i.enabled_by_flag,
                }
                for i in intended
            ],
            "actual_evidence": [
                {
                    "phase_name": a.phase_name,
                    "file_path": a.file_path,
                    "has_assertions": a.has_assertions,
                    "has_validations": a.has_validations,
                    "assertion_count": a.assertion_count,
                    "validation_keywords": a.validation_keywords,
                    "function_defs": a.function_defs,
                }
                for a in actual
            ],
            "gaps": [
                {
                    "phase_name": g.phase_name,
                    "intended": g.intended,
                    "has_evidence": g.has_evidence,
                    "gap_type": g.gap_type,
                    "description": g.description,
                }
                for g in gaps
            ],
            "truth_score": truth_score,
        }

    def _parse_intended_execution(self) -> list[IntendedExecution]:
        """
        _parse_intended_execution

        Purpose:
        Parses build.py to extract all phase_* function calls and their
        associated CLI flag gating.

        Inputs:
        None

        Outputs:
        List of IntendedExecution entries.
        """
        build_path = os.path.join(self.scripts_dir, "build.py")
        intended: list[IntendedExecution] = []
        if not os.path.exists(build_path):
            return intended

        try:
            with open(build_path, encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=build_path)
        except (SyntaxError, OSError):
            return intended

        phase_calls = set()
        phases_dir = os.path.join(self.scripts_dir, "phases")
        if os.path.isdir(phases_dir):
            for fname in os.listdir(phases_dir):
                if fname.startswith("phase_") and fname.endswith(".py"):
                    phase_name = fname[:-3]
                    phase_calls.add(phase_name)

        flag_map = self._build_flag_map(source)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Expr):
                continue
            if not isinstance(node.value, ast.Call):
                continue
            call = node.value
            if not isinstance(call.func, ast.Name):
                continue
            func_name = call.func.id
            if func_name in phase_calls:
                enabled_by = None
                for flag_name, flag_lines in flag_map.items():
                    if any(abs(node.lineno - fl) < 50 for fl in flag_lines):
                        enabled_by = flag_name
                        break
                intended.append(IntendedExecution(
                    phase_name=func_name,
                    line_number=node.lineno,
                    call_expression=f"{func_name}(...)",
                    enabled_by_flag=enabled_by,
                ))

        # Also check for patterns like "phase_xxx(opts)" or "phase_xxx("
        for match in re.finditer(
            r"(phase_\w+)\s*\((?:\s*opts|\s*args|\s*[^)]*)\)",
            source,
        ):
            pname = match.group(1)
            if pname not in {i.phase_name for i in intended}:
                line_no = source[:match.start()].count("\n") + 1
                intended.append(IntendedExecution(
                    phase_name=pname,
                    line_number=line_no,
                    call_expression=match.group(0),
                ))

        return intended

    def _build_flag_map(self, source: str) -> dict[str, list[int]]:
        """
        _build_flag_map

        Purpose:
        Extracts CLI flag names and their line numbers from build.py's
        parser.add_argument() calls.

        Inputs:
        source — raw source text of build.py

        Outputs:
        Dict mapping flag_name -> list of line numbers where it appears.
        """
        flag_map: dict[str, list[int]] = {}
        for match in re.finditer(
            r'parser\.add_argument\(["\']-{1,2}(\w[\w-]*)["\']',
            source,
        ):
            flag_name = match.group(1).replace("-", "_")
            line_no = source[:match.start()].count("\n") + 1
            flag_map.setdefault(flag_name, []).append(line_no)
        return flag_map

    def _gather_actual_evidence(
        self, intended: list[IntendedExecution]
    ) -> list[ActualEvidence]:
        """
        _gather_actual_evidence

        Purpose:
        For each intended execution, opens the corresponding phase file and
        counts assertions, validations, and function definitions.

        Inputs:
        intended — list of IntendedExecution entries

        Outputs:
        List of ActualEvidence entries for each found phase file.
        """

        evidence: list[ActualEvidence] = []
        phases_dir = os.path.join(self.scripts_dir, "phases")
        if not os.path.isdir(phases_dir):
            return evidence

        for intent in intended:
            phase_file = os.path.join(phases_dir, f"{intent.phase_name}.py")
            if not os.path.exists(phase_file):
                continue
            try:
                with open(phase_file, encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source, filename=phase_file)
            except (SyntaxError, OSError):
                continue

            func_defs = [
                n.name
                for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef)
            ]
            found_keywords: list[str] = []
            for pattern in VALIDATION_PATTERNS:
                matches = re.findall(pattern, source, re.MULTILINE)
                if matches:
                    found_keywords.append(pattern)

            assertions = [
                n for n in ast.walk(tree)
                if isinstance(n, ast.Assert)
            ]

            evidence.append(ActualEvidence(
                phase_name=intent.phase_name,
                file_path=phase_file,
                has_assertions=len(assertions) > 0,
                has_validations=len(found_keywords) > 0,
                assertion_count=len(assertions),
                validation_keywords=found_keywords[:5],
                function_defs=func_defs[:10],
            ))
        return evidence

    def _compute_gaps(
        self,
        intended: list[IntendedExecution],
        actual: list[ActualEvidence],
    ) -> list[GapAnalysis]:
        """
        _compute_gaps

        Purpose:
        Compares intended vs. actual to identify missing phase files, phases
        without validation, and phases lacking assertions.

        Inputs:
        intended — list of IntendedExecution entries
        actual — list of ActualEvidence entries

        Outputs:
        List of GapAnalysis entries.
        """

        gaps: list[GapAnalysis] = []
        actual_map = {a.phase_name: a for a in actual}

        for intent in intended:
            ev = actual_map.get(intent.phase_name)
            if ev is None:
                gaps.append(GapAnalysis(
                    phase_name=intent.phase_name,
                    intended=True,
                    has_evidence=False,
                    gap_type="missing_phase_file",
                    description=f"Phase {intent.phase_name} has no corresponding file",
                ))
            elif not ev.has_assertions and not ev.has_validations:
                gaps.append(GapAnalysis(
                    phase_name=intent.phase_name,
                    intended=True,
                    has_evidence=True,
                    gap_type="no_validation",
                    description=f"Phase {intent.phase_name} has no assertions or validations "
                                f"(0 assertions, 0 validation keywords)",
                ))
            elif ev.assertion_count == 0:
                gaps.append(GapAnalysis(
                    phase_name=intent.phase_name,
                    intended=True,
                    has_evidence=True,
                    gap_type="low_assertion",
                    description=f"Phase {intent.phase_name} has no assertions "
                                f"(only pattern-based validations)",
                ))

        return gaps

    def _compute_truth_score(
        self,
        intended: list[IntendedExecution],
        actual: list[ActualEvidence],
        gaps: list[GapAnalysis],
    ) -> float:
        """
        _compute_truth_score

        Purpose:
        Calculates a 0-100 truth score based on coverage ratio, validation
        ratio, and gap penalty.

        Inputs:
        intended — list of IntendedExecution entries
        actual — list of ActualEvidence entries
        gaps — list of GapAnalysis entries

        Outputs:
        Float between 0.0 (no truth) and 100.0 (full truth).
        """

        if not intended:
            return 0.0

        actual_map = {a.phase_name: a for a in actual}
        phases_with_evidence = sum(
            1 for i in intended if i.phase_name in actual_map
        )
        phases_with_validation = sum(
            1 for i in intended
            if i.phase_name in actual_map
            and actual_map[i.phase_name].has_assertions
        )
        phases_with_gaps = len(gaps)

        coverage_ratio = phases_with_evidence / max(len(intended), 1)
        validation_ratio = phases_with_validation / max(len(intended), 1)
        gap_penalty = phases_with_gaps / max(len(intended), 1)

        score = (coverage_ratio * 0.4 + validation_ratio * 0.4) * (1 - gap_penalty * 0.5)
        return round(max(0.0, min(1.0, score)) * 100, 2)
