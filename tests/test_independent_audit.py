"""
test_independent_audit.py

Tests for Independent Audit (Feature 182).

Test coverage:
- Positive tests verify reachability, proof, benchmark, evidence, and claim audits
- Negative tests verify missing directories, unreferenced phases, no-claim code
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.independent_audit.auditor import IndependentAuditor, independent_audit


# =========================================================================
# Reachability Audit Tests
# =========================================================================

class TestIndependentAuditReachability:
    """
    TestIndependentAuditReachability
    
    Positive test cases for independentauditreachability.
    """
    def test_reachability_returns_nonempty(self):
        auditor = IndependentAuditor()
        findings = auditor.check_reachability()
        assert isinstance(findings, list)
        assert len(findings) > 0

    def test_reachability_returns_list(self):
        auditor = IndependentAuditor()
        findings = auditor.check_reachability()
        assert isinstance(findings, list)
        for f in findings:
            assert "phase" in f or "issue" in f


# =========================================================================
# Proof Audit Tests
# =========================================================================

class TestIndependentAuditProofs:
    """
    TestIndependentAuditProofs
    
    Positive test cases for independentauditproofs.
    """
    def test_proof_audit_returns_list(self):
        auditor = IndependentAuditor()
        findings = auditor.check_proofs()
        assert isinstance(findings, list)

    def test_proof_audit_has_detail_field(self):
        auditor = IndependentAuditor()
        findings = auditor.check_proofs()
        for f in findings:
            assert "detail" in f or "issue" in f


# =========================================================================
# Benchmark Audit Tests
# =========================================================================

class TestIndependentAuditBenchmarks:
    """
    TestIndependentAuditBenchmarks
    
    Positive test cases for independentauditbenchmarks.
    """
    def test_benchmark_audit_returns_list(self):
        auditor = IndependentAuditor()
        findings = auditor.check_benchmarks()
        assert isinstance(findings, list)

    def test_benchmark_audit_has_assertions_field(self):
        auditor = IndependentAuditor()
        findings = auditor.check_benchmarks()
        for f in findings:
            if "exists" in f:
                assert "has_assertions" in f or "issue" in f


# =========================================================================
# Evidence Audit Tests
# =========================================================================

class TestIndependentAuditEvidence:
    """
    TestIndependentAuditEvidence
    
    Positive test cases for independentauditevidence.
    """
    def test_evidence_checks_build_dir(self):
        auditor = IndependentAuditor()
        findings = auditor.check_evidence()
        assert isinstance(findings, list)
        found_reports = any(
            f.get("file", "").endswith((".json", ".md", ".txt"))
            for f in findings if "file" in f
        )
        assert found_reports or all("issue" in f for f in findings)

    def test_evidence_shows_size(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report = os.path.join(tmpdir, "report.json")
            with open(report, "w") as f:
                f.write(json.dumps({"test": 1}))
            auditor = IndependentAuditor(root_dir=tmpdir)
            os.makedirs(os.path.join(tmpdir, "scripts"), exist_ok=True)
            auditor.build_dir = tmpdir
            findings = auditor.check_evidence()
            assert len(findings) >= 1
            assert findings[0]["size_bytes"] > 0


# =========================================================================
# Claims Audit Tests
# =========================================================================

class TestIndependentAuditClaims:
    """
    TestIndependentAuditClaims
    
    Positive test cases for independentauditclaims.
    """
    def test_claim_audit_scans_scripts(self):
        auditor = IndependentAuditor()
        findings = auditor.check_claims()
        assert isinstance(findings, list)

    def test_claim_audit_detects_keywords(self, tmpdir):
        scripts_dir = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts_dir)
        fake = os.path.join(scripts_dir, "fake.py")
        with open(fake, "w") as f:
            f.write("# this is 100% secure and unbreakable\nx = 1\n")
        auditor = IndependentAuditor(root_dir=tmpdir)
        auditor.scripts_dir = scripts_dir
        findings = auditor.check_claims()
        assert any("100%" in str(f) for f in findings)
        assert any("secure" in str(f) for f in findings)

    def test_claim_audit_no_false_positives(self, tmpdir):
        scripts_dir = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts_dir)
        clean = os.path.join(scripts_dir, "clean.py")
        with open(clean, "w") as f:
            f.write("x = 42\ny = x + 1\n")
        auditor = IndependentAuditor(root_dir=tmpdir)
        auditor.scripts_dir = scripts_dir
        findings = auditor.check_claims()
        assert len(findings) == 0


# =========================================================================
# Top-Level Function Tests
# =========================================================================

class TestIndependentAuditTopLevel:
    """
    TestIndependentAuditTopLevel
    
    Positive test cases for independentaudittoplevel.
    """
    def test_independent_audit_returns_dict(self):
        result = independent_audit()
        assert isinstance(result, dict)
        for key in ("reachability_audit", "proof_audit", "benchmark_audit", "evidence_audit", "claim_audit"):
            assert key in result, f"Missing key: {key}"
            assert isinstance(result[key], list), f"{key} should be a list"

    def test_independent_audit_all_keys_present(self):
        result = independent_audit()
        expected_keys = {"reachability_audit", "proof_audit", "benchmark_audit", "evidence_audit", "claim_audit"}
        assert set(result.keys()) == expected_keys


# =========================================================================
# Auditor Class Tests
# =========================================================================

class TestIndependentAuditorClass:
    """
    TestIndependentAuditorClass
    
    Positive test cases for independentauditorclass.
    """
    def test_init_with_root(self):
        auditor = IndependentAuditor(root_dir="/tmp")
        assert auditor.root == "/tmp"

    def test_init_default_root(self):
        auditor = IndependentAuditor()
        assert os.path.isdir(auditor.scripts_dir)

    def test_check_reachability_no_build_py(self, tmpdir):
        scripts = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts)
        auditor = IndependentAuditor(root_dir=tmpdir)
        auditor.scripts_dir = scripts
        findings = auditor.check_reachability()
        assert any("not found" in str(f.get("issue", "")) for f in findings)


# =========================================================================
# Negative Tests
# =========================================================================

class TestReachabilityNegative:
    """
    TestReachabilityNegative
    
    Negative test cases — exercises error handling and edge cases for reachabilitynegative.
    """
    def test_reachability_unreferenced_phase(self, tmpdir):
        scripts_dir = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts_dir)
        build_py = os.path.join(scripts_dir, "build.py")
        with open(build_py, "w") as f:
            f.write("x = 1\n")
        phase_dir = os.path.join(scripts_dir, "phases")
        os.makedirs(phase_dir)
        unreachable = os.path.join(phase_dir, "phase_ghost.py")
        with open(unreachable, "w") as f:
            f.write("def phase_ghost():\n    pass\n")
        auditor = IndependentAuditor(root_dir=tmpdir)
        auditor.scripts_dir = scripts_dir
        findings = auditor.check_reachability()
        ghost_findings = [f for f in findings if "ghost" in str(f)]
        assert len(ghost_findings) >= 1
        assert not ghost_findings[0]["reachable"]


class TestProofAuditNegative:
    """
    TestProofAuditNegative
    
    Negative test cases — exercises error handling and edge cases for proofauditnegative.
    """
    def test_proof_audit_no_proofs_dir(self, tmpdir):
        auditor = IndependentAuditor(root_dir=tmpdir)
        findings = auditor.check_proofs()
        assert any("missing" in str(f.get("issue", "")) for f in findings)

    def test_proof_audit_no_proof_logic(self, tmpdir):
        scripts_dir = os.path.join(tmpdir, "scripts")
        proofs_dir = os.path.join(scripts_dir, "proofs")
        os.makedirs(proofs_dir)
        stub = os.path.join(proofs_dir, "stub.py")
        with open(stub, "w") as f:
            f.write("x = 1\n")
        auditor = IndependentAuditor(root_dir=tmpdir)
        auditor.scripts_dir = scripts_dir
        findings = auditor.check_proofs()
        assert len(findings) >= 1
        assert not any(f.get("has_proof_logic", True) for f in findings if "stub" in f.get("file", ""))


class TestBenchmarkNegative:
    """
    TestBenchmarkNegative
    
    Negative test cases — exercises error handling and edge cases for benchmarknegative.
    """
    def test_benchmark_missing_tests_dir(self, tmpdir):
        auditor = IndependentAuditor(root_dir=tmpdir)
        findings = auditor.check_benchmarks()
        assert any("missing" in str(f.get("issue", "")) for f in findings)

    def test_benchmark_no_assertions(self, tmpdir):
        tests_dir = os.path.join(tmpdir, "tests")
        os.makedirs(tests_dir)
        bench_file = os.path.join(tests_dir, "bench_empty.py")
        with open(bench_file, "w") as f:
            f.write("def bench_nothing():\n    pass\n")
        auditor = IndependentAuditor(root_dir=tmpdir)
        auditor.tests_dir = tests_dir
        findings = auditor.check_benchmarks()
        matching = [f for f in findings if "bench_empty" in f.get("file", "")]
        assert len(matching) >= 1
        assert not matching[0]["has_assertions"]


class TestClaimAuditNegative:
    """
    TestClaimAuditNegative
    
    Negative test cases — exercises error handling and edge cases for claimauditnegative.
    """
    def test_claim_no_claims_in_clean_code(self, tmpdir):
        scripts_dir = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts_dir)
        clean = os.path.join(scripts_dir, "clean.py")
        with open(clean, "w") as f:
            f.write("def add(a, b):\n    return a + b\n")
        auditor = IndependentAuditor(root_dir=tmpdir)
        auditor.scripts_dir = scripts_dir
        findings = auditor.check_claims()
        assert len(findings) == 0


class TestEvidenceNegative:
    """
    TestEvidenceNegative
    
    Negative test cases — exercises error handling and edge cases for evidencenegative.
    """
    def test_evidence_empty_build_dir(self, tmpdir):
        auditor = IndependentAuditor(root_dir=tmpdir)
        auditor.build_dir = tmpdir
        findings = auditor.check_evidence()
        assert len(findings) == 0
