"""Bounded symbolic probes for artefact-derived expressions."""
import pytest

z3 = pytest.importorskip("z3")

from pydeobsbench import dynamic_probes as dp  # noqa: E402
from pydeobsbench import transform_solvers as ts  # noqa: E402


def test_opaque_predicate_uses_bounded_bitvectors_and_solves_identity():
    result = dp.probe_z3_opaque(
        "((__nx_opa_1 * (__nx_opa_1 + 1)) & 1) == 0")
    assert result["translatable"] is True
    assert result["forced_true"] is True
    assert result["forced_false"] is False
    assert result["constant"] is True


def test_opaque_predicate_reports_a_nonconstant_predicate():
    result = dp.probe_z3_opaque("__nx_opa_1 > 0")
    assert result["translatable"] is True
    assert result["constant"] is False


def test_opaque_predicate_rejects_an_integer_wider_than_its_bitvectors():
    result = dp.probe_z3_opaque("__nx_opa_1 == 1099511627776")
    assert result["translatable"] is False
    assert result.get("constant") is not True


def test_opaque_predicate_rejects_expression_complexity(monkeypatch):
    created = False

    class SolverMustNotBeCreated:
        def __init__(self):
            nonlocal created
            created = True
            raise AssertionError("solver created for an over-budget expression")

    monkeypatch.setattr(z3, "Solver", SolverMustNotBeCreated)
    expression = "__nx_opa_1 == (" + "+".join(
        ["1"] * (ts.MAX_EXPRESSION_NODES + 1)) + ")"
    result = dp.probe_z3_opaque(expression)
    assert created is False
    assert result["translatable"] is False


def test_z3_unknown_is_a_timeout_not_a_constant(monkeypatch):
    timeouts = []

    class UnknownSolver:
        def __init__(self):
            self.timeout = None

        def set(self, **options):
            self.timeout = options.get("timeout")

        def add(self, _constraint):
            return None

        def check(self):
            timeouts.append(self.timeout)
            return z3.unknown

    monkeypatch.setattr(z3, "Solver", UnknownSolver)
    result = dp.probe_z3_opaque("__nx_opa_1 > 0")
    assert result["translatable"] is False
    assert result["timed_out"] is True
    assert result.get("constant") is not True
    assert timeouts == [dp.Z3_SOLVER_TIMEOUT_MS, dp.Z3_SOLVER_TIMEOUT_MS]


