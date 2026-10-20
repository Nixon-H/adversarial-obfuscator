"""
test_self_audit.py

Tests for Self-Audit Agent (Feature 180).

Test coverage:
- Positive tests verify source audit, test audit, reachability, proofs, benchmarks,
  claims, metrics, debt, assumptions, reality, and full run
- Negative tests verify missing files, syntax errors, empty directories
"""
import json
import os
import sys
import tempfile


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.self_audit import AuditFinding, AuditCategory, AuditReport, score_to_grade
from scripts.self_audit.auditor import SelfAuditor


# =========================================================================
# Domain model tests (positive + negative)
# =========================================================================

class TestAuditFinding:
    """
    Tests for AuditFinding dataclass defaults and full construction.
    """
    def test_default_construction(self):
        af = AuditFinding(category="test", severity="critical",
                          title="Test", description="Desc", recommendation="Rec")
        assert af.category == "test"
        assert af.severity == "critical"
        assert af.file is None
        assert af.line is None

    def test_full_construction(self):
        af = AuditFinding(category="source", severity="major",
                          title="Unsafe import", description="os imported",
                          recommendation="Sandbox it",
                          file="/tmp/test.py", line=42,
                          metric_name="unsafe_imports", metric_value=1.0, threshold=0.0)
        assert af.metric_name == "unsafe_imports"
        assert af.metric_value == 1.0


class TestAuditCategory:
    """
    Tests for AuditCategory: pass/fail threshold, percentage, findings list.
    """
    def test_passed_when_above_70(self):
        cat = AuditCategory(name="tests", score=80, max_score=100)
        assert cat.passed is True
        assert cat.percentage == 80.0

    def test_failed_when_below_70(self):
        cat = AuditCategory(name="tests", score=30, max_score=100)
        assert cat.passed is False
        assert cat.percentage == 30.0

    def test_percentage_zero_on_zero_max(self):
        cat = AuditCategory(name="empty", score=0, max_score=0)
        assert cat.percentage == 0.0
        assert cat.passed is False

    def test_findings_list_empty_by_default(self):
        cat = AuditCategory(name="empty", score=100, max_score=100)
        assert cat.findings == []


class TestAuditReport:
    """
    Tests for AuditReport defaults and dict serialization.
    """
    def test_default_values(self):
        report = AuditReport(timestamp="now", overall_score=0.0, overall_grade="F")
        assert report.total_findings == 0
        assert report.critical_findings == 0
        assert report.major_findings == 0
        assert report.minor_findings == 0
        assert report.categories == {}

    def test_to_dict_structure(self):
        cat = AuditCategory(name="source", score=80, max_score=100,
                            findings=[AuditFinding("source", "major", "X", "Y", "Z")])
        report = AuditReport(
            timestamp="2025-01-01T00:00:00Z",
            overall_score=85.0,
            overall_grade="B",
            categories={"source": cat},
            total_findings=1, critical_findings=0, major_findings=1, minor_findings=0,
        )
        d = report.to_dict()
        assert d["overall_score"] == 85.0
        assert d["overall_grade"] == "B"
        assert d["total_findings"] == 1
        assert "source" in d["categories"]
        assert d["categories"]["source"]["passed"] is True
        assert len(d["categories"]["source"]["findings"]) == 1


class TestScoreToGrade:
    """
    Tests for A/B/C/D/F grade boundaries.
    """
    def test_a_grade(self):
        assert score_to_grade(95) == "A"
        assert score_to_grade(100) == "A"
        assert score_to_grade(90) == "A"

    def test_b_grade(self):
        assert score_to_grade(89) == "B"
        assert score_to_grade(80) == "B"
        assert score_to_grade(85) == "B"

    def test_c_grade(self):
        assert score_to_grade(79) == "C"
        assert score_to_grade(70) == "C"
        assert score_to_grade(75) == "C"

    def test_d_grade(self):
        assert score_to_grade(69) == "D"
        assert score_to_grade(50) == "D"
        assert score_to_grade(55) == "D"

    def test_f_grade(self):
        assert score_to_grade(49) == "F"
        assert score_to_grade(0) == "F"
        assert score_to_grade(25) == "F"


