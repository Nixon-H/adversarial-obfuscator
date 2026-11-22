"""The RE evaluation protocol's scoring key must match the subject.

`docs/security/RE_EVALUATION_PROTOCOL.md` §4 states ground truth that an
independent analyst will be GRADED against: the decay constant, the divisor,
the threshold, the three string constants, and the expected output. If the
subject drifts and the key does not, the evaluation silently grades a correct
analyst as failing — the worst possible outcome for an external review,
because the error is invisible to both parties.

So every number in the scoring key is asserted here against the subject that
actually runs. This module asserts NOTHING about obfuscation strength; it
only keeps the answer key true.
"""
import ast
import importlib.util
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SUBJECT = os.path.join(REPO, "tests", "fixtures", "re_subject.py")
PROTOCOL = os.path.join(REPO, "docs", "security", "RE_EVALUATION_PROTOCOL.md")


def _protocol_text():
    with open(PROTOCOL, encoding="utf-8") as fh:
        return fh.read()


def _load_subject():
    spec = importlib.util.spec_from_file_location("_re_subject", SUBJECT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _subject_source():
    with open(SUBJECT, encoding="utf-8") as fh:
        return fh.read()


# ── O1: the entry function exists and is the one the protocol names ─────

def test_the_named_entry_function_exists():
    module = _load_subject()
    assert callable(getattr(module, "settle_account", None)), (
        "the protocol names settle_account as objective O1; it must exist")


# ── O2: the ground-truth constants are the subject's constants ──────────

def test_the_scoring_key_constants_match_the_subject():
    module = _load_subject()
    assert module.THRESHOLD == 50000, (
        "protocol §4 states threshold 50000; subject says %r"
        % (module.THRESHOLD,))
    assert module.DECAY == 7, (
        "protocol §4 states decay 7; subject says %r" % (module.DECAY,))
    assert "1000" in _protocol_text(), "the divisor 1000 must stay in the key"


def test_the_documented_formula_reproduces_the_subject_exactly():
    """Recompute §4's formula and compare to the module's own function.

    This is the strongest form of the check: not "the constants look right"
    but "the formula an analyst is graded against produces the same numbers".
    """
    module = _load_subject()

    def documented(entries, penalty):
        balance = 0
        for i, amount in enumerate(entries):
            weight = max(1, 1000 - 7 * i)
            balance += amount * weight
        balance //= 1000
        if balance > 50000:
            return balance - penalty, "settled"
        return balance, "rejected"

    cases = [
        ([12000, 9000, 15000, 3000], 250),
        ([], 0),
        ([100000], 0),
        ([1, 2, 3], 1),
        # The threshold is pinned on BOTH sides. A case list that only
        # contains 50000 and 100000 cannot distinguish THRESHOLD=50000 from
        # THRESHOLD=50001 — verified by perturbing the key and watching this
        # test still pass. 50001 makes the boundary unambiguous.
        ([50000], 0),
        ([50001], 0),
        ([60000, 50000], 7),
        ([10 ** 6, 10 ** 6, 10 ** 6], 999),
    ]
    for entries, penalty in cases:
        assert documented(entries, penalty) == module.settle_account(
            entries, penalty), (
            "the scoring key's formula diverges from the subject for "
            "entries=%r penalty=%r" % (entries, penalty))


def test_the_threshold_boundary_is_the_documented_one():
    """The key says '> 50000' not '>= 50000'; the subject must agree.

    To land the balance on exactly 50000 with a single entry, the amount must
    be 50000: weight is 1000 at index 0, so 50000 * 1000 // 1000 == 50000.
    """
    module = _load_subject()
    balance, verdict = module.settle_account([50000], 0)
    assert balance == 50000, "expected the boundary balance, got %r" % (balance,)
    assert verdict == "rejected", (
        "the boundary at exactly THRESHOLD must be 'rejected'; the protocol "
        "documents a strict greater-than")
    balance2, verdict2 = module.settle_account([50001], 0)
    assert balance2 == 50001 and verdict2 == "settled"


# ── O3: the three string constants ─────────────────────────────────────

def test_the_three_string_constants_are_present():
    src = _subject_source()
    for literal in ('"settled"', '"rejected"', '"audit"'):
        assert literal in src, (
            "protocol §4 (O3) names %s as a scored string constant; it is "
            "missing from the subject" % (literal,))


def test_the_audit_prefix_is_produced_by_the_named_function():
    module = _load_subject()
    assert module.emit_audit("settled") == "audit:settled"
    assert module.emit_audit("rejected") == "audit:rejected"


# ── §5: the expected output the analyst is told to check ───────────────

def test_the_expected_output_in_the_protocol_is_the_real_output(capsys):
    """§5 tells the analyst to expect a specific string. Verify it."""
    module = _load_subject()
    module.main()
    out = capsys.readouterr().out
    assert "RE-SUBJECT-OUTCOME 38664 rejected" in out, (
        "the protocol's §5 expected output does not match the subject: %r"
        % (out,))
    assert "audit:rejected" in out
    assert "RE-SUBJECT-OUTCOME 38664 rejected" in _protocol_text(), (
        "protocol §5 stopped stating the expected output")


# ── keep the protocol's honesty markers ────────────────────────────────

def test_the_protocol_states_the_evaluation_has_not_run():
    text = _protocol_text()
    assert "NOT RUN" in text, (
        "the protocol must state up front that no analyst has performed the "
        "evaluation, or it reads as a completed review")
    assert "DO NOT GIVE THIS SECTION TO THE ANALYST" in text, (
        "the scoring key must stay marked as withheld from the analyst")


def test_the_protocol_requires_both_arms_and_the_delta():
    """A favourable arm reported alone is the failure mode this guards."""
    text = _protocol_text()
    assert "control" in text.lower()
    assert "delta" in text.lower(), (
        "the protocol must require the control arm and the delta")
    assert "Both arms and the delta" in text, (
        "§7's prohibition on reporting one arm must stay")


def test_the_protocol_keeps_its_limitations_section():
    """The limitations are what stop a good score over-claiming."""
    text = _protocol_text()
    assert "Known limitations" in text
    for limit in ("One subject", "coarse", "not a certification"):
        assert limit in text, (
            "the protocol stopped naming its limitation %r" % (limit,))


# ── the subject stays small enough for a 40-hour budget ────────────────

def test_the_subject_is_the_size_the_protocol_claims():
    src = _subject_source()
    code_lines = [ln for ln in src.splitlines()
                  if ln.strip() and not ln.strip().startswith("#")]
    assert len(code_lines) < 80, (
        "the protocol describes a ~60-line subject; it is now %d lines, so "
        "the 40-hour budget assumption no longer holds"
        % (len(code_lines),))
    # And no imports beyond sys: the protocol says "no imports beyond sys".
    tree = ast.parse(src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert imported <= {"sys"}, (
        "the subject gained imports (%r); the protocol's stated simplicity "
        "no longer describes it" % (sorted(imported),))
