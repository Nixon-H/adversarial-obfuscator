"""
test_conflicts.py

Tests for protection conflict detection.

Test Categories:
- Positive tests verify known conflict definitions, flag checking,
  conflict graph construction, report generation, and CLI argument checking.
- Negative tests verify empty flags, malformed flags, no-false-positive scenarios.

Coverage:
- Known conflicts: list integrity, minimum entries
- Conflict dataclass: construction, equality
- ConflictDetector: initialization, flag checking (incompatible, requires)
- ConflictGraph: add, query, compatibility, serialization (dict, JSON, DOT)
- Convenience functions: check_flag_conflicts, generate_conflict_report
- Known conflict matrix: specific flag pair validation
- CLI arg checking: argparse namespace verification
"""

import json
import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.conflicts import (
    KNOWN_CONFLICTS,
    Conflict,
    ConflictDetector,
    ConflictGraph,
    ConflictType,
    Severity,
    check_flag_conflicts,
    generate_conflict_report,
)


class TestKnownConflicts:
    """
    TestKnownConflicts

    Positive test cases for the KNOWN_CONFLICTS registry: structure,
    field presence, and minimum number of entries.
    """
    def test_known_conflicts_list(self):
        assert len(KNOWN_CONFLICTS) > 0
        for c in KNOWN_CONFLICTS:
            assert isinstance(c, Conflict)
            assert isinstance(c.flag_a, str) and c.flag_a
            assert isinstance(c.flag_b, str) and c.flag_b
            assert isinstance(c.conflict_type, ConflictType)
            assert isinstance(c.severity, Severity)
            assert isinstance(c.description, str) and c.description
            assert isinstance(c.resolution, str) and c.resolution

    def test_known_conflicts_minimum_entries(self):
        assert len(KNOWN_CONFLICTS) >= 20, f"Expected >=20 conflicts, got {len(KNOWN_CONFLICTS)}"


class TestConflictDataclass:
    """
    TestConflictDataclass

    Positive test cases for Conflict dataclass construction and equality.
    """
    def test_conflict_dataclass(self):
        c = Conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix")
        assert c.flag_a == "a"
        assert c.flag_b == "b"
        assert c.conflict_type == ConflictType.INCOMPATIBLE
        assert c.severity == Severity.ERROR
        assert c.description == "desc"
        assert c.resolution == "fix"

    def test_conflict_equality(self):
        c1 = Conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix")
        c2 = Conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix")
        assert c1 == c2


class TestConflictDetectorInit:
    """
    TestConflictDetectorInit

    Positive test cases for ConflictDetector initialization with
    and without known conflict lists.
    """
    def test_conflict_detector_init(self):
        detector = ConflictDetector()
        assert detector.known_conflicts == []

    def test_conflict_detector_init_with_conflicts(self):
        conflicts = [
            Conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix")
        ]
        detector = ConflictDetector(conflicts)
        assert len(detector.known_conflicts) == 1


