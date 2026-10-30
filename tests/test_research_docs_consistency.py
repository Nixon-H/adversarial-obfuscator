"""Research documents must agree with each other and with the code.

Two documents drifted during this programme and a reviewer, not a test,
caught both:

  * `real-corpus-tasks.md` kept a "12/12 cells" title over a 24-cell table,
    said "four modules" while using five, and said "36 cells" when the total
    was 48 — all left over from doubling the benchmark;
  * `manuscript-draft.md` kept "the cost curve is flat" in its abstract for
    two rounds after the endpoint was retracted.

Both were stale prose, not stale data. The tables were right; the sentences
around them were not. Nothing checked, because markdown has no compiler.

These tests check the three things that actually went wrong: an arithmetic
claim in the prose that disagrees with the committed code, a retracted claim
that survives in a document, and a document that contradicts its own tables.
"""

import os
import re

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
DOCS = os.path.join(ROOT, "docs", "research")


def _read(name):
    with open(os.path.join(DOCS, name), encoding="utf-8") as f:
        return f.read()


def _benchmark_counts():
    import sys
    sys.path.insert(0, ROOT)
    from scripts.transfer.real_tasks import TASKS as REAL
    from scripts.transfer.tasks import TASKS as SYNTH
    return len(SYNTH), len(REAL)


def test_benchmark_counts_match_the_documents():
    synth, real = _benchmark_counts()
    assert synth == 9, "synthetic task count changed; update the documents"
    assert real == 8, "corpus task count changed; update the documents"


def test_real_corpus_doc_title_matches_its_table():
    doc = _read("real-corpus-tasks.md")
    title = doc.splitlines()[0]
    m = re.search(r"(\d+)/(\d+) Cells", title)
    assert m, "title no longer states a cells ratio: %r" % title
    cells = int(m.group(1))
    # the table's total row is the source of truth
    total = re.search(r"\|\s*\*\*total\*\*\s*\|\s*\*\*(\d+)\*\*", doc)
    assert total, "table has no total row"
    assert cells == int(total.group(1)), (
        "title says %d cells but the table totals %s" % (cells, total.group(1))
    )


def test_real_corpus_doc_module_count_is_consistent():
    doc = _read("real-corpus-tasks.md")
    words = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
    claimed = [words[w] for w in words if re.search(r"\b%s modules\b" % w, doc)]
    if not claimed:
        pytest.skip("document does not state a module count")
    assert len(set(claimed)) == 1, (
        "document states conflicting module counts: %r" % (claimed,)
    )


def test_no_document_reinstates_the_retracted_flat_curve_claim():
    """The endpoint was retracted; no document may assert the old result."""
    banned = [
        "The cost curve is flat",
        "the cost curve is flat",
    ]
    offenders = []
    for name in sorted(os.listdir(DOCS)):
        if not name.endswith(".md"):
            continue
        if name.startswith("retraction"):
            continue        # the retraction quotes what it withdraws
        doc = _read(name)
        for phrase in banned:
            if phrase in doc:
                offenders.append("%s: %r" % (name, phrase))
    assert not offenders, (
        "the flat-curve claim was retracted; these documents still assert it: %r"
        % (offenders,)
    )


def test_manuscript_mentions_the_retraction():
    doc = _read("manuscript-draft.md")
    assert "retraction-cost-curve.md" in doc, (
        "the manuscript cites no retraction; if it reports the endpoint it "
        "must record that an earlier version was withdrawn"
    )
    assert "bounded null" in doc or "withdrawn" in doc, (
        "the manuscript states no bounded-null or withdrawal language"
    )


def test_documents_do_not_claim_a_total_that_the_code_contradicts():
    synth, real = _benchmark_counts()
    expected_total = synth * 3 + real * 3     # three build indices each
    doc = _read("real-corpus-tasks.md")
    m = re.search(r"All (\d+) cells", doc)
    if not m:
        pytest.skip("document does not state a combined total")
    assert int(m.group(1)) == synth * 3 + real * 3, (
        "document says %s combined cells; code implies %d (%d+%d tasks x 3)"
        % (m.group(1), expected_total, synth, real)
    )


def test_authoring_count_matches_the_documents():
    """The authoring figure drifted once (33 -> 38). Catch it next time."""
    import sys
    sys.path.insert(0, ROOT)
    from scripts.transfer.tasks import TASKS as SYNTH
    total = sum(len(t["props"]) for t in SYNTH.values())
    doc = _read("authoring-cost-proxy.md")
    m = re.search(r"\*\*(\d+) properties authored", doc)
    assert m, "authoring doc no longer states a property count"
    assert int(m.group(1)) == total, (
        "authoring doc says %s properties; the task files have %d"
        % (m.group(1), total)
    )


def test_module_size_figure_matches_the_documents():
    """The module-size mean drifted once (8.3 -> 8.6). It is a computed mean,
    so the documents must not restate it from memory; this checks that every
    document quoting it quotes the same number as its own table."""
    import sys
    sys.path.insert(0, ROOT)
    claims = []
    for name in ("cost-is-build-independent.md", "manuscript-draft.md"):
        doc = _read(name)
        for m in re.finditer(r"(\d+\.\d+) at four", doc):
            claims.append((name, m.group(1)))
    if not claims:
        pytest.skip("no document states the four-candidate figure")
    values = {v for _, v in claims}
    assert len(values) == 1, (
        "documents disagree on the four-candidate mean: %r" % (claims,)
    )


def test_reproduce_script_exists_and_is_runnable():
    path = os.path.join(ROOT, "scripts", "transfer", "reproduce.py")
    assert os.path.exists(path), "the reproduction script is missing"
    src = open(path, encoding="utf-8").read()
    for table in ("table_singleton", "table_module_size", "table_diversity",
                  "table_fixed_build", "table_fault_control", "table_authoring"):
        assert "def %s(" % table in src, "reproduce.py lost %s" % table
