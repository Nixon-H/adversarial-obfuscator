"""
test_proof_coverage.py

Tests for Proof Coverage Analysis.

Test coverage:
- Positive tests verify proof module detection, coverage computation, report generation
- Negative tests verify empty modules, missing proofs, edge cases
"""
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from scripts.proof_coverage.coverage import ProofCoverage, ProofCoverageReport
from scripts.proof_coverage.scanner import ProofCoverageScanner
from scripts.proof_coverage.aggregator import (
    aggregate_proof_coverage,
    compute_overall_score,
    generate_recommendations,
    merge_reports,
)
from scripts.proof_coverage.inspector import (
    check_proof_validity,
    inspect_preservation_module,
    inspect_proofs_module,
    probe_z3_availability,
)


class TestProofCoverageDataclass:
    """
    TestProofCoverageDataclass
    
    Positive test cases for proofcoveragedataclass.
    """
    def test_dataclass_defaults(self):
        pc = ProofCoverage(stage="ast_ir")
        assert pc.stage == "ast_ir"
        assert pc.has_proof is False
        assert pc.proof_type == "none"
        assert pc.functions_covered == 0
        assert pc.functions_total == 0
        assert pc.coverage_percent == 0.0
        assert pc.proof_validated is False
        assert pc.last_validated != ""

    def test_dataclass_with_values(self):
        pc = ProofCoverage(
            stage="llvm_vm",
            has_proof=True,
            proof_type="z3",
            functions_covered=18,
            functions_total=20,
            proof_validated=True,
        )
        assert pc.stage == "llvm_vm"
        assert pc.has_proof is True
        assert pc.proof_type == "z3"
        assert pc.functions_covered == 18
        assert pc.coverage_percent == 90.0

    def test_dataclass_to_dict_roundtrip(self):
        pc = ProofCoverage(
            stage="watermark",
            has_proof=True,
            proof_type="z3",
            functions_covered=4,
            functions_total=4,
            proof_validated=True,
        )
        d = pc.to_dict()
        assert d["stage"] == "watermark"
        assert d["coverage_percent"] == 100.0
        restored = ProofCoverage.from_dict(d)
        assert restored.stage == pc.stage
        assert restored.has_proof == pc.has_proof
        assert restored.functions_covered == pc.functions_covered

    def test_dataclass_proof_type_default(self):
        pc = ProofCoverage(stage="jit", has_proof=True)
        assert pc.proof_type == "structural"

    def test_dataclass_coverage_auto_calc(self):
        pc = ProofCoverage(stage="mutation", has_proof=True, functions_covered=1, functions_total=2)
        assert pc.coverage_percent == 50.0


class TestProofCoverageReport:
    """
    TestProofCoverageReport
    
    Positive test cases for proofcoveragereport.
    """
    def test_report_defaults(self):
        report = ProofCoverageReport()
        assert report.overall_coverage == 0.0
        assert report.stage_scores == {}
        assert report.uncovered_stages == []
        assert report.partially_covered_stages == []
        assert report.recommendations == []
        assert report.generated_at != ""

    def test_report_with_stages(self):
        pc1 = ProofCoverage(stage="ast_ir", has_proof=True, proof_validated=True)
        pc2 = ProofCoverage(stage="ir_llvm", has_proof=False)
        report = ProofCoverageReport(
            overall_coverage=50.0,
            stage_scores={"ast_ir": pc1, "ir_llvm": pc2},
            uncovered_stages=["ir_llvm"],
            recommendations=["Add proofs for ir_llvm"],
        )
        assert report.overall_coverage == 50.0
        assert len(report.uncovered_stages) == 1

    def test_report_to_dict_roundtrip(self):
        pc = ProofCoverage(stage="ast_ir", has_proof=True, proof_validated=True, functions_covered=3, functions_total=3)
        report = ProofCoverageReport(
            overall_coverage=100.0,
            stage_scores={"ast_ir": pc},
        )
        d = report.to_dict()
        assert d["overall_coverage"] == 100.0
        restored = ProofCoverageReport.from_dict(d)
        assert restored.overall_coverage == report.overall_coverage
        assert "ast_ir" in restored.stage_scores


