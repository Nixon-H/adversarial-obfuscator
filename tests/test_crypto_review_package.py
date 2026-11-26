"""The crypto review package must keep describing the code it points at.

`docs/security/CRYPTO_REVIEW_PACKAGE.md` is the commissioning package for the
register's P1 row *independent cryptographic review*. It is handed to a
reviewer who has no context, so every concrete claim in it is either:

  * a measured property, which is asserted here, or
  * an open question, which is not asserted (asking a reviewer to judge
    something is not a claim that it holds).

This module enforces the first category. If the construction changes shape,
the package stops matching and a test fails — which is the right outcome,
because a review package describing a construction that no longer exists is
worse than none: the reviewer's findings would attach to the wrong code.

It deliberately does NOT assert anything about cryptographic soundness. That
is the reviewer's job, and a green test here must never be read as one.
"""
import hashlib
import inspect
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from obfuscator import section_split as ss  # noqa: E402
from obfuscator.pack_state import STATE_SCHEMA, state_digest  # noqa: E402

PACKAGE = os.path.join(REPO, "docs", "security", "CRYPTO_REVIEW_PACKAGE.md")


def _package_text():
    with open(PACKAGE, encoding="utf-8") as fh:
        return fh.read()


def _pack(sections=4, payload=b"payload bytes for review " * 4):
    return ss.split_sealed(payload, sections=sections, key=b"\x11" * 32,
                           nonce_seed=b"review")


# ── §3.1 key derivation is domain-separated and positional ──────────────

def test_the_documented_domains_are_the_implemented_ones():
    assert ss.SECTION_ENC_DOMAIN == b"nx-section-enc:"
    assert ss.SECTION_MAC_DOMAIN == b"nx-section-mac:"
    text = _package_text()
    assert "nx-section-enc:" in text and "nx-section-mac:" in text


def test_enc_and_mac_keys_are_independent():
    """§3.1 claims role separation; a shared key would be a real weakness."""
    enc, mac = ss._section_keys_v2(b"\x11" * 32, 3, b"\x22" * 16)
    assert enc != mac, "the encryption and MAC keys must not be the same key"
    # Both must depend on the index and the nonce, or sections collide.
    enc2, mac2 = ss._section_keys_v2(b"\x11" * 32, 4, b"\x22" * 16)
    assert enc != enc2 and mac != mac2
    enc3, mac3 = ss._section_keys_v2(b"\x11" * 32, 3, b"\x33" * 16)
    assert enc != enc3 and mac != mac3


# ── §3.2 the authenticated context ─────────────────────────────────────

def test_the_documented_context_is_the_implemented_one():
    ctx = ss._mac_context_v2(index=2, total=999, nonce=b"\x00" * 16)
    assert ctx[:4] == ss.SECTION_PACK_VERSION.to_bytes(4, "big")
    assert ctx[4:8] == (2).to_bytes(4, "big")
    assert ctx[8:12] == (999).to_bytes(4, "big")
    assert ctx[12:] == b"\x00" * 16
    assert len(ctx) == 28, "the package documents a fixed-width 28-byte ctx"


def test_the_version_is_inside_the_context_so_downgrade_fails():
    """§4's downgrade claim, measured: editing `v` must break the tag."""
    pack = _pack()
    assert pack["v"] == ss.SECTION_PACK_VERSION

    import copy
    for label, mutate in (
            ("downgrade to v1", lambda p: p.__setitem__("v", 1)),
            ("strip the version", lambda p: p.pop("v", None)),
    ):
        tampered = copy.deepcopy(pack)
        mutate(tampered)
        with pytest.raises(ValueError, match="integrity failure"):
            ss.stream_join(tampered, b"\x11" * 32)


# ── §3.3/§3.4 composition order: tag precedes plaintext, verify precedes use

def test_verification_precedes_plaintext_accumulation():
    """§5.1's measured claim: no plaintext is used before its tag verifies."""
    src = inspect.getsource(ss.stream_join)
    lines = [ln.strip() for ln in src.splitlines()]
    verify_at = next(i for i, ln in enumerate(lines)
                     if "compare_digest" in ln)
    extend_at = next(i for i, ln in enumerate(lines) if "joined.extend" in ln)
    assert verify_at < extend_at, (
        "stream_join accumulates plaintext before verifying the section tag; "
        "the package claims the opposite")


def test_every_tag_comparison_is_constant_time():
    """§6 question 7, measured: four sites, all compare_digest."""
    with open(os.path.join(REPO, "obfuscator", "section_split.py"),
              encoding="utf-8") as fh:
        src = fh.read()
    assert src.count("compare_digest") == 4, (
        "expected four tag comparisons (in-process join + three emitted "
        "loader templates); update the package if this legitimately changed")
    # And no tag comparison uses bare ==.
    assert "tag ==" not in src and "== tag" not in src


# ── §5.3 key_hint: the documented weakness is real, not hypothetical ────

def test_key_hint_is_an_unkeyed_hash_of_the_session_key():
    """The package calls this an oracle; here is the measurement.

    This is asserted so the weakness cannot be quietly removed from the
    package while the code still has it — a reviewer must be told.
    """
    key = b"\x11" * 32
    pack = ss.split_sealed(b"abc", sections=1, key=key, nonce_seed=b"r")
    assert pack["key_hint"] == hashlib.sha256(key).hexdigest()[:16], (
        "key_hint changed shape; the package's §5.3 description is stale")
    assert "key_hint" in _package_text()


def test_the_state_digest_is_unkeyed_as_documented():
    """§3.6/§5.6: the state digest is not a security boundary."""
    a = state_digest([{"i": 0, "salt": "aa"}], 1, 10)
    b = state_digest([{"i": 0, "salt": "aa"}], 1, 10)
    assert a == b
    # Unkeyed: recomputable by anyone holding the declared structure.
    assert a == state_digest([{"i": 0, "salt": "aa"}], 1, 10)
    assert STATE_SCHEMA == "nx-pack-state/v1"
    assert "unkeyed" in _package_text()


# ── §7 the package must keep its honesty markers ───────────────────────

def test_the_package_states_the_review_is_not_performed():
    text = _package_text()
    assert "NOT PERFORMED" in text, (
        "the package must state up front that no independent review has "
        "happened, or it reads as a completed review")
    assert "not" in text.lower()
    assert "What the maintainers are NOT claiming" in text, (
        "the package must keep its explicit non-claims section")


def test_the_package_keeps_naming_its_open_questions():
    """The questions are the deliverable; losing them loses the commission."""
    text = _package_text()
    assert "Specific questions for the reviewer" in text
    for question in ("MAC-then-encrypt", "key_hint", "nonce", "ctx_i"):
        assert question in text, (
            "the package stopped asking about %r" % (question,))


def test_the_package_documents_reproduction_commands():
    """A reviewer must be able to re-derive every number without us."""
    text = _package_text()
    assert "pytest" in text
    assert "nx_fuzz.py" in text
    assert "split_sealed" in text


def test_the_package_matches_the_current_pack_version():
    """The package's header must name the shipped format, not a literal.

    This was hardcoded to v2 and kept passing after the constant moved --
    exactly the staleness this module exists to catch.
    """
    text = _package_text()
    expected_title = "section pack v%d" % (ss.SECTION_PACK_VERSION,)
    assert expected_title in text, (
        "the package title must name the shipped format version (%d)"
        % (ss.SECTION_PACK_VERSION,))
    assert "pack_id" in text or "pack identity" in text, (
        "the package must describe the v3 pack identity; a reviewer with the "
        "v2 context would be reviewing a construction that no longer ships")
