"""
test_self_critique.py

Tests for Self-Critique Engine (Feature 200+).

Test coverage:
- Positive tests verify all six critique questions, honesty score, markdown report generation
- Negative tests verify empty directories, missing sources, graceful handling
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestSelfCritiqueEngine:
    """
    TestSelfCritiqueEngine
    
    Positive test cases for selfcritiqueengine.
    """
    def test_question1_assumptions_without_evidence(self):
        from scripts.self_critique.engine import SelfCritiqueEngine
        with tempfile.TemporaryDirectory() as td:
            sdir = os.path.join(td, "scripts", "assumptions")
            os.makedirs(sdir)
            with open(os.path.join(sdir, "registry.py"), "w") as f:
                f.write(
                    'Assumption("FHE", "python3", "software", required=True)\n'
                )
            engine = SelfCritiqueEngine(td)
            finding = engine.question1_assumptions_without_evidence()
            assert finding.question.startswith("What assumptions")
            assert finding.severity == "high"
            assert len(finding.references) >= 1

    def test_question2_weakest_evidence_missing_report(self):
        from scripts.self_critique.engine import SelfCritiqueEngine
        with tempfile.TemporaryDirectory() as td:
            engine = SelfCritiqueEngine(td)
            finding = engine.question2_weakest_evidence()
            assert "evidence" in finding.question.lower()
            assert isinstance(finding.answer, str)

    def test_question2_weakest_evidence_with_report(self):
        from scripts.self_critique.engine import SelfCritiqueEngine
        with tempfile.TemporaryDirectory() as td:
            bdir = os.path.join(td, "build")
            os.makedirs(bdir)
            data = {
                "claim_coverage_pct": 50.0,
                "coverage_pct": 50.0,
                "claims_without_runtime_evidence": ["claim1"],
            }
            with open(os.path.join(bdir, "evidence_report.json"), "w") as f:
                json.dump(data, f)
            engine = SelfCritiqueEngine(td)
            finding = engine.question2_weakest_evidence()
            assert len(finding.references) >= 1

    def test_question3_least_trustworthy_metrics(self):
        from scripts.self_critique.engine import SelfCritiqueEngine
        with tempfile.TemporaryDirectory() as td:
            mdir = os.path.join(td, "scripts", "metrics")
            os.makedirs(mdir)
            with open(os.path.join(mdir, "fake_metric.py"), "w") as f:
                f.write("def compute():\n    return True  # mock\n")
            engine = SelfCritiqueEngine(td)
            finding = engine.question3_least_trustworthy_metrics()
            assert "metric" in finding.question.lower()
            assert len(finding.references) >= 1

    def test_question4_least_convincing_proofs(self):
        from scripts.self_critique.engine import SelfCritiqueEngine
        with tempfile.TemporaryDirectory() as td:
            pdir = os.path.join(td, "scripts", "proofs")
            os.makedirs(pdir)
            with open(os.path.join(pdir, "bad_proof.py"), "w") as f:
                f.write("def prove():\n    return True\n")
            engine = SelfCritiqueEngine(td)
            finding = engine.question4_least_convincing_proofs()
            assert "proof" in finding.question.lower()
            assert len(finding.references) >= 1

    def test_question5_lowest_confidence_features(self):
        from scripts.self_critique.engine import SelfCritiqueEngine
        with tempfile.TemporaryDirectory() as td:
            tdir = os.path.join(td, "tests")
            os.makedirs(tdir)
            with open(os.path.join(tdir, "test_feature_a.py"), "w") as f:
                f.write("class TestA:\n    pass\n")
            with open(os.path.join(tdir, "test_feature_b.py"), "w") as f:
                f.write("class TestB1:\n    pass\nclass TestB2:\n    pass\n")
            engine = SelfCritiqueEngine(td)
            finding = engine.question5_lowest_confidence_features()
            assert "feature" in finding.question.lower()
            assert "feature_a" in str(finding.references) or "feature_b" in str(finding.references)

    def test_question6_weakest_claims_no_file(self):
        from scripts.self_critique.engine import SelfCritiqueEngine
        with tempfile.TemporaryDirectory() as td:
            engine = SelfCritiqueEngine(td)
            finding = engine.question6_weakest_claims()
            assert "claim" in finding.question.lower()
            assert isinstance(finding.answer, str)

    def test_evaluate_returns_six_findings(self):
        from scripts.self_critique.engine import SelfCritiqueEngine
        engine = SelfCritiqueEngine()
        findings = engine.evaluate()
        assert len(findings) == 6

    def test_honesty_score(self):
        from scripts.self_critique.engine import SelfCritiqueEngine
        engine = SelfCritiqueEngine()
        score = engine.honesty_score()
        assert 0.0 <= score <= 1.0

    def test_generate_report(self):
        from scripts.self_critique.engine import SelfCritiqueEngine
        engine = SelfCritiqueEngine()
        report = engine.generate_report()
        assert len(report.critiques) == 6
        assert report.honesty_score >= 0
        assert report.evidence_summary != ""

    def test_generate_markdown(self):
        from scripts.self_critique.engine import SelfCritiqueEngine
        engine = SelfCritiqueEngine()
        md = engine.generate_markdown()
        assert "# Self-Critique Report" in md
        assert "Honesty Score" in md
        assert "What assumptions" in md or "What" in md

    def test_generate_self_critique_function(self):
        from scripts.self_critique.engine import generate_self_critique
        result = generate_self_critique()
        assert "critiques" in result
        assert "honesty_score" in result
        assert len(result["critiques"]) == 6


class TestSelfCritiqueNegative:
    """
    TestSelfCritiqueNegative
    
    Negative test cases — exercises error handling and edge cases for selfcritiquenegative.
    """
    def test_empty_assumptions_dir(self):
        from scripts.self_critique.engine import SelfCritiqueEngine
        with tempfile.TemporaryDirectory() as td:
            sdir = os.path.join(td, "scripts", "assumptions")
            os.makedirs(sdir)
            engine = SelfCritiqueEngine(td)
            finding = engine.question1_assumptions_without_evidence()
            assert finding.references is not None

    def test_no_metrics_dir(self):
        from scripts.self_critique.engine import SelfCritiqueEngine
        with tempfile.TemporaryDirectory() as td:
            engine = SelfCritiqueEngine(td)
            finding = engine.question3_least_trustworthy_metrics()
            assert isinstance(finding.answer, str)

    def test_no_proofs_dir(self):
        from scripts.self_critique.engine import SelfCritiqueEngine
        with tempfile.TemporaryDirectory() as td:
            engine = SelfCritiqueEngine(td)
            finding = engine.question4_least_convincing_proofs()
            assert isinstance(finding.answer, str)

    def test_no_tests_dir(self):
        from scripts.self_critique.engine import SelfCritiqueEngine
        with tempfile.TemporaryDirectory() as td:
            engine = SelfCritiqueEngine(td)
            finding = engine.question5_lowest_confidence_features()
            assert isinstance(finding.answer, str)

    def test_evidence_summary_empty_findings(self):
        from scripts.self_critique.engine import SelfCritiqueEngine
        engine = SelfCritiqueEngine()
        engine.findings = []
        summary = engine.evidence_summary()
        assert summary != ""