class TestCoverageScanner:
    """
    TestCoverageScanner
    
    Positive test cases for coveragescanner.
    """
    def test_scanner_scan(self):
        scanner = ProofCoverageScanner()
        results = scanner.scan_all()
        assert len(results) == 7
        for stage in ["ast_ir", "ir_llvm", "llvm_vm", "watermark", "fragmentation", "mutation", "jit"]:
            assert stage in results
            assert isinstance(results[stage], ProofCoverage)
            assert results[stage].stage == stage

    def test_scanner_ast_ir_proof(self):
        scanner = ProofCoverageScanner()
        pc = scanner.check_ast_ir_proof()
        assert isinstance(pc, ProofCoverage)
        assert pc.stage == "ast_ir"

    def test_scanner_watermark_proof(self):
        scanner = ProofCoverageScanner()
        pc = scanner.check_watermark_proof()
        assert isinstance(pc, ProofCoverage)
        assert pc.stage == "watermark"

    def test_scanner_jit_proof(self):
        scanner = ProofCoverageScanner()
        pc = scanner.check_jit_proof()
        assert isinstance(pc, ProofCoverage)
        assert pc.stage == "jit"


class TestAggregation:
    """
    TestAggregation
    
    Positive test cases for aggregation.
    """
    def test_aggregate_coverage(self):
        scanner = ProofCoverageScanner()
        results = scanner.scan_all()
        aggregated = aggregate_proof_coverage(results)
        assert len(aggregated) == 7

    def test_aggregate_empty(self):
        aggregated = aggregate_proof_coverage({})
        assert aggregated == {}

    def test_aggregate_fills_missing(self):
        results = {"ast_ir": ProofCoverage(stage="ast_ir")}
        aggregated = aggregate_proof_coverage(results)
        assert "ast_ir" in aggregated
        assert "ir_llvm" in aggregated
        assert "llvm_vm" in aggregated

    def test_compute_overall_score(self):
        scores = {
            "ast_ir": ProofCoverage(stage="ast_ir", has_proof=True, proof_validated=True),
            "ir_llvm": ProofCoverage(stage="ir_llvm", has_proof=True, proof_validated=True),
            "llvm_vm": ProofCoverage(stage="llvm_vm", has_proof=True, proof_validated=True),
            "watermark": ProofCoverage(stage="watermark", has_proof=True, proof_validated=True),
            "fragmentation": ProofCoverage(stage="fragmentation", has_proof=True, proof_validated=True),
            "mutation": ProofCoverage(stage="mutation", has_proof=True, proof_validated=True),
            "jit": ProofCoverage(stage="jit", has_proof=True, proof_validated=True),
        }
        score = compute_overall_score(scores)
        assert score == 100.0

    def test_compute_overall_score_zero(self):
        scores = {
            "ast_ir": ProofCoverage(stage="ast_ir"),
            "ir_llvm": ProofCoverage(stage="ir_llvm"),
            "llvm_vm": ProofCoverage(stage="llvm_vm"),
            "watermark": ProofCoverage(stage="watermark"),
            "fragmentation": ProofCoverage(stage="fragmentation"),
            "mutation": ProofCoverage(stage="mutation"),
            "jit": ProofCoverage(stage="jit"),
        }
        score = compute_overall_score(scores)
        assert score == 0.0

    def test_compute_overall_half_proven(self):
        scores = {
            "ast_ir": ProofCoverage(stage="ast_ir", has_proof=True, proof_validated=True),
            "ir_llvm": ProofCoverage(stage="ir_llvm", has_proof=False),
            "llvm_vm": ProofCoverage(stage="llvm_vm", has_proof=False),
            "watermark": ProofCoverage(stage="watermark", has_proof=False),
            "fragmentation": ProofCoverage(stage="fragmentation", has_proof=False),
            "mutation": ProofCoverage(stage="mutation", has_proof=False),
            "jit": ProofCoverage(stage="jit", has_proof=False),
        }
        score = compute_overall_score(scores)
        assert 0 < score < 100

    def test_generate_recommendations(self):
        scores = {
            "ast_ir": ProofCoverage(stage="ast_ir", has_proof=False),
            "ir_llvm": ProofCoverage(stage="ir_llvm", has_proof=True, proof_validated=True),
            "llvm_vm": ProofCoverage(stage="llvm_vm", has_proof=True, proof_validated=False),
            "watermark": ProofCoverage(stage="watermark", has_proof=False),
            "fragmentation": ProofCoverage(stage="fragmentation", has_proof=False),
            "mutation": ProofCoverage(stage="mutation", has_proof=False),
            "jit": ProofCoverage(stage="jit", has_proof=False),
        }
        recs = generate_recommendations(scores)
        assert len(recs) > 0
        assert any("Uncovered" in r for r in recs)
        assert any("unvalidated" in r for r in recs)

    def test_merge_reports(self):
        pc1 = ProofCoverage(stage="ast_ir", has_proof=True, proof_validated=True, functions_covered=3, functions_total=3)
        pc2 = ProofCoverage(stage="ast_ir", has_proof=True, proof_validated=True, functions_covered=2, functions_total=3)
        r1 = ProofCoverageReport(overall_coverage=100.0, stage_scores={"ast_ir": pc1})
        r2 = ProofCoverageReport(overall_coverage=66.67, stage_scores={"ast_ir": pc2})
        merged = merge_reports([r1, r2])
        assert merged.overall_coverage >= 0
        assert "ast_ir" in merged.stage_scores
        assert merged.stage_scores["ast_ir"].functions_covered == 2


