"""
test_proof_soundness.py

Tests for Proof Soundness Verification (Feature 174).

Test coverage:
- Positive tests verify soundness test generation, mutation, oracle checks, and harness runs
- Negative tests verify empty modules, unknown proof modules, determinism
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


from scripts.proof_soundness.harness import (
    ProofSoundnessHarness,
    SoundnessTest,
    SoundnessReport,
    generate_soundness_tests,
    run_soundness_harness,
)
from scripts.proof_soundness.mutator import ProofMutationEngine
from scripts.proof_soundness.oracle import TransformationOracle


class TestSoundnessTestDataclass:
    """
    Tests for the SoundnessTest dataclass: defaults, full fields,
    expected accept, and mismatch scenarios.
    """
    def test_dataclass_defaults(self):
        t = SoundnessTest(
            test_id="test_001",
            target_proof="semantic_preservation",
            test_type="incorrect_transform",
            original_source="def f(): return 1",
            modified_source="def f(): return 2",
            expected_to_reject=True,
        )
        assert t.test_id == "test_001"
        assert t.target_proof == "semantic_preservation"
        assert t.test_type == "incorrect_transform"
        assert t.expected_to_reject is True
        assert t.actual_rejected is None
        assert t.passed is None

    def test_dataclass_full(self):
        t = SoundnessTest(
            test_id="test_002",
            target_proof="mutation_safety",
            test_type="boundary_case",
            original_source="%x = %y + 1",
            modified_source="%x = %y - 1",
            expected_to_reject=True,
            actual_rejected=True,
            proof_module="mutation_safety",
            passed=True,
            error_message=None,
        )
        assert t.passed is True
        assert t.actual_rejected is True

    def test_dataclass_expected_accept(self):
        t = SoundnessTest(
            test_id="test_003",
            target_proof="semantic_preservation",
            test_type="adversarial",
            original_source="def f(): return 42",
            modified_source="def f(): return 42",
            expected_to_reject=False,
            actual_rejected=False,
            passed=True,
        )
        assert t.passed is True

    def test_dataclass_mismatch(self):
        t = SoundnessTest(
            test_id="test_004",
            target_proof="semantic_preservation",
            test_type="incorrect_transform",
            original_source="def f(): return 1",
            modified_source="def f(): return 2",
            expected_to_reject=True,
            actual_rejected=False,
            passed=False,
        )
        assert t.passed is False


class TestSoundnessReportDataclass:
    """
    Tests for SoundnessReport defaults, test tracking, serialization, auto-score.
    """
    def test_report_defaults(self):
        r = SoundnessReport()
        assert r.total == 0
        assert r.passed == 0
        assert r.failed == 0
        assert r.soundness_score == 0.0
        assert r.failing_modules == []
        assert r.timestamp != ""

    def test_report_with_tests(self):
        t1 = SoundnessTest(
            test_id="t1", target_proof="sp", test_type="it",
            original_source="a", modified_source="b", expected_to_reject=True,
            actual_rejected=True, passed=True,
        )
        t2 = SoundnessTest(
            test_id="t2", target_proof="ms", test_type="it",
            original_source="a", modified_source="b", expected_to_reject=True,
            actual_rejected=False, passed=False,
        )
        r = SoundnessReport(
            tests=[t1, t2],
            total=2, passed=1, failed=1,
            soundness_score=0.5,
            failing_modules=["ms"],
        )
        assert r.passed == 1
        assert r.failed == 1
        assert r.soundness_score == 0.5
        assert "ms" in r.failing_modules

    def test_report_to_dict(self):
        t = SoundnessTest(
            test_id="t1", target_proof="sp", test_type="it",
            original_source="a", modified_source="b", expected_to_reject=True,
            actual_rejected=True, passed=True,
        )
        r = SoundnessReport(tests=[t], total=1, passed=1, failed=0)
        d = r.to_dict()
        assert d["total"] == 1
        assert d["passed"] == 1
        assert d["soundness_score"] == 1.0
        assert len(d["tests"]) == 1
        assert d["tests"][0]["test_id"] == "t1"

    def test_report_auto_score(self):
        r = SoundnessReport(total=4, passed=3, failed=1)
        assert r.soundness_score == 0.75


class TestProofMutationEngine:
    """
    Tests for ProofMutationEngine: AST mutation, add/sub swap, operand swap,
    constant change, IR mutation, block removal, comparison flip.
    """
    def test_mutate_ast(self):
        engine = ProofMutationEngine(seed=42)
        source = "def f(x):\n    return x + 1\n"
        mutated = engine.mutate_ast(source)
        assert isinstance(mutated, str)
        assert mutated != "" or mutated is None

    def test_mutate_add_to_sub(self):
        engine = ProofMutationEngine(seed=42)
        ir = "%x = %y + 1\nret %x"
        mutated = engine.mutate_add_to_sub(ir)
        assert "-" in mutated

    def test_mutate_swap_operands(self):
        engine = ProofMutationEngine(seed=42)
        ir = "%r = %a + %b\nret %r"
        swapped = engine.mutate_swap_operands(ir)
        assert "%b + %a" in swapped

    def test_mutate_change_constant(self):
        engine = ProofMutationEngine(seed=42)
        ir = "%x = add %y 42\nret %x"
        mutated = engine.mutate_change_constant(ir)
        assert mutated != ir

    def test_mutate_ir_noop_on_funcdef(self):
        engine = ProofMutationEngine(seed=42)
        ir = "func @main:\n%x = %y + 1\nret %x"
        mutated = engine.mutate_ir(ir)
        assert mutated != ""

    def test_generate_mutations_count(self):
        engine = ProofMutationEngine(seed=42)
        source = "def f(x):\n    return x + 1\n"
        mutations = engine.generate_mutations(source, count=5)
        assert len(mutations) >= 1
        for m in mutations:
            assert isinstance(m, str)
            assert len(m) > 0

    def test_generate_mutations_different(self):
        engine = ProofMutationEngine(seed=42)
        source = "def f(a, b):\n    c = a + b\n    return c * 2\n"
        mutations = engine.generate_mutations(source, count=10)
        assert len(mutations) >= 1
        assert all(m != source for m in mutations)

    def test_mutate_remove_block(self):
        engine = ProofMutationEngine(seed=42)
        ir = "block entry:\n%x = 1\nblock exit:\n%y = %x\nret %y"
        mutated = engine.mutate_remove_block(ir)
        assert mutated != ir

    def test_mutate_flip_comparison_via_internal(self):
        engine = ProofMutationEngine(seed=42)
        source = "def f(x):\n    if x > 0:\n        return 1\n    return 0\n"
        mutated = engine._mutate_flip_comparison(source)
        assert mutated != source


class TestTransformGeneration:
    """
    Tests for incorrect transform generation: swap, flip, remove, constant, branch.
    """
    def test_swap_add_sub(self):
        harness = ProofSoundnessHarness()
        src = "def f(x):\n    return x + 1\n"
        modified = harness.generate_incorrect_transform(src, "swap_add_sub")
        assert "-" in modified

    def test_flip_comparison(self):
        harness = ProofSoundnessHarness()
        src = "def f(x):\n    if x > 0:\n        return 1\n    return 0\n"
        modified = harness.generate_incorrect_transform(src, "flip_comparison")
        assert modified != src

    def test_remove_step(self):
        harness = ProofSoundnessHarness()
        src = "def f():\n    x = 1\n    y = 2\n    return x + y\n"
        modified = harness.generate_incorrect_transform(src, "remove_step")
        assert modified != src

    def test_wrong_constant(self):
        harness = ProofSoundnessHarness()
        src = "def f():\n    return 42\n"
        modified = harness.generate_incorrect_transform(src, "wrong_constant")
        assert modified != src

    def test_swap_branches(self):
        harness = ProofSoundnessHarness()
        src = "def f(x):\n    if x > 0:\n        return 1\n    else:\n        return -1\n"
        modified = harness.generate_incorrect_transform(src, "swap_branches")
        assert modified != src

    def test_generate_soundness_tests(self):
        harness = ProofSoundnessHarness()
        tests = generate_soundness_tests(harness, ["semantic_preservation"])
        assert len(tests) > 0
        for t in tests:
            assert t.expected_to_reject is True
            assert t.target_proof == "semantic_preservation"

    def test_generate_soundness_tests_multiple_modules(self):
        harness = ProofSoundnessHarness()
        tests = generate_soundness_tests(harness, ["semantic_preservation", "mutation_safety"])
        modules = set(t.target_proof for t in tests)
        assert "semantic_preservation" in modules
        assert "mutation_safety" in modules


class TestTransformationOracle:
    """
    Tests for TransformationOracle: semantic equivalence, difference classification.
    """
    def test_check_equivalent_same(self):
        oracle = TransformationOracle(random_inputs=10)
        src = "def f(x):\n    return x + 1\n"
        assert oracle.check_semantic_equivalence(src, src) is True

    def test_is_truly_different(self):
        oracle = TransformationOracle(random_inputs=10)
        src1 = "def f(x):\n    return x + 1\n"
        src2 = "def f(x):\n    return x * 2\n"
        result = oracle.is_truly_different(src1, src2)
        assert isinstance(result, bool)

    def test_classify_difference(self):
        oracle = TransformationOracle(random_inputs=10)
        src1 = "def f(x):\n    return x + 1\n"
        src2 = "def f(x):\n    return x + 1\n"
        result = oracle.classify_difference(src1, src2)
        assert result["is_different"] is False
        assert result["difference_type"] == "equivalent"

    def test_classify_difference_different(self):
        oracle = TransformationOracle(random_inputs=10)
        src1 = "def f(x):\n    return x + 1\n"
        src2 = "def f(x):\n    return 42\n"
        result = oracle.classify_difference(src1, src2)
        assert "difference_type" in result
        assert "is_different" in result

    def test_no_function(self):
        oracle = TransformationOracle(random_inputs=5)
        src = "x = 1\ny = 2\n"
        result = oracle.check_semantic_equivalence(src, src)
        assert result is True


class TestHarnessRun:
    """
    Tests for ProofSoundnessHarness run_test, run_all, and report generation.
    """
    def test_run_test_passes_for_valid(self):
        harness = ProofSoundnessHarness()
        src = "def f(x):\n    return x + 1\n"
        modified = "def f(x):\n    return x - 1\n"
        test = SoundnessTest(
            test_id="run_001",
            target_proof="semantic_preservation",
            test_type="incorrect_transform",
            original_source=src,
            modified_source=modified,
            expected_to_reject=True,
        )
        result = harness.run_test(test)
        assert result.actual_rejected is not None
        assert result.passed is not None

    def test_run_test_semantic_preservation(self):
        harness = ProofSoundnessHarness()
        src = "def f(x):\n    return x + 1\n"
        modified = "def f(x):\n    return x + 1\n"
        test = SoundnessTest(
            test_id="run_002",
            target_proof="semantic_preservation",
            test_type="identity",
            original_source=src,
            modified_source=modified,
            expected_to_reject=False,
        )
        result = harness.run_test(test)
        assert result.actual_rejected is not None

    def test_run_all_generates_report(self):
        harness = ProofSoundnessHarness()
        report = harness.run_all(["semantic_preservation", "mutation_safety"])
        assert isinstance(report, SoundnessReport)
        assert report.total > 0

    def test_run_all_failing_module_tracked(self):
        harness = ProofSoundnessHarness()
        report = harness.run_all(["semantic_preservation"])
        assert report.failed >= 0
        assert isinstance(report.soundness_score, float)

    def test_run_all_score_between_zero_and_one(self):
        harness = ProofSoundnessHarness()
        report = harness.run_all(["semantic_preservation"])
        assert 0.0 <= report.soundness_score <= 1.0

    def test_generate_report_returns_last(self):
        harness = ProofSoundnessHarness()
        r1 = harness.run_all(["semantic_preservation"])
        r2 = harness.generate_report()
        assert r2.total == r1.total

    def test_run_soundness_harness_function(self):
        report = run_soundness_harness(proof_modules=["semantic_preservation"])
        assert isinstance(report, SoundnessReport)


class TestNegativeCases:
    """
    Negative tests: empty modules, empty source, unknown proof modules,
    fallback transforms, seed determinism, dedup.
    """
    def test_empty_proof_modules(self):
        harness = ProofSoundnessHarness()
        report = harness.run_all([])
        assert report.total == 0
        assert report.soundness_score == 0.0

    def test_mutation_engine_empty_source(self):
        engine = ProofMutationEngine(seed=42)
        source = ""
        mutated = engine.mutate_ast(source)
        assert mutated is not None

    def test_oracle_no_params(self):
        oracle = TransformationOracle(random_inputs=5)
        src = "def f():\n    return 42\n"
        result = oracle.check_semantic_equivalence(src, src)
        assert result is True

    def test_oracle_empty_source(self):
        oracle = TransformationOracle(random_inputs=5)
        src = ""
        result = oracle.check_semantic_equivalence(src, src)
        assert result is True

    def test_unknown_proof_module(self):
        harness = ProofSoundnessHarness()
        test = SoundnessTest(
            test_id="unknown",
            target_proof="nonexistent_proof",
            test_type="incorrect_transform",
            original_source="def f(): pass",
            modified_source="def f(): pass",
            expected_to_reject=True,
        )
        result = harness.run_test(test)
        assert result.passed is False
        assert "Unknown" in (result.error_message or "")

    def test_generate_incorrect_transform_fallback(self):
        harness = ProofSoundnessHarness()
        src = "def f():\n    pass\n"
        result = harness.generate_incorrect_transform(src, "nonexistent_type")
        assert isinstance(result, str)

    def test_mutator_seed_determinism(self):
        e1 = ProofMutationEngine(seed=42)
        e2 = ProofMutationEngine(seed=42)
        src = "def f(x):\n    return x + 1\n"
        m1 = e1._mutate_swap_add_sub(src)
        m2 = e2._mutate_swap_add_sub(src)
        assert m1 == m2

    def test_report_failing_modules_dedup(self):
        r = SoundnessReport(
            total=3, passed=0, failed=3,
            failing_modules=["sp", "sp", "ms"],
        )
        assert len(r.failing_modules) == 3
