"""AES-256 implementation (pure Python).

Provides AES-256 encryption/decryption primitives including key expansion,
CTR mode keystream generation, and per-block key derivation for the
binary encryption pipeline.

Public API:
    - aes256_encrypt_block(plaintext, key) -> bytes
    - aes256_ctr_keystream(key, nonce, length) -> bytes
    - aes256_ctr_encrypt(plaintext, key, nonce) -> bytes
    - aes256_ctr_decrypt(plaintext, key, nonce) -> bytes
    - derive_block_key(seed, block_index, block_size) -> bytes
    - expand_key_to_keystream(key, block_size) -> bytes
    - generate_encryption_seed() -> bytes (32-byte random seed)

Dependencies:
    - None (standard library only: os, hashlib, struct)
"""

import os
import hashlib
import struct


def secure_zero(data):
    if isinstance(data, bytearray):
        for i in range(len(data)):
            data[i] = 0
    elif isinstance(data, list):
        for i in range(len(data)):
            data[i] = 0
    # bytes are immutable - can't zero

_AES_SBOX = [
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16,
]

_AES_INV_SBOX = [0] * 256
for _i, _v in enumerate(_AES_SBOX):
    _AES_INV_SBOX[_v] = _i

_AES_RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d]


def _xtime(a):
    return ((a << 1) ^ 0x11b) & 0xff if a & 0x80 else (a << 1) & 0xff


def _gf_mul(a, b):
    result = 0
    for _ in range(8):
        if b & 1:
            result ^= a
        a = _xtime(a)
        b >>= 1
    return result


def _sub_word(word):
    return (
        (_AES_SBOX[(word >> 24) & 0xff] << 24) |
        (_AES_SBOX[(word >> 16) & 0xff] << 16) |
        (_AES_SBOX[(word >> 8) & 0xff] << 8) |
        _AES_SBOX[word & 0xff]
    )


def _rot_word(word):
    return ((word << 8) | (word >> 24)) & 0xffffffff