# =========================================================================
# SelfAuditor tests
# =========================================================================

class TestSelfAuditorSource:
    """
    Tests for SelfAuditor source auditing: valid, missing, syntax error, empty, unsafe imports.
    """
    def test_audit_source_valid(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def foo():\n    return 42\n")
            path = f.name
        try:
            auditor = SelfAuditor()
            cat = auditor.audit_source(path)
            assert cat.name == "source"
            assert cat.score > 0
            assert cat.max_score == 100
        finally:
            os.unlink(path)

    def test_audit_source_missing_file(self):
        auditor = SelfAuditor()
        cat = auditor.audit_source("/nonexistent/path.py")
        assert cat.score == 0.0
        assert len(cat.findings) > 0

    def test_audit_source_syntax_error(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def broken(\n")
            path = f.name
        try:
            auditor = SelfAuditor()
            cat = auditor.audit_source(path)
            assert cat.score == 0.0
        finally:
            os.unlink(path)

    def test_audit_source_empty_no_functions(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x = 1\n")
            path = f.name
        try:
            auditor = SelfAuditor()
            cat = auditor.audit_source(path)
            assert cat.score <= 70
            assert any("No functions" in f.title for f in cat.findings)
        finally:
            os.unlink(path)

    def test_audit_source_unsafe_imports(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import os\nimport subprocess\ndef run():\n    return 1\n")
            path = f.name
        try:
            auditor = SelfAuditor()
            cat = auditor.audit_source(path)
            assert any("unsafe" in f.title.lower() for f in cat.findings)
        finally:
            os.unlink(path)

    def test_audit_source_large_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def x():\n    pass\n" * 3000)
            path = f.name
        try:
            auditor = SelfAuditor()
            cat = auditor.audit_source(path)
            assert any("large" in f.title.lower() for f in cat.findings)
        finally:
            os.unlink(path)


class TestSelfAuditorTests:
    """
    TestSelfAuditorTests
    
    Positive test cases for selfauditors.
    """
    def test_audit_tests_no_tests_dir(self):
        auditor = SelfAuditor()
        cat = auditor.audit_tests()
        assert cat.score >= 0
        assert cat.name == "tests"

    def test_audit_tests_has_functions(self):
        auditor = SelfAuditor()
        cat = auditor.audit_tests()
        assert cat.max_score > 0


class TestSelfAuditorReachability:
    """
    TestSelfAuditorReachability
    
    Positive test cases for selfauditorreachability.
    """
    def test_audit_reachability_no_report(self):
        auditor = SelfAuditor(build_dir="/tmp/nonexistent_build_xyz")
        cat = auditor.audit_reachability()
        assert cat.score == 0.0

    def test_audit_reachability_with_report(self):
        auditor = SelfAuditor()
        report = {
            "total_features": 100,
            "reachable": list(range(80)),
            "partially_reachable": list(range(10)),
            "unreachable": list(range(10)),
        }
        cat = auditor.audit_reachability(report)
        assert cat.score > 0
        assert cat.score <= 100

    def test_audit_reachability_critical(self):
        auditor = SelfAuditor()
        report = {
            "total_features": 10,
            "reachable": [],
            "partially_reachable": [],
            "unreachable": list(range(10)),
        }
        cat = auditor.audit_reachability(report)
        assert any(f.severity == "critical" for f in cat.findings)
        assert cat.score < 50


class TestSelfAuditorProofs:
    """
    TestSelfAuditorProofs
    
    Positive test cases for selfauditorproofs.
    """
    def test_audit_proofs_no_dir(self):
        auditor = SelfAuditor(build_dir="/tmp/nonexistent_build_xyz")
        cat = auditor.audit_proofs()
        assert cat.score == 0.0

    def test_audit_proofs_with_certs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proofs_dir = os.path.join(tmpdir, "proofs", "vm")
            os.makedirs(proofs_dir)
            with open(os.path.join(proofs_dir, "vm_proof_add.json"), "w") as f:
                json.dump({"validated": True, "equivalent": True}, f)
            with open(os.path.join(proofs_dir, "vm_proof_sub.json"), "w") as f:
                json.dump({"validated": False, "equivalent": False}, f)
            auditor = SelfAuditor(build_dir=tmpdir)
            cat = auditor.audit_proofs()
            assert cat.score > 0
            assert len(cat.findings) > 0


class TestSelfAuditorBenchmarks:
    """
    TestSelfAuditorBenchmarks
    
    Positive test cases for selfauditorbenchmarks.
    """
    def test_audit_benchmarks_no_report(self):
        auditor = SelfAuditor(build_dir="/tmp/nonexistent_build_xyz")
        cat = auditor.audit_benchmarks()
        assert cat.score == 0.0

    def test_audit_benchmarks_with_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "benchmark_report.json"), "w") as f:
                json.dump({"overall": 0.95, "subscores": {"naming": {"score": 0.8}}}, f)
            auditor = SelfAuditor(build_dir=tmpdir)
            cat = auditor.audit_benchmarks()
            assert cat.score > 50


class TestSelfAuditorClaims:
    """
    TestSelfAuditorClaims
    
    Positive test cases for selfauditorclaims.
    """
    def test_audit_claims_no_report(self):
        auditor = SelfAuditor(build_dir="/tmp/nonexistent_build_xyz")
        cat = auditor.audit_claims()
        assert cat.score == 0.0

    def test_audit_claims_with_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "evidence_report.json"), "w") as f:
                json.dump({
                    "total_claims": 10,
                    "total_evidence": 20,
                    "verified_evidence": 18,
                    "coverage_pct": 90.0,
                    "unverified_claims": [],
                }, f)
            auditor = SelfAuditor(build_dir=tmpdir)
            cat = auditor.audit_claims()
            assert cat.score > 70


class TestSelfAuditorMetrics:
    """
    TestSelfAuditorMetrics
    
    Positive test cases for selfauditormetrics.
    """
    def test_audit_metrics_no_report(self):
        auditor = SelfAuditor(build_dir="/tmp/nonexistent_build_xyz")
        cat = auditor.audit_metrics()
        assert cat.score == 0.0

    def test_audit_metrics_good_scores(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "metrics_report.json"), "w") as f:
                json.dump({"overall": 0.85}, f)
            auditor = SelfAuditor(build_dir=tmpdir)
            cat = auditor.audit_metrics()
            assert cat.score > 70

    def test_audit_metrics_low_scores(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "metrics_report.json"), "w") as f:
                json.dump({"overall": 0.3}, f)
            auditor = SelfAuditor(build_dir=tmpdir)
            cat = auditor.audit_metrics()
            assert any(f.severity == "critical" for f in cat.findings)


