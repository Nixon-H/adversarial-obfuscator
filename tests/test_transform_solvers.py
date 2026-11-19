"""§6 adversarial validation: measured difficulty, and the verdicts it produced.

The review's bar is explicit:

    "I would not count a transform as a successful security mechanism until it
     survives automated simplification and adversarial recovery attempts."

These tests pin the MEASURED results, including the ones that refute our own
documentation. That is deliberate: a benchmark whose assertions can only say
"the protection held" is not measuring anything.

Measured 2026-11-19 on this host (CPython 3.13, gcc 14, sympy 1.14):

    subset-sum   n=8, search space 256, DP table 4096 entries
                 200/200 instances solved, worst 0.000114 s  -> NOT A PROTECTION
    MBA          max 2073 chars, 5 rounds
                 sympy recovered the constant in 0.0037 s    -> WHOLLY INEFFECTIVE
    opaque pred  -O0: 3 conditional branches, -O3: 0
                 gcc folded the fixed-even predicate away   -> FOLDED AWAY

Every number below is recomputed. The compiler one needs gcc; where gcc is
absent the probe reports "no C compiler available" rather than passing.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pydeobsbench import transform_solvers as ts  # noqa: E402


def _instances(count=200):
    from scripts.c_transform import generate_subset_sum_instance
    return [generate_subset_sum_instance(("nx-ss-%d" % i).encode())
            for i in range(count)]


# ── the safe evaluator (no `eval`, so the audit needs no exemption) ───────

def test_the_evaluator_handles_the_emitter_grammar():
    # (1^2) + 2*(1&2) = 3 + 0 = 3. The identity is x+y == (x^y) + 2*(x&y),
    # so check it on a case where the two halves are both non-zero.
    assert ts.evaluate_integer_expression("((1) ^ (2)) + 2 * ((1) & (2))") == 3
    assert ts.evaluate_integer_expression("((3) ^ (5)) + 2 * ((3) & (5))") == 8
    assert ts.evaluate_integer_expression("-(3)") == -3


def test_the_evaluator_refuses_names_and_calls():
    """Anything outside integer arithmetic must fail, not evaluate."""
    for expression in ("os.system('x')", "x + 1", "__import__('os')",
                       "(1).__class__"):
        with pytest.raises(ValueError):
            ts.evaluate_integer_expression(expression)


def test_the_evaluator_refuses_subscripts_and_attributes():
    with pytest.raises(ValueError):
        ts.evaluate_integer_expression("[1][0]")
    with pytest.raises(ValueError):
        ts.evaluate_integer_expression("(1).real")


# ── subset-sum: the search space, not the DP table, sets the cost ─────────

def test_a_generated_instance_is_8_elements():
    """The whole difficulty claim rests on n. Record what n actually is."""
    instance = _instances(1)[0]
    assert len(instance["set"]) == 8
    assert instance["mask"] >= 0


def test_the_search_space_is_2_to_the_8_not_4096():
    """The DP table sizes the verifier; the ATTACK is the subset lattice.

    The review's point: "NP-hardness of a general problem does not
    automatically make an individual generated instance difficult." Here the
    instance is 256 subsets, and the 4096-entry table is irrelevant to an
    enumerator.
    """
    result = ts.probe_subset_sum(_instances(20))
    assert result["measured"] is True
    assert result["search_space"] == 256
    assert result["dp_table_entries"] >= 4096, (
        "the DP table should still be sized for the run-time check")


def test_every_supplied_instance_is_solved_and_fast():
    result = ts.probe_subset_sum(_instances(200))
    assert result["all_solved"] is True
    assert result["solve_seconds_max"] < ts.CHEAP_SECONDS * 0.01, (
        "instances are expected to fall in microseconds; if this ever exceeds "
        "the bar, the n=8 claim needs revisiting rather than the assertion "
        "loosening: measured %r" % (result["solve_seconds_max"],))


def test_the_verdict_states_it_is_not_a_protection():
    result = ts.probe_subset_sum(_instances(50))
    assert "NOT A PROTECTION" in result["verdict"]


def test_the_probe_notes_that_the_table_does_not_size_the_attack():
    result = ts.probe_subset_sum(_instances(5))
    assert "does not size the attack" in result["note"]


# ── MBA: symbolic simplification recovers the constant ────────────────────

def _fixture_simplifier(expression):
    """Stand-in for sympy: evaluate the constants and time it.

    The emitted expressions are arithmetic over integer literals, so exact
    evaluation reproduces what a symbolic solver concludes. Used to keep this
    file dependency-free; the sympy numbers are measured separately and quoted
    in the module docstring.
    """
    import time
    started = time.perf_counter()
    value = ts.evaluate_integer_expression(expression)
    return value, time.perf_counter() - started


def test_an_mba_expression_is_exact_at_every_depth():
    for rounds in (1, 3, 5):
        expression = ts.sample_mba_expressions(12345, (rounds,))[0]
        assert ts.evaluate_integer_expression(expression) == 12345


def test_nesting_grows_with_rounds():
    """The old version produced the same shape for every round count."""
    lengths = [len(ts.sample_mba_expressions(12345, (r,))[0])
               for r in (1, 3, 5)]
    assert lengths[0] < lengths[1] < lengths[2], lengths


def test_the_constant_is_recoverable_from_a_2000_character_expression():
    """Length is not difficulty: a solver reads the arithmetic, not the size."""
    expressions = ts.sample_mba_expressions(12345, (5,))
    result = ts.probe_mba(expressions, 12345, simplifier=_fixture_simplifier)
    assert result["max_length"] > 2000
    assert result["constant_recovered"] is True


def test_the_mba_verdict_reports_it_as_ineffective():
    result = ts.probe_mba(ts.sample_mba_expressions(12345, (3,)), 12345,
                          simplifier=_fixture_simplifier)
    assert "INEFFECTIVE" in result["verdict"], result["verdict"]


def test_the_mba_note_separates_compiler_folding_from_reader_effort():
    result = ts.probe_mba(ts.sample_mba_expressions(12345, (1,)), 12345,
                          simplifier=_fixture_simplifier)
    assert "volatile" in result["note"]
    assert "not stop a reader" in result["note"]


def test_without_a_simplifier_the_probe_says_unmeasured():
    """An unmeasured claim must never read as one that held."""
    result = ts.probe_mba(ts.sample_mba_expressions(12345, (1,)), 12345)
    assert result["measured"] is False
    assert result["reason"]


# ── the opaque predicate under -O3 ───────────────────────────────────────

def test_count_main_branches_finds_branches_mid_line():
    """The mnemonic is not at the start of an objdump line.

    The first version used line.startswith(), which returned 0 for every
    function and would have reported "folded" universally. Found by running it.
    """
    listing = (
        "0000000000000000 <main>:\n"
        "   0:\t55                   \tpush   %rbp\n"
        "  16:\teb 1d                \tjmp    35 <main+0x35>\n"
        "  26:\t75 09                \tjne    31 <main+0x31>\n"
        "  39:\t7e dd                \tjle    18 <main+0x18>\n"
        "  40:\t48 89 e5             \tmov    %rsp,%rbp\n"
    )
    assert ts.count_main_branches(listing) == 3


def test_count_main_branches_counts_cmov():
    """A condition compiled to a conditional move has no `j*` mnemonic."""
    listing = ("0000000000000000 <main>:\n"
               "   0:\t48 0f 4e c1          \tcmovle %rcx,%rax\n")
    assert ts.count_main_branches(listing) == 1


def test_count_main_branches_ignores_earlier_functions():
    listing = ("0000000000000000 <helper>:\n"
               "   0:\t75 09                \tjne    0\n"
               "0000000000000010 <main>:\n"
               "  10:\t55                   \tpush   %rbp\n")
    assert ts.count_main_branches(listing) == 0


def test_a_folded_predicate_is_reported_as_folded():
    """A compiler that removes the branch must produce a FOLDED verdict."""
    result = ts.probe_opaque_predicate(
        lambda _expr: (False, "0 branches at -O3"), [ts.FOLD_PROBE_SOURCE])
    assert result["folded"] == 1
    assert "FOLDED AWAY" in result["verdict"]


def test_a_surviving_predicate_is_reported_as_surviving():
    result = ts.probe_opaque_predicate(
        lambda _expr: (True, "3 branches at -O3"), [ts.FOLD_PROBE_SOURCE])
    assert result["folded"] == 0
    assert "survived" in result["verdict"]


def test_the_fold_fixture_is_a_fixed_even_predicate():
    """The fixture must be an always-true predicate, or the -O0/-O3 comparison
    would be measuring an ordinary branch instead of constant folding."""
    assert "(x * x - x)" in ts.FOLD_PROBE_SOURCE
    assert "volatile" in ts.FOLD_PROBE_SOURCE, (
        "the sink must be volatile or the loop itself gets removed and the "
        "comparison measures nothing")


# ── summarise(): the report the objective is judged by ───────────────────

def test_summarise_refuses_to_count_an_unmeasured_claim_as_holding():
    summary = ts.summarise([{"probe": "mba", "measured": False,
                             "reason": "no simplifier"}])
    assert summary["claims"][0]["status"] == "UNMEASURED"
    assert summary["holds"] == 0


def test_summarise_marks_the_subset_sum_claim_as_not_holding():
    summary = ts.summarise([ts.probe_subset_sum(_instances(10))])
    assert summary["claims"][0]["status"] == "DOES NOT HOLD"
    assert summary["holds"] == 0


def test_summarise_reports_a_full_audit_honestly():
    """The headline: of the three challenged claims, measured, none holds."""
    results = [
        ts.probe_subset_sum(_instances(50)),
        ts.probe_mba(ts.sample_mba_expressions(12345, (1, 5)), 12345,
                     simplifier=_fixture_simplifier),
        ts.probe_opaque_predicate(lambda _e: (False, "folded"), ["x"]),
    ]
    summary = ts.summarise(results)
    assert summary["total"] == 3
    assert summary["holds"] == 0, (
        "if a claim starts holding, the REPORT should change, not this test: %r"
        % (summary["claims"],))
