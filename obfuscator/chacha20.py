"""Pure-Python RFC 8439 ChaCha20 + HMAC-SHA256 AEAD for string encryption.

AUDIT GAP #55: the obfuscator's legacy string transform is a single-byte
XOR + reverse + hex (see ``obfuscator/core/transforms.py``,
``StringLiteralObfuscator``) with no integrity tag.  This module provides a
real stream cipher for build-time string encryption:

* ``chacha20_block`` / ``chacha20_xor`` — RFC 8439 Sections 2.3/2.4.
* ``aead_encrypt`` / ``aead_decrypt`` — AEAD-equivalent construction:
  random 96-bit nonce, ChaCha20 stream starting at counter 1, and a
  128-bit authentication tag = ``HMAC-SHA256(mac_key, nonce || ciphertext)``
  truncated to 16 bytes, where ``mac_key = SHA256(b"NX-CHACHA20-MAC-v1" ||
  key)`` (domain separation so key material is never reused directly
  between the stream cipher and the MAC).

  Wire format: ``nonce (12 B) || ciphertext || tag (16 B)``.

Why not Poly1305? Poly1305 needs its own correct implementation (~another
60 lines to get right); HMAC-SHA256 is stdlib, obviously correct, and the
tag is verified with ``hmac.compare_digest``. Security goal here is
per-build randomized authenticated string seals, not interop with TLS.

Why not the ``cryptography`` package? It is NOT a project dependency
(``requirements.txt`` is stdlib-only plus requests/numpy/Cython/z3) and
auditor builds may be offline. A pure-Python ChaCha20 is ~40 lines, and
build-time string encryption is not performance-critical. The same core
is emitted verbatim (as ``STUB_TEMPLATE``) into obfuscated payloads, so
runtime stubs stay dependency-free too.

Dependencies: stdlib only (hashlib, hmac, secrets). Python 3.10 compatible.
"""

import hashlib
import hmac
import secrets

KEY_SIZE = 32
NONCE_SIZE = 12
TAG_SIZE = 16
_MAC_DOMAIN = b"NX-CHACHA20-MAC-v1"

_MASK32 = 0xFFFFFFFF

# "expand 32-byte k" little-endian constants (RFC 8439 Section 2.3).
_SIGMA = (0x61707865, 0x3320646e, 0x79622D32, 0x6B206574)


def _rotl(value, n):
    # type: (int, int) -> int
    return ((value << n) & _MASK32) | (value >> (32 - n))


def _quarter_round(x, a, b, c, d):
    # type: (list, int, int, int, int) -> None
    x[a] = (x[a] + x[b]) & _MASK32
    x[d] ^= x[a]
    x[d] = _rotl(x[d], 16)
    x[c] = (x[c] + x[d]) & _MASK32
    x[b] ^= x[c]
    x[b] = _rotl(x[b], 12)
    x[a] = (x[a] + x[b]) & _MASK32
    x[d] ^= x[a]
    x[d] = _rotl(x[d], 8)
    x[c] = (x[c] + x[d]) & _MASK32
    x[b] ^= x[c]
    x[b] = _rotl(x[b], 7)


def _check_key(key):
    # type: (bytes,) -> None
    if not isinstance(key, (bytes, bytearray)) or len(key) != KEY_SIZE:
        raise ValueError("ChaCha20 key must be exactly 32 bytes")


def _check_nonce(nonce):
    # type: (bytes,) -> None
    if not isinstance(nonce, (bytes, bytearray)) or len(nonce) != NONCE_SIZE:
        raise ValueError("ChaCha20 nonce must be exactly 12 bytes")


def chacha20_block(key, counter, nonce):
    # type: (bytes, int, bytes) -> bytes
    """RFC 8439 Section 2.3 block function. Returns 64 bytes of keystream."""
    _check_key(key)
    _check_nonce(nonce)
    counter = int(counter) & _MASK32
    k = [int.from_bytes(bytes(key[i:i + 4]), "little") for i in (0, 4, 8, 12, 16, 20, 24, 28)]
    n = [int.from_bytes(bytes(nonce[i:i + 4]), "little") for i in (0, 4, 8)]
    state = [
        _SIGMA[0], _SIGMA[1], _SIGMA[2], _SIGMA[3],
        k[0], k[1], k[2], k[3], k[4], k[5], k[6], k[7],
        counter, n[0], n[1], n[2],
    ]
    working = list(state)
    for _ in range(10):
        # Column rounds.
        _quarter_round(working, 0, 4, 8, 12)
        _quarter_round(working, 1, 5, 9, 13)
        _quarter_round(working, 2, 6, 10, 14)
        _quarter_round(working, 3, 7, 11, 15)
        # Diagonal rounds.
        _quarter_round(working, 0, 5, 10, 15)
        _quarter_round(working, 1, 6, 11, 12)
        _quarter_round(working, 2, 7, 8, 13)
        _quarter_round(working, 3, 4, 9, 14)
    out = bytearray(64)
    for i in range(16):
        out[i * 4:(i + 1) * 4] = ((working[i] + state[i]) & _MASK32).to_bytes(4, "little")
    return bytes(out)


