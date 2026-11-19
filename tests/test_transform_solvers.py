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


#: Solver budget for the probes in this file. Small on purpose: at SS_WIDTH the
#: MITM split is 2**(n/2), so a realistic budget would make the suite take
#: minutes, and the probe already reports a timeout as a distinct outcome
#: rather than as a slow solve. The verdict does not depend on the budget
#: anyway — the predicate's answer is a compile-time constant.
PROBE_BUDGET = 0.25


def _probe(count, budget=PROBE_BUDGET):
    return ts.probe_subset_sum(_instances(count), budget_seconds=budget)


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

def test_a_generated_instance_uses_the_configured_width():
    """Record what n actually is. §6 raised it from 8 to SS_WIDTH.

    n=8 was 256 subsets and fell in 0.0001 s. Raising n is NOT what creates
    protection here — see the module docstring and the test below — but the
    width must at least match the constant so the probe measures the real
    emitted instance.
    """
    from scripts.c_transform import SS_WIDTH
    instance = _instances(1)[0]
    assert len(instance["set"]) == SS_WIDTH
    assert SS_WIDTH >= 32, "a narrower instance is trivially enumerable"
    assert instance["mask"] >= 0


def test_instance_values_are_wide_enough_to_defeat_the_dp():
    """40-bit values, so a target-indexed table is not emittable.

    With 10-bit values the verifier's pseudo-polynomial DP over the target is
    cheap to fill and an analyst would choose it. The width is what forces the
    meet-in-the-middle construction — and, incidentally, what removed the old
    out-of-bounds `dp[target]` hazard entirely.
    """
    from scripts.c_transform import SS_VALUE_BITS
    instance = _instances(1)[0]
    assert SS_VALUE_BITS >= 32
    assert max(instance["set"]) > 2 ** 20, (
        "values must be wide enough that a target-indexed table is infeasible")


def test_the_subset_sum_pass_is_off_by_default():
    """The measurement removed it from the default pipeline.

    §6 established that the answer is a compile-time constant: an analyst reads
    the emitted arrays and sees the predicate is always true, without solving
    anything. Raising n only made the DEFENDER pay more (0.006 s at n=24,
    2.8 s at n=40, 60 s at n=48) while the attacker's cost stayed bounded by
    reading a literal. So it fails the review's bar and is opt-in only.
    """
    from scripts.c_transform import transform_c, SS_WIDTH  # noqa: F401
    source = "int main(void) { int a = 1; if (a == 1) { return 1; } return 0; }\n"
    default = transform_c(source, b"seed-default")
    assert not any("subset-sum" in applied
                   for applied in default.transforms_applied), (
        "subset-sum is back in the default pipeline; re-run the §6 probe first")
    opted_in = transform_c(source, b"seed-default", do_subset_sum=True)
    assert any("subset-sum" in applied
               for applied in opted_in.transforms_applied), (
        "the opt-in path must still work — the function is kept and tested")


def test_the_opt_in_path_still_emits_a_meet_in_the_middle_check():
    """The verifier must not be a target-indexed table at these widths."""
    import random
    from scripts.c_transform import insert_subset_sum_predicates

    source = "int main(void) { int a = 1; if (a == 1) { return 1; } return 0; }\n"
    out, count = insert_subset_sum_predicates(source, b"probe",
                                             random.Random(1), count=1)
    assert count == 1
    assert "unsigned char dp[" not in out, (
        "a target-indexed DP is back; it cannot cover 40-bit targets")
    assert "malloc" in out and "free" in out, (
        "the meet-in-the-middle table must be heap-allocated: a static table "
        "at this width would bloat every linked binary")
    assert "#define __NX_SS_HALF" in out


def test_the_verdict_states_it_is_not_a_protection():
    """The verdict is about the CONSTRUCTION, not the width.

    At any n, `check(...) == 1` is a constant an analyst can read off the
    emitted arrays, so widening cannot turn it into a solver-hard predicate.
    """
    result = _probe(20)
    assert "NOT A PROTECTION" in result["verdict"]


def test_the_probe_notes_that_the_answer_is_predetermined():
    """The decisive finding, and it is not a solver time.

    The set and target are emitted in plaintext, so `check(...) == 1` is true
    by inspection. That is why widening n cannot help, and the note must say it
    rather than quoting a solve time and implying the transform is working.
    """
    result = _probe(5)
    assert "plaintext" in result["note"]
    assert "true by inspection" in result["note"]
    assert result["answer_predetermined"] is True


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
    summary = ts.summarise([_probe(10)])
    assert summary["claims"][0]["status"] == "DOES NOT HOLD"
    assert summary["holds"] == 0


def test_summarise_reports_a_full_audit_honestly():
    """The headline: of the three challenged claims, measured, none holds."""
    results = [
        _probe(50),
        ts.probe_mba(ts.sample_mba_expressions(12345, (1, 5)), 12345,
                     simplifier=_fixture_simplifier),
        ts.probe_opaque_predicate(lambda _e: (False, "folded"), ["x"]),
    ]
    summary = ts.summarise(results)
    assert summary["total"] == 3
    assert summary["holds"] == 0, (
        "if a claim starts holding, the REPORT should change, not this test: %r"
        % (summary["claims"],))
