"""The intake channel claim in SECURITY.md must match reality.

`SECURITY.md` now states, with a date, that GitHub private vulnerability
reporting is NOT ENABLED on this repository, and names the one command that
would change that. That sentence is load-bearing: it is the documented reason
the three independent-review rows stay open. If somebody enables the feature
and forgets the document — or the reverse — a reviewer would be told the wrong
thing about where to send a disclosure.

This module checks the *document* for internal consistency and for the pieces
that would be needed once the channel exists. It deliberately does NOT query
GitHub: the test suite must run offline and in CI without credentials, and a
test that silently skipped without a token would be a check that cannot fire.
The live check is a two-line command in SECURITY.md itself, run by the
maintainer when the setting changes.

Nothing here asserts that a review happened. It asserts that the document does
not claim one did.
"""
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

SECURITY = os.path.join(REPO, "SECURITY.md")
INTAKE = os.path.join(REPO, "docs", "security", "REVIEW_FINDINGS_INTAKE.md")
PACKAGES = {
    "CRYPTO": os.path.join(REPO, "docs", "security", "CRYPTO_REVIEW_PACKAGE.md"),
    "RE_EVAL": os.path.join(REPO, "docs", "security", "RE_EVALUATION_PROTOCOL.md"),
    "MIMOSA": os.path.join(REPO, "docs", "security", "MIMOSA_REVIEW_PACKAGE.md"),
}


def _text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ── SECURITY.md: the channel statement ────────────────────────────────

def test_security_md_names_a_channel_or_says_there_is_none():
    """Either a real intake route or an explicit statement that none exists.

    The failure this prevents is the old text, which said "no contact is
    configured" with no route and no way to tell whether that was still true.
    """
    text = _text(SECURITY)
    has_route = "private vulnerability reporting" in text.lower()
    assert has_route, (
        "SECURITY.md must name the intake route (GitHub private vulnerability "
        "reporting) so a reporter knows where to go once it is enabled")
    assert "NOT ENABLED" in text or "is enabled" in text, (
        "SECURITY.md must state the CURRENT state of the channel, dated, or a "
        "reader cannot tell whether the route works")


def test_security_md_states_the_current_state_with_a_date():
    """A status claim without a date rots silently."""
    text = _text(SECURITY)
    match = re.search(r"verified (\d{4}-\d{2}-\d{2})",
                      text, re.IGNORECASE)
    assert match, (
        "the channel status must carry a verification date so staleness is "
        "visible")
    year = int(match.group(1)[:4])
    assert 2026 <= year <= 2030, "implausible verification date: %r" % (
        match.group(1),)


def test_security_md_gives_the_enabling_command():
    """So enabling the channel is one copy-paste, not an API hunt."""
    text = _text(SECURITY)
    assert "gh api" in text, (
        "SECURITY.md should carry the exact command that enables the channel")
    assert "private_vulnerability_reporting" in text, (
        "the command must name the setting it changes")


def test_security_md_does_not_publish_an_invented_address():
    """The specific harm: a fake security@ would swallow real disclosures."""
    text = _text(SECURITY)
    addresses = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    assert not addresses, (
        "SECURITY.md contains what looks like an email address (%r). An "
        "invented or unmonitored address sends disclosures into a void; a "
        "real one has to come from the maintainer." % (addresses,))


def test_security_md_says_the_absence_is_not_a_refusal():
    """A reader must not read 'not configured' as 'go away'."""
    text = _text(SECURITY).lower()
    assert "not welcome" in text or "not a refusal" in text or \
        "nobody should treat" in text, (
        "the section must distinguish 'automation not configured' from "
        "'reports unwelcome'")


# ── SECURITY.md: the package table must match the packages ────────────

def test_the_package_table_names_all_three_and_their_status():
    text = _text(SECURITY)
    for name in ("CRYPTO_REVIEW_PACKAGE.md", "RE_EVALUATION_PROTOCOL.md",
                 "MIMOSA_REVIEW_PACKAGE.md"):
        assert name in text, (
            "SECURITY.md must point at %s so a reviewer can find it" % (name,))
    assert text.count("NOT PERFORMED") >= 2
    assert "NOT RUN" in text


@pytest.mark.parametrize("label,banner", [
    ("CRYPTO", "NOT PERFORMED"),
    ("RE_EVAL", "NOT RUN"),
    ("MIMOSA", "NOT PERFORMED"),
])
def test_each_package_still_carries_its_own_banner(label, banner):
    """SECURITY.md's table would be a lie if a package lost its banner."""
    text = _text(PACKAGES[label])
    assert banner in text, (
        "%s no longer states %r; SECURITY.md's table would then misreport it"
        % (os.path.basename(PACKAGES[label]), banner))


# ── the findings-intake format ───────────────────────────────────────

def test_the_intake_format_exists_and_admits_no_findings_arrived():
    text = _text(INTAKE)
    assert "no findings have been returned" in text.lower(), (
        "the intake document must state that nothing has been returned, or it "
        "reads as a record of findings")
    for field in ("package:", "reviewer:", "claim:", "evidence:",
                  "reproducible:", "maintainer-response:", "resolution:"):
        assert field in text, (
            "the intake row format must include the %r field" % (field,))


def test_the_intake_format_forbids_silent_deletion():
    """The rule that stops an inconvenient finding from disappearing."""
    text = _text(INTAKE)
    assert "stays in the register" in text, (
        "the intake rules must say a disputed finding stays recorded")
    assert "out-of-scope" in text, (
        "out-of-scope findings must be recorded AS out-of-scope, not dropped")


def test_the_intake_format_does_not_promise_a_parser():
    """No automation that would bias what reviewers report."""
    text = _text(INTAKE)
    assert "no parser" in text.lower(), (
        "the document should say plainly that reviewer output is transcribed "
        "by hand, so nobody builds a form reviewers must fit")
    assert "do not need to use this format" in text.lower(), (
        "reviewers must be told the format constrains the maintainers, not "
        "their report")


def test_no_document_claims_a_review_has_occurred():
    """The claim that would convert a gap into a fabrication."""
    for path in [SECURITY, INTAKE] + list(PACKAGES.values()):
        lowered = _text(path).lower()
        for phrase in ("independently reviewed", "reviewer confirmed",
                       "review completed", "review has been performed"):
            assert phrase not in lowered, (
                "%s claims %r" % (os.path.basename(path), phrase))
