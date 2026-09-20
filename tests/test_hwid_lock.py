import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.hwid_lock import derive_hwid_key, lock_payload, unlock_payload


def test_roundtrip():
    pack = lock_payload(b"hello world", "HWID-1")
    assert set(pack) == {"salt", "nonce", "data"}
    assert unlock_payload(pack, "HWID-1") == b"hello world"


def test_wrong_hwid_fails():
    pack = lock_payload(b"secret", "HWID-1")
    with pytest.raises(ValueError):
        unlock_payload(pack, "HWID-2")


def test_tampered_data_fails():
    pack = lock_payload(b"secret", "HWID-1")
    bad = dict(pack)
    raw = bytearray.fromhex(bad["data"])
    raw[-1] ^= 0xFF
    bad["data"] = bytes(raw).hex()
    with pytest.raises(ValueError):
        unlock_payload(bad, "HWID-1")
    bad2 = dict(pack)
    raw2 = bytearray.fromhex(bad2["salt"])
    raw2[0] ^= 0xFF
    bad2["salt"] = bytes(raw2).hex()
    with pytest.raises(ValueError):
        unlock_payload(bad2, "HWID-1")


def test_different_salt_different_ciphertext():
    p1 = lock_payload(b"same", "HWID-1")
    p2 = lock_payload(b"same", "HWID-1")
    # Random salt/nonce -> ciphertext differs (overwhelmingly likely;
    # salts themselves must differ).
    assert p1["salt"] != p2["salt"] or p1["nonce"] != p2["nonce"]
    assert p1["data"] != p2["data"]
    assert unlock_payload(p1, "HWID-1") == unlock_payload(p2, "HWID-1") == b"same"


def test_empty_payload_roundtrip():
    pack = lock_payload(b"", "HWID-1")
    assert unlock_payload(pack, "HWID-1") == b""


def test_derive_key_properties():
    k1 = derive_hwid_key("HWID-1", bytes.fromhex("00" * 16))
    k2 = derive_hwid_key("HWID-1", bytes.fromhex("00" * 16))
    k3 = derive_hwid_key("HWID-2", bytes.fromhex("00" * 16))
    assert len(k1) == 32
    assert k1 == k2
    assert k1 != k3


def test_large_payload_roundtrip():
    data = bytes(range(256)) * 64
    pack = lock_payload(data, "HWID-X")
    assert unlock_payload(pack, "HWID-X") == data
