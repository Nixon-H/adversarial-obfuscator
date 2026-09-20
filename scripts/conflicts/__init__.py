"""
__init__.py

Purpose:
Package initializer for the protection conflict detection module.
Exports conflict data types, the conflict detector, conflict graph,
and known conflict rules.

Architectural Role:
Conflict detection runs before protection synthesis to catch
incompatible flag combinations. The detector is invoked by the
build pipeline's argument validation step.

Execution Context:
check_flag_conflicts() is called during CLI argument parsing to
validate that no incompatible protections are requested. The
conflict graph is built at pipeline start for visualization.

Dependencies:
- detector (Conflict, ConflictDetector, ConflictType, Severity)
- graph (ConflictGraph)
- known_conflicts (KNOWN_CONFLICTS)

Security Relevance:
Protection conflicts can cause silent failures (e.g., VM + FHE
both trying to control the same function). The conflict detector
catches these before the pipeline runs, preventing wasted build
time and unexpected behavior.

Maintenance Notes:
- Adding a new conflict rule requires: (1) an entry in known_conflicts.py,
  (2) if the conflict involves new flags, ensuring those flags exist
  in the CLI argument parser.
"""

from scripts.conflicts.detector import (
    Conflict,
    ConflictDetector,
    ConflictType,
    Severity,
)
from scripts.conflicts.graph import ConflictGraph
from scripts.conflicts.known_conflicts import KNOWN_CONFLICTS


def check_flag_conflicts(flags: dict) -> list:
    """Convenience: check a dict of flags against KNOWN_CONFLICTS."""
    detector = ConflictDetector(KNOWN_CONFLICTS)
    return detector.check_flags(flags)


def generate_conflict_report(conflicts: list) -> str:
    """Convenience: generate a report from a conflict list."""
    return ConflictDetector().generate_report(conflicts)


__all__ = [
    "Conflict",
    "ConflictDetector",
    "ConflictGraph",
    "ConflictType",
    "Severity",
    "KNOWN_CONFLICTS",
    "check_flag_conflicts",
    "generate_conflict_report",
]