class TestSelfAuditorDebt:
    """
    TestSelfAuditorDebt
    
    Positive test cases for selfauditordebt.
    """
    def test_audit_debt_no_stubs(self):
        auditor = SelfAuditor()
        cat = auditor.audit_debt()
        assert cat.max_score == 100
        assert cat.score >= 0

    def test_audit_debt_penalizes_stubs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scripts_dir = os.path.join(tmpdir, "scripts")
            os.makedirs(scripts_dir)
            for i in range(10):
                with open(os.path.join(scripts_dir, f"stub_{i}.py"), "w") as f:
                    f.write(f"def stub_{i}():\n    pass\n")
            import scripts.self_audit.auditor as aud_mod
            old_root_val = getattr(aud_mod, "_ROOT", None)
            try:
                aud_mod._ROOT = tmpdir
                auditor = SelfAuditor()
                cat = auditor.audit_debt()
                assert any("stub" in f.title.lower() for f in cat.findings)
            finally:
                aud_mod._ROOT = old_root_val if old_root_val else os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )


class TestSelfAuditorAssumptions:
    """
    TestSelfAuditorAssumptions
    
    Positive test cases for selfauditorassumptions.
    """
    def test_audit_assumptions_no_report(self):
        auditor = SelfAuditor(build_dir="/tmp/nonexistent_build_xyz")
        cat = auditor.audit_assumptions()
        assert cat.score == 0.0

    def test_audit_assumptions_clean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "assumption_report.json"), "w") as f:
                json.dump({
                    "total_count": 20,
                    "satisfied_count": 20,
                    "unsatisfied_count": 0,
                    "unknown_count": 0,
                    "critical_unsatisfied": [],
                }, f)
            auditor = SelfAuditor(build_dir=tmpdir)
            cat = auditor.audit_assumptions()
            assert cat.score >= 90

    def test_audit_assumptions_critical(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "assumption_report.json"), "w") as f:
                json.dump({
                    "total_count": 20,
                    "satisfied_count": 10,
                    "unsatisfied_count": 5,
                    "unknown_count": 5,
                    "critical_unsatisfied": ["z3 missing"],
                }, f)
            auditor = SelfAuditor(build_dir=tmpdir)
            cat = auditor.audit_assumptions()
            assert any(f.severity == "critical" for f in cat.findings)
            assert cat.score < 60


