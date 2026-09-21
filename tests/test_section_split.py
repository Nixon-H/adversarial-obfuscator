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
    pack["sections"][1]["data"] = "ff" + pack["sections"][1]["data"][2:]
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
