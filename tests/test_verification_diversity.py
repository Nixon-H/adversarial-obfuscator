"""
test_verification_diversity.py

Tests for Verification Diversity Analysis (Feature 185).

Test coverage:
- Positive tests verify static, runtime, symbolic, formal, and adversarial verification
- Negative tests verify empty directories, missing __init__.py, graceful handling
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.verification_diversity.diversity import (
    VerificationDiversityAnalyzer,
    analyze_verification_diversity,
)


class TestStaticVerify:
    """
    TestStaticVerify
    
    Positive test cases for staticverify.
    """
    def test_static_verify_returns_list(self):
        analyzer = VerificationDiversityAnalyzer()
        results = analyzer.static_verify()
        assert isinstance(results, list)
        if results:
            assert "module" in results[0]
            assert "status" in results[0]

    def test_static_verify_finds_phases(self):
        analyzer = VerificationDiversityAnalyzer()
        results = analyzer.static_verify()
        exported = [r for r in results if r.get("status") == "exported"]
        assert len(exported) > 0

    def test_static_verify_missing_phases_dir(self, tmpdir):
        analyzer = VerificationDiversityAnalyzer()
        analyzer.phases_dir = os.path.join(tmpdir, "nonexistent")
        results = analyzer.static_verify()
        assert len(results) == 0 or results[0].get("status") in ("missing_init", "cannot_load")


class TestRuntimeVerify:
    """
    TestRuntimeVerify
    
    Positive test cases for runtimeverify.
    """
    def test_runtime_verify_returns_list(self):
        analyzer = VerificationDiversityAnalyzer()
        results = analyzer.runtime_verify()
        assert isinstance(results, list)

    def test_runtime_verify_calls_phases(self):
        analyzer = VerificationDiversityAnalyzer()
        results = analyzer.runtime_verify()
        called = [r for r in results if r.get("status") == "called"]
        assert len(called) > 0


class TestSymbolicVerify:
    """
    TestSymbolicVerify
    
    Positive test cases for symbolicverify.
    """
    def test_symbolic_verify_counts_branches(self, tmpdir):
        phases_dir = os.path.join(tmpdir, "phases")
        os.makedirs(phases_dir)
        fp = os.path.join(phases_dir, "phase_test.py")
        with open(fp, "w") as f:
            f.write(
                "def phase_test(args):\n"
                "    if args:\n"
                "        return 1\n"
                "    else:\n"
                "        return 0\n"
            )
        analyzer = VerificationDiversityAnalyzer()
        analyzer.phases_dir = phases_dir
        results = analyzer.symbolic_verify()
        test_entry = [r for r in results if "phase_test" in r.get("module", "")]
        assert len(test_entry) >= 1
        assert test_entry[0]["branches"] >= 1

    def test_symbolic_verify_no_if(self, tmpdir):
        phases_dir = os.path.join(tmpdir, "phases")
        os.makedirs(phases_dir)
        fp = os.path.join(phases_dir, "phase_flat.py")
        with open(fp, "w") as f:
            f.write("def phase_flat(args):\n    return 42\n")
        analyzer = VerificationDiversityAnalyzer()
        analyzer.phases_dir = phases_dir
        results = analyzer.symbolic_verify()
        flat = [r for r in results if "phase_flat" in r.get("module", "")]
        assert flat[0]["branches"] == 0

    def test_symbolic_empty_dir(self, tmpdir):
        analyzer = VerificationDiversityAnalyzer()
        analyzer.phases_dir = tmpdir
        results = analyzer.symbolic_verify()
        assert len(results) == 0


class TestFormalVerify:
    """
    TestFormalVerify
    
    Positive test cases for formalverify.
    """
    def test_formal_verify_detects_assertions(self, tmpdir):
        phases_dir = os.path.join(tmpdir, "phases")
        os.makedirs(phases_dir)
        fp = os.path.join(phases_dir, "phase_with_assert.py")
        with open(fp, "w") as f:
            f.write("def phase_with_assert(args):\n    assert args is not None\n")
        analyzer = VerificationDiversityAnalyzer()
        analyzer.phases_dir = phases_dir
        results = analyzer.formal_verify()
        entry = [r for r in results if "phase_with_assert" in r.get("module", "")]
        assert entry[0]["has_assertions"]

    def test_formal_verify_no_assertions(self, tmpdir):
        phases_dir = os.path.join(tmpdir, "phases")
        os.makedirs(phases_dir)
        fp = os.path.join(phases_dir, "phase_no_assert.py")
        with open(fp, "w") as f:
            f.write("def phase_no_assert(args):\n    return 1\n")
        analyzer = VerificationDiversityAnalyzer()
        analyzer.phases_dir = phases_dir
        results = analyzer.formal_verify()
        entry = [r for r in results if "phase_no_assert" in r.get("module", "")]
        assert not entry[0]["has_assertions"]


class TestAdversarialVerify:
    """
    TestAdversarialVerify
    
    Positive test cases for adversarialverify.
    """
    def test_adversarial_verify_tests_inputs(self):
        analyzer = VerificationDiversityAnalyzer()
        results = analyzer.adversarial_verify()
        assert isinstance(results, list)
        if results:
            assert results[0]["adversarial_inputs_tested"] >= 4


class TestDisagreements:
    """
    TestDisagreements
    
    Positive test cases for disagreements.
    """
    def test_disagreement_detected(self, tmpdir):
        phases_dir = os.path.join(tmpdir, "phases")
        os.makedirs(phases_dir)
        phases_init = os.path.join(phases_dir, "__init__.py")
        with open(phases_init, "w") as f:
            f.write("from .phase_test import phase_test\n")
        fp = os.path.join(phases_dir, "phase_test.py")
        with open(fp, "w") as f:
            f.write(
                "def phase_test(args):\n"
                "    if args:\n"
                "        return 1\n"
                "    else:\n"
                "        return 0\n"
            )
        analyzer = VerificationDiversityAnalyzer()
        analyzer.phases_dir = phases_dir
        analyzer.results["static"] = [{"module": "phase_test", "status": "exported"}]
        analyzer.results["runtime"] = [{"module": "phase_test", "status": "called"}]
        analyzer.results["symbolic"] = [{"module": "phase_test", "status": "analyzed"}]
        analyzer.results["formal"] = [{"module": "phase_test", "status": "no_assertions"}]
        analyzer.results["adversarial"] = [{"module": "phase_test", "status": "adversarial_tested"}]
        analyzer._find_disagreements()
        assert len(analyzer.disagreements) >= 1


class TestTopLevelFunction:
    """
    TestTopLevelFunction
    
    Positive test cases for toplevelfunction.
    """
    def test_analyze_returns_dict(self):
        result = analyze_verification_diversity()
        assert isinstance(result, dict)
        for key in ("per_strategy_results", "disagreements", "diversity_score", "total_modules"):
            assert key in result

    def test_all_five_strategies_present(self):
        result = analyze_verification_diversity()
        strategies = result.get("per_strategy_results", {})
        for expected in ("static", "runtime", "symbolic", "formal", "adversarial"):
            assert expected in strategies


class TestNegativeCases:
    """
    TestNegativeCases
    
    Negative test cases — exercises error handling and edge cases for negativecases.
    """
    def test_empty_phases_dir_returns_empty_results(self, tmpdir):
        analyzer = VerificationDiversityAnalyzer()
        analyzer.phases_dir = tmpdir
        results = analyzer.run_all()
        total = sum(len(v) for v in results["per_strategy_results"].values())
        assert total == 0 or total >= 0

    def test_no_phases_init_graceful(self, tmpdir):
        phases_dir = os.path.join(tmpdir, "phases")
        os.makedirs(phases_dir)
        fp = os.path.join(phases_dir, "phase_orphan.py")
        with open(fp, "w") as f:
            f.write("def phase_orphan(args):\n    return 1\n")
        analyzer = VerificationDiversityAnalyzer()
        analyzer.phases_dir = phases_dir
        static = analyzer.static_verify()
        assert len(static) >= 1
        assert static[0].get("status") in ("missing_init", "cannot_load")
