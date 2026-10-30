"""Numbers in the research documents must match the things they describe.

Round 163 audited all fifty documents by hand and found three stale counts: "seven
defects" where the table listed nine, "three external sources" after a package was
vendored, and an artefact count from before the corpus grew. The existing guards
checked specific claims; nothing checked the numbers that drift.

This file checks the numbers that can be derived mechanically.

It does not check every number in every document — that needs a human or a much
better parser — so it is a floor, not a ceiling. Three stale counts survived
eleven guards, which is why even a floor is worth having.
"""

import ast
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
DOCS = os.path.join(ROOT, "docs", "research")
GATE = os.path.join(ROOT, "scripts", "transfer", "artefact_gate.py")
PAPER = os.path.join(DOCS, "paper-draft.md")
README = os.path.join(DOCS, "README.md")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _defect_rows(paper_text):
    """Rows of the defect table in section 6, by index.

    Scoped to section 6 because the paper has other numbered tables -- the
    module-size table is also rows 1..4 -- and an unscoped scan reported a
    "gap" that was a different table.
    """
    lines = paper_text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines)
                     if ln.startswith("## 6."))
    except StopIteration:
        return []
    rows = []
    for line in lines[start + 1:]:
        if line.startswith("## ") and not line.startswith("### "):
            break                    # next top-level section (6.1 is a subsection)
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 2 and cells[1].isdigit():
            rows.append(cells[1])
    return rows


def _gate_module_count():
    """How many modules the gate iterates, without running it."""
    src = _read(GATE)
    tree = ast.parse(src)

    def literal_list(node):
        if isinstance(node, (ast.List, ast.Tuple)):
            return [e for e in node.elts if isinstance(e, ast.Constant)]
        return []

    # every string literal that looks like a corpus path or a package name
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.startswith(("foo", "Bar")) or "/" in node.value:
                if node.value.endswith(".py") or "/" in node.value:
                    names.add(node.value)
    return len(names)


def test_paper_defect_table_is_contiguous_from_one():
    """The table's row indices must be 1..n with no gaps or repeats.

    Round 145 added rows 8 and 9 and the abstract kept saying five; a gap here
    would let a row be lost without any count changing.
    """
    rows = _defect_rows(_read(PAPER))
    assert rows, "no defect rows found in the paper"
    expected = [str(i) for i in range(1, len(rows) + 1)]
    assert rows == expected, (
        "defect table rows are %r, expected %r" % (rows, expected))


def test_readme_defect_count_matches_the_paper_table():
    """README's defect count must equal the number of rows in the paper's table."""
    n_rows = len(_defect_rows(_read(PAPER)))
    readme = _read(README)
    words = {5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",
             10: "ten", 11: "eleven", 12: "twelve"}
    word = words.get(n_rows)
    if word is None:
        return
    assert word + " product" in readme or word + " defects" in readme, (
        "the paper lists %d defects but the research README does not say %r"
        % (n_rows, word))


def test_readme_has_no_smaller_defect_count_than_the_paper():
    """No document may claim fewer defects than the table supports.

    This is the specific failure from round 163: README said seven while the
    table listed nine.
    """
    n_rows = len(_defect_rows(_read(PAPER)))
    readme = _read(README)
    for word, n in (("three", 3), ("four", 4), ("five", 5),
                    ("six", 6), ("seven", 7), ("eight", 8)):
        if n >= n_rows:
            continue
        assert word + " defects" not in readme, (
            "README says %r but the paper's table lists %d rows" % (word, n_rows))


def test_paper_and_readme_agree_on_the_corpus_shapes():
    """If the gate iterates a package directory, both documents must say so."""
    gate_src = _read(GATE)
    if "PKG_DIR" not in gate_src:
        return
    for name, path in (("paper", PAPER), ("research README", README)):
        text = _read(path)
        assert "package" in text, (
            "%s does not mention packages, but the gate iterates one" % name)


def test_no_document_claims_a_defect_count_the_paper_does_not_support():
    """Any 'N defects' in the research docs must not exceed the table."""
    n_rows = len(_defect_rows(_read(PAPER)))
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
             "twelve": 12}
    for fn in sorted(os.listdir(DOCS)):
        if not fn.endswith(".md"):
            continue
        text = _read(os.path.join(DOCS, fn))
        for m in re.finditer(r"\b(one|two|three|four|five|six|seven|eight|nine|"
                             r"ten|eleven|twelve) (?:correctness )?defects?\b", text):
            # Allow one more than the table's rows: a document may count the
            # stale call and the swallowed exception that returned the input as
            # two defects, while the paper folds them into one row because they
            # were found together. Both counts are defensible; anything more than
            # that is an over-claim.
            if words[m.group(1)] > n_rows + 1:
                raise AssertionError(
                    "%s claims %r defects but the paper's table lists %d"
                    % (fn, m.group(1), n_rows))


def test_handoff_defect_count_matches_the_paper_table():
    """The handoff must not understate the defect count either.

    Round 203 found HANDOFF.md still saying nine a round after the paper said ten.
    The existing guards checked the paper's table and the research README; the
    handoff is a third document that describes state, and state drifts fastest of
    all because it is written once and read later.

    A handoff that understates the record is worse than a stale table: it is the
    file a successor reads first.
    """
    n_rows = len(_defect_rows(_read(PAPER)))
    handoff = _read(os.path.join(DOCS, "HANDOFF.md"))
    words = {5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",
             10: "ten", 11: "eleven", 12: "twelve"}
    word = words.get(n_rows)
    if word is None:
        return
    assert word in handoff, (
        "the paper lists %d defects but HANDOFF.md never says %r" % (n_rows, word))
    for n, smaller in words.items():
        if n >= n_rows:
            continue
        assert ("| defects found and fixed | **%s**" % smaller) not in handoff, (
            "HANDOFF.md's defect count says %r but the paper's table lists %d"
            % (smaller, n_rows))