class TestSelfAuditorReality:
    """
    TestSelfAuditorReality
    
    Positive test cases for selfauditorreality.
    """
    def test_audit_reality_no_report(self):
        auditor = SelfAuditor(build_dir="/tmp/nonexistent_build_xyz")
        cat = auditor.audit_reality()
        assert cat.score == 0.0

    def test_audit_reality_good(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "reality_report.json"), "w") as f:
                json.dump({
                    "overall_reality_score": 85.0,
                    "grade": "B",
                    "critical_gaps": [],
                }, f)
            auditor = SelfAuditor(build_dir=tmpdir)
            cat = auditor.audit_reality()
            assert cat.score > 70

    def test_audit_reality_poor(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "reality_report.json"), "w") as f:
                json.dump({
                    "overall_reality_score": 30.0,
                    "grade": "F",
                    "critical_gaps": ["CFG Flattening", "MBA Substitution"],
                }, f)
            auditor = SelfAuditor(build_dir=tmpdir)
            cat = auditor.audit_reality()
            assert any(f.severity == "critical" for f in cat.findings)
            assert cat.score < 60


class TestSelfAuditorFullRun:
    """
    Tests for SelfAuditor full run with and without source path.
    """
    def test_full_run_returns_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            auditor = SelfAuditor(build_dir=tmpdir)
            report = auditor.run()
            assert isinstance(report, AuditReport)
            assert report.overall_score >= 0
            assert len(report.categories) == 10

    def test_full_run_with_source(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def valid():\n    return 42\n")
            path = f.name
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                auditor = SelfAuditor(build_dir=tmpdir)
                report = auditor.run(payload_path=path)
                assert report.overall_score >= 0
                assert "source" in report.categories
                assert report.categories["source"].score > 0
        finally:
            os.unlink(path)


class TestReporter:
    """
    Tests for markdown and JSON report generation and file writing.
    """
    def test_generate_markdown_report(self):
        from scripts.self_audit.reporter import generate_markdown_report
        report = AuditReport(
            timestamp="2025-06-01T12:00:00Z",
            overall_score=75.0,
            overall_grade="C",
            categories={
                "source": AuditCategory(
                    name="source", score=80, max_score=100,
                    findings=[AuditFinding("source", "major", "Test finding", "Description", "Fix it")],
                ),
            },
            total_findings=1, critical_findings=0, major_findings=1, minor_findings=0,
        )
        md = generate_markdown_report(report)
        assert "SECURITY SELF-AUDIT REPORT" in md
        assert "75.0" in md
        assert "Test finding" in md

    def test_generate_json_report(self):
        from scripts.self_audit.reporter import generate_json_report
        report = AuditReport(
            timestamp="now", overall_score=80.0, overall_grade="B",
            total_findings=0, critical_findings=0, major_findings=0, minor_findings=0,
        )
        d = generate_json_report(report)
        assert d["overall_score"] == 80.0
        assert d["overall_grade"] == "B"

    def test_write_reports(self):
        from scripts.self_audit.reporter import write_reports
        report = AuditReport(
            timestamp="now", overall_score=90.0, overall_grade="A",
            total_findings=0, critical_findings=0, major_findings=0, minor_findings=0,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            write_reports(report, tmpdir)
            assert os.path.isfile(os.path.join(tmpdir, "security_audit.md"))
            assert os.path.isfile(os.path.join(tmpdir, "security_audit.json"))
            with open(os.path.join(tmpdir, "security_audit.json")) as f:
                data = json.load(f)
            assert data["overall_score"] == 90.0
