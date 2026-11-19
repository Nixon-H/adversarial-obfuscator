"""Pure-stdlib Ed25519 verification, for the loader that cannot import anything.

The artefact runs in the customer's interpreter with no third-party packages, so
it cannot import `cryptography`. `obfuscator/licensing.py` says so explicitly:

    "Checking the token *inside the artefact*. The emitted loader runs in the
     customer's interpreter with no third-party packages, so it cannot import
     cryptography; the loader needs a small pure-Python Ed25519 verify"

This module is that verify, and it exists to close the measured double-stamp
attack: recomputing the Merkle root and the HMAC is possible because both are
derivable from the artefact, so neither binds the file to the publisher. A
signature checked against an embedded PUBLIC key does — the private key never
ships.

Scope and honesty
-----------------
* Verification only. There is no signing here, and no private key handling; the
  build side keeps using `cryptography` (`obfuscator/licensing.py`).
* RFC 8032 Ed25519, the common single-signature profile. It is not constant-time
  and must not be used where signing happens on a machine with an attacker.
  Verification handles only public data, so timing leakage there reveals
  nothing secret.
* It is slower than the C implementation by roughly two orders of magnitude —
  measured on this host at ~30 ms per verification. That is the cost of
  avoiding a dependency in a file that must run anywhere, and it is paid once
  per load.
"""
from __future__ import annotations

import hashlib

#: Curve25519 field prime: p = 2**255 - 19.
_P = 2 ** 255 - 19

#: Group order: l = 2**252 + 27742317777372353535851937790883648493.
_L = 2 ** 252 + 27742317777372353535851937790883648493

#: d = -121665/121666 mod p.
_D = (-121665 * pow(121666, _P - 2, _P)) % _P

#: sqrt(-1) mod p.
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)


def _sha512_int(data):
    return int.from_bytes(hashlib.sha512(data).digest(), "little")


def _inv(x):
    return pow(x, _P - 2, _P)


def _recover_x(y, sign):
    """Recover the x coordinate from y, per RFC 8032 §5.1.3."""
    if y >= _P:
        return None
    x2 = (y * y - 1) * _inv(_D * y * y + 1)
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = (x * _SQRT_M1) % _P
    if (x * x - x2) % _P != 0:
        return None
    if (x & 1) != sign:
        x = _P - x
    return x


def _point_add(p, q):
    """Extended-coordinate addition (X, Y, Z, T)."""
    a = (p[1] - p[0]) * (q[1] - q[0]) % _P
    b = (p[1] + p[0]) * (q[1] + q[0]) % _P
    c = 2 * p[3] * q[3] * _D % _P
    d = 2 * p[2] * q[2] % _P
    e, f, g, h = b - a, d - c, d + c, b + a
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _point_mul(s, p):
    """Scalar multiplication, MSB-first double-and-add."""
    q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            q = _point_add(q, p)
        p = _point_add(p, p)
        s >>= 1
    return q


def _point_equal(p, q):
    if (p[0] * q[2] - q[0] * p[2]) % _P != 0:
        return False
    return (p[1] * q[2] - q[1] * p[2]) % _P == 0


def _compress(p):
    zinv = _inv(p[2])
    x = p[0] * zinv % _P
    y = p[1] * zinv % _P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _decompress(data):
    if len(data) != 32:
        return None
    y = int.from_bytes(data, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x is None:
        return None
    return (x, y, 1, x * y % _P)


def _base_point():
    """The Ed25519 base point B, decoded once."""
    y = 4 * _inv(5) % _P
    x = _recover_x(y, 0)
    return (x, y, 1, x * y % _P)


_B = _base_point()


def verify(public_key, signature, message):
    """RFC 8032 Ed25519 verify. Returns True only for a valid signature.

    ``public_key`` is 32 raw bytes; ``signature`` is 64 raw bytes; ``message``
    is bytes. Any malformed input returns False rather than raising — a loader
    that must not print anything cannot afford an exception path, and a
    verification failure is a refusal, not a crash.

    The check is the standard one: decode A and R, recompute
    ``h = SHA512(R || A || M)``, and confirm ``[S]B == R + [h]A`` with S in
    range. Both the point decode and the range check matter: skipping the range
    check admits trivially malleable signatures.
    """
    try:
        if len(public_key) != 32 or len(signature) != 64:
            return False
        a_point = _decompress(bytes(public_key))
        if a_point is None:
            return False
        r_bytes = bytes(signature[:32])
        r_point = _decompress(r_bytes)
        if r_point is None:
            return False
        s = int.from_bytes(bytes(signature[32:]), "little")
        if s >= _L:
            return False
        h = _sha512_int(r_bytes + bytes(public_key) + bytes(message)) % _L
        return _point_equal(_point_mul(s, _B),
                            _point_add(r_point, _point_mul(h, a_point)))
    except Exception:
        # Any arithmetic failure is a refusal. Never propagate: the caller is a
        # loader whose only options are "verify" and "die quietly".
        return False
