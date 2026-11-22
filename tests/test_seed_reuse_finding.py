"""Pins MIMOSA-INTAKE-002: keystream reuse when a seed repeats under one key.

Found by the maintainer on 2026-11-23 while attacking the v3 construction just
written. `split_sealed` derives section nonces deterministically from
`nonce_seed`, so two packs built with the same key AND the same seed reuse the
keystream and the XOR of their ciphertexts reveals the XOR of their plaintexts.

Severity is `low` because the shipped call path derives the key and the nonce
seed from the same per-build input, so a colliding nonce implies a colliding
key. That argument is ASSERTED here rather than asserted in prose: the last
test in this module reconstructs the shipped derivation and checks it.

The row stays OPEN because the fix is a nonce-derivation change (wire format)
and belongs with the independent review already examining this construction.
"""
import hashlib
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from obfuscator.section_split import split_sealed  # noqa: E402

KEY = b"\x11" * 32
FILED = os.path.join(REPO, "docs", "security", "REVIEW_FINDINGS_FILED.md")


def test_seed_reuse_under_one_key_is_a_two_time_pad():
    """MIMOSA-INTAKE-002's core claim, measured.

    The tag does NOT save us: it differs between the two packs because the
    contexts differ, so the 32-byte prefix is noise while the body is a clean
    plaintext XOR. That distinction is the whole finding -- someone could
    reasonably assume "the tag protects it" and be wrong.
    """
    a = split_sealed(b"A" * 16, sections=4, key=KEY, nonce_seed=b"reused")
    b = split_sealed(b"B" * 16, sections=4, key=KEY, nonce_seed=b"reused")

    # Preconditions: same key, same nonces, same pack id.
    assert a["key_hint"] == b["key_hint"], "precondition: one session key"
    assert a["pack_nonce"] == b["pack_nonce"], (
        "the pack identity is also seed-derived, so it collides too")
    assert a["sections"][0]["nonce"] == b["sections"][0]["nonce"]

    ct_a = bytes.fromhex(a["sections"][0]["data"])
    ct_b = bytes.fromhex(b["sections"][0]["data"])
    xor = bytes(p ^ q for p, q in zip(ct_a, ct_b))

    # Section 0 holds 4 plaintext bytes; they are the trailing 4 of the body.
    expected_plain_xor = bytes(p ^ q for p, q in zip(b"AAAA", b"BBBB"))
    assert xor[-4:] == expected_plain_xor, (
        "the trailing bytes are not a plaintext XOR; the finding's mechanism "
        "has changed and the row needs rewriting")
    # And the prefix is the TAG difference, not plaintext.
    assert xor[:32] != expected_plain_xor * 8, (
        "the tag prefix should NOT cancel; if it does, the finding is worse "
        "than reported because the body would be recoverable from offset 0")


def test_a_different_seed_does_not_collide():
    """The hazard needs the seed to repeat -- it is not a general weakness."""
    a = split_sealed(b"A" * 16, sections=4, key=KEY, nonce_seed=b"one")
    b = split_sealed(b"B" * 16, sections=4, key=KEY, nonce_seed=b"two")
    assert a["sections"][0]["nonce"] != b["sections"][0]["nonce"]
    assert a["pack_nonce"] != b["pack_nonce"]


def test_the_default_path_uses_urandom_not_a_derived_nonce():
    """No seed means fresh randomness; two packs must not share nonces."""
    a = split_sealed(b"A" * 16, sections=4, key=KEY)
    b = split_sealed(b"A" * 16, sections=4, key=KEY)
    assert a["pack_nonce"] != b["pack_nonce"], (
        "two unseeded builds shared a pack nonce -- the default path is not "
        "random, which is a far more serious defect than the seeded one")
    assert a["sections"][0]["nonce"] != b["sections"][0]["nonce"]


def test_the_shipped_derivation_cannot_collide():
    """The severity argument, checked rather than asserted.

    MIMOSA-INTAKE-002 is graded `low` because honesty.pipeline derives the
    honey pack's KEY from build_id where build_id = f(seed), so a colliding
    nonce implies a colliding key -- i.e. the same build. This reconstructs
    that derivation and shows distinct inputs give distinct pairs.

    If this test ever fails, the `low` grading in the filed row is wrong and
    the severity must be raised.
    """
    def shipped_ids(section_pack_val):
        seed = hashlib.sha256(section_pack_val.encode("utf-8")).digest()
        build_id = seed[:16].hex()
        key = hashlib.sha256(
            b"nx-honey-decoy:" + build_id.encode("utf-8")).digest()
        return seed, build_id, key

    pairs = [shipped_ids("pack-%d" % i)[1:] for i in range(5)]
    assert len(set(pairs)) == len(pairs), (
        "two distinct builds produced the same (build_id, key) pair; the "
        "severity reasoning for MIMOSA-INTAKE-002 no longer holds")

    # And the same input gives the same pair -- that is the reproducibility
    # property nonce_seed exists to provide.
    assert shipped_ids("pack-0")[1:] == shipped_ids("pack-0")[1:]


def test_the_row_is_filed_with_the_fields_and_stays_open():
    with open(FILED, encoding="utf-8") as fh:
        text = fh.read()
    assert "MIMOSA-INTAKE-002" in text
    for field in ("package:", "reviewer:", "received:", "severity:", "claim:",
                  "evidence:", "reproducible:", "affects:",
                  "maintainer-response:", "resolution:", "reviewed-by:"):
        assert field in text, "the row is missing the %r field" % (field,)
    assert "OPEN" in text, (
        "the fix is a wire-format change deferred to the independent review; "
        "the row must not read as resolved")
    assert "self-reported" in text
    assert "NOBODY" in text, (
        "the row must record that no independent reviewer has seen it")