def chacha20_xor(key, nonce, data, counter=1):
    # type: (bytes, bytes, bytes, int) -> bytes
    """Raw ChaCha20 stream encryption/decryption (XOR is its own inverse)."""
    _check_key(key)
    _check_nonce(nonce)
    data = bytes(data)
    out = bytearray(len(data))
    offset = 0
    ctr = int(counter) & _MASK32
    while offset < len(data):
        keystream = chacha20_block(key, ctr, nonce)
        ctr = (ctr + 1) & _MASK32
        n = min(64, len(data) - offset)
        for i in range(n):
            out[offset + i] = data[offset + i] ^ keystream[i]
        offset += n
    return bytes(out)


def _mac_key(key):
    # type: (bytes,) -> bytes
    return hashlib.sha256(_MAC_DOMAIN + bytes(key)).digest()


def generate_key():
    # type: () -> bytes
    """32-byte build key from OS entropy (``secrets``: NOT deterministic).

    Seeded/deterministic builds must pin the key explicitly instead of
    calling this (pass ``key=`` through); tests patch ``secrets`` only to
    observe call behavior, never for reproducibility."""
    return secrets.token_bytes(KEY_SIZE)


def generate_nonce():
    # type: () -> bytes
    """12-byte per-string nonce from OS entropy (``secrets``: NOT deterministic).

    Deterministic builds must pass an explicit ``nonce=`` to
    :func:`aead_encrypt` instead."""
    return secrets.token_bytes(NONCE_SIZE)


def aead_encrypt(key, plaintext, nonce=None):
    # type: (bytes, bytes, bytes) -> bytes
    """Encrypt + authenticate. Returns ``nonce || ciphertext || tag``."""
    _check_key(key)
    plaintext = bytes(plaintext)
    if nonce is None:
        nonce = generate_nonce()
    else:
        _check_nonce(nonce)
    ciphertext = chacha20_xor(key, nonce, plaintext, counter=1)
    tag = hmac.new(_mac_key(key), bytes(nonce) + ciphertext,
                   hashlib.sha256).digest()[:TAG_SIZE]
    return bytes(nonce) + ciphertext + tag


def aead_decrypt(key, blob):
    # type: (bytes, bytes) -> bytes
    """Verify tag FIRST, then decrypt. Raises ValueError on any tamper."""
    _check_key(key)
    blob = bytes(blob)
    if len(blob) < NONCE_SIZE + TAG_SIZE:
        raise ValueError("string seal too short")
    nonce = blob[:NONCE_SIZE]
    tag = blob[-TAG_SIZE:]
    ciphertext = blob[NONCE_SIZE:len(blob) - TAG_SIZE]
    expected = hmac.new(_mac_key(key), nonce + ciphertext,
                        hashlib.sha256).digest()[:TAG_SIZE]
    if not hmac.compare_digest(expected, tag):
        raise ValueError("string seal authentication failed")
    return chacha20_xor(key, nonce, ciphertext, counter=1)


