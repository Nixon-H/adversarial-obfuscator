"""Pins the worked test vector published in the crypto review bundle.

`CRYPTO_REVIEW_BUNDLE_STANDALONE.md` §11 gives a reviewer every intermediate for
one pack, so the construction can be checked by hand with nothing but `hashlib`
and `hmac`. Before that vector was published it was reproduced in a clean
interpreter importing nothing from this project -- which is the property that
makes it useful, and the property that a wire-format change would silently
break.

These tests do two jobs:

  1. RECOMPUTE the vector from the documented formulas, with no import of this
     project's crypto code beyond the builder that produced it. If the
     construction changes shape, the published numbers become wrong and a
     reviewer following §11 would get a mismatch and file it as a defect. That
     must instead fail here, first.
  2. CHECK the bundle still carries those numbers, so the document and the
     implementation cannot drift apart -- the failure mode behind two of the
     three findings already filed.
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

from obfuscator.section_split import split_sealed  # noqa: E402

BUNDLE = os.path.join(REPO, "docs", "security",
                      "CRYPTO_REVIEW_BUNDLE_STANDALONE.md")

# The published inputs.
K = bytes(range(32))
PLAINTEXT = b"ABCDEFGH"
NONCE_SEED = b"vector"

# The published outputs.
PACK_NONCE = "5549563aed1e0f84069b3d0dbe9d9cf7"
PACK_ID = "5b1f3620a4cf5b1cc4979f2d94cf6e4e"
KEY_HINT = "630dcd2966c43366"
STATE = "eae758258ea4975adcb4a802d68b5170"
SECTIONS = [
    {"i": 0, "nonce": "f59dcefd82e7c385dae4264e1193c4af",
     "enc_key": "0129e91768c48513f2ee2aa6fd7eab2d"
                "aa17fafb5d135ec4c521140b17703cf0",
     "mac_key": "0f354d91e5242ce78044b22e1b8d5ed0"
                "13159299d287687386ec52cad9f45224",
     "salt": "c7401dba1e9fbcdf", "plaintext": b"ABCD",
     "tag": "3ac5b01ffc3d691ad2a0635d76cc5f2d"
            "37ffacc043cb2d284f92d66dbeda9a23"},
    {"i": 1, "nonce": "bd433f1f970e6ef95f036f9d54e1bf98",
     "enc_key": "bd5b1a54554207be6052ad9791ca9ff8"
                "d85beb712eaa39fac118bd8d4a28653d",
     "mac_key": "75ff1cb8917363f9bc57db1fddce735c"
                "84f359fc0b40ba6b69b2e5e300057c65",
     "salt": "5e459fe597a2ad2a", "plaintext": b"EFGH",
     "tag": "b2b4a3ffa0e897f00cda84b5dd0b39fb"
            "7331b3ba1188b038017580e3a30335ee"},
]


def _recompute(i, nonce, plaintext, total, version, pack_id):
    """The §11 recipe, standard library only — exactly what a reviewer runs."""
    basis = K + i.to_bytes(4, "big") + nonce
    enc_key = hashlib.sha256(b"nx-section-enc:" + basis).digest()
    mac_key = hashlib.sha256(b"nx-section-mac:" + basis).digest()
    ctx = (version.to_bytes(4, "big") + i.to_bytes(4, "big")
           + total.to_bytes(4, "big") + nonce + pack_id)
    tag = hmac.new(mac_key, ctx + plaintext, hashlib.sha256).digest()
    salt = hashlib.sha256(enc_key + nonce).hexdigest()[:16]
    return enc_key, mac_key, ctx, tag, salt


def test_the_published_vector_recomputes_from_the_documented_formulas():
    """The reviewer's hand-check, executed."""
    pack_nonce = bytes.fromhex(PACK_NONCE)
    pack_id = hashlib.sha256(
        b"nx-pack-id:" + K + pack_nonce).digest()[:16]
    assert pack_id.hex() == PACK_ID, (
        "the published pack_id does not follow from the published formulas")

    total = len(PLAINTEXT)
    for expected in SECTIONS:
        nonce = bytes.fromhex(expected["nonce"])
        enc_key, mac_key, ctx, tag, salt = _recompute(
            expected["i"], nonce, expected["plaintext"], total, 3, pack_id)
        assert enc_key.hex() == expected["enc_key"]
        assert mac_key.hex() == expected["mac_key"]
        assert len(ctx) == 44, "§11 documents a 44-byte v3 context"
        assert tag.hex() == expected["tag"], (
            "section %d's published tag does not recompute; a reviewer "
            "following §11 would report a mismatch" % (expected["i"],))
        assert salt == expected["salt"]


def test_the_builder_produces_the_published_vector():
    """The other direction: the shipped builder emits these exact values."""
    pack = split_sealed(PLAINTEXT, sections=2, key=K, nonce_seed=NONCE_SEED)
    assert pack["v"] == 3
    assert pack["pack_nonce"] == PACK_NONCE
    assert pack["key_hint"] == KEY_HINT
    assert pack["state"] == STATE
    assert pack["count"] == 2 and pack["total"] == len(PLAINTEXT)
    for expected, actual in zip(SECTIONS, pack["sections"]):
        assert actual["i"] == expected["i"]
        assert actual["nonce"] == expected["nonce"]
        assert actual["salt"] == expected["salt"]


def test_the_bundle_publishes_the_vector_it_is_pinned_to():
    """The document must still carry these numbers, or §11 misleads."""
    with open(BUNDLE, encoding="utf-8") as fh:
        text = fh.read()
    for label, value in (("pack_nonce", PACK_NONCE), ("pack_id", PACK_ID),
                         ("key_hint", KEY_HINT)):
        assert value in text, (
            "§11 no longer publishes %s=%s" % (label, value))
    for section in SECTIONS:
        assert section["tag"] in text, (
            "§11 no longer publishes the section %d tag" % (section["i"],))
        assert section["salt"] in text


def test_the_bundle_states_the_vector_was_independently_reproduced():
    """The claim that makes the vector worth trusting must be present."""
    with open(BUNDLE, encoding="utf-8") as fh:
        lowered = fh.read().lower()
    assert "importing nothing from" in lowered or \
        "standard-library-only" in lowered or "clean interpreter" in lowered, (
        "§11 must say the vector was reproduced without importing the "
        "project, which is what makes it checkable by an outsider")
    assert "if your recomputation disagrees" in lowered, (
        "§11 should invite the reviewer to report a mismatch as a finding")


def test_the_bundle_names_the_regeneration_script():
    """A reviewer or maintainer must be able to regenerate the vector."""
    with open(BUNDLE, encoding="utf-8") as fh:
        text = fh.read()
    assert "gen_crypto_test_vectors.py" in text
    assert "test_crypto_test_vectors.py" in text, (
        "§11 must name the test that fails if the implementation drifts")
