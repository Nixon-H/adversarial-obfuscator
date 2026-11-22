"""Pins the section-substitution finding (MIMOSA-INTAKE-001).

Found by the maintainer on 2026-11-23 while attacking a weakness listed in
`CRYPTO_REVIEW_BUNDLE_STANDALONE.md` §8. Two packs built with the same session
key and the same total length are interchangeable section-by-section, because
the authenticated context binds (v, i, total, nonce) but not a pack identity.

These tests exist for three reasons, in order of importance:

1. **The row must not be silently closed.** If a future change adds a pack
   identity to the context, `test_the_substitution_still_works_or_is_fixed`
   fails and the finder is told to update the register row deliberately. A
   vulnerability that quietly stops reproducing is indistinguishable from one
   that was never there.
2. **The mitigation decision must be visible.** The row is OPEN on purpose:
   the fix is a wire-format change, and the independent crypto review was
   commissioned to adjudicate exactly this construction. A unilateral redesign
   here would pre-empt that review.
3. **Scope must stay measured.** Different-total substitution IS defended (the
   total is in the context) and that must keep being true — if it ever stops,
   the severity in the row is understated.

Nothing here is an exploit tool: the inputs are constants in this file and the
attack needs the session key, which the row states.
"""
import copy
import importlib.util
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from obfuscator.pack_state import state_digest  # noqa: E402
from obfuscator.section_split import split_sealed, stream_join  # noqa: E402

KEY = b"\x11" * 32
FILED = os.path.join(REPO, "docs", "security", "REVIEW_FINDINGS_FILED.md")


def _packs():
    """Two packs: same key, same section count, same total, different content."""
    a = split_sealed(b"A" * 32, sections=4, key=KEY, nonce_seed=b"aaa")
    b = split_sealed(b"B" * 32, sections=4, key=KEY, nonce_seed=b"bbb")
    return a, b


def _splice(host, donor, indices):
    """Replace `indices` in host with donor's, recomputing the unkeyed digest."""
    forged = copy.deepcopy(host)
    for i in indices:
        forged["sections"][i] = copy.deepcopy(donor["sections"][i])
    forged["state"] = state_digest(forged["sections"], forged["count"],
                                   forged["total"])
    return forged


def test_the_substitution_still_works_or_is_fixed():
    """MIMOSA-INTAKE-001's core claim, measured either way.

    If this test ever takes the 'refused' branch, the context gained a pack
    identity: update the register row and this test together. If it takes the
    'accepted' branch, the finding is still open and the row must still say so.
    """
    a, b = _packs()
    assert a["total"] == b["total"], "precondition: equal totals"
    assert a["key_hint"] == b["key_hint"], "precondition: same session key"

    forged = _splice(a, b, [0, 1])
    try:
        joined = bytes(stream_join(forged, KEY))
    except ValueError as exc:
        # The fix landed. Fail loudly so the row is updated deliberately.
        pytest.fail(
            "the cross-pack substitution is now REFUSED (%s). That means a "
            "pack identity was added to the context -- good, but the register "
            "row MIMOSA-INTAKE-001 still says OPEN. Close it with the fix "
            "commit and update this test to assert the refusal." % (exc,))

    assert joined.startswith(b"B" * 16), (
        "expected the donor's plaintext to be present, got %r" % (joined[:32],))
    assert b"B" * 16 in joined and b"A" * 8 in joined, (
        "the joined plaintext should MIX both packs: %r" % (joined,))


def test_a_different_total_is_still_refused():
    """Scope: the total IS bound, so a mismatched pack cannot be spliced.

    This keeps the severity grading honest. If this ever starts passing a
    subst, the row's 'requires equal total' qualifier is wrong.
    """
    a, _ = _packs()
    c = split_sealed(b"C" * 16, sections=4, key=KEY, nonce_seed=b"ccc")
    assert a["total"] != c["total"], "precondition: different totals"

    forged = _splice(a, c, [0])
    with pytest.raises(ValueError, match="integrity failure"):
        stream_join(forged, KEY)


def test_the_structural_digest_is_not_a_defence():
    """The digest is unkeyed, so recomputing it must bypass it.

    This is the reason the finding exists at all: the first attempt at the
    substitution was refused by the digest, and an attacker who recomputes it
    gets past that check. Documented so nobody mistakes the digest for a
    boundary.
    """
    a, b = _packs()
    unpatched = copy.deepcopy(a)
    unpatched["sections"][0] = copy.deepcopy(b["sections"][0])
    with pytest.raises(ValueError, match="state invalid"):
        stream_join(unpatched, KEY), "the unkeyed digest should catch the "
        "naive splice -- if not, this test's premise is wrong"

    # Recomputing the digest defeats that check; only the MAC is left.
    patched = _splice(a, b, [0])
    patched["state"] = state_digest(patched["sections"], patched["count"],
                                    patched["total"])
    try:
        stream_join(patched, KEY)
    except ValueError as exc:
        pytest.fail(
            "the recomputed digest did not get past the state check (%s); the "
            "finding's mechanism has changed and the row needs rewriting"
            % (exc,))


def test_no_pack_identity_exists_in_the_context():
    """The root cause, asserted so the fix is visible when it lands."""
    import inspect
    from obfuscator import section_split as ss

    ctx = ss._mac_context_v2(index=0, total=32, nonce=b"\x00" * 16)
    assert len(ctx) == 28, (
        "the context changed size; if a pack identity was added, close "
        "MIMOSA-INTAKE-001 and update this test")
    source = inspect.getsource(ss)
    for name in ("pack_id", "packid", "pack_nonce", "bundle_id"):
        assert name not in source, (
            "%r now appears in section_split.py -- a pack identity may have "
            "landed; close MIMOSA-INTAKE-001 deliberately" % (name,))


def test_the_row_is_filed_and_says_it_is_self_reported():
    """The register must not let a maintainer-found issue read as a review."""
    with open(FILED, encoding="utf-8") as fh:
        text = fh.read()
    assert "MIMOSA-INTAKE-001" in text
    assert "self-reported" in text, (
        "the row must say a maintainer found it; the format's `reviewer` "
        "field exists to prevent exactly this confusion")
    assert "NOT an independent review" in text
    for field in ("package:", "reviewer:", "received:", "severity:", "claim:",
                  "evidence:", "reproducible:", "affects:",
                  "maintainer-response:", "resolution:"):
        assert field in text, "the row is missing the %r field" % (field,)
    assert "OPEN" in text, (
        "the resolution is deliberately open pending the independent review; "
        "it must not read as fixed")


def test_the_row_does_not_claim_the_review_is_closed():
    with open(FILED, encoding="utf-8") as fh:
        lowered = fh.read().lower()
    assert "does not close the crypto review row" in lowered, (
        "the row must state that one self-found defect is not a review")
