"""Tests for obfuscator/section_split.py — sealed section streaming."""
import json

import pytest

from obfuscator.section_split import (
    _keystream, _section_key, pack_json, split_sealed, stream_join,
)


def test_roundtrip_basic():
    payload = b"payload-bytes-" * 100
    pack = split_sealed(payload, sections=4, key=b"K" * 32)
    assert pack["count"] == 4
    out = stream_join(pack, b"K" * 32)
    assert bytes(out) == payload


def test_roundtrip_single_and_empty():
    assert bytes(stream_join(split_sealed(b"x", sections=4, key=b"K" * 32), b"K" * 32)) == b"x"
    assert bytes(stream_join(split_sealed(b"", sections=4, key=b"K" * 32), b"K" * 32)) == b""


def test_wrong_key_fails():
    pack = split_sealed(b"secret", sections=2, key=b"K" * 32)
    with pytest.raises(ValueError):
        stream_join(pack, b"W" * 32)


def test_tampered_section_fails():
    pack = split_sealed(b"secret-data-here", sections=3, key=b"K" * 32)
    # XOR the first byte instead of overwriting it with "ff": 1 run
    # in 256 the original byte IS 0xff, the pack is unchanged, and
    # the test fails with "DID NOT RAISE" (seen on the 3.11 job).
    _data = pack["sections"][1]["data"]
    pack["sections"][1]["data"] = ("%02x" % (int(_data[:2], 16) ^ 0xFF)) + _data[2:]
    with pytest.raises(ValueError):
        stream_join(pack, b"K" * 32)


def test_reordered_sections_still_join():
    # Order travels with the sections (index field), so shuffle is fine.
    pack = split_sealed(b"order-test-payload", sections=4, key=b"K" * 32)
    pack["sections"] = list(reversed(pack["sections"]))
    assert bytes(stream_join(pack, b"K" * 32)) == b"order-test-payload"


def test_missing_section_fails():
    pack = split_sealed(b"0123456789abcdef", sections=4, key=b"K" * 32)
    pack["sections"].pop()
    with pytest.raises(ValueError):
        stream_join(pack, b"K" * 32)


def test_pack_json_envelope():
    blob, key = pack_json(b"hello", sections=2)
    pack = json.loads(blob.decode())
    assert pack["count"] == 2
    assert bytes(stream_join(pack, key)) == b"hello"


def test_returns_mutable_buffer():
    pack = split_sealed(b"wipe-me", sections=2, key=b"K" * 32)
    out = stream_join(pack, b"K" * 32)
    assert isinstance(out, bytearray)


def test_unkeyed_tag_forgery_is_rejected():
    """The section tag must be a MAC, not a bare digest.

    Anyone can recompute sha256(part); the old format accepted that, so an
    attacker who could touch the ciphertext could re-seal modified bytes
    with an unkeyed tag.  With the HMAC, the same forgery -- correct
    keystream, correct unkeyed tag -- must be rejected.
    """
    import hashlib

    import pytest

    from obfuscator.section_split import _keystream, split_sealed, stream_join

    key = b"K" * 32
    pack = split_sealed(b"secret-payload-bytes", sections=2, key=key)
    # Attacker with the pack (not the key) rewrites section 0 using the OLD
    # scheme: plaintext, sha256(part) tag, keystream ciphertext.
    sec = pack["sections"][0]
    nonce = bytes.fromhex(sec["nonce"])
    forged_plain = b"FORGED" + b"x" * 8
    forged_tagged = hashlib.sha256(forged_plain).digest() + forged_plain
    sec["data"] = bytes(
        a ^ b for a, b in zip(forged_tagged, _keystream(key, nonce, len(forged_tagged)))
    ).hex()
    with pytest.raises(ValueError):
        stream_join(pack, key)


# ── crypto-architecture audit (reviewer P1, 2026-11-20) ──────────────────
#
# The reviewer asked which primitive protects the shipped sections, how the
# keys are derived and separated, and whether nonces are unique. These tests
# pin the answers to the code that actually ships, so the documentation
# cannot drift into "AES-GCM is implemented, therefore AES-GCM is used".

def test_the_shipped_construction_is_keystream_xor_plus_hmac_not_aead():
    """Section data is SHA-256 keystream XOR; integrity is HMAC-SHA256.

    The AEAD helper (obfuscator.aead) exists and is separately tested, but it
    is NOT what protects the section pack. Anyone summarising this project
    must not report "AES-GCM sections".
    """
    key = b"A" * 32
    payload = b"shipped-path" * 50
    pack = split_sealed(payload, sections=3, key=key)
    for section in pack["sections"]:
        nonce = bytes.fromhex(section["nonce"])
        ciphertext = bytes.fromhex(section["data"])
        # 32-byte tag prefix + the plaintext slice, all XORed with the
        # SHA-256 counter-mode keystream under this section's derived key.
        section_key = _section_key(key, section["i"], nonce)
        recovered = bytes(
            a ^ b for a, b in zip(
                ciphertext, _keystream(section_key, nonce, len(ciphertext))))
        assert recovered[32:] == payload[
            section["i"] * (len(payload) // 3):
            (section["i"] + 1) * (len(payload) // 3)], (
            "section body is not a plain keystream XOR under the derived key")
        # the 32-byte prefix is an HMAC, not a bare digest
        import hashlib
        import hmac
        expected = hmac.new(section_key + nonce, recovered[32:],
                            hashlib.sha256).digest()
        assert recovered[:32] == expected


def test_each_section_uses_a_distinct_derived_key():
    """Key separation: master + index + nonce, never the master directly."""
    key = b"B" * 32
    pack = split_sealed(b"x" * 300, sections=4, key=key)
    derived = set()
    for section in pack["sections"]:
        nonce = bytes.fromhex(section["nonce"])
        section_key = _section_key(key, section["i"], nonce)
        assert section_key != key, (
            "a section used the master key directly instead of a derived one")
        derived.add(section_key)
    assert len(derived) == 4, "two sections share a derived key"


def test_section_nonces_are_unique_per_pack():
    """Nonce uniqueness: the counter-mode stream must never repeat."""
    key = b"C" * 32
    pack = split_sealed(b"y" * 400, sections=6, key=key)
    nonces = [section["nonce"] for section in pack["sections"]]
    assert len(set(nonces)) == len(nonces), "nonce reuse inside one pack"


def test_index_binds_the_key_not_just_the_metadata():
    """Same master key, same nonce, different index -> different key.

    If the index only appeared in the metadata, an attacker could relabel a
    section and have it decrypt; it must be part of the key derivation.
    """
    key = b"D" * 32
    nonce = b"N" * 16
    assert _section_key(key, 0, nonce) != _section_key(key, 1, nonce)


def test_a_relabelled_section_fails_to_join():
    """Moving ciphertext between sections breaks the tag (key is bound)."""
    key = b"E" * 32
    payload = b"z" * 400
    pack = split_sealed(payload, sections=4, key=key)
    pack["sections"][0]["data"] = pack["sections"][1]["data"]
    with pytest.raises(ValueError):
        stream_join(pack, key)
