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
    """No email address, no invented URL, no phone number.

    URLs are allowed only for domains that were FETCHED AND READ while
    preparing this brief: trailofbits.com (services and contact pages) and its
    sendsafely subdomain, plus github.com for the repository. Anything else is
    a name or a link added from memory.
    """
    text = _text()
    assert not re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", text), (
        "the brief contains an email address; none has been verified and an "
        "invented one sends enquiries into a void")
    allowed = ("trailofbits", "github.com")
    for url in re.findall(r"https?://[^\s)>`]+", text):
        assert any(a in url for a in allowed), (
            "the brief cites %r, which was not among the pages fetched and "
            "read" % (url,))


def test_the_intake_route_is_recorded_and_carries_the_one_rule():
    """The brief must say HOW to approach, and warn against the wrong order.

    Verified 2026-11-23: the vendor publishes a contact form and, for sensitive
    material, SendSafely or PGP. No plain email address exists -- so the brief
    must not imply one, and it must warn that the bundle should NOT be attached
    to a first web form: that would disclose a live construction and an open
    weakness before a confidential channel exists.
    """
    text = _text()
    lowered = text.lower()
    assert "intake route" in lowered, (
        "the brief must record the verified intake route")
    assert "contact form" in lowered
    assert "sendsafely" in lowered or "pgp" in lowered, (
        "the brief should name the secure channel for sensitive material")
    assert "do not attach the bundle" in lowered, (
        "the brief must warn against attaching the bundle to a first contact "
        "form; that discloses before a confidential channel exists")
    assert "no plain email" in lowered or "no email address is published" in \
        lowered, (
        "the brief must state that no plain email is published, so nobody "
        "hunts for one")


def test_the_draft_enquiry_exists_and_leaks_nothing():
    """The draft must be sendable as-is, and must not describe the construction.

    A first contact that names the product, counts the weaknesses, or hints at
    the design has disclosed before a confidential channel exists. The draft's
    only job is to ask whether they want the material and over which channel.
    """
    text = _text()
    lowered = text.lower()
    assert "draft enquiry" in lowered, (
        "the brief must carry a sendable draft, or the owner still has to "
        "compose the one message the brief exists to prepare")
    # It must ask the two scoping questions.
    assert "scope you would take on" in lowered or "scope you would" in lowered
    assert "which channel" in lowered, (
        "the draft must ask which channel to use")
    # And it must repeat the prohibition inside the draft's own section.
    assert "do not paste the bundle into this message" in lowered, (
        "the prohibition must appear next to the draft, not only above it")

    # Negative: the draft itself must not name the construction's internals.
    # The slice must start at the DRAFT HEADING, not at the first occurrence of
    # the words "draft enquiry" -- that first hit is the prohibition sentence
    # above it, and slicing from there swept in the eight questions further
    # down the document and failed on text that is nowhere near the draft.
    marker = "### 1.2 draft enquiry"
    assert marker in lowered, (
        "the brief must keep a clearly headed draft section")
    draft_start = lowered.index(marker)
    # The draft ends at the next heading, so the check covers only the draft.
    rest = lowered[draft_start:]
    end = rest.find("**do not paste the bundle")
    assert end > 0, "the draft must be followed by its own prohibition"
    draft = rest[:end]
    for leaked in ("mac-then-encrypt", "sha-256 counter", "pack_id",
                   "mimosa-intake-00"):
        assert leaked not in draft, (
            "the draft enquiry names %r; a first contact must not describe "
            "the construction before a confidential channel exists" % (leaked,))


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


def test_the_form_requirements_are_recorded():
    """The brief must say what the form requires, so the send is a checklist.

    Inspected in a browser 2026-11-23: the form renders inside an iframe and is
    invisible to a static fetch. Four fields are REQUIRED and are the owner's
    identity -- first name, last name, email, company name -- which is exactly
    why a maintainer cannot submit it. That must be recorded as a FACT rather
    than left as an unexplained refusal.
    """
    text = _text()
    lowered = text.lower()
    assert "what the form actually requires" in lowered, (
        "the brief must record the inspected form requirements")
    for field in ("first name", "last name", "email", "company name"):
        assert field in lowered, (
            "the brief must name the required field %r" % (field,))
    assert "design review" in lowered, (
        "the brief should name the checkbox that matches the ask")
    assert "cryptography (libraries" in lowered, (
        "the brief should quote the inquiry-type option verbatim, so the "
        "sender picks the right one rather than paraphrasing")
    assert "cannot submit" in lowered or "could not submit" in lowered, (
        "the brief must state plainly why the maintainer could not submit: "
        "the required fields are the owner's identity")
    assert "invent" in lowered, (
        "the brief must say that inventing those details is not acceptable")
