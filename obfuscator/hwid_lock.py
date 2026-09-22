"""HWID-locked payload encryption (Phase-4, stdlib only).

AES-CTR-like stream via SHA-256(key + nonce + counter) XOR. An embedded
SHA-256 check tag (prepended before encryption) authenticates both the HWID
and the ciphertext: wrong HWID or tampered data raises ValueError.

HWID fingerprint formats (AUDIT GAP #33):

- dynamic (default): the runtime collects ``format(uuid.getnode(), "x")``
  on each run; ``--hwid`` may carry any opaque string and the PBKDF2 key
  derivation below consumes it verbatim.
- static: the canonical fingerprint ``HWID:<64 hex chars>`` (hex case
 -insensitive, canonicalized to lowercase), e.g.::

      HWID:9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c9f2c

  A static fingerprint binds the artifact to a known value instead of
  dynamic ``uuid.getnode()`` collection: build with ``--hwid
  'HWID:<64 hex>' --hwid-lock`` and the emitted loader embeds the value as
  ``_NX_HWID_STATIC`` so unlock uses it verbatim. The PBKDF2-HMAC-SHA256
  derivation downstream is unchanged; only the fingerprint string feeding
  it is canonicalized. Non-static strings pass through untouched, so the
  dynamic path is byte-identical to before.
"""

import hashlib
import re
import secrets

_ITERATIONS_DEFAULT = 100_000
_SALT_LEN = 16
_NONCE_LEN = 16
_TAG_LEN = 32  # sha256 digest

#: Canonical static fingerprint: ``HWID:<64 hex chars>`` (GAP #33).
_STATIC_HWID_RE = re.compile(r"^HWID:([0-9a-fA-F]{64})$")


def is_static_hwid(hwid):
    # type: (object) -> bool
    """Return True when ``hwid`` is a static ``HWID:<64 hex>`` fingerprint.

    Pure predicate; never raises, never coerces non-strings.
    """
    try:
        return bool(_STATIC_HWID_RE.match(str(hwid)))
    except Exception:
        return False


def normalize_static_hwid(hwid):
    # type: (object) -> str
    """Canonicalize a static fingerprint to ``HWID:<lowercase hex>``.

    Non-static inputs pass through as ``str(hwid)`` unchanged, so the
    dynamic ``uuid.getnode()`` / opaque ``--hwid`` path is byte-identical
    to before. Raises ValueError on ``HWID:``-prefixed but malformed
    values (wrong length / non-hex) to fail closed at build time.
    """
    s = str(hwid)
    if s.startswith("HWID:"):
        m = _STATIC_HWID_RE.match(s)
        if not m:
            raise ValueError(
                "bad static HWID fingerprint: expected 'HWID:<64 hex chars>'"
            )
        return "HWID:" + m.group(1).lower()
    return s


def _canonical_hwid(hwid):
    # type: (object) -> str
    """Internal: canonical form feeding PBKDF2 (static lowercased)."""
    try:
        return normalize_static_hwid(hwid)
    except ValueError:
        raise
    except Exception:
        return str(hwid)


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
        "sha256", _canonical_hwid(hwid).encode("utf-8"), bytes(salt), iterations, dklen=32
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
