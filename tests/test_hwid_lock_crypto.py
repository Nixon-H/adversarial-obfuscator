"""Regression tests for the hwid-lock keyed-authentication fix."""
import hashlib

import pytest
from obfuscator.hwid_lock import lock_payload, unlock_payload


def _keystream(key, nonce, length):
    out = bytearray()
    c = 0
    while len(out) < length:
        out.extend(hashlib.sha256(key + nonce + c.to_bytes(8, "big")).digest())
        c += 1
    return bytes(out[:length])


def test_known_plaintext_forgery_fails():
    """The pre-fix attack: one known plaintext exposes the keystream, and the
    unkeyed sha256 tag let the attacker forge a valid pack for ANY payload.
    With keyed HMAC the forgery must fail."""
    hwid = "HWID:" + "ab" * 32
    known = b" legitimate payload content the attacker captured "
    pack = lock_payload(known, hwid)
    enc = bytes.fromhex(pack["data"])

    # Attacker recovers the keystream from the known plaintext pair.
    stream = bytes(a ^ b for a, b in zip(enc, known))
    # Attacker encrypts a malicious payload of the same length.
    evil = b"X" * len(known)
    evil_enc = bytes(a ^ b for a, b in zip(evil, stream))
    forged = {"salt": pack["salt"], "nonce": pack["nonce"], "data": evil_enc.hex()}
    # Attacker cannot supply any valid mac — try omitting it entirely:
    with pytest.raises(ValueError):
        unlock_payload(forged, hwid)
    # ... or guessing/replaying the original mac:
    forged["mac"] = pack["mac"]
    with pytest.raises(ValueError):
        unlock_payload(forged, hwid)


def test_roundtrip_and_wrong_hwid():
    hwid = "HWID:" + "cd" * 32
    pack = lock_payload(b"hello", hwid)
    assert unlock_payload(pack, hwid) == b"hello"
    with pytest.raises(ValueError):
        unlock_payload(pack, "HWID:" + "ef" * 32)


def test_bitflip_tamper_fails():
    hwid = "some-dynamic-hwid"
    pack = lock_payload(b"sensitive", hwid)
    raw = bytearray.fromhex(pack["data"])
    raw[0] ^= 1
    pack["data"] = raw.hex()
    with pytest.raises(ValueError):
        unlock_payload(pack, hwid)


def test_mac_is_keyed_and_binds_salt_nonce():
    """Rearranging salt/nonce across packs must invalidate the mac."""
    hwid = "h"
    p1 = lock_payload(b"aaa", hwid)
    p2 = lock_payload(b"aaa", hwid)
    swapped = dict(p1)
    swapped["salt"] = p2["salt"]
    with pytest.raises(ValueError):
        unlock_payload(swapped, hwid)


def test_empty_payload_roundtrip():
    hwid = "h"
    pack = lock_payload(b"", hwid)
    assert unlock_payload(pack, hwid) == b""
