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


# ── §4.2: the context encoding is injective ───────────────────────────
#
# The bundle now asserts that `ctx_i ‖ plaintext_i` is unambiguous because
# every context field is fixed-width. That is a claim about the ENCODING, and
# it is what makes a length-prefix-free concatenation safe. Pin it.

def test_the_context_is_injective_across_indices():
    """ctx_i ‖ P_i cannot collide with ctx_j ‖ P_j for i != j.

    If contexts differed only in a field a caller could control, two sections
    could share a MAC input. The index field guarantees they do not.
    """
    from obfuscator.section_split import _mac_context_v2, _pack_id

    pack = split_sealed(PLAINTEXT, sections=2, key=K, nonce_seed=NONCE_SEED)
    pid = _pack_id(K, bytes.fromhex(pack["pack_nonce"]))
    nonce = bytes.fromhex(SECTIONS[0]["nonce"])

    ctxs = [_mac_context_v2(i, len(PLAINTEXT), nonce, pid, version=3)
            for i in range(4)]
    assert len(set(ctxs)) == 4, (
        "two section indices produced the same context, so two sections "
        "could share a MAC input")
    # The concatenation with plaintext is unambiguous because the context
    # length is fixed: the boundary is always byte 44 for v3.
    assert all(len(c) == 44 for c in ctxs)


def test_the_context_fields_are_all_fixed_width():
    """The injectivity argument rests entirely on fixed widths."""
    from obfuscator.section_split import (PACK_ID_BYTES, _mac_context_v2)

    v2 = _mac_context_v2(0, 8, b"\x00" * 16, version=2)
    v3 = _mac_context_v2(0, 8, b"\x00" * 16, b"\x00" * PACK_ID_BYTES)
    assert len(v2) == 28, "v2 context must be 4+4+4+16"
    assert len(v3) == 44, "v3 context must be 4+4+4+16+16"
    # The version is the FIRST field, so the two are distinguishable without
    # knowing which length to expect.
    assert v2[:4] == (2).to_bytes(4, "big")
    assert v3[:4] == (3).to_bytes(4, "big")


def test_plaintext_chunks_really_are_variable_length():
    """The premise of the §4.2 discussion: chunks are not fixed-width.

    If this ever became false the §4.2 wording would overstate the risk, and
    it says so explicitly -- so the claim is measured rather than assumed.
    """
    pack = split_sealed(b"x" * 10, sections=4, key=K, nonce_seed=b"t")
    lengths = [len(bytes.fromhex(s["data"])) - 32 for s in pack["sections"]]
    assert len(set(lengths)) > 1, (
        "chunks are uniform for this input; §4.2's 'variable-length' premise "
        "is not demonstrated by this case")
    assert sum(lengths) == 10


def test_the_bundle_documents_the_encoding_question():
    """§4.2 must be present and must not overclaim soundness."""
    with open(BUNDLE, encoding="utf-8") as fh:
        text = fh.read()
    assert "4.2" in text and "injective" in text.lower(), (
        "§4.2 must discuss whether the context encoding is injective")
    assert "length-prefix" in text.lower() or "fixed-width" in text.lower()
    assert "do not have a proof" in text.lower() or \
        "not claiming" in text.lower(), (
        "§4.2 must not present injectivity as a soundness proof")