def test_mba_probe_rejects_oversized_expression_before_evaluation():
    expression = "__nx_mba_0+" + "1+" * (ts.MAX_EXPRESSION_LENGTH // 2)
    result = dp.probe_z3_mba(expression, {"__nx_mba_0": 1})
    assert result["is_literal"] is False
    assert result["simplified"] is None
    assert "budget" in result["reason"].lower()


def test_mba_slot_substitution_cannot_bypass_integer_width_budget():
    result = dp.probe_z3_mba("__nx_mba_0", {"__nx_mba_0": "1" * 80})
    assert result["is_literal"] is False
    assert result["simplified"] is None
    assert "integer width" in result["reason"].lower()


def test_opaque_predicate_does_not_use_z3_signed_modulo_for_c_remainder():
    result = dp.probe_z3_opaque(
        "((__nx_opa_1-__nx_opa_1-1)%2)==1")
    assert result.get("forced_true") is not True
    assert result["translatable"] is False or result.get("forced_false") is True


@pytest.mark.parametrize("literal", [2 ** 31, 2 ** 32 - 1])
def test_opaque_predicate_rejects_literals_above_int32_max(literal):
    result = dp.probe_z3_opaque("__nx_opa_1 == %d" % literal)
    assert result["translatable"] is False
    assert result.get("constant") is not True


@pytest.mark.parametrize("literal", [-(2 ** 31), 2 ** 31 - 1])
def test_opaque_predicate_accepts_int32_literal_boundaries(literal):
    result = dp.probe_z3_opaque("__nx_opa_1 == %d" % literal)
    assert result["translatable"] is True
    assert result["constant"] is False


def test_opaque_predicate_configures_all_solver_resource_ceilings(monkeypatch):
    configured = []

    class RecordingSolver:
        def __init__(self):
            self.options = None
            configured.append(self)

        def set(self, **options):
            self.options = options

        def add(self, _constraint):
            return None

        def check(self):
            return z3.sat

    assert dp.Z3_SOLVER_RLIMIT > 0
    assert dp.Z3_SOLVER_MAX_MEMORY > 0
    monkeypatch.setattr(z3, "Solver", RecordingSolver)
    monkeypatch.setattr(dp, "Z3_SOLVER_RLIMIT", 1234)
    monkeypatch.setattr(dp, "Z3_SOLVER_MAX_MEMORY", 64)
    result = dp.probe_z3_opaque("__nx_opa_1 > 0")

    assert result["translatable"] is True
    expected = {
        "timeout": dp.Z3_SOLVER_TIMEOUT_MS,
        "rlimit": 1234,
        "max_memory": 64,
    }
    assert [solver.options for solver in configured] == [expected, expected]


def test_opaque_predicate_rejects_length_before_regex_scanning(monkeypatch):
    class RegexMustNotRun:
        def findall(self, *_args, **_kwargs):
            raise AssertionError("regex scanned an over-budget expression")

        def fullmatch(self, *_args, **_kwargs):
            raise AssertionError("regex scanned an over-budget expression")

    monkeypatch.setattr(dp, "re", RegexMustNotRun())
    expression = "__nx_opa_1==" + " " * ts.MAX_EXPRESSION_LENGTH
    result = dp.probe_z3_opaque(expression)
    assert result["translatable"] is False
    assert "length" in result["reason"].lower()


def test_mba_probe_rejects_length_before_regex_scanning(monkeypatch):
    class RegexMustNotRun:
        def findall(self, *_args, **_kwargs):
            raise AssertionError("regex scanned an over-budget expression")

    monkeypatch.setattr(dp, "re", RegexMustNotRun())
    expression = "__nx_mba_0+" + " " * ts.MAX_EXPRESSION_LENGTH
    result = dp.probe_z3_mba(expression, {"__nx_mba_0": 1})
    assert result["is_literal"] is False
    assert "length" in result["reason"].lower()


def test_z3_ast_translation_enforces_length_before_parsing(monkeypatch):
    class AstMustNotParse:
        def parse(self, *_args, **_kwargs):
            raise AssertionError("parser received an over-budget expression")

    monkeypatch.setattr(dp, "ast", AstMustNotParse())
    expression = "1" * (ts.MAX_EXPRESSION_LENGTH + 1)
    assert dp._z3_from_ast(expression, {}, z3) is None


def test_z3_ast_translation_reuses_expression_depth_budget(monkeypatch):
    monkeypatch.setattr(dp, "MAX_EXPRESSION_DEPTH", 2)
    assert dp._z3_from_ast("1 + 2 + 3", {}, z3) is None


@pytest.mark.parametrize("expression", [
    "__nx_opa_1 == True",
    "__nx_opa_1 == 1_000",
])
def test_opaque_predicate_rejects_bool_and_underscore_numerals(expression):
    result = dp.probe_z3_opaque(expression)
    assert result["translatable"] is False
    assert result.get("constant") is not True


@pytest.mark.parametrize("expression", ["True", "1_000"])
def test_mba_probe_rejects_bool_and_underscore_numerals(expression):
    result = dp.probe_z3_mba(expression)
    assert result["is_literal"] is False
    assert result["simplified"] is None


@pytest.mark.parametrize(("expression", "reason"), [
    ("__nx_mba_0 + True", "bool"),
    ("__nx_mba_0 + 1_000", "underscore"),
])
def test_mba_probe_validates_grammar_before_checking_slot_values(expression,
                                                                  reason):
    result = dp.probe_z3_mba(expression)
    assert result["is_literal"] is False
    assert reason in result["reason"].lower()