class TestCheckFlags:
    """
    TestCheckFlags

    Positive and negative test cases for flag conflict checking,
    including incompatible flags, requires relationships,
    no-false-positives, and empty/malformed flag sets.
    """
    def test_check_skip_obfuscate_conflict(self):
        detector = ConflictDetector([
            Conflict("skip_obfuscate", "obfuscate", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix"),
        ])
        conflicts = detector.check_flags({"skip_obfuscate": True, "obfuscate": True})
        assert len(conflicts) == 1
        assert conflicts[0].flag_a == "skip_obfuscate"

    def test_check_skip_irgen_fhe(self):
        detector = ConflictDetector([
            Conflict("skip_irgen", "fhe_vm", ConflictType.REQUIRES, Severity.ERROR, "desc", "fix"),
        ])
        conflicts = detector.check_flags({"skip_irgen": True, "fhe_vm": True})
        assert len(conflicts) == 1

    def test_no_false_positive(self):
        detector = ConflictDetector([
            Conflict("skip_obfuscate", "obfuscate", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix"),
        ])
        conflicts = detector.check_flags({"skip_obfuscate": False, "obfuscate": True})
        assert len(conflicts) == 0

    def test_empty_flags(self):
        detector = ConflictDetector([
            Conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix"),
        ])
        conflicts = detector.check_flags({})
        assert len(conflicts) == 0

    def test_malformed_flag(self):
        detector = ConflictDetector([
            Conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix"),
        ])
        conflicts = detector.check_flags({"a": True, "nonexistent": True})
        assert len(conflicts) == 0

    def test_conflict_self(self):
        detector = ConflictDetector([
            Conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix"),
        ])
        conflicts = detector.check_flags({"a": True, "b": True})
        assert len(conflicts) == 1


class TestGenerateReport:
    """
    TestGenerateReport

    Positive test cases for conflict report text generation with
    errors, warnings, and empty conflict lists.
    """
    def test_generate_report(self):
        detector = ConflictDetector()
        conflicts = [
            Conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix"),
        ]
        report = detector.generate_report(conflicts)
        assert "PROTECTION CONFLICT REPORT" in report
        assert "a" in report
        assert "b" in report
        assert "desc" in report
        assert "fix" in report

    def test_report_with_warnings(self):
        detector = ConflictDetector()
        conflicts = [
            Conflict("x", "y", ConflictType.SUBSUMES, Severity.WARNING, "warn desc", "warn fix"),
        ]
        report = detector.generate_report(conflicts)
        assert "WARNING" in report
        assert "warn desc" in report

    def test_report_empty(self):
        detector = ConflictDetector()
        report = detector.generate_report([])
        assert "No protection conflicts detected" in report


class TestHasErrors:
    """
    TestHasErrors

    Positive test cases for detecting ERROR-severity conflicts
    in a list with mixed severities.
    """
    def test_has_errors(self):
        assert ConflictDetector.has_errors([
            Conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix"),
        ])

    def test_no_errors(self):
        assert not ConflictDetector.has_errors([
            Conflict("x", "y", ConflictType.SUBSUMES, Severity.WARNING, "desc", "fix"),
        ])

    def test_has_errors_mixed(self):
        assert ConflictDetector.has_errors([
            Conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.WARNING, "desc", "fix"),
            Conflict("c", "d", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix"),
        ])


class TestConflictGraph:
    """
    TestConflictGraph

    Positive test cases for ConflictGraph construction, querying,
    compatibility checks, serialization (dict, JSON, DOT), and
    connected component analysis.
    """
    def test_conflict_graph_add(self):
        g = ConflictGraph()
        g.add_conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix")
        g.add_conflict("b", "c", ConflictType.REQUIRES, Severity.WARNING, "desc2", "fix2")
        conflicts_a = g.get_conflicts("a")
        assert len(conflicts_a) == 1
        assert conflicts_a[0].flag_b == "b"

    def test_conflict_graph_get_conflicts(self):
        g = ConflictGraph()
        g.add_conflict("x", "y", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix")
        g.add_conflict("x", "z", ConflictType.REQUIRES, Severity.WARNING, "desc2", "fix2")
        assert len(g.get_conflicts("x")) == 2
        assert len(g.get_conflicts("y")) == 1
        assert len(g.get_conflicts("nonexistent")) == 0

    def test_is_compatible(self):
        g = ConflictGraph()
        g.add_conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix")
        assert g.is_compatible(["a"])
        assert g.is_compatible(["b"])
        assert not g.is_compatible(["a", "b"])

    def test_conflict_graph_serialization(self):
        g = ConflictGraph()
        g.add_conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix")
        d = g.to_dict()
        assert "nodes" in d
        assert "edges" in d
        assert "a" in d["nodes"]
        assert "b" in d["nodes"]
        assert len(d["edges"]) == 1

    def test_conflict_graph_json(self):
        g = ConflictGraph()
        g.add_conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix")
        j = g.to_json()
        d = json.loads(j)
        assert "nodes" in d
        assert "edges" in d

    def test_conflict_graph_dot(self):
        g = ConflictGraph()
        g.add_conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix")
        g.add_conflict("c", "d", ConflictType.SUBSUMES, Severity.WARNING, "desc2", "fix2")
        dot = g.generate_dot()
        assert "digraph ConflictGraph" in dot
        assert '"a"' in dot
        assert '"b"' in dot
        assert '"c"' in dot
        assert '"d"' in dot
        assert "incompatible" in dot
        assert "subsumes" in dot
        assert "red" in dot
        assert "orange" in dot
        assert "dashed" in dot
        assert "solid" in dot

    def test_get_connected_components(self):
        g = ConflictGraph()
        g.add_conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix")
        g.add_conflict("c", "d", ConflictType.REQUIRES, Severity.WARNING, "desc2", "fix2")
        components = g.get_connected_components()
        assert len(components) == 2

    def test_add_conflict_obj(self):
        g = ConflictGraph()
        c = Conflict("x", "y", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix")
        g.add_conflict_obj(c)
        assert len(g.get_conflicts("x")) == 1


class TestConvenienceFunctions:
    """
    TestConvenienceFunctions

    Positive test cases for module-level convenience functions:
    check_flag_conflicts and generate_conflict_report.
    """
    def test_check_flag_conflicts(self):
        conflicts = check_flag_conflicts({"skip_obfuscate": True, "obfuscate": True})
        assert len(conflicts) >= 1

    def test_generate_conflict_report(self):
        conflicts = [
            Conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix"),
        ]
        report = generate_conflict_report(conflicts)
        assert "PROTECTION CONFLICT REPORT" in report


class TestKnownConflictMatrix:
    """
    TestKnownConflictMatrix

    Positive test cases validating specific known conflict entries
    against the full KNOWN_CONFLICTS list.
    """
    def test_skip_irgen_blocks_fhe_vm(self):
        detector = ConflictDetector(KNOWN_CONFLICTS)
        conflicts = detector.check_flags({"skip_irgen": True, "fhe_vm": True})
        assert any(c.flag_a == "skip_irgen" and c.flag_b == "fhe_vm" for c in conflicts)

    def test_skip_llvmgen_blocks_rop(self):
        detector = ConflictDetector(KNOWN_CONFLICTS)
        conflicts = detector.check_flags({"skip_llvmgen": True, "rop": True})
        assert any(c.flag_a == "skip_llvmgen" and c.flag_b == "rop" for c in conflicts)

    def test_tee_sgx_subsumes(self):
        detector = ConflictDetector(KNOWN_CONFLICTS)
        conflicts = detector.check_flags({"tee": True, "sgx": True})
        assert any(c.flag_a == "tee" and c.flag_b == "sgx" for c in conflicts)

    def test_incompatible_flags(self):
        detector = ConflictDetector([
            Conflict("a", "b", ConflictType.INCOMPATIBLE, Severity.ERROR, "desc", "fix"),
        ])
        c = detector.check_flags({"a": True, "b": True})
        assert len(c) == 1

    def test_requires_triggered_when_violated(self):
        detector = ConflictDetector([
            Conflict("a", "b", ConflictType.REQUIRES, Severity.ERROR, "b requires a to be absent", "fix"),
        ])
        c = detector.check_flags({"a": True, "b": True})
        assert len(c) == 1
        assert c[0].flag_a == "a"
        assert c[0].flag_b == "b"

    def test_requires_not_triggered_when_requirement_absent(self):
        detector = ConflictDetector([
            Conflict("a", "b", ConflictType.REQUIRES, Severity.ERROR, "b requires a to be absent", "fix"),
        ])
        c = detector.check_flags({"a": False, "b": True})
        assert len(c) == 0


class TestCLIArgCheck:
    """
    TestCLIArgCheck

    Positive test cases for checking conflicts from argparse Namespace objects.
    """
    def test_check_cli_args_basic(self):
        import argparse
        detector = ConflictDetector([
            Conflict("skip_irgen", "fhe_vm", ConflictType.REQUIRES, Severity.ERROR, "desc", "fix"),
        ])
        ns = argparse.Namespace(skip_irgen=True, fhe_vm=True, payload="test.py")
        conflicts = detector.check_cli_args(ns)
        assert len(conflicts) == 1
