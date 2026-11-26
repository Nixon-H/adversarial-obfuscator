"""Resource budgets for artefact-derived MBA expressions."""
import time

import pytest

from pydeobsbench import transform_solvers as ts


def test_expression_length_is_rejected_before_parsing():
    expression = "1" * (ts.MAX_EXPRESSION_LENGTH + 1)
    started = time.perf_counter()
    with pytest.raises(ValueError, match="length"):
        ts.evaluate_integer_expression(expression)
    assert time.perf_counter() - started < 0.5


def test_expression_node_count_is_rejected_before_evaluation():
    expression = "+".join(["1"] * (ts.MAX_EXPRESSION_NODES + 1))
    with pytest.raises(ValueError, match="node"):
        ts.evaluate_integer_expression(expression)


def test_expression_depth_is_rejected_before_evaluation():
    expression = "+" * (ts.MAX_EXPRESSION_DEPTH + 1) + "1"
    with pytest.raises(ValueError, match="depth"):
        ts.evaluate_integer_expression(expression)


def test_integer_literals_have_a_width_budget():
    with pytest.raises(ValueError, match="integer width"):
        ts.evaluate_integer_expression("1" * 80)


def test_intermediate_results_have_a_width_budget():
    expression = ("9" * 70) + "*" + ("9" * 70)
    with pytest.raises(ValueError, match="integer width"):
        ts.evaluate_integer_expression(expression)


def test_probe_mba_does_not_invoke_a_simplifier_for_over_budget_text():
    called = False

    def simplifier(_expression):
        nonlocal called
        called = True
        return 0, 0.0

    expression = "1+" * (ts.MAX_EXPRESSION_LENGTH // 2) + "1"
    result = ts.probe_mba([expression], 0, simplifier=simplifier)
    assert called is False
    assert result["measured"] is False
    assert "budget" in result["rows"][0]["reason"].lower()


def test_probe_mba_rejects_over_budget_nodes_before_simplifier():
    called = False

    def simplifier(_expression):
        nonlocal called
        called = True
        return 0, 0.0

    expression = "+".join(["1"] * (ts.MAX_EXPRESSION_NODES + 1))
    result = ts.probe_mba([expression], 0, simplifier=simplifier)
    assert called is False
    assert result["measured"] is False
    assert "node" in result["rows"][0]["reason"].lower()


@pytest.mark.parametrize(("expression", "reason"), [
    ("9**9**9", "Pow"),
    ("1" * 80, "integer width"),
    ("True", "bool"),
    ("1_000", "underscore"),
    ("__import__('os')", "Call"),
])
def test_probe_mba_validates_grammar_before_simplifier(expression, reason):
    called = False

    def simplifier(_expression):
        nonlocal called
        called = True
        return 0, 0.0

    result = ts.probe_mba([expression], 0, simplifier=simplifier)
    assert called is False
    assert result["measured"] is False
    assert reason.lower() in result["rows"][0]["reason"].lower()


def test_signed_64_bit_literal_boundaries_are_accepted():
    assert ts.evaluate_integer_expression(str(-(2 ** 63))) == -(2 ** 63)
    assert ts.evaluate_integer_expression(str(2 ** 63 - 1)) == 2 ** 63 - 1


@pytest.mark.parametrize(("expression", "reason"), [
    ("True", "bool"),
    ("1_000", "underscore"),
])
def test_evaluator_rejects_bool_and_underscore_numerals(expression, reason):
    with pytest.raises(ValueError, match=reason):
        ts.evaluate_integer_expression(expression)


def test_probe_mba_rejects_length_even_without_a_simplifier():
    expression = "1" * (ts.MAX_EXPRESSION_LENGTH + 1)
    result = ts.probe_mba([expression], 0)
    assert result["measured"] is False
    assert "length" in result["rows"][0]["reason"].lower()
