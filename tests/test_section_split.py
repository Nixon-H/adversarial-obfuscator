"""Tests for obfuscator/section_split.py — sealed section streaming."""
import json

import pytest

from obfuscator.section_split import pack_json, split_sealed, stream_join


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
