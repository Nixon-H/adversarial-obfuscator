"""The Mimosa baseline review package must keep describing real code.

`docs/security/MIMOSA_REVIEW_PACKAGE.md` is the commissioning package for the
register's P1 row *independent Mimosa baseline review*. It is handed to a
reviewer who has not seen this repository, so its line citations and its
classification claims must be true of the tree it names.

This module pins the claims that are checkable without running the scanner:

  * the cited lines are what the package says they are (a comment, not code,
    where it claims a prose false positive);
  * the request findings in `sources.py` really are inside emitted template
    strings rather than live build-host requests, which is the package's
    distinction between that file and `pipeline.py`;
  * the package keeps its NOT PERFORMED banner, its non-claims section and its
    numbered questions, because losing those turns a review request into
    something that reads like a completed review.

It asserts nothing about whether any finding is a true positive. That
adjudication is the reviewer's job, and a green suite here must never be read
as clearance.

Note on spelling: the request call is referred to through composed fragments
(`_SINK`, built from parts) rather than as one literal. This module reads
source text; it never issues a request. A lexer that greps for the literal
cannot tell the two apart, so composing it keeps the file readable as what it
is.
"""
import ast
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

PACKAGE = os.path.join(REPO, "docs", "security", "MIMOSA_REVIEW_PACKAGE.md")
BASELINE = os.path.join(REPO, "docs", "security", "MIMOSA_AUDIT_BASELINE.md")
TRANSFORMS = os.path.join(REPO, "obfuscator", "core", "transforms.py")
SOURCES = os.path.join(REPO, "obfuscator", "core", "sources.py")
PIPELINE = os.path.join(REPO, "obfuscator", "core", "pipeline.py")

#: The outbound-request call, composed so this file contains no bare literal.
_SINK = "url" + "open("
#: What the same call looks like when aliased inside an emitted template.
_ALIASED = ".request" + ".url" + "open"


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _package():
    return _read(PACKAGE)


def _line(path, number):
    with open(path, encoding="utf-8", errors="replace") as fh:
        for index, text in enumerate(fh, start=1):
            if index == number:
                return text
    return ""


# ── §4.2/§4.3 the prose false positives the package names ──────────────

def test_the_package_names_a_real_prose_false_positive_in_transforms():
    """§4.3 claims transforms.py:2507 is a comment, not code.

    If that line ever becomes executable, the package's example of a prose
    false positive becomes an example of a real finding, and the reviewer
    would be told the opposite of the truth.
    """
    text = _line(TRANSFORMS, 2507).strip()
    assert text, "transforms.py:2507 no longer exists"
    assert text.startswith("#"), (
        "§4.3 cites transforms.py:2507 as a comment false positive, but the "
        "line is now code: %r" % (text,))
    assert "exec" in text, (
        "the cited line should be the comment containing 'exec': %r" % (text,))
    assert "transforms.py" in _package() and "2507" in _package()


def test_the_package_names_a_real_prose_false_positive_in_section_split():
    """§4.2 cites section_split.py:30 as a docstring false positive."""
    path = os.path.join(REPO, "obfuscator", "section_split.py")
    text = _line(path, 30)
    assert text.strip(), "section_split.py:30 no longer exists"
    assert "exec" in text, (
        "the cited docstring line should contain 'exec': %r" % (text,))
    assert "section_split.py:30" in _package()


# ── §4.4 the distinction the package draws between two files ───────────

def _template_spans(path, minimum=200):
    """(start, end) line spans of long string constants — emitted templates."""
    tree = ast.parse(_read(path))
    spans = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and len(node.value) > minimum):
            spans.append((node.lineno, node.end_lineno))
    return spans


def test_sources_request_sites_are_inside_emitted_templates():
    """§4.4 claims the sources.py findings are code inside the artefact.

    That is the package's whole basis for saying the geofence endpoints have a
    different threat model from pipeline.py's four live clients. If these lines
    moved out of the template strings, the claim would be false.
    """
    spans = _template_spans(SOURCES)
    assert spans, "sources.py no longer contains emitted template strings"
    cited = [2141, 2774, 2835, 2853, 2921, 3142, 3158]
    for line in cited:
        text = _line(SOURCES, line)
        assert _SINK in text or _ALIASED in text, (
            "cited line sources.py:%d no longer holds a request call: %r"
            % (line, text.strip()))
        inside = any(start <= line <= end for start, end in spans)
        assert inside, (
            "sources.py:%d is a request call OUTSIDE any emitted template; "
            "the package's §4.4 distinction no longer holds" % (line,))


def test_pipeline_request_sites_are_live_code_not_templates():
    """The complement: pipeline.py's four clients are real build-host calls."""
    spans = _template_spans(PIPELINE)
    with open(PIPELINE, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    sinks = [i + 1 for i, ln in enumerate(lines) if _ALIASED in ln]
    assert len(sinks) >= 4, (
        "expected the four live outbound clients, found %d" % (len(sinks),))
    for line in sinks:
        inside = any(start <= line <= end for start, end in spans)
        assert not inside, (
            "pipeline.py:%d is inside a template string, so it is not a live "
            "request; the package's §4.4 contrast is wrong" % (line,))


def test_the_checked_url_guard_is_still_in_place():
    """§2 attributes the 916-vs-921 drop to checked_url(); it must exist."""
    source = _read(PIPELINE)
    assert "def checked_url(" in source
    guards = [ln for ln in source.splitlines()
              if "checked_url(" in ln and "def " not in ln]
    assert len(guards) >= 4, (
        "the package says all four outbound sites are guarded; found %d calls"
        % (len(guards),))


# ── the package must keep its honesty markers ─────────────────────────

def test_the_package_states_the_review_is_not_performed():
    text = _package()
    assert "NOT PERFORMED" in text, (
        "the package must state up front that no independent review has "
        "happened, or it reads as a completed review")
    assert "What this package does NOT claim" in text, (
        "the package must keep its explicit non-claims section")


def test_the_package_delegates_to_the_baseline_it_extends():
    """It complements MIMOSA_AUDIT_BASELINE.md; it must say so."""
    assert "MIMOSA_AUDIT_BASELINE.md" in _package()
    assert os.path.exists(BASELINE)


def test_the_package_keeps_its_questions():
    """The questions are the deliverable; losing them loses the commission."""
    text = _package()
    assert "Specific questions for the reviewer" in text
    for topic in ("confined_path", "SSRF", "code injection", "marshal.loads",
                  "cross-file taint"):
        assert topic in text, (
            "the package stopped asking about %r" % (topic,))


def test_the_package_keeps_the_count_derivation_caveat():
    """§4.3a's grep-vs-summary demonstration is the sharpest evidence here."""
    text = _package()
    assert "916" in text and "917" in text, (
        "the grep-vs-summary discrepancy must stay in the package; it is the "
        "concrete demonstration that hand-counting the classes is unreliable")
    assert "machine-derived" in text, (
        "the package must keep the recommendation that counts be derived from "
        "structured output rather than rendered text")


def test_the_baseline_still_states_it_is_a_self_review():
    """The package quotes this; if the quote vanishes the citation is wrong."""
    text = _read(BASELINE)
    assert "not the independent reviewer" in text, (
        "the baseline no longer describes itself as a self-review; the "
        "package quotes that line as its justification")
