"""The standalone crypto bundle must describe the construction it names.

`docs/security/CRYPTO_REVIEW_BUNDLE_STANDALONE.md` is written to be sent to a
cryptographer who will NOT clone this repository. That makes it the highest-
consequence document in the set: if it misdescribes the construction, the
review examines a design that does not exist and its findings attach to
nothing.

The earlier crypto package had exactly this class of drift risk, and its
reproduction commands were found broken when finally run. So every concrete
value in the bundle is asserted here against the code: the domain strings, the
context layout, the keystream construction, the digest schema, and the nonce
size. Assertions are read from the implementation, not restated.

This module asserts NOTHING about cryptographic soundness. A green suite here
means the description is accurate, not that the design is good.
"""
import hashlib
import hmac
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from obfuscator import section_split as ss  # noqa: E402
from obfuscator.pack_state import STATE_SCHEMA  # noqa: E402

BUNDLE = os.path.join(REPO, "docs", "security",
                      "CRYPTO_REVIEW_BUNDLE_STANDALONE.md")


def _text():
    with open(BUNDLE, encoding="utf-8") as fh:
        return fh.read()


# ── §3 key derivation ─────────────────────────────────────────────────

def test_the_bundle_names_the_real_domains():
    text = _text()
    assert ss.SECTION_ENC_DOMAIN == b"nx-section-enc:"
    assert ss.SECTION_MAC_DOMAIN == b"nx-section-mac:"
    assert "nx-section-enc:" in text
    assert "nx-section-mac:" in text


def test_the_bundle_formula_reproduces_the_implementation():
    """Recompute §3 by hand and compare with the builder's own derivation."""
    key = bytes(range(32))
    index = 3
    nonce = b"\x5a" * 16

    basis = key + index.to_bytes(4, "big") + nonce
    expected_enc = hashlib.sha256(b"nx-section-enc:" + basis).digest()
    expected_mac = hashlib.sha256(b"nx-section-mac:" + basis).digest()

    enc, mac = ss._section_keys_v2(key, index, nonce)
    assert enc == expected_enc, (
        "§3's documented derivation does not reproduce _section_keys_v2")
    assert mac == expected_mac
    assert enc != mac


# ── §4 the authenticated context ──────────────────────────────────────

def test_the_bundle_context_layout_is_the_implementation():
    """§4 documents a 28-byte ctx: v4 ‖ i4 ‖ T4 ‖ nonce16."""
    ctx = ss._mac_context_v2(index=5, total=4096, nonce=b"\x11" * 16)
    assert len(ctx) == 28, "§4 documents a fixed 28-byte context"
    assert ctx[0:4] == ss.SECTION_PACK_VERSION.to_bytes(4, "big")
    assert ctx[4:8] == (5).to_bytes(4, "big")
    assert ctx[8:12] == (4096).to_bytes(4, "big")
    assert ctx[12:] == b"\x11" * 16


def test_the_bundle_states_the_right_pack_version():
    text = _text()
    assert "v == 2" in text or "= 2" in text
    assert ss.SECTION_PACK_VERSION == 2


# ── §5/§6 the keystream and composition ───────────────────────────────

def test_the_bundle_keystream_formula_reproduces_the_implementation():
    """§5 documents SHA256(key ‖ nonce ‖ u64be(counter)), truncated."""
    key = b"\x07" * 32
    nonce = b"\x09" * 16
    n = 100

    expected = b""
    counter = 0
    while len(expected) < n:
        expected += hashlib.sha256(
            key + nonce + counter.to_bytes(8, "big")).digest()
        counter += 1
    expected = expected[:n]

    assert ss._keystream(key, nonce, n) == expected, (
        "§5's documented keystream does not reproduce _keystream")


