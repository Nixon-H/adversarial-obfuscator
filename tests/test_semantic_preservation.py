import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import z3


class TestSemanticPreservationProver:
    """
    TestSemanticPreservationProver
    
    Positive test cases for semanticpreservationprover.
    """
    @pytest.fixture(autouse=True)
    def _setup(self):
        from scripts.proofs.semantic_preservation import SemanticPreservationProver
        self.prover = SemanticPreservationProver(timeout_ms=10000)

    def test_variable_renaming_equivalence(self):
        before = "def f(x):\n    y = x + 1\n    return y\n"
        after = "def f(a):\n    b = a + 1\n    return b\n"
        result = self.prover.prove_variable_renaming(before, after)
        assert result.equivalent is True

    def test_expression_substitution_equivalence(self):
        before = "def f(x):\n    return x * 2\n"
        after = "def f(x):\n    return x + x\n"
        result = self.prover.prove_expression_substitution(before, after)
        assert result.equivalent is True

    def test_nonequivalent_transformation(self):
        before = "def f(x):\n    return x + 1\n"
        after = "def f(x):\n    return x * 2\n"
        result = self.prover.prove_equivalence(before, after, "test_noneq")
        assert result.equivalent is False

    def test_commutative_addition(self):
        before = "def f(x, y):\n    a = x + y\n    return a\n"
        after = "def f(x, y):\n    a = y + x\n    return a\n"
        result = self.prover.prove_equivalence(before, after, "add_commute")
        assert result.equivalent is True

    def test_commutative_reordering(self):
        source = "a = x\na = y\n"
        result = self.prover.prove_commutative_reordering(source, "x", "y")
        assert result.equivalent is True

    def test_identical_sources(self):
        source = "def f(x):\n    return x\n"
        result = self.prover.prove_equivalence(source, source, "identical")
        assert result.equivalent is True

    def test_proof_collection(self):
        self.prover.prove_equivalence("x = 1", "x = 1", "test")
        stats = self.prover.get_stats()
        assert stats["total"] >= 1
        assert stats["equivalent"] >= 1

    def test_to_certificate_dict(self):
        before = "def f(x):\n    return x + 1\n"
        after = "def f(x):\n    return x + 1\n"
        result = self.prover.prove_equivalence(before, after, "cert_test")
        cert = result.to_certificate_dict()
        assert cert["equivalent"] is True
        assert cert["transformation"] == "cert_test"

    def test_smt_formula_construction(self):
        import ast
        from scripts.validation.ast_to_smt import ASTToSMT
        tree = ast.parse("def f(x):\n    return x + 1\n", mode="exec")
        translator = ASTToSMT()
        formula = translator.translate(tree)
        assert formula is not None
        solver = z3.Solver()
        solver.add(formula)
        result = solver.check()
        assert result == z3.sat

    def test_prover_rejects_semantic_change(self):
        before = "def f(x):\n    if x > 0:\n        return x\n    return 0\n"
        after = "def f(x):\n    if x > 0:\n        return 0\n    return x\n"
        result = self.prover.prove_equivalence(before, after, "logic_change")
        assert result.equivalent is False
