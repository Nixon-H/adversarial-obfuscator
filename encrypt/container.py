"""NIX v3 authenticated encrypted-payload container format.

v3 uses AES-256-CTR with HKDF-SHA256-separated encryption/authentication keys
and a random 128-bit nonce. HMAC-SHA256 authenticates the canonical header,
nonce, and ciphertext. Legacy v1/v2 containers are rejected: neither format
authenticates all bytes that affect parsing, so accepting them would require
trusting unauthenticated metadata.

Public API:
    - pack_encrypted_payload(payload_path, key) -> bytes
    - pack_bytes(plaintext, key) -> bytes
    - unpack_encrypted_payload(container, key) -> bytes
    - unpack_bytes(container, key) -> bytes
    - container_info(container) -> dict
"""

import hashlib
import hmac
import os
import struct

from . import aes

NIX_MAGIC = 0x4E4958
CONTAINER_VERSION = 3
LEGACY_VERSIONS = (1, 2)
_HEADER_FMT = "<IIII"
_HEADER_SIZE = struct.calcsize(_HEADER_FMT)
_NONCE_SIZE = 16
_TAG_SIZE = 32
_MIN_SIZE = _HEADER_SIZE + _NONCE_SIZE + _TAG_SIZE
_HKDF_ENCRYPTION_INFO = b"NIX-v3-encryption"
_HKDF_AUTH_INFO = b"NIX-v3-authentication"
_HKDF_IV_INFO = b"NIX-v3-iv"


def _hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    """RFC 5869 HKDF-SHA256 (extract and expand)."""
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    output = bytearray()
    previous = b""
    counter = 1
    while len(output) < length:
        previous = hmac.new(
            prk, previous + info + bytes([counter]), hashlib.sha256
        ).digest()
        output += previous
        counter += 1
    return bytes(output[:length])


def _derive_v3_keys(key: bytes, nonce: bytes) -> tuple[bytes, bytes, bytes]:
    return (
        _hkdf_sha256(key, nonce, _HKDF_ENCRYPTION_INFO, 32),
        _hkdf_sha256(key, nonce, _HKDF_AUTH_INFO, 32),
        _hkdf_sha256(key, nonce, _HKDF_IV_INFO, 8),
    )


def pack_encrypted_payload(payload_path: str, key: bytes) -> bytes:
    """Encrypt a full payload file into the NIX v3 container format."""
    with open(payload_path, "rb") as f:
        plaintext = f.read()
    return _pack(plaintext, key)


def pack_bytes(plaintext: bytes, key: bytes) -> bytes:
    return _pack(plaintext, key)


def _pack(plaintext: bytes, key: bytes) -> bytes:
    if len(key) != 32:
        raise ValueError("Container key must be 32 bytes (AES-256)")
    if len(plaintext) > 0xFFFFFFFF:
        raise ValueError("Container plaintext size exceeds the v3 32-bit limit")

    nonce = os.urandom(_NONCE_SIZE)
    enc_key, mac_key, ctr_nonce = _derive_v3_keys(key, nonce)
    encrypted = aes.aes256_ctr_encrypt(plaintext, enc_key, ctr_nonce)
    header = struct.pack(
        _HEADER_FMT, NIX_MAGIC, CONTAINER_VERSION, len(plaintext), len(encrypted)
    )
    tag = hmac.new(
        mac_key, header + nonce + encrypted, hashlib.sha256
    ).digest()
    return header + nonce + tag + encrypted


def unpack_encrypted_payload(container: bytes, key: bytes) -> bytes:
    """Authenticate and decrypt a NIX v3 container."""
    if len(key) != 32:
        raise ValueError("Container key must be 32 bytes (AES-256)")
    return _unpack(container, key)


def unpack_bytes(container: bytes, key: bytes) -> bytes:
    return _unpack(container, key)


def _unpack(container: bytes, key: bytes) -> bytes:
    if len(container) < _HEADER_SIZE:
        raise ValueError("Container too short")

    magic, version, orig_size, enc_size = struct.unpack_from(_HEADER_FMT, container)
    if magic != NIX_MAGIC:
        raise ValueError(f"Invalid magic: expected 0x{NIX_MAGIC:08X}, got 0x{magic:08X}")
    if version != CONTAINER_VERSION:
        if version in LEGACY_VERSIONS:
            raise ValueError(
                f"legacy NIX v{version} is not safely authenticated; "
                "re-encrypt with v3 before unpacking"
            )
        raise ValueError(f"Unsupported container version: {version}")
    if orig_size != enc_size:
        raise ValueError("Container size mismatch: original and encrypted sizes differ")
    expected_size = _MIN_SIZE + enc_size
    if len(container) != expected_size:
        raise ValueError(
            "Container length mismatch: trailing or truncated encrypted data"
        )

    nonce = container[_HEADER_SIZE:_HEADER_SIZE + _NONCE_SIZE]
    stored_tag = container[_HEADER_SIZE + _NONCE_SIZE:_MIN_SIZE]
    encrypted = container[_MIN_SIZE:]
    enc_key, mac_key, ctr_nonce = _derive_v3_keys(key, nonce)
    expected_tag = hmac.new(
        mac_key, container[:_HEADER_SIZE] + nonce + encrypted, hashlib.sha256
    ).digest()
    if not hmac.compare_digest(expected_tag, stored_tag):
        raise ValueError("Integrity check failed: HMAC mismatch")

    return aes.aes256_ctr_decrypt(encrypted, enc_key, ctr_nonce)


def container_info(container: bytes) -> dict:
    if len(container) < _HEADER_SIZE:
        return {"error": "Container too short"}

    magic, version, orig_size, enc_size = struct.unpack_from(_HEADER_FMT, container)
    return {
        "magic": hex(magic),
        "version": version,
        "original_size": orig_size,
        "encrypted_size": enc_size,
        "total_size": len(container),
    }
