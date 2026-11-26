"""Pins MIMOSA-INTAKE-003: `salt` is keyed, and the docs said otherwise.

Found by auditing the review documents against the implementation rather than by
reading either alone. Both the standalone bundle (§8 item 6) and the main
package (§3.6, §5.6) described `salt` as "unkeyed". It is
`SHA256(K_enc_i ‖ N_i)[:16]` — a truncated hash of the ENCRYPTION KEY.

Two of the three findings in this register so far came from making a document
and an implementation disagree. These tests formalise that move: the claim in
the prose is recomputed from the code, so it cannot drift back.

The finding is about DOCUMENTATION ACCURACY, not a new cryptographic break.
Whether three published 64-bit truncations are acceptable is explicitly left to
the reviewer, and these tests assert that the documents leave it there.
"""
import hashlib
import os
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from obfuscator.section_split import (  # noqa: E402
    PACK_ID_BYTES, _pack_id, _section_keys_v2, split_sealed,
)

BUNDLE = os.path.join(REPO, "docs", "security",
                      "CRYPTO_REVIEW_BUNDLE_STANDALONE.md")
PACKAGE = os.path.join(REPO, "docs", "security", "CRYPTO_REVIEW_PACKAGE.md")
FILED = os.path.join(REPO, "docs", "security", "REVIEW_FINDINGS_FILED.md")

KEY = b"\x11" * 32


def _text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _pack():
    return split_sealed(b"x" * 32, sections=4, key=KEY, nonce_seed=b"s")


# ── the measurement: salt is a function of the ENC key ────────────────

def test_salt_is_a_truncated_hash_of_the_encryption_key():
    """The core claim. If this ever stops holding, the docs must change back."""
    pack = _pack()
    for section in pack["sections"]:
        nonce = bytes.fromhex(section["nonce"])
        skey, _mkey = _section_keys_v2(KEY, section["i"], nonce)
        expected = hashlib.sha256(skey + nonce).hexdigest()[:16]
        assert section["salt"] == expected, (
            "salt is no longer SHA256(K_enc || nonce)[:16]; the documents "
            "describe it as such and would need updating")
        # And it is genuinely key-dependent: a different key gives a different
        # salt for the same index and nonce.
    other = split_sealed(b"x" * 32, sections=4, key=b"\x22" * 32,
                         nonce_seed=b"s")
    assert other["sections"][0]["salt"] != pack["sections"][0]["salt"], (
        "salt did not change with the key, so it would actually be unkeyed "
        "after all and the finding's premise is wrong")


def test_the_pack_publishes_three_independent_truncations():
    """key_hint, salt_i and pack_id are all 64-bit functions of key material.

    Sizes are checked in BYTES: PACK_ID_BYTES is 16 and the ids are compared as
    bytes. (An earlier draft of this test compared hex-string lengths and
    wrongly expected pack_id to be 16 characters when it is 16 BYTES = 32 hex
    characters. The code was right; the assertion was not.)
    """
    pack = _pack()
    hint = pack["key_hint"]
    salt0 = pack["sections"][0]["salt"]
    pid_bytes = _pack_id(KEY, bytes.fromhex(pack["pack_nonce"]))

    assert len(pid_bytes) == PACK_ID_BYTES == 16, (
        "pack_id should be %d bytes, got %d" % (PACK_ID_BYTES,
                                                len(pid_bytes)))
    for value, label in ((hint, "key_hint"), (salt0, "salt")):
        assert len(value) == 16, (
            "%s should be a 16-hex-char (64-bit) truncation, got %r"
            % (label, value))

    pid_hex = pid_bytes.hex()
    assert hint != salt0 and hint != pid_hex and salt0 != pid_hex, (
        "the three truncations are not independent, so counting them "
        "separately overstates the exposure -- the documents say they are "
        "independent and would need correcting")

    # Salts differ per section: one hash of key material per section.
    salts = [s["salt"] for s in pack["sections"]]
    assert len(set(salts)) == len(salts)
    assert pack["pack_nonce"]  # the pack id's input is published too


# ── the documents must not call salt unkeyed ──────────────────────────

def test_the_bundle_no_longer_calls_salt_unkeyed():
    text = _text(BUNDLE)
    assert "KEYED" in text, (
        "the bundle must describe salt as keyed")
    # The old phrasing must be gone.
    assert "`salt` is unkeyed" not in text, (
        "the bundle still calls salt unkeyed -- the exact error "
        "MIMOSA-INTAKE-003 records")
    assert "MIMOSA-INTAKE-003" in text, (
        "the correction must cite the finding, so a reader can follow it")


def test_the_package_no_longer_calls_salt_unkeyed():
    text = _text(PACKAGE)
    assert "**5.6 `salt` is unkeyed" not in text, (
        "the main package still opens 5.6 by calling salt unkeyed")
    assert "KEYED" in text
    assert "MIMOSA-INTAKE-003" in text


def test_the_documents_list_all_three_truncations_together():
    """The finding's substance: the set must be enumerated, not one at a time."""
    for path in (BUNDLE, PACKAGE):
        text = _text(path)
        for name in ("key_hint", "salt", "pack_id"):
            assert name in text, (
                "%s does not mention %s" % (os.path.basename(path), name))
        assert "64" in text, (
            "%s does not state the truncation width" % os.path.basename(path))


def test_the_documents_leave_the_judgement_to_the_reviewer():
    """The fix is disclosure, not a decision. Do not pre-empt the review."""
    for path in (BUNDLE, PACKAGE):
        lowered = _text(path).lower()
        assert "reviewer" in lowered, (
            "%s must hand the truncation question to the reviewer rather "
            "than deciding it" % os.path.basename(path))


# ── the row ───────────────────────────────────────────────────────────

def test_the_row_is_filed_and_admits_the_error_direction():
    text = _text(FILED)
    assert "MIMOSA-INTAKE-003" in text
    for field in ("package:", "reviewer:", "received:", "severity:", "claim:",
                  "evidence:", "reproducible:", "affects:",
                  "maintainer-response:", "resolution:", "reviewed-by:"):
        assert field in text, "the row is missing the %r field" % (field,)
    assert "flatters the construction" in text, (
        "the row should say which direction the documentation error ran, "
        "because that is what made it worth filing rather than fixing quietly")
    assert "NOBODY" in text
