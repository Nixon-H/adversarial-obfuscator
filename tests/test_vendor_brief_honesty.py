"""The vendor brief must not name a firm that was not actually checked.

I cannot engage a cryptographer, and naming one from memory would put a firm in
a security document on the strength of a guess -- which is the same failure as
an invented email address or a fabricated commit hash, all of which this project
has had to correct once already.

So `CRYPTO_REVIEW_VENDOR_BRIEF.md` records only vendors whose pages were FETCHED
AND READ, states which attempts failed, and explains why unverified names are
excluded. These tests pin that discipline: the brief may not list a firm without
a verification note, and it must keep saying it is not engaged.
"""
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

BRIEF = os.path.join(REPO, "docs", "security",
                     "CRYPTO_REVIEW_VENDOR_BRIEF.md")


def _text():
    with open(BRIEF, encoding="utf-8") as fh:
        return fh.read()


# ── the brief must not overstate what was verified ────────────────────

def test_the_brief_states_it_is_not_engaged():
    """A brief that reads as a booking is worse than no brief."""
    lowered = _text().lower()
    assert "not engaged" in lowered, (
        "the brief must state up front that no vendor has been contacted")
    # Phrasing-agnostic: the document says "No vendor has been contacted",
    # which is the right sentence but not the substring an earlier draft of
    # this test looked for. Check the MEANING rather than one wording.
    assert ("no vendor has been contacted" in lowered
            or "not contacted" in lowered
            or "nobody has been contacted" in lowered), (
        "the brief must say plainly that no vendor has been approached")


def test_the_brief_distinguishes_verified_from_unverified():
    """The one-item shortlist is only honest if it says why it is one item."""
    text = _text()
    assert "verified" in text.lower()
    assert "404" in text or "not listed" in text.lower(), (
        "the brief must record the attempts that FAILED, so a reader knows the "
        "shortlist is short because of verification, not because of a search")
    assert "memory" in text.lower(), (
        "the brief must say why firms named from memory are excluded")


def test_every_named_firm_has_a_verification_marker():
    """No firm may appear without evidence it was checked.

    The table has a `verified` column; a firm row must say YES or that its
    attempt failed. A row with neither is a name added from memory.
    """
    text = _text()
    # The markdown table rows for firms start with "| **" or "| two others".
    rows = [ln for ln in text.splitlines()
            if ln.startswith("| **") or "others attempted" in ln]
    assert rows, "the brief no longer contains the vendor table"
    for row in rows:
        lowered = row.lower()
        assert ("yes" in lowered or "no —" in lowered or "no -" in lowered
                or "attempted" in lowered), (
            "this row names a firm without recording whether its page was "
            "verified: %r" % (row,))


def test_the_brief_does_not_invent_contact_details():
    """No email address, no invented URL, no phone number."""
    text = _text()
    assert not re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", text), (
        "the brief contains an email address; none has been verified and an "
        "invented one sends enquiries into a void")
    # Only URLs that were actually fetched may appear.
    urls = re.findall(r"https?://[^\s)>`]+", text)
    for url in urls:
        assert "trailofbits" in url or "github.com" in url, (
            "the brief cites %r, which was not among the pages fetched and "
            "read" % (url,))


def test_the_brief_does_not_estimate_price():
    """Prices are commercial and unverified; an invented figure is a claim."""
    lowered = _text().lower()
    assert "not estimated" in lowered or "not estimated here" in lowered
    # No currency amounts.
    assert not re.search(r"[$€£]\s?\d", _text()), (
        "the brief contains a currency figure; none was verified")


# ── the substantive ask must be preserved ─────────────────────────────

def test_the_brief_asks_for_a_design_assessment_not_a_pentest():
    text = _text().lower()
    assert "design assessment" in text
    assert "penetration test" in text or "pentest" in text, (
        "the brief should say explicitly that a pentest or a whole-repo code "
        "audit is NOT what is being asked for")


def test_the_brief_discloses_the_known_findings_up_front():
    """A reviewer must not bill time rediscovering what is already filed."""
    text = _text()
    for marker in ("MIMOSA-INTAKE-001", "REVIEW_FINDINGS_FILED.md"):
        assert marker in text
    lowered = text.lower()
    assert "already known" in lowered or "pre-disclosed" in lowered \
        or "disclose" in lowered, (
        "the brief must say the known findings are disclosed before the "
        "engagement, so the reviewer does not charge for rediscovery")
    assert "unreviewed" in lowered, (
        "the brief must flag the v3 fix as unreviewed maintainer design -- it "
        "is the item most in need of independent opinion")


def test_the_brief_keeps_the_eight_questions():
    """The scoped ask is the deliverable; losing it loses the engagement."""
    text = _text()
    numbered = re.findall(r"^\d+\. (?:Is|If|Does|Are)", text, re.M)
    assert len(numbered) >= 8, (
        "expected the eight numbered questions from the bundle, found %d"
        % (len(numbered),))


def test_the_brief_says_a_negative_answer_is_acceptable():
    """Silence must not read as 'no defects found'."""
    lowered = _text().lower()
    assert "unmeasured" in lowered or "not as absence" in lowered, (
        "the brief should state that the register treats silence as "
        "unmeasured rather than as proof of absence")
