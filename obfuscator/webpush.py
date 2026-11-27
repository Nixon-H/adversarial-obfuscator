"""Minimal payload-less Web Push sender (VAPID only).

Pushes carry no payload body: they are pure "tickle" notifications whose
only content is a constant, meaningless nudge. All sensitive data continues
to flow through the authenticated approval page channel, so no aes128gcm
payload encryption is required — only the VAPID ES256 JWT that proves the
sender operates this service. Implemented in pure Python so the Cloudflare
Python worker needs no compiled dependencies.
"""

import base64
import hashlib
import hmac as _hmac
import json
import os
import time
import urllib.request

# ── P-256 / secp256r1 arithmetic ──────────────────────────────────────────

_P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
_N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
_GX = 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296
_GY = 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5


def _inv(x, m):
    return pow(x, m - 2, m)


def _add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and (y1 + y2) % _P == 0:
        return None
    if p1 == p2:
        lam = (3 * x1 * x1 - 3) * _inv(2 * y1 % _P, _P) % _P
    else:
        lam = (y2 - y1) * _inv((x2 - x1) % _P, _P) % _P
    x3 = (lam * lam - x1 - x2) % _P
    y3 = (lam * (x1 - x3) - y1) % _P
    return (x3, y3)


def _mul(k, point):
    result = None
    addend = point
    while k:
        if k & 1:
            result = _add(result, addend)
        addend = _add(addend, addend)
        k >>= 1
    return result


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64u_dec(text: str) -> bytes:
    pad = "=".repeat(0) if False else "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode(text + pad)


def es256_sign(private_key_b64u: str, message: bytes) -> bytes:
    """Sign ``message`` with ES256 (ECDSA over P-256 with SHA-256) and return
    the JWS raw concatenated r||s signature. Uses RFC 6979 deterministic
    nonces so signatures are reproducible and side-channel-resistant."""
    d = int.from_bytes(_b64u_dec(private_key_b64u), "big")
    z = int.from_bytes(hashlib.sha256(message).digest(), "big")
    # RFC 6979 deterministic k generation
    x = d.to_bytes(32, "big")
    h1 = hashlib.sha256(message).digest()
    v = b"\x01" * 32
    k = b"\x00" * 32
    k = _hmac.new(k, v + b"\x00" + x + h1, hashlib.sha256).digest()
    v = _hmac.new(k, v, hashlib.sha256).digest()
    k = _hmac.new(k, v + b"\x01" + x + h1, hashlib.sha256).digest()
    v = _hmac.new(k, v, hashlib.sha256).digest()
    while True:
        v = _hmac.new(k, v, hashlib.sha256).digest()
        candidate = int.from_bytes(v, "big")
        if 1 <= candidate < _N:
            kk = candidate
            break
        k = _hmac.new(k, v + b"\x00", hashlib.sha256).digest()
        v = _hmac.new(k, v, hashlib.sha256).digest()
    point = _mul(kk, (_GX, _GY))
    r = point[0] % _N
    s = (_inv(kk, _N) * (z + r * d)) % _N
    if s > _N // 2:  # low-S normalisation (JOSE expectation)
        s = _N - s
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def vapid_jwt(private_key_b64u: str, audience: str, subject: str,
              lifetime: int = 43200) -> str:
    """Build a VAPID ES256 JWT for the push service ``audience``."""
    header = _b64u(json.dumps({"typ": "JWT", "alg": "ES256"},
                              separators=(",", ":")).encode())
    now = int(time.time())
    claims = _b64u(json.dumps(
        {"aud": audience, "exp": now + lifetime, "sub": subject},
        separators=(",", ":")).encode())
    signing_input = (header + "." + claims).encode("ascii")
    return header + "." + claims + "." + _b64u(es256_sign(private_key_b64u, signing_input))


def send_tickle(endpoint: str, vapid_private_b64u: str, vapid_public_b64u: str,
                subject: str, ttl: int = 900, timeout: float = 15.0) -> int:
    """POST an empty-body push to the subscription endpoint. Returns the push
    service HTTP status. Raises nothing: callers treat non-2xx as a dead or
    transient subscription and never let push failures affect execution."""
    parts = urllib.parse.urlparse(endpoint)
    audience = "%s://%s" % (parts.scheme, parts.netloc)
    token = vapid_jwt(vapid_private_b64u, audience, subject)
    headers = {
        "TTL": str(int(ttl)),
        "Content-Length": "0",
        "Authorization": "vapid t=%s, k=%s" % (token, vapid_public_b64u),
        "User-Agent": "nixon-remote-approval/1",
    }
    request = urllib.request.Request(endpoint, data=b"", method="POST",
                                     headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


import urllib.parse  # noqa: E402  (kept at bottom to keep the crypto block compact)