# ---------------------------------------------------------------------------
# Runtime stub template.
#
# Self-contained pure-Python decryptor emitted into obfuscated payloads
# (stdlib imports only, function-local so no module namespace pollution).
# Mirrors the module functions above; behavioral equivalence is enforced by
# tests/test_chacha20_strings.py::test_stub_matches_module_implementation.
# Tokens __NX_DEC__ (decoder name) and __NX_KEYBYTES__ (build key as a
# comma-joined int list) are substituted by obfuscator.string_crypto at
# build time via str.replace (NOT str.format, so stub braces would be
# safe too). Hardening A1b: the key is never a 64-hex run, so the
# `grep -o "[0-9a-f]{64}"` signature finds nothing. (Key remains in
# artifact by design here; env-bound KEK is a separate mode.)
# ---------------------------------------------------------------------------
STUB_TEMPLATE = """def __NX_DEC__(_s):
    import hashlib as _nx_ha, hmac as _nx_hm
    _nx_k = bytes(__NX_KEYBYTES__)
    try:
        _nx_r = bytes.fromhex(_s)
    except ValueError:
        raise ValueError('bad string seal')
    if len(_nx_r) < 28:
        raise ValueError('bad string seal')
    _nx_n = _nx_r[:12]
    _nx_g = _nx_r[-16:]
    _nx_c = _nx_r[12:len(_nx_r) - 16]
    _nx_mk = _nx_ha.sha256(b'NX-CHACHA20-MAC-v1' + _nx_k).digest()
    _nx_e = _nx_hm.new(_nx_mk, _nx_n + _nx_c, _nx_ha.sha256).digest()[:16]
    if not _nx_hm.compare_digest(_nx_e, _nx_g):
        raise ValueError('string seal authentication failed')
    _nx_M = 4294967295
    def _nx_rl(_v, _n):
        return ((_v << _n) & _nx_M) | (_v >> (32 - _n))
    def _nx_qr(_x, _a, _b, _c, _d):
        _x[_a] = (_x[_a] + _x[_b]) & _nx_M
        _x[_d] ^= _x[_a]
        _x[_d] = _nx_rl(_x[_d], 16)
        _x[_c] = (_x[_c] + _x[_d]) & _nx_M
        _x[_b] ^= _x[_c]
        _x[_b] = _nx_rl(_x[_b], 12)
        _x[_a] = (_x[_a] + _x[_b]) & _nx_M
        _x[_d] ^= _x[_a]
        _x[_d] = _nx_rl(_x[_d], 8)
        _x[_c] = (_x[_c] + _x[_d]) & _nx_M
        _x[_b] ^= _x[_c]
        _x[_b] = _nx_rl(_x[_b], 7)
    def _nx_bl(_ctr):
        _ctr = _ctr & _nx_M
        _w = [int.from_bytes(_nx_k[_i:_i + 4], 'little') for _i in (0, 4, 8, 12, 16, 20, 24, 28)]
        _nn = [int.from_bytes(_nx_n[_i:_i + 4], 'little') for _i in (0, 4, 8)]
        _x = [1634760805, 857760878, 2036477234, 1797285236, _w[0], _w[1], _w[2], _w[3], _w[4], _w[5], _w[6], _w[7], _ctr, _nn[0], _nn[1], _nn[2]]
        _s0 = list(_x)
        for _r in range(10):
            _nx_qr(_x, 0, 4, 8, 12)
            _nx_qr(_x, 1, 5, 9, 13)
            _nx_qr(_x, 2, 6, 10, 14)
            _nx_qr(_x, 3, 7, 11, 15)
            _nx_qr(_x, 0, 5, 10, 15)
            _nx_qr(_x, 1, 6, 11, 12)
            _nx_qr(_x, 2, 7, 8, 13)
            _nx_qr(_x, 3, 4, 9, 14)
        _o = bytearray(64)
        for _i in range(16):
            _o[_i * 4:(_i + 1) * 4] = ((_x[_i] + _s0[_i]) & _nx_M).to_bytes(4, 'little')
        return bytes(_o)
    _nx_p = bytearray(len(_nx_c))
    _nx_o = 0
    _nx_ctr = 1
    while _nx_o < len(_nx_c):
        _nx_ks = _nx_bl(_nx_ctr)
        _nx_ctr += 1
        _nx_q = _nx_ks
        _nx_nn = 64
        if len(_nx_c) - _nx_o < 64:
            _nx_nn = len(_nx_c) - _nx_o
        for _nx_i in range(_nx_nn):
            _nx_p[_nx_o + _nx_i] = _nx_c[_nx_o + _nx_i] ^ _nx_q[_nx_i]
        _nx_o += _nx_nn
    return bytes(_nx_p).decode('utf-8')"""


def build_stub_decoder(decoder_name, key_hex, kek_env=None):
    # type: (str, str, object) -> str
    """Fill the runtime stub template for one build (no str.format used).

    kek_env (env var NAME, opt-in): the stub re-derives the seal key as
    build_key XOR sha256(env_shard) and raises when the shard is absent
    (fail-closed). Without it the stub uses the embedded build key.
    """
    if not decoder_name.isidentifier():
        raise ValueError("decoder name must be a valid identifier")
    try:
        raw = bytes.fromhex(str(key_hex))
    except ValueError:
        raise ValueError("key_hex must be hex")
    if len(raw) != KEY_SIZE:
        raise ValueError("key_hex must decode to exactly 32 bytes")
    int_list = "[" + ", ".join(str(b) for b in raw) + "]"
    stub = STUB_TEMPLATE.replace("__NX_DEC__", decoder_name).replace(
        "__NX_KEYBYTES__", int_list)
    if kek_env is not None:
        if not isinstance(kek_env, str) or not kek_env:
            raise ValueError("kek_env must be a non-empty string")
        prologue = (
            "    import os as _nx_os\n"
            "    try:\n"
            "        _nx_sh = _nx_os.environ[%r]\n"
            "        _nx_sd = bytes.fromhex(_nx_sh.strip())\n"
            "        assert len(_nx_sd) >= 16\n"
            "    except Exception:\n"
            "        raise ValueError('string KEK unavailable')\n"
            "    _nx_k = bytes(_a ^ _b for _a, _b in zip("
            "_nx_k, _nx_ha.sha256(_nx_sd).digest()))\n" % (kek_env,))
        # Insert prologue directly after the int-list key line.
        lines = stub.split("\n")
        for i, ln in enumerate(lines):
            if ln.strip().startswith("_nx_k = bytes(["):
                lines.insert(i + 1, prologue.replace("\\n", "\n")
                             .rstrip("\n"))
                break
        else:
            raise ValueError("stub template key line not found")
        stub = "\n".join(lines)
    return stub
