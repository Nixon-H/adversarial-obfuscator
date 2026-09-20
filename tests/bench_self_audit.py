"""
bench_self_audit.py

Benchmarks for Self-Audit Agent (Feature 180).

Measures source audit, test audit, and full run performance.
"""
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestSelfAuditBenchmarks:
    @pytest.fixture
    def auditor(self):
        from scripts.self_audit.auditor import SelfAuditor
        return SelfAuditor()

    @pytest.fixture
    def temp_source(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import sys\n\ndef compute(x, y):\n    return x * y + 42\n\n")
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_bench_full_run_no_source(self, benchmark, auditor):
        result = benchmark(auditor.run)
        assert result is not None
        assert result.overall_score >= 0

    def test_bench_full_run_with_source(self, benchmark, auditor, temp_source):
        result = benchmark(auditor.run, temp_source)
        assert result is not None
        assert result.overall_score >= 0

    def test_bench_source_audit(self, benchmark, auditor, temp_source):
        cat = benchmark(auditor.audit_source, temp_source)
        assert cat.score >= 0

    def test_bench_source_missing(self, benchmark, auditor):
        cat = benchmark(auditor.audit_source, "/nonexistent.py")
        assert cat.score == 0.0

    def test_bench_tests_audit(self, benchmark, auditor):
        cat = benchmark(auditor.audit_tests)
        assert cat.max_score > 0

    def test_bench_reachability_audit(self, benchmark, auditor):
        report = {
            "total_features": 200,
            "reachable": list(range(150)),
            "partially_reachable": list(range(30)),
            "unreachable": list(range(20)),
        }
        cat = benchmark(auditor.audit_reachability, report)
        assert cat.score >= 0

    def test_bench_reachability_no_report(self, benchmark, auditor):
        auditor.build_dir = "/tmp/nonexistent_bench_xyz"
        cat = benchmark(auditor.audit_reachability)
        assert cat.score == 0.0

    def test_bench_proofs_with_certs(self, benchmark, auditor):
        with tempfile.TemporaryDirectory() as tmpdir:
            proofs_dir = os.path.join(tmpdir, "proofs", "vm")
            os.makedirs(proofs_dir)
            for i in range(20):
                with open(os.path.join(proofs_dir, f"proof_{i}.json"), "w") as f:
                    json.dump({"validated": i % 3 != 0, "equivalent": i % 3 != 0}, f)
            auditor.build_dir = tmpdir
            cat = benchmark(auditor.audit_proofs)
            assert cat.score >= 0

    def test_bench_proofs_no_dir(self, benchmark, auditor):
        auditor.build_dir = "/tmp/nonexistent_bench_xyz"
        cat = benchmark(auditor.audit_proofs)
        assert cat.score == 0.0

    def test_bench_metrics_good(self, benchmark, auditor):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "metrics_report.json"), "w") as f:
                json.dump({"overall": 0.92, "scores": {"resilience": 0.95}}, f)
            auditor.build_dir = tmpdir
            cat = benchmark(auditor.audit_metrics)
            assert cat.score > 50

    def test_bench_metrics_no_report(self, benchmark, auditor):
        auditor.build_dir = "/tmp/nonexistent_bench_xyz"
        cat = benchmark(auditor.audit_metrics)
        assert cat.score == 0.0

    def test_bench_claims_audit(self, benchmark, auditor):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "evidence_report.json"), "w") as f:
                json.dump({
                    "total_claims": 50,
                    "total_evidence": 120,
                    "verified_evidence": 110,
                    "coverage_pct": 91.7,
                    "unverified_claims": [],
                }, f)
            auditor.build_dir = tmpdir
            cat = benchmark(auditor.audit_claims)
            assert cat.score > 70

    def test_bench_debt_audit(self, benchmark, auditor):
        cat = benchmark(auditor.audit_debt)
        assert cat.max_score == 100

    def test_bench_assumptions_good(self, benchmark, auditor):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "assumption_report.json"), "w") as f:
                json.dump({
                    "total_count": 50,
                    "satisfied_count": 48,
                    "unsatisfied_count": 1,
                    "unknown_count": 1,
                    "critical_unsatisfied": [],
                }, f)
            auditor.build_dir = tmpdir
            cat = benchmark(auditor.audit_assumptions)
            assert cat.score > 50

    def test_bench_reality_good(self, benchmark, auditor):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "reality_report.json"), "w") as f:
                json.dump({
                    "overall_reality_score": 88.0,
                    "grade": "B",
                    "critical_gaps": [],
                }, f)
            auditor.build_dir = tmpdir
            cat = benchmark(auditor.audit_reality)
            assert cat.score > 70

    def test_bench_markdown_report(self, benchmark):
        from scripts.self_audit import AuditReport, AuditCategory, AuditFinding
        from scripts.self_audit.reporter import generate_markdown_report
        findings = [AuditFinding("source", "major", f"Finding {i}", "desc", "fix") for i in range(50)]
        cat = AuditCategory(name="source", score=75, max_score=100, findings=findings)
        report = AuditReport(
            timestamp="now", overall_score=75.0, overall_grade="C",
            categories={"source": cat},
            total_findings=50, critical_findings=5, major_findings=30, minor_findings=15,
        )
        md = benchmark(generate_markdown_report, report)
        assert "SECURITY SELF-AUDIT REPORT" in md

    def test_bench_json_report(self, benchmark):
        from scripts.self_audit import AuditReport, AuditCategory, AuditFinding
        from scripts.self_audit.reporter import generate_json_report
        findings = [AuditFinding("source", "major", f"Finding {i}", "desc", "fix") for i in range(50)]
        cat = AuditCategory(name="source", score=75, max_score=100, findings=findings)
        report = AuditReport(
            timestamp="now", overall_score=75.0, overall_grade="C",
            categories={"source": cat},
            total_findings=50, critical_findings=5, major_findings=30, minor_findings=15,
        )
        d = benchmark(generate_json_report, report)
        assert d["overall_score"] == 75.0

    def test_bench_write_reports(self, benchmark):
        from scripts.self_audit import AuditReport, AuditCategory, AuditFinding
        from scripts.self_audit.reporter import write_reports
        findings = [AuditFinding("source", "major", "F", "desc", "fix") for _ in range(10)]
        cat = AuditCategory(name="source", score=80, max_score=100, findings=findings)
        report = AuditReport(
            timestamp="now", overall_score=80.0, overall_grade="B",
            categories={"source": cat},
            total_findings=10, critical_findings=1, major_findings=5, minor_findings=4,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            benchmark(write_reports, report, tmpdir)
            assert os.path.isfile(os.path.join(tmpdir, "security_audit.md"))
            assert os.path.isfile(os.path.join(tmpdir, "security_audit.json"))