class TestInspector:
    """
    TestInspector
    
    Positive test cases for inspector.
    """
    def test_inspect_preservation(self):
        results = inspect_preservation_module()
        assert isinstance(results, dict)
        assert "ast_ir" in results
        assert isinstance(results["ast_ir"], bool)

    def test_inspect_proofs(self):
        results = inspect_proofs_module()
        assert isinstance(results, dict)
        assert "fragment_safety" in results
        frag = results["fragment_safety"]
        assert "has_prover" in frag
        assert frag["has_prover"] is True

    def test_probe_z3(self):
        available, error = probe_z3_availability()
        assert isinstance(available, bool)
        assert error is None or isinstance(error, str)

    def test_check_proof_validity(self):
        result = check_proof_validity("scripts.proofs.fragment_safety")
        assert isinstance(result, bool)


class TestNegativeCases:
    """
    TestNegativeCases
    
    Negative test cases — exercises error handling and edge cases for negativecases.
    """
    def test_empty_stages(self):
        scanner = ProofCoverageScanner()
        empty = {}
        aggregated = aggregate_proof_coverage(empty)
        assert aggregated == {}

    def test_zero_coverage(self):
        scores = {
            "ast_ir": ProofCoverage(stage="ast_ir", has_proof=False),
            "ir_llvm": ProofCoverage(stage="ir_llvm", has_proof=False),
            "llvm_vm": ProofCoverage(stage="llvm_vm", has_proof=False),
            "watermark": ProofCoverage(stage="watermark", has_proof=False),
            "fragmentation": ProofCoverage(stage="fragmentation", has_proof=False),
            "mutation": ProofCoverage(stage="mutation", has_proof=False),
            "jit": ProofCoverage(stage="jit", has_proof=False),
        }
        score = compute_overall_score(scores)
        assert score == 0.0

    def test_invalid_stage_name(self):
        pc = ProofCoverage(stage="nonexistent_stage")
        assert pc.stage == "nonexistent_stage"
        d = pc.to_dict()
        assert d["stage"] == "nonexistent_stage"
        restored = ProofCoverage.from_dict(d)
        assert restored.stage == "nonexistent_stage"

    def test_empty_report_merge(self):
        merged = merge_reports([])
        assert isinstance(merged, ProofCoverageReport)
        assert merged.overall_coverage == 0.0
        assert merged.stage_scores == {}

    def test_partial_stage_coverage(self):
        pc = ProofCoverage(stage="fragmentation", has_proof=True, proof_type="z3",
                           functions_covered=1, functions_total=4, proof_validated=False)
        assert pc.coverage_percent == 25.0
        assert pc.proof_validated is False
        d = pc.to_dict()
        assert d["coverage_percent"] == 25.0
