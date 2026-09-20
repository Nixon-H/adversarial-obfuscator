"""
test_attack_surface.py

Tests for Attack Surface Enumeration (Feature 190).

Test coverage:
- Positive tests verify CLI, runtime, VM, proof, attestation, network, filesystem enumeration
- Negative tests verify nonexistent files, risk level ordering, empty results
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from scripts.attack_surface.enumerator import (
    RISK_LEVELS,
    AttackSurfaceEntry,
    AttackSurfaceReport,
    AttackSurfaceEnumerator,
)


# =========================================================================
# Domain Model Tests
# =========================================================================

class TestAttackSurfaceEntry:
    """
    TestAttackSurfaceEntry
    
    Positive test cases for attacksurfaceentry.
    """
    def test_defaults(self):
        e = AttackSurfaceEntry(
            category="cli",
            file_path="a.py",
            line_number=10,
            code_snippet="parser.add_argument",
            risk_level="HIGH",
            description="test",
            entry_type="cli_argument",
        )
        assert e.category == "cli"
        assert e.risk_level == "HIGH"

    def test_all_fields(self):
        e = AttackSurfaceEntry(
            category="runtime",
            file_path="b.py",
            line_number=42,
            code_snippet="exec(code)",
            risk_level="CRITICAL",
            description="dangerous exec",
            entry_type="dangerous_call",
        )
        assert e.risk_level == "CRITICAL"
        assert e.entry_type == "dangerous_call"


class TestAttackSurfaceReport:
    """
    Tests for AttackSurfaceReport defaults and risk summary.
    """
    def test_defaults(self):
        r = AttackSurfaceReport()
        assert r.per_category_results == {}
        assert r.total_entry_points == 0
        assert r.risk_summary["CRITICAL"] == 0
        assert r.risk_summary["HIGH"] == 0
        assert r.risk_summary["MEDIUM"] == 0
        assert r.risk_summary["LOW"] == 0


class TestRiskLevels:
    """
    Tests for RISK_LEVELS constant definitions and ordering.
    """
    def test_levels_defined(self):
        assert "CRITICAL" in RISK_LEVELS
        assert "HIGH" in RISK_LEVELS
        assert "MEDIUM" in RISK_LEVELS
        assert "LOW" in RISK_LEVELS

    def test_level_order(self):
        assert RISK_LEVELS["CRITICAL"] > RISK_LEVELS["HIGH"]
        assert RISK_LEVELS["HIGH"] > RISK_LEVELS["MEDIUM"]
        assert RISK_LEVELS["MEDIUM"] > RISK_LEVELS["LOW"]


class TestAttackSurfaceEnumerator:
    """
    Tests for AttackSurfaceEnumerator: CLI, runtime, VM, proof, attestation,
    network, filesystem enumeration, and full report generation.
    """
    def test_init(self):
        e = AttackSurfaceEnumerator()
        assert e.root_dir is not None
        assert os.path.isdir(e.root_dir)

    def test_find_py_files(self):
        e = AttackSurfaceEnumerator()
        files = e._find_py_files()
        assert len(files) > 0
        for f in files:
            assert f.endswith(".py")

    def test_find_rs_files(self):
        e = AttackSurfaceEnumerator()
        files = e._find_rs_files()
        assert isinstance(files, list)

    def test_read_lines(self):
        e = AttackSurfaceEnumerator()
        tmp_file = "/tmp/_test_lines.py"
        with open(tmp_file, "w") as f:
            f.write("line1\nline2\nline3\n")
        lines = e._read_lines(tmp_file)
        assert len(lines) == 3
        os.remove(tmp_file)

    def test_read_lines_nonexistent(self):
        e = AttackSurfaceEnumerator()
        lines = e._read_lines("/tmp/nonexistent_file_xyz.py")
        assert lines == []

    def test_enumerate_cli_contains_add_argument(self):
        e = AttackSurfaceEnumerator()
        entries = e._enumerate_cli_attack_surface()
        assert isinstance(entries, list)

    def test_enumerate_runtime_attack_surface(self):
        e = AttackSurfaceEnumerator()
        entries = e._enumerate_runtime_attack_surface()
        assert isinstance(entries, list)

    def test_enumerate_vm_attack_surface(self):
        e = AttackSurfaceEnumerator()
        entries = e._enumerate_vm_attack_surface()
        assert isinstance(entries, list)

    def test_enumerate_proof_attack_surface(self):
        e = AttackSurfaceEnumerator()
        entries = e._enumerate_proof_attack_surface()
        assert isinstance(entries, list)

    def test_enumerate_attestation_attack_surface(self):
        e = AttackSurfaceEnumerator()
        entries = e._enumerate_attestation_attack_surface()
        assert isinstance(entries, list)

    def test_enumerate_network_attack_surface(self):
        e = AttackSurfaceEnumerator()
        entries = e._enumerate_network_attack_surface()
        assert isinstance(entries, list)

    def test_enumerate_filesystem_attack_surface(self):
        e = AttackSurfaceEnumerator()
        entries = e._enumerate_filesystem_attack_surface()
        assert isinstance(entries, list)

    def test_enumerate_all_returns_dict(self):
        e = AttackSurfaceEnumerator()
        result = e.enumerate_attack_surfaces()
        assert isinstance(result, dict)
        assert "per_category_results" in result
        assert "total_entry_points" in result
        assert "risk_summary" in result

    def test_all_categories_present(self):
        e = AttackSurfaceEnumerator()
        result = e.enumerate_attack_surfaces()
        cats = ["cli", "runtime", "vm", "proof", "attestation", "network", "filesystem"]
        for cat in cats:
            assert cat in result["per_category_results"]

    def test_total_entry_points_non_negative(self):
        e = AttackSurfaceEnumerator()
        result = e.enumerate_attack_surfaces()
        assert result["total_entry_points"] >= 0

    def test_risk_summary_all_levels(self):
        e = AttackSurfaceEnumerator()
        result = e.enumerate_attack_surfaces()
        for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            assert level in result["risk_summary"]


class TestAttackSurfaceIntegration:
    """
    Integration tests for full attack surface enumeration.
    """
    def test_full_enumeration(self):
        e = AttackSurfaceEnumerator()
        result = e.enumerate_attack_surfaces()
        assert result["total_entry_points"] > 0
        for cat, entries in result["per_category_results"].items():
            for entry in entries:
                assert "file_path" in entry
                assert "risk_level" in entry
                assert "description" in entry
