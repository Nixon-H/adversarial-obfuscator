"""HWID-locked payload encryption (Phase-4, stdlib only).

AES-CTR-like stream via SHA-256(key + nonce + counter) XOR. An embedded
SHA-256 check tag (prepended before encryption) authenticates both the HWID
and the ciphertext: wrong HWID or tampered data raises ValueError.
"""

import hashlib
import secrets

_ITERATIONS_DEFAULT = 100_000
_SALT_LEN = 16
_NONCE_LEN = 16
_TAG_LEN = 32  # sha256 digest


def derive_hwid_key(hwid: str, salt: bytes, iterations: int = 100_000) -> bytes:
    """PBKDF2-HMAC-SHA256, 32 bytes."""
    if not isinstance(salt, (bytes, bytearray)):
        raise TypeError("salt must be bytes")
    if iterations is None:
        iterations = _ITERATIONS_DEFAULT
    iterations = int(iterations)
    if iterations < 1:
        raise ValueError("iterations must be >= 1")
    return hashlib.pbkdf2_hmac(
        "sha256", str(hwid).encode("utf-8"), bytes(salt), iterations, dklen=32
    )


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hashlib.sha256(key + nonce + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(out[:length])


def lock_payload(payload: bytes, hwid: str) -> dict:
    """Encrypt payload for hwid. Returns {'salt': hex, 'nonce': hex, 'data': hex}."""
    data = bytes(payload)
    salt = secrets.token_bytes(_SALT_LEN)
    nonce = secrets.token_bytes(_NONCE_LEN)
    key = derive_hwid_key(hwid, salt)
    tagged = hashlib.sha256(data).digest() + data
    stream = _keystream(key, nonce, len(tagged))
    enc = bytes(a ^ b for a, b in zip(tagged, stream))
    return {"salt": salt.hex(), "nonce": nonce.hex(), "data": enc.hex()}


def unlock_payload(pack: dict, hwid: str) -> bytes:
    """Inverse of lock_payload; wrong hwid or tampered data raises ValueError."""
    try:
        salt = bytes.fromhex(pack["salt"])
        nonce = bytes.fromhex(pack["nonce"])
        enc = bytes.fromhex(pack["data"])
    except Exception as e:
        raise ValueError(f"bad pack: {e}")
    key = derive_hwid_key(hwid, salt)
    stream = _keystream(key, nonce, len(enc))
    tagged = bytes(a ^ b for a, b in zip(enc, stream))
    if len(tagged) < _TAG_LEN:
        raise ValueError("decryption failed (truncated)")
    tag, data = tagged[:_TAG_LEN], tagged[_TAG_LEN:]
    if hashlib.sha256(data).digest() != tag:
        raise ValueError("decryption failed: wrong hwid or tampered data")
    return data