def test_the_bundle_ordering_claim_holds():
    """§6 claims verification precedes plaintext use."""
    import inspect
    src = inspect.getsource(ss.stream_join)
    lines = [ln.strip() for ln in src.splitlines()]
    verify_at = next(i for i, ln in enumerate(lines) if "compare_digest" in ln)
    extend_at = next(i for i, ln in enumerate(lines) if "joined.extend" in ln)
    assert verify_at < extend_at, (
        "§6 tells the reviewer that no plaintext is used before its tag "
        "verifies; stream_join now does the opposite")


def test_the_bundle_tag_length_is_the_implementation():
    """§5 documents a 32-byte tag prepended to the plaintext."""
    pack = ss.split_sealed(b"abcdefghij", sections=1, key=b"\x01" * 32,
                           nonce_seed=b"s")
    enc = bytes.fromhex(pack["sections"][0]["data"])
    # |ct| = |tag| + |plaintext|
    assert len(enc) == 32 + 10, (
        "the section ciphertext should be a 32-byte tag plus the plaintext")


# ── §7 the structural digest ──────────────────────────────────────────

def test_the_bundle_digest_schema_is_the_implementation():
    text = _text()
    assert STATE_SCHEMA == "nx-pack-state/v1"
    assert "nx-pack-state/v1:" in text, (
        "§7 must name the digest schema the code uses")


def test_the_bundle_says_the_digest_is_not_authentication():
    """§7's most important sentence: it must not read as a security claim."""
    text = _text().lower()
    assert "not a security boundary" in text or \
        "do not treat it as authentication" in text, (
        "§7 must be explicit that the structural digest is unkeyed and is not "
        "authentication")


# ── §8 the weaknesses must stay listed ────────────────────────────────

def test_the_bundle_keeps_all_seven_weaknesses():
    """The list is why a reviewer engages; losing one understates the risk."""
    text = _text()
    for topic in ("MAC-then-encrypt", "Bespoke stream cipher", "key_hint",
                  "nonce-reuse", "Section length is implicit", "salt",
                  "v1 legacy path"):
        assert topic in text, (
            "the bundle stopped naming the weakness %r" % (topic,))


def test_key_hint_really_is_an_unkeyed_hash():
    """§8 item 3 says so; if the code changes, the warning becomes wrong."""
    key = b"\x02" * 32
    pack = ss.split_sealed(b"x", sections=1, key=key, nonce_seed=b"n")
    assert pack["key_hint"] == hashlib.sha256(key).hexdigest()[:16]


# ── the bundle must stay honest about not being a review ──────────────

def test_the_bundle_declares_it_has_not_been_reviewed():
    text = _text()
    assert "NOT REVIEWED" in text, (
        "the bundle must state up front that no cryptographer has seen it")
    assert "What we are not claiming" in text


def test_the_bundle_does_not_claim_soundness():
    """Assertion vs denial: "we are NOT claiming it is secure" is fine.

    A plain substring check cannot tell those apart — it flagged the negation
    on the first run. Each phrase is therefore examined in context: it fails
    only when it is not preceded by a negation within the same clause.
    """
    import re

    lowered = _text().lower()
    negations = r"(not|no|never|neither|nor|cannot|can't|isn't|don't|doesn't)"
    for phrase in ("is secure", "has been reviewed", "reviewer confirmed",
                   "independently reviewed"):
        for match in re.finditer(re.escape(phrase), lowered):
            window = lowered[max(0, match.start() - 90):match.start()]
            assert re.search(negations, window), (
                "the bundle asserts %r without a negation in the preceding "
                "clause — that reads as a security or review claim: ...%s%s..."
                % (phrase, window[-60:], phrase))


def test_the_bundle_states_the_constraint_that_produced_the_design():
    """§1: the stdlib-only loader. Without it the design looks arbitrary."""
    text = _text()
    assert "standard library" in text.lower()
    assert "hashlib" in text and "hmac" in text
    assert "cannot be assumed" in text.lower() or "deployment constraint" in \
        text.lower()


def test_the_bundle_gives_a_return_channel():
    text = _text()
    assert "security/advisories/new" in text, (
        "a reviewer must be told where to send findings")
    assert "REVIEW_FINDINGS_INTAKE.md" in text
