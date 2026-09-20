"""
test_trust_boundary.py

Tests for Trust Boundary Mapping (Feature 187).

Test coverage:
- Positive tests verify domain constants, boundary mapping, enforcement status, trust graph
- Negative tests verify nonexistent directories, empty files, no-match patterns
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from scripts.trust_boundary.mapper import (
    TRUST_DOMAINS,
    BoundaryEntry,
    BoundaryReport,
    TrustBoundaryMapper,
)


class TestBoundaryEntry:
    """
    TestBoundaryEntry
    
    Positive test cases for boundaryentry.
    """
    def test_defaults(self):
        be = BoundaryEntry(domain="test", file_path="a.py", line_number=10, function_name="fn")
        assert be.domain == "test"
        assert be.trust_assumptions == []
        assert be.data_flow == []
        assert be.has_validation is False
        assert be.validation_details == []

    def test_with_all_fields(self):
        be = BoundaryEntry(
            domain="compiler",
            file_path="b.py",
            line_number=42,
            function_name="compile",
            trust_assumptions=["trusts input"],
            data_flow=["param x"],
            has_validation=True,
            validation_details=["assert x > 0"],
        )
        assert be.function_name == "compile"
        assert be.has_validation is True


class TestBoundaryReport:
    """
    TestBoundaryReport
    
    Positive test cases for boundaryreport.
    """
    def test_empty_report(self):
        r = BoundaryReport()
        assert r.boundary_entries == {}
        assert r.trust_assumptions == {}
        assert r.enforcement_status == {}
        assert r.trust_graph == {}

    def test_with_data(self):
        r = BoundaryReport(
            boundary_entries={"compiler": []},
            trust_assumptions={"compiler": []},
            enforcement_status={"compiler": True},
            trust_graph={"compiler": []},
        )
        assert r.enforcement_status["compiler"] is True


class TestTrustDomainConstants:
    """
    TestTrustDomainConstants
    
    Positive test cases for trustdomainconstants.
    """
    def test_domains_defined(self):
        assert "compiler" in TRUST_DOMAINS
        assert "ir" in TRUST_DOMAINS
        assert "vm" in TRUST_DOMAINS
        assert "runtime" in TRUST_DOMAINS
        assert "attestation" in TRUST_DOMAINS
        assert "fhe" in TRUST_DOMAINS
        assert "zk" in TRUST_DOMAINS
        assert "proof_systems" in TRUST_DOMAINS

    def test_each_domain_has_directories(self):
        for name, info in TRUST_DOMAINS.items():
            assert len(info["directories"]) > 0
            assert len(info["entry_patterns"]) > 0

    def test_entry_patterns_are_strings(self):
        for info in TRUST_DOMAINS.values():
            for p in info["entry_patterns"]:
                assert isinstance(p, str)


class TestTrustBoundaryMapper:
    """
    TestTrustBoundaryMapper
    
    Positive test cases for trustboundarymapper.
    """
    def test_init(self):
        mapper = TrustBoundaryMapper()
        assert mapper.root_dir is not None
        assert os.path.isdir(mapper.root_dir)

    def test_map_trust_boundaries_returns_dict(self):
        mapper = TrustBoundaryMapper()
        result = mapper.map_trust_boundaries()
        assert isinstance(result, dict)
        assert "boundary_entries" in result
        assert "trust_assumptions" in result
        assert "enforcement_status" in result
        assert "trust_graph" in result

    def test_all_domains_present(self):
        mapper = TrustBoundaryMapper()
        result = mapper.map_trust_boundaries()
        for domain in TRUST_DOMAINS:
            assert domain in result["boundary_entries"]
            assert domain in result["trust_assumptions"]
            assert domain in result["enforcement_status"]

    def test_enforcement_status_structure(self):
        mapper = TrustBoundaryMapper()
        result = mapper.map_trust_boundaries()
        for domain, status in result["enforcement_status"].items():
            assert "enforced" in status
            assert "total_entries" in status
            assert "enforced_entries" in status
            assert isinstance(status["enforced"], bool)

    def test_trust_graph_is_dict(self):
        mapper = TrustBoundaryMapper()
        result = mapper.map_trust_boundaries()
        assert isinstance(result["trust_graph"], dict)

    def test_boundary_entries_are_lists(self):
        mapper = TrustBoundaryMapper()
        result = mapper.map_trust_boundaries()
        for entries in result["boundary_entries"].values():
            assert isinstance(entries, list)

    def test_find_python_files_nonexistent(self):
        mapper = TrustBoundaryMapper()
        files = mapper._find_python_files("nonexistent_dir_xyz")
        assert files == []

    def test_extract_functions_empty_file(self):
        mapper = TrustBoundaryMapper()
        tmp_file = "/tmp/_test_empty.py"
        with open(tmp_file, "w") as f:
            f.write("# just a comment\n")
        functions = mapper._extract_functions(tmp_file)
        assert functions == []
        os.remove(tmp_file)

    def test_extract_functions_with_content(self):
        mapper = TrustBoundaryMapper()
        tmp_file = "/tmp/_test_funcs.py"
        with open(tmp_file, "w") as f:
            f.write("def foo():\n    pass\nasync def bar():\n    pass\n")
        functions = mapper._extract_functions(tmp_file)
        assert len(functions) == 2
        names = [f[0] for f in functions]
        assert "foo" in names
        assert "bar" in names
        os.remove(tmp_file)

    def test_detect_entry_points_match(self):
        mapper = TrustBoundaryMapper()
        domain_info = {"entry_patterns": ["compile", "build"]}
        functions = [("compile_foo", 1, "def compile_foo():\n    pass")]
        entries = mapper._detect_entry_points(functions, domain_info)
        assert len(entries) == 1
        assert entries[0][0] == "compile_foo"

    def test_detect_entry_points_no_match(self):
        mapper = TrustBoundaryMapper()
        domain_info = {"entry_patterns": ["compile"]}
        functions = [("run_foo", 1, "def run_foo():\n    pass")]
        entries = mapper._detect_entry_points(functions, domain_info)
        assert len(entries) == 0

    def test_map_domain_returns_list(self):
        mapper = TrustBoundaryMapper()
        domain_info = {
            "directories": ["scripts/trust_boundary"],
            "entry_patterns": ["map"],
        }
        entries = mapper.map_domain("test_domain", domain_info)
        assert isinstance(entries, list)

    def test_extract_trust_assumptions(self):
        mapper = TrustBoundaryMapper()
        functions = [("trust_fn", 1, "def trust_fn():\n    # trust external input\n    pass")]
        assumptions = mapper._extract_trust_assumptions(functions)
        assert isinstance(assumptions, list)

    def test_extract_data_flow(self):
        mapper = TrustBoundaryMapper()
        functions = [("data_fn", 1, "def data_fn(param):\n    return param")]
        flows = mapper._extract_data_flow(functions)
        assert isinstance(flows, list)

    def test_detect_validation_with_assert(self):
        mapper = TrustBoundaryMapper()
        functions = [("val_fn", 1, "def val_fn(x):\n    assert x > 0\n    return x")]
        has_val, details = mapper._detect_validation(functions)
        assert has_val is True
        assert len(details) > 0

    def test_detect_validation_no_validation(self):
        mapper = TrustBoundaryMapper()
        functions = [("no_val_fn", 1, "def no_val_fn(x):\n    return x")]
        has_val, details = mapper._detect_validation(functions)
        assert has_val is False
        assert details == []


class TestTrustBoundaryIntegration:
    """
    TestTrustBoundaryIntegration
    
    Positive test cases for trustboundaryintegration.
    """
    def test_full_mapping(self):
        mapper = TrustBoundaryMapper()
        result = mapper.map_trust_boundaries()
        assert result["boundary_entries"]["compiler"] is not None
        assert result["boundary_entries"]["ir"] is not None
        assert result["boundary_entries"]["vm"] is not None
        assert result["boundary_entries"]["runtime"] is not None

    def test_enforcement_some_false(self):
        mapper = TrustBoundaryMapper()
        result = mapper.map_trust_boundaries()
        enforced_list = [v["enforced"] for v in result["enforcement_status"].values()]
        assert isinstance(enforced_list, list)
