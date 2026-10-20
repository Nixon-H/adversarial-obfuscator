"""NIX encrypted payload container format.

Packs encrypted payloads into a self-describing container with magic,
version, original/encrypted sizes, SHA-256 integrity hash, and the
encrypted data itself.

Public API:
    - pack_encrypted_payload(payload_path, key) -> bytes
    - pack_bytes(plaintext, key) -> bytes
    - unpack_encrypted_payload(container, key) -> bytes
    - unpack_bytes(container, key) -> bytes
    - container_info(container) -> dict

Dependencies:
    - encrypt.aes (aes256_ctr_encrypt, aes256_ctr_decrypt)
"""

import hashlib
import struct

from . import aes

NIX_MAGIC = 0x4E4958
CONTAINER_VERSION = 1


def pack_encrypted_payload(payload_path: str, key: bytes) -> bytes:
    """Encrypt a full payload file into the NIX container format."""
    with open(payload_path, 'rb') as f:
        plaintext = f.read()

    return _pack(plaintext, key)


def pack_bytes(plaintext: bytes, key: bytes) -> bytes:
    return _pack(plaintext, key)


def _pack(plaintext: bytes, key: bytes) -> bytes:
    if len(key) != 32:
        raise ValueError("Container key must be 32 bytes (AES-256)")

    plain_sha256 = hashlib.sha256(plaintext).digest()
    nonce = plain_sha256[:8]

    encrypted = aes.aes256_ctr_encrypt(plaintext, key, nonce)

    container = b''
    container += struct.pack('<I', NIX_MAGIC)
    container += struct.pack('<I', CONTAINER_VERSION)
    container += struct.pack('<I', len(plaintext))
    container += struct.pack('<I', len(encrypted))
    container += plain_sha256
    container += encrypted

    return container


def unpack_encrypted_payload(container: bytes, key: bytes) -> bytes:
    """Decrypt a NIX container back into the original payload."""
    if len(key) != 32:
        raise ValueError("Container key must be 32 bytes (AES-256)")

    return _unpack(container, key)


def unpack_bytes(container: bytes, key: bytes) -> bytes:
    return _unpack(container, key)


def _unpack(container: bytes, key: bytes) -> bytes:
    header_fmt = '<IIII'
    header_size = struct.calcsize(header_fmt)
    if len(container) < header_size + 32:
        raise ValueError("Container too short")

    magic, version, orig_size, enc_size = struct.unpack_from(header_fmt, container, 0)

    if magic != NIX_MAGIC:
        raise ValueError(f"Invalid magic: expected 0x{NIX_MAGIC:08X}, got 0x{magic:08X}")
    if version > CONTAINER_VERSION:
        raise ValueError(f"Unsupported container version: {version}")

    sha_offset = header_size
    stored_sha256 = container[sha_offset:sha_offset + 32]
    encrypted = container[sha_offset + 32:sha_offset + 32 + enc_size]

    if len(encrypted) != enc_size:
        raise ValueError("Container encrypted data size mismatch")

    nonce = stored_sha256[:8]
    plaintext = aes.aes256_ctr_decrypt(encrypted, key, nonce)

    if len(plaintext) < orig_size:
        raise ValueError("Decrypted data too short")
    plaintext = plaintext[:orig_size]

    actual_sha256 = hashlib.sha256(plaintext).digest()
    if actual_sha256 != stored_sha256:
        raise ValueError("Integrity check failed: SHA-256 mismatch")

    return plaintext


def container_info(container: bytes) -> dict:
    header_fmt = '<IIII'
    header_size = struct.calcsize(header_fmt)
    if len(container) < header_size + 32:
        return {'error': 'Container too short'}

    magic, version, orig_size, enc_size = struct.unpack_from(header_fmt, container, 0)

    return {
        'magic': hex(magic),
        'version': version,
        'original_size': orig_size,
        'encrypted_size': enc_size,
        'total_size': len(container),
    }
