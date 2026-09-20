"""
detector.py

Purpose:
Core conflict detection engine for protection features. Defines
conflict types (INCOMPATIBLE, SUBSUMES, REQUIRES), severity levels
(ERROR, WARNING), the Conflict dataclass, and the ConflictDetector
that checks flag combinations against known conflict rules.

Architectural Role:
Validation layer for the build pipeline. The detector is called
during CLI argument parsing to catch incompatible protection flags
before the pipeline executes.

Execution Context:
ConflictDetector is instantiated with KNOWN_CONFLICTS and called
with a dict of flags (from argparse Namespace or CLI parser). The
check_flags() method returns a list of detected conflicts.

Dependencies:
- Standard library (argparse, enum, dataclasses, typing)

Security Relevance:
Conflict detection prevents silently incompatible protection
combinations that could leave code unprotected or cause runtime
failures. ERROR-severity conflicts block the build; WARNING-severity
conflicts are reported but do not block.

Maintenance Notes:
- ConflictType.REQUIRES means: if flag_b is present, flag_a must
  also be present (a one-way dependency).
- The _is_set static method uses Python truthiness with special
  handling for "0", "false", "none" strings (case-insensitive).
"""

from __future__ import annotations

import argparse
import enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class ConflictType(enum.Enum):
    INCOMPATIBLE = "incompatible"
    SUBSUMES = "subsumes"
    REQUIRES = "requires"


class Severity(enum.Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class Conflict:
    flag_a: str
    flag_b: str
    conflict_type: ConflictType
    severity: Severity
    description: str
    resolution: str


@dataclass
class ConflictDetector:
    known_conflicts: List[Conflict] = field(default_factory=list)

    def __init__(self, known_conflicts: Optional[List[Conflict]] = None):
        self.known_conflicts = known_conflicts or []

    def check_flags(self, flags: Dict[str, Any]) -> List[Conflict]:
        detected: List[Conflict] = []
        for c in self.known_conflicts:
            val_a = flags.get(c.flag_a)
            val_b = flags.get(c.flag_b)
            a_present = val_a is not None and self._is_set(val_a)
            b_present = val_b is not None and self._is_set(val_b)

            if c.conflict_type == ConflictType.INCOMPATIBLE:
                if a_present and b_present:
                    detected.append(c)

            elif c.conflict_type == ConflictType.REQUIRES:
                if b_present and a_present:
                    detected.append(c)

            elif c.conflict_type == ConflictType.SUBSUMES:
                if a_present and b_present:
                    detected.append(c)

        return detected

    @staticmethod
    def _is_set(val: Any) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return bool(val) and val.lower() not in ("0", "false", "none", "")
        if isinstance(val, (int, float)):
            return val != 0
        if val is None:
            return False
        return True

    def check_cli_args(self, args: argparse.Namespace) -> List[Conflict]:
        flags = vars(args)
        return self.check_flags(flags)

    def generate_report(self, conflicts: List[Conflict]) -> str:
        if not conflicts:
            return "No protection conflicts detected.\n"

        lines: List[str] = []
        lines.append("=" * 68)
        lines.append("  PROTECTION CONFLICT REPORT")
        lines.append("=" * 68)

        errors = [c for c in conflicts if c.severity == Severity.ERROR]
        warnings = [c for c in conflicts if c.severity == Severity.WARNING]

        if errors:
            lines.append(f"\n  [{Severity.ERROR.value.upper()}] {len(errors)} blocking conflict(s):\n")
            for i, c in enumerate(errors, 1):
                lines.append(f"  {i}. {c.flag_a} ↔ {c.flag_b} ({c.conflict_type.value})")
                lines.append(f"     {c.description}")
                lines.append(f"     Fix: {c.resolution}")
                lines.append("")

        if warnings:
            lines.append(f"\n  [{Severity.WARNING.value.upper()}] {len(warnings)} warning(s):\n")
            for i, c in enumerate(warnings, 1):
                lines.append(f"  {i}. {c.flag_a} ↔ {c.flag_b} ({c.conflict_type.value})")
                lines.append(f"     {c.description}")
                lines.append(f"     Fix: {c.resolution}")
                lines.append("")

        lines.append("=" * 68)
        return "\n".join(lines)

    @staticmethod
    def has_errors(conflicts: List[Conflict]) -> bool:
        return any(c.severity == Severity.ERROR for c in conflicts)
