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
             10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen"}
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
             "twelve": 12, "thirteen": 13}
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
             10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen"}
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


def test_every_retracted_defect_document_is_cited_by_the_paper():
    """A defect with its own document must appear somewhere in the paper.

    Round 220 found the table at eleven rows while thirteen defects were fixed: the
    two urllib3 fixes had documents and no row. The count guards compare documents
    to each other and stayed green.

    This checks the other direction -- documents against the paper -- by requiring
    every `*defect*.md` file to be named in the paper's artefacts section or its
    body. A document nobody cites is a defect nobody recorded.

    Files whose own title begins RETRACTED are skipped: they record removed claims,
    not defects.
    """
    import glob
    paper = _read(PAPER)
    missing = []
    for path in sorted(glob.glob(os.path.join(DOCS, "*defect*.md"))):
        name = os.path.basename(path)
        text = _read(path)
        if text.lstrip().startswith("# RETRACTED") or "# RETRACTED" in text[:200]:
            continue
        # cite by filename or by the defect's own short name in the table
        if name in paper:
            continue
        stem = name[:-3].replace("-defect", "").replace("-", " ").split()[0]
        if stem and stem in paper:
            continue
        missing.append(name)
    assert not missing, (
        "defect documents not cited anywhere in the paper: %r. Round 220 found two "
        "fixes with documents and no table row; the count guards could not see it."
        % (missing,))


def test_documented_artefact_count_matches_the_gate_record():
    """Documents quoting an artefact count must match the gate's own record.

    Round 226 found three documents quoting 104 artefacts twenty rounds after the gate
    narrowed to 38. Round 227 tried to derive the count from the gate's AST and reported
    21 against a real 38 -- the count depends on --variants and on conditionals, so it is
    a measurement, not a source property.

    The fix is this: the gate writes `gate-count.json` each run, and this guard compares
    documents to that record. Skipped when the file is absent, because the guard must not
    fail merely because the gate has not been run in this checkout.
    """
    import json
    import re
    rec_path = os.path.join(DOCS, "gate-count.json")
    if not os.path.exists(rec_path):
        return
    with open(rec_path, encoding="utf-8") as f:
        rec = json.load(f)
    actual = rec.get("artefacts")
    if not isinstance(actual, int) or actual <= 0:
        return
    wrong = {}
    # Only the two documents that speak for the programme as a whole. Every other
    # document is either historical or about one measurement, and scoping this to
    # all 61 files made the guard fire on numbers that were correct when written.
    for fn in ("paper-draft.md", "README.md"):
        text = _read(os.path.join(DOCS, fn))
        for m in re.finditer(r"\*{0,2}(\d{1,3})\*{0,2} artefacts", text):
            claimed = int(m.group(1))
            if claimed == actual:
                continue
            snippet = text[max(0, m.start() - 40):m.end() + 20]
            if "measured at" in snippet or "at the time" in snippet:
                continue
            # A file whose header declares itself historical is skipped entirely.
            if "Historical." in text[:400] or "RETRACTED" in text[:200]:
                continue
            wrong.setdefault("%s: %s" % (fn, m.group(0)), claimed)
    assert not wrong, (
        "documents quote artefact counts the gate does not produce "
        "(gate-count.json says %d): %r" % (actual, wrong))