def _aes256_key_expansion(key):
    if len(key) != 32:
        raise ValueError("AES-256 requires a 32-byte key")
    w = [0] * 60
    for i in range(8):
        w[i] = struct.unpack('>I', key[4*i:4*i+4])[0]
    for i in range(8, 60):
        temp = w[i-1]
        if i % 8 == 0:
            temp = _sub_word(_rot_word(temp)) ^ (_AES_RCON[i // 8 - 1] << 24)
        elif i % 8 == 4:
            temp = _sub_word(temp)
        w[i] = w[i-8] ^ temp
    return w


def _bytes_to_state(b):
    return list(struct.unpack('>4I', b))


def _state_to_bytes(s):
    return struct.pack('>4I', *s)


def _add_round_key(s, rk):
    return [s[i] ^ rk[i] for i in range(4)]


def _sub_bytes(s):
    return [
        ((_AES_SBOX[(s[0] >> 24) & 0xff] << 24) |
         (_AES_SBOX[(s[0] >> 16) & 0xff] << 16) |
         (_AES_SBOX[(s[0] >> 8) & 0xff] << 8) |
         _AES_SBOX[s[0] & 0xff]),
        ((_AES_SBOX[(s[1] >> 24) & 0xff] << 24) |
         (_AES_SBOX[(s[1] >> 16) & 0xff] << 16) |
         (_AES_SBOX[(s[1] >> 8) & 0xff] << 8) |
         _AES_SBOX[s[1] & 0xff]),
        ((_AES_SBOX[(s[2] >> 24) & 0xff] << 24) |
         (_AES_SBOX[(s[2] >> 16) & 0xff] << 16) |
         (_AES_SBOX[(s[2] >> 8) & 0xff] << 8) |
         _AES_SBOX[s[2] & 0xff]),
        ((_AES_SBOX[(s[3] >> 24) & 0xff] << 24) |
         (_AES_SBOX[(s[3] >> 16) & 0xff] << 16) |
         (_AES_SBOX[(s[3] >> 8) & 0xff] << 8) |
         _AES_SBOX[s[3] & 0xff]),
    ]


def _inv_sub_bytes(s):
    return [
        ((_AES_INV_SBOX[(s[0] >> 24) & 0xff] << 24) |
         (_AES_INV_SBOX[(s[0] >> 16) & 0xff] << 16) |
         (_AES_INV_SBOX[(s[0] >> 8) & 0xff] << 8) |
         _AES_INV_SBOX[s[0] & 0xff]),
        ((_AES_INV_SBOX[(s[1] >> 24) & 0xff] << 24) |
         (_AES_INV_SBOX[(s[1] >> 16) & 0xff] << 16) |
         (_AES_INV_SBOX[(s[1] >> 8) & 0xff] << 8) |
         _AES_INV_SBOX[s[1] & 0xff]),
        ((_AES_INV_SBOX[(s[2] >> 24) & 0xff] << 24) |
         (_AES_INV_SBOX[(s[2] >> 16) & 0xff] << 16) |
         (_AES_INV_SBOX[(s[2] >> 8) & 0xff] << 8) |
         _AES_INV_SBOX[s[2] & 0xff]),
        ((_AES_INV_SBOX[(s[3] >> 24) & 0xff] << 24) |
         (_AES_INV_SBOX[(s[3] >> 16) & 0xff] << 16) |
         (_AES_INV_SBOX[(s[3] >> 8) & 0xff] << 8) |
         _AES_INV_SBOX[s[3] & 0xff]),
    ]


def _shift_rows(s):
    # AES ShiftRows: rotate rows left by row index (0, 1, 2, 3)
    # s[i] is column i, bytes are big-endian: [row0, row1, row2, row3]
    b0 = [(s[0] >> 24) & 0xFF, (s[0] >> 16) & 0xFF, (s[0] >> 8) & 0xFF, s[0] & 0xFF]
    b1 = [(s[1] >> 24) & 0xFF, (s[1] >> 16) & 0xFF, (s[1] >> 8) & 0xFF, s[1] & 0xFF]
    b2 = [(s[2] >> 24) & 0xFF, (s[2] >> 16) & 0xFF, (s[2] >> 8) & 0xFF, s[2] & 0xFF]
    b3 = [(s[3] >> 24) & 0xFF, (s[3] >> 16) & 0xFF, (s[3] >> 8) & 0xFF, s[3] & 0xFF]
    # New columns after row shifts: col j = row0:s[j][0], row1:s[(j+1)%4][1], row2:s[(j+2)%4][2], row3:s[(j+3)%4][3]
    return [
        (b0[0] << 24) | (b1[1] << 16) | (b2[2] << 8) | b3[3],
        (b1[0] << 24) | (b2[1] << 16) | (b3[2] << 8) | b0[3],
        (b2[0] << 24) | (b3[1] << 16) | (b0[2] << 8) | b1[3],
        (b3[0] << 24) | (b0[1] << 16) | (b1[2] << 8) | b2[3],
    ]


def _inv_shift_rows(s):
    # Inverse ShiftRows: rotate rows right by row index
    b0 = [(s[0] >> 24) & 0xFF, (s[0] >> 16) & 0xFF, (s[0] >> 8) & 0xFF, s[0] & 0xFF]
    b1 = [(s[1] >> 24) & 0xFF, (s[1] >> 16) & 0xFF, (s[1] >> 8) & 0xFF, s[1] & 0xFF]
    b2 = [(s[2] >> 24) & 0xFF, (s[2] >> 16) & 0xFF, (s[2] >> 8) & 0xFF, s[2] & 0xFF]
    b3 = [(s[3] >> 24) & 0xFF, (s[3] >> 16) & 0xFF, (s[3] >> 8) & 0xFF, s[3] & 0xFF]
    # After inv shift: col j = row0:s[j][0], row1:s[(j-1)%4][1], row2:s[(j-2)%4][2], row3:s[(j-3)%4][3]
    return [
        (b0[0] << 24) | (b3[1] << 16) | (b2[2] << 8) | b1[3],
        (b1[0] << 24) | (b0[1] << 16) | (b3[2] << 8) | b2[3],
        (b2[0] << 24) | (b1[1] << 16) | (b0[2] << 8) | b3[3],
        (b3[0] << 24) | (b2[1] << 16) | (b1[2] << 8) | b0[3],
    ]


def _mix_column(col):
    a0 = (col >> 24) & 0xff
    a1 = (col >> 16) & 0xff
    a2 = (col >> 8) & 0xff
    a3 = col & 0xff
    return (
        (_gf_mul(2, a0) ^ _gf_mul(3, a1) ^ a2 ^ a3) << 24 |
        (a0 ^ _gf_mul(2, a1) ^ _gf_mul(3, a2) ^ a3) << 16 |
        (a0 ^ a1 ^ _gf_mul(2, a2) ^ _gf_mul(3, a3)) << 8 |
        (_gf_mul(3, a0) ^ a1 ^ a2 ^ _gf_mul(2, a3))
    )


def _inv_mix_column(col):
    a0 = (col >> 24) & 0xff
    a1 = (col >> 16) & 0xff
    a2 = (col >> 8) & 0xff
    a3 = col & 0xff
    return (
        (_gf_mul(14, a0) ^ _gf_mul(11, a1) ^ _gf_mul(13, a2) ^ _gf_mul(9, a3)) << 24 |
        (_gf_mul(9, a0) ^ _gf_mul(14, a1) ^ _gf_mul(11, a2) ^ _gf_mul(13, a3)) << 16 |
        (_gf_mul(13, a0) ^ _gf_mul(9, a1) ^ _gf_mul(14, a2) ^ _gf_mul(11, a3)) << 8 |
        (_gf_mul(11, a0) ^ _gf_mul(13, a1) ^ _gf_mul(9, a2) ^ _gf_mul(14, a3))
    )


def _mix_columns(s):
    return [_mix_column(col) for col in s]


def _inv_mix_columns(s):
    return [_inv_mix_column(col) for col in s]


def aes256_encrypt_block(plaintext: bytes, key: bytes) -> bytes:
    """AES-256 single block encrypt.

    Args:
        plaintext: 16-byte input block.
        key: 32-byte key (immutable — caller must zero on their side).
    """
    if len(plaintext) != 16:
        raise ValueError("AES block must be 16 bytes")
    w = _aes256_key_expansion(key)
    state = _bytes_to_state(plaintext)
    state = _add_round_key(state, w[0:4])
    for rnd in range(1, 14):
        state = _sub_bytes(state)
        state = _shift_rows(state)
        state = _mix_columns(state)
        state = _add_round_key(state, w[4*rnd:4*rnd+4])
    state = _sub_bytes(state)
    state = _shift_rows(state)
    state = _add_round_key(state, w[56:60])
    result = _state_to_bytes(state)
    secure_zero(state)
    secure_zero(w)
    return result


def aes256_ctr_keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    """Generate AES-256-CTR keystream.

    Args:
        key: 32-byte key (immutable — caller must zero on their side).
        nonce: 8-byte nonce.
        length: number of keystream bytes to produce.
    """
    if len(nonce) != 8:
        raise ValueError("Nonce must be 8 bytes")
    keystream = b''
    counter_block = nonce + b'\x00' * 8
    while len(keystream) < length:
        encrypted = aes256_encrypt_block(counter_block, key)
        keystream += encrypted
        counter_bytes = bytearray(counter_block)
        for i in range(15, 7, -1):
            counter_bytes[i] = (counter_bytes[i] + 1) & 0xff
            if counter_bytes[i] != 0:
                break
        counter_block = bytes(counter_bytes)
        secure_zero(counter_bytes)
    return keystream[:length]


def aes256_ctr_encrypt(plaintext: bytes, key: bytes, nonce: bytes) -> bytes:
    """AES-256-CTR encrypt.

    Args:
        plaintext: data to encrypt.
        key: 32-byte key (immutable — caller must zero on their side).
        nonce: 8-byte nonce.
    """
    keystream = aes256_ctr_keystream(key, nonce, len(plaintext))
    return bytes(p ^ k for p, k in zip(plaintext, keystream))


aes256_ctr_decrypt = aes256_ctr_encrypt


def derive_block_key(seed: bytes, block_index: int, block_size: int) -> bytes:
    """Derive a per-block key from a seed.

    Returns immutable bytes — caller should zero the returned value
    when done with it.

    Args:
        seed: 32-byte seed (immutable — caller must zero on their side).
        block_index: block number.
        block_size: size of each block.
    """
    h = hashlib.sha256(seed)
    h.update(struct.pack('<I', block_index))
    h.update(struct.pack('<I', block_size))
    return h.digest()


def expand_key_to_keystream(key: bytes, block_size: int) -> bytes:
    """Expand a key into a full keystream.

    Args:
        key: 32-byte key (immutable — caller must zero on their side).
        block_size: desired keystream length.
    """
    nonce = hashlib.sha256(key).digest()[:8]
    return aes256_ctr_keystream(key, nonce, block_size)


def generate_encryption_seed() -> bytes:
    return os.urandom(32)
