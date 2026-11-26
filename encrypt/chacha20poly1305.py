"""Pure-Python RFC 8439 ChaCha20-Poly1305.

The ELF decryptor uses the same construction. Keys remain in the separate
0600 sidecar; artifacts carry only the public 96-bit nonce, ciphertext, and
128-bit authentication tag.
"""

import hmac
import struct

_KEY_SIZE = 32
_NONCE_SIZE = 12
_TAG_SIZE = 16
_MASK32 = 0xFFFFFFFF
_POLY_MODULUS = (1 << 130) - 5
_POLY_R_CLAMP = 0x0FFFFFFC0FFFFFFC0FFFFFFC0FFFFFFF


def _rotl32(value, count):
    return ((value << count) | (value >> (32 - count))) & _MASK32


def _quarter_round(state, a, b, c, d):
    state[a] = (state[a] + state[b]) & _MASK32
    state[d] = _rotl32(state[d] ^ state[a], 16)
    state[c] = (state[c] + state[d]) & _MASK32
    state[b] = _rotl32(state[b] ^ state[c], 12)
    state[a] = (state[a] + state[b]) & _MASK32
    state[d] = _rotl32(state[d] ^ state[a], 8)
    state[c] = (state[c] + state[d]) & _MASK32
    state[b] = _rotl32(state[b] ^ state[c], 7)


def _block(key, nonce, counter):
    initial = list(struct.unpack("<4I", b"expand 32-byte k"))
    initial += list(struct.unpack("<8I", key))
    initial += [counter & _MASK32]
    initial += list(struct.unpack("<3I", nonce))
    state = initial[:]
    for _ in range(10):
        _quarter_round(state, 0, 4, 8, 12)
        _quarter_round(state, 1, 5, 9, 13)
        _quarter_round(state, 2, 6, 10, 14)
        _quarter_round(state, 3, 7, 11, 15)
        _quarter_round(state, 0, 5, 10, 15)
        _quarter_round(state, 1, 6, 11, 12)
        _quarter_round(state, 2, 7, 8, 13)
        _quarter_round(state, 3, 4, 9, 14)
    return struct.pack("<16I", *((a + b) & _MASK32 for a, b in zip(state, initial)))


def _xor_ciphertext(key, nonce, data, counter=1):
    output = bytearray(len(data))
    for offset in range(0, len(data), 64):
        stream = _block(key, nonce, counter + offset // 64)
        chunk = data[offset:offset + 64]
        output[offset:offset + len(chunk)] = bytes(
            value ^ mask for value, mask in zip(chunk, stream)
        )
    return bytes(output)


def _poly1305(message, one_time_key):
    r = int.from_bytes(one_time_key[:16], "little") & _POLY_R_CLAMP
    s = int.from_bytes(one_time_key[16:], "little")
    accumulator = 0
    for offset in range(0, len(message), 16):
        block = message[offset:offset + 16]
        number = int.from_bytes(block + b"\x01", "little")
        accumulator = ((accumulator + number) * r) % _POLY_MODULUS
    return ((accumulator + s) % (1 << 128)).to_bytes(16, "little")


def _mac_data(aad, ciphertext):
    return (
        aad + b"\x00" * (-len(aad) % 16)
        + ciphertext + b"\x00" * (-len(ciphertext) % 16)
        + struct.pack("<QQ", len(aad), len(ciphertext))
    )


def _validate(key, nonce):
    if len(key) != _KEY_SIZE:
        raise ValueError("ChaCha20-Poly1305 key must be 32 bytes")
    if len(nonce) != _NONCE_SIZE:
        raise ValueError("ChaCha20-Poly1305 nonce must be 12 bytes")


def seal(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes = b"") -> tuple[bytes, bytes]:
    """Return ``(ciphertext, tag)`` using a caller-supplied random nonce."""
    _validate(key, nonce)
    if len(plaintext) > (0xFFFFFFFF - 1) * 64:
        raise ValueError("ChaCha20-Poly1305 plaintext exceeds the counter limit")
    poly_key = _block(key, nonce, 0)[:32]
    ciphertext = _xor_ciphertext(key, nonce, plaintext)
    tag = _poly1305(_mac_data(aad, ciphertext), poly_key)
    return ciphertext, tag


def open(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes,
         aad: bytes = b"") -> bytes:
    """Authenticate before decrypting; refuse every invalid tag."""
    _validate(key, nonce)
    if len(tag) != _TAG_SIZE:
        raise ValueError("ChaCha20-Poly1305 tag must be 16 bytes")
    poly_key = _block(key, nonce, 0)[:32]
    expected = _poly1305(_mac_data(aad, ciphertext), poly_key)
    if not hmac.compare_digest(expected, tag):
        raise ValueError("ChaCha20-Poly1305 authentication failed")
    return _xor_ciphertext(key, nonce, ciphertext)
