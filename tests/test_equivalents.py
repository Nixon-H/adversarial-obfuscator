"""§8 independent equivalents: behavioural equality WITHOUT textual similarity.

The benchmark's semantic-reconstruction metric is only meaningful if "same
behaviour" and "same text" can be told apart. This file pins both halves:

  * every equivalent reproduces the target's observed output exactly, and
  * it does so with ZERO shared identifiers, so a low-similarity result cannot
    be an artefact of how the equivalent happened to be written.

If a future edit made an equivalent a paraphrase of the original, the overlap
test fires. If an edit broke the behaviour, the output test fires. Neither test
looks at the other's property, which is what keeps them independent.

The expected outputs are literals captured by running the ORIGINAL targets; a
separate case here recomputes them from the independent implementation, so an
invented or stale literal fails rather than becoming load-bearing. Keeping this
file free of file and process access is deliberate: the project's write-time
scanner rejects a new file that combines ``open()`` with ``subprocess``, and a
test has no need for either.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pydeobsbench import equivalents as eq  # noqa: E402
from pydeobsbench.targets import TARGETS  # noqa: E402


@pytest.mark.parametrize("name", sorted(TARGETS))
def test_every_equivalent_reproduces_the_observed_output(name):
    """The semantic metric's ground truth: same observable behaviour."""
    assert name in eq.EXPECTED_OUTPUT, (
        "%s has no recorded target output, so semantic reconstruction is "
        "unmeasured for it" % name)
    assert eq.observe(name) == eq.EXPECTED_OUTPUT[name], (
        "the independent implementation for %s no longer reproduces the "
        "target's output; either the equivalent or the recorded ground truth "
        "is wrong" % name)


@pytest.mark.parametrize("name", sorted(TARGETS))
def test_every_equivalent_is_textually_independent(name):
    """Zero shared top-level identifiers: behaviour, not a paraphrase.

    A high overlap would mean the "semantic" score was really measuring text,
    so this is a guard on the metric itself rather than on the code.
    """
    overlap = eq.source_overlap(TARGETS[name]["source"], eq.equivalent_source())
    assert overlap == 0.0, (
        "%s: equivalent shares identifiers with the target (Jaccard %.2f); it "
        "is not an independent implementation" % (name, overlap))


def test_the_equivalents_use_a_different_idiom_than_the_originals():
    """A copy would share structure even where identifiers differ.

    Docstrings are excluded: this module QUOTES the original's ``MASK32`` to
    explain what differs, and a substring check over the raw text matched that
    explanation instead of executable structure (the same trap as the driver
    flag test).
    """
    import ast
    tree = ast.parse(eq.equivalent_source())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
            if node.body and isinstance(node.body[0], ast.Expr) and \
                    isinstance(node.body[0].value, ast.Constant) and \
                    isinstance(node.body[0].value.value, str):
                node.body[0].value.value = ""   # drop the docstring
    code = ast.unparse(tree)
    assert "_fold" in code
    assert "MASK32" not in code, "the target's constant name leaked into code"
    assert "bytearray" not in code, "the target's container idiom leaked in"


def test_verify_equivalents_is_clean_for_the_real_targets():
    assert eq.verify_equivalents(TARGETS) == []


def test_verify_equivalents_reports_a_missing_equivalent():
    """A gap must be reported, never treated as a pass."""
    problems = eq.verify_equivalents({"ghost": {"source": "pass\n"}})
    assert any("ghost" in p for p in problems)


def test_verify_equivalents_catches_a_paraphrased_equivalent(monkeypatch):
    """The independence guard works: a copy would be rejected."""
    copied = "def sign(payload):\n    pass\n\n\ndef main():\n    pass\n"
    target = {"tiny": {"source": copied}}
    monkeypatch.setattr(eq, "equivalent_source", lambda: copied)
    problems = eq.verify_equivalents(target)
    assert any("independent" in p for p in problems), problems


def test_observe_returns_none_for_an_unknown_target():
    assert eq.observe("not-a-target") is None


def test_coverage_names_every_target():
    for name in TARGETS:
        assert name in eq.COVERAGE
        assert not eq.COVERAGE[name].startswith("none"), (
            "%s is declared uncovered" % name)


def test_the_spec_strings_actually_determine_the_behaviour():
    """If the spec were incomplete, the equivalent could not match -- and the
    regression would then be in the ground truth, not in the code under test.
    """
    for name, target in TARGETS.items():
        assert target.get("algorithms"), "%s has no algorithm spec" % name
        assert len(target["algorithms"]) > 20, (
            "%s's spec is too vague to reimplement" % name)


def test_the_recorded_outputs_are_distinct_per_target():
    """A copy-paste in EXPECTED_OUTPUT would make two targets look equal."""
    values = list(eq.EXPECTED_OUTPUT.values())
    assert len(set(values)) == len(values), values
    for name, value in eq.EXPECTED_OUTPUT.items():
        assert value.strip(), "%s has an empty expected output" % name
