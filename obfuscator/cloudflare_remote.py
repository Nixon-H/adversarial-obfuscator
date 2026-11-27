"""Cloudflare Workers deployment artifacts for server-side split execution.

The Rust reference relay is the self-hosted deployment target. This module is
the serverless target: it generates a self-contained Python Worker that keeps
``@remote`` implementations in Cloudflare, verifies the existing protocol-v1
HMAC envelope, requires two independent authenticator TOTP codes, and uses a
SQLite-backed Durable Object for strongly consistent nonce replay rejection.

The generator deliberately does not embed any secret. Recommended deployments
use a worker-only master secret to derive per-customer HMAC/TOTP credentials;
the Worker also supports explicit revocation, rate limits, quotas,
TOTP-failure throttling, verified-code-pair replay limitation, and
metadata-only audit events. A legacy shared-secret mode is retained only as an
explicit compatibility opt-in.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import tempfile
from typing import Iterable

from obfuscator.remote_exec import ExtractedFunction, RemoteError, validate_customer_id
from obfuscator.totp import new_base32_secret, otpauth_uri

WORKER_MARKER = ".nixon-cloudflare-worker"
DEFAULT_WORKER_NAME = "nixon-remote-service"
COMPATIBILITY_DATE = "2026-09-08"

_WORKER_NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")

_WORKER_TEMPLATE = r'''"""Generated Nixon remote-execution Cloudflare Worker.

DO NOT SHIP THIS FILE TO CUSTOMERS. It is the operator-side service runtime;
the confidential @remote implementations are in remote_impl.py. Deploy both
only to the operator-controlled Cloudflare account.
"""
from workers import DurableObject, Response, WorkerEntrypoint

import base64
import hashlib
import hmac
import json
import math
import struct
import time

import remote_impl as _remote_impl

MAX_SKEW = 300.0
REPLAY_TTL = 600.0
TOTP_PAIR_TTL = 120.0
PROTOCOL_VERSION = 1
MAX_BODY_CHARS = 1000000
DEFAULT_RATE_LIMIT_PER_MINUTE = 60
DEFAULT_QUOTA_PER_DAY = 10000
DEFAULT_AUTH_FAILURE_LIMIT_PER_MINUTE = 10
DEFAULT_TOTP_PAIR_MAX_USES = 1
DEFAULT_APPROVAL_EXPIRY_SECONDS = 120
DEFAULT_MAX_PENDING_PER_CUSTOMER = 8
DEFAULT_ANOMALY_MAX_APPROVALS = 5
DEFAULT_ANOMALY_WINDOW_SECONDS = 600
ENROL_TOKEN_COUNT = 8


_FUNCTIONS = {
__FUNCTION_MAP__
}


def _utf8_hex(value):
    return value.encode("utf-8").hex()


def _canonical(value):
    if value is None:
        return '["n"]'
    if isinstance(value, bool):
        return '["b","1"]' if value else '["b","0"]'
    if isinstance(value, int):
        if value < -(1 << 63) or value > (1 << 64) - 1:
            raise ValueError("integer out of range")
        return '["i","%s"]' % value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite number")
        return '["f","%s"]' % struct.pack(">d", value).hex()
    if isinstance(value, str):
        return '["s","%s"]' % _utf8_hex(value)
    if isinstance(value, (list, tuple)):
        return '["a",[%s]]' % ",".join(_canonical(item) for item in value)
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("object keys must be strings")
        parts = []
        for key in sorted(value, key=lambda item: item.encode("utf-8")):
            parts.append("[%s,%s]" % (_canonical(key), _canonical(value[key])))
        return '["o",[%s]]' % ",".join(parts)
    raise ValueError("value is not JSON-compatible")


def _sign(secret, function, args, kwargs, nonce, timestamp):
    material = "\n".join([
        "nixon-remote-v1",
        _canonical(function),
        _canonical(list(args)),
        _canonical(dict(kwargs or {})),
        _canonical(nonce),
        _canonical(timestamp),
    ]).encode("utf-8")
    return hmac.new(bytes(secret), material, hashlib.sha256).hexdigest()


def _verify_hmac(secret, function, args, kwargs, nonce, timestamp, signature, now):
    if abs(now - float(timestamp)) > MAX_SKEW:
        raise ValueError("remote request expired")
    expected = _sign(secret, function, args, kwargs, nonce, float(timestamp))
    if (not isinstance(signature, str) or len(signature) != 64
            or any(ch not in "0123456789abcdef" for ch in signature)
            or not hmac.compare_digest(expected, signature)):
        raise ValueError("remote request signature mismatch")


def _b32_bytes(secret):
    if not isinstance(secret, str) or not secret.strip():
        raise ValueError("empty TOTP secret")
    compact = "".join(secret.strip().split()).replace("-", "").upper()
    padded = compact + "=" * ((8 - len(compact) % 8) % 8)
    return base64.b32decode(padded, casefold=False)


def _totp(secret, at):
    counter = int(float(at) // 30)
    if counter < 0:
        raise ValueError("negative TOTP time")
    digest = hmac.new(
        _b32_bytes(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % 1000000).zfill(6)


def _code_text(value):
    if not isinstance(value, str):
        return ""
    return "".join(value.strip().split())


def _valid_totp(secret, code, now):
    candidate = _code_text(code)
    if len(candidate) != 6 or not candidate.isdigit():
        return False
    try:
        for offset in (-30, 0, 30):
            when = now + offset
            if when >= 0 and hmac.compare_digest(_totp(secret, when), candidate):
                return True
    except Exception:
        return False
    return False


def _totp_pair_fingerprint(secret, customer, primary_code, secondary_code):
    # Store only an HMAC fingerprint. The authenticator codes themselves are
    # short-lived secrets and must not be written to the replay database.
    material = (
        str(customer) + "\x00" + _code_text(primary_code)
        + "\x00" + _code_text(secondary_code)).encode("utf-8")
    return hmac.new(bytes(secret), material, hashlib.sha256).hexdigest()


def _binding(env, name):
    try:
        return getattr(env, name)
    except Exception:
        try:
            return env[name]
        except Exception:
            return None


def _env(env, name):
    value = _binding(env, name)
    if value is None:
        return ""
    return str(value)


def _truthy(value):
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def _positive_int_env(env, name, default):
    raw = _env(env, name).strip()
    if not raw:
        return int(default)
    try:
        value = int(raw, 10)
    except ValueError as exc:
        raise ValueError(name + " must be a positive integer") from exc
    if value <= 0:
        raise ValueError(name + " must be a positive integer")
    return value


def _hex32(value):
    text = str(value or "").strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError("expected a 64-character hex secret")
    return bytes.fromhex(text)


def _valid_customer(value):
    if not isinstance(value, str) or not value or len(value) > 128:
        return False
    first = value[0]
    if not (("a" <= first <= "z") or ("A" <= first <= "Z") or ("0" <= first <= "9")):
        return False
    for ch in value[1:]:
        if not (("a" <= ch <= "z") or ("A" <= ch <= "Z")
                or ("0" <= ch <= "9") or ch in ("_", ".", "-")):
            return False
    return True


def _customer_material(master, customer, purpose):
    material = (
        b"nixon-remote-customer-v1\x00" + purpose.encode("ascii")
        + b"\x00" + customer.encode("utf-8"))
    return hmac.new(master, material, hashlib.sha256).digest()


def _derive_customer_credentials(master, customer):
    hmac_secret = _customer_material(master, customer, "hmac")
    primary = base64.b32encode(
        _customer_material(master, customer, "totp-primary")[:20]).decode("ascii").rstrip("=")
    secondary = base64.b32encode(
        _customer_material(master, customer, "totp-secondary")[:20]).decode("ascii").rstrip("=")
    return hmac_secret, primary, secondary


# Baseline hardening applied to every response the Worker emits. frame-ancestors
# 'none' plus X-Frame-Options: DENY keep the approval surface out of iframes
# (clickjacking/UI-redress); nosniff and no-referrer are defence-in-depth.
_SEC_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}
# The approval page is self-contained inline HTML/JS by design: script-src
# 'unsafe-inline' is required for it to execute at all, so the policy instead
# leans on default-src 'none' — no external resources, no exfiltration channel
# beyond same-origin connect-src, no base/form hijacking, no framing.
_PAGE_CSP = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
    "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")


def _sec(extra=None):
    headers = dict(_SEC_HEADERS)
    if extra:
        headers.update(extra)
    return headers


def _response(doc):
    # Remote clients intentionally read the JSON error body. Non-200 statuses
    # would be collapsed by urllib into a transport error before that body is
    # available, so protocol/authentication failures remain JSON responses.
    return Response(
        json.dumps(doc, separators=(",", ":")),
        headers=_sec({"Content-Type": "application/json; charset=utf-8",
                      "Cache-Control": "no-store"}))


def _audit(outcome, customer="", function="", detail=""):
    """Emit metadata-only operator telemetry; never arguments or secrets."""
    try:
        record = {
            "event": "nixon-remote",
            "outcome": str(outcome),
            "customer": str(customer or ""),
            "function": str(function or ""),
            "detail": str(detail or ""),
            "timestamp": int(time.time()),
        }
        print(json.dumps(record, sort_keys=True, separators=(",", ":")))
    except Exception:
        pass



def _ecdsa_dependencies():
    try:
        from js import crypto, Object
        from pyodide.ffi import to_js
    except Exception:
        return None, None, None

    def jobj(value):
        return to_js(value, dict_converter=Object.fromEntries)

    return crypto, to_js, jobj


async def _ecdsa_verify(x, y, signature_hex, message):
    """Verify a WebCrypto ECDSA P-256/SHA-256 approval signature.

    Phones enrol only public keys, so verification is the only worker-side
    operation. The FFI performs cryptography in the runtime rather than in
    interpreted Python. Any failure returns False: approval is fail-closed.
    """
    crypto, to_js, jobj = _ecdsa_dependencies()
    if crypto is None:
        return False
    try:
        if (not isinstance(x, str) or not isinstance(y, str)
                or len(x) != 43 or len(y) != 43):
            return False
        if (not isinstance(signature_hex, str) or len(signature_hex) != 128
                or any(ch not in "0123456789abcdef" for ch in signature_hex)):
            return False
        jwk = {"kty": "EC", "crv": "P-256", "x": x, "y": y, "ext": True}
        key = await crypto.subtle.importKey(
            "jwk", jobj(jwk), jobj({"name": "ECDSA", "namedCurve": "P-256"}),
            False, to_js(["verify"]))
        result = await crypto.subtle.verify(
            jobj({"name": "ECDSA", "hash": "SHA-256"}),
            key, to_js(bytes.fromhex(signature_hex)), to_js(bytes(message)))
        return bool(result)
    except Exception:
        return False


def _approval_key_id(x, y):
    material = (str(x) + ":" + str(y)).encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:24]


def _enrol_token(master, customer, index):
    material = (
        b"nixon-remote-enrol-v1\x00" + customer.encode("utf-8")
        + b"\x00" + str(int(index)).encode("ascii"))
    return hmac.new(master, material, hashlib.sha256).hexdigest()


def _admin_secret(master):
    return hmac.new(
        master, b"nixon-remote-admin-v1\x00", hashlib.sha256).hexdigest()


def _enrol_proof_message(customer, token):
    return ("nixon-remote-enrol-v1\x00" + str(customer)
            + "\x00" + str(token)).encode("utf-8")


def _pending_message(customer, key_id, ts):
    return ("nixon-remote-pending-v1\x00" + str(customer) + "\x00"
            + str(key_id) + "\x00" + str(ts)).encode("utf-8")


def _approval_message(customer, approval_id, request_hash, decision, ts):
    return ("nixon-remote-approval-v1\x00" + str(customer) + "\x00"
            + str(approval_id) + "\x00" + str(request_hash) + "\x00"
            + str(decision) + "\x00" + str(ts)).encode("utf-8")


def _b64url_decode(text):
    if not isinstance(text, str):
        raise ValueError("not text")
    padded = text + "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _b64url_encode(raw):
    return base64.urlsafe_b64encode(bytes(raw)).decode("ascii").rstrip("=")


def _cbor_decode(data, pos=0):
    """Minimal definite-length CBOR decoder sufficient for WebAuthn
    attestation objects and COSE keys. Returns (value, next_position)."""
    if pos >= len(data):
        raise ValueError("truncated cbor")
    initial = data[pos]
    pos += 1
    major = initial >> 5
    info = initial & 0x1F
    if info < 24:
        argument = info
    elif info == 24:
        argument = data[pos]; pos += 1
    elif info == 25:
        argument = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    elif info == 26:
        argument = struct.unpack(">I", data[pos:pos + 4])[0]; pos += 4
    elif info == 27:
        argument = struct.unpack(">Q", data[pos:pos + 8])[0]; pos += 8
    else:
        raise ValueError("indefinite cbor is unsupported")
    if major == 0:
        return argument, pos
    if major == 1:
        return -1 - argument, pos
    if major == 2:
        end = pos + argument
        if end > len(data):
            raise ValueError("truncated cbor bytes")
        return bytes(data[pos:end]), end
    if major == 3:
        end = pos + argument
        if end > len(data):
            raise ValueError("truncated cbor text")
        return bytes(data[pos:end]).decode("utf-8"), end
    if major == 4:
        items = []
        for _index in range(argument):
            value, pos = _cbor_decode(data, pos)
            items.append(value)
        return items, pos
    if major == 5:
        mapping = {}
        for _index in range(argument):
            key, pos = _cbor_decode(data, pos)
            value, pos = _cbor_decode(data, pos)
            mapping[key] = value
        return mapping, pos
    if major == 7:
        if info == 20:
            return False, pos
        if info == 21:
            return True, pos
        if info in (22, 23):
            return None, pos
    raise ValueError("unsupported cbor major type")


def _der_to_raw64(der):
    """Convert a DER-encoded ECDSA signature to the 64-byte P1363 form
    WebCrypto expects. Returns None when the structure is invalid."""
    try:
        if len(der) < 8 or der[0] != 0x30:
            return None
        total = der[1]
        if total + 2 > len(der):
            return None
        pos = 2
        parts = []
        for _index in range(2):
            if der[pos] != 0x02:
                return None
            length = der[pos + 1]
            pos += 2
            part = bytes(der[pos:pos + length])
            if len(part) != length:
                return None
            pos += length
            part = part.lstrip(b"\x00")
            if len(part) > 32:
                return None
            parts.append(part.rjust(32, b"\x00"))
        return parts[0] + parts[1]
    except Exception:
        return None


def _webauthn_challenge(message):
    return _b64url_encode(hashlib.sha256(bytes(message)).digest())


def _check_client_data(client_raw, expected_type, expected_message):
    """Validate clientDataJSON structure and exact challenge binding."""
    try:
        client = json.loads(bytes(client_raw).decode("utf-8"))
    except Exception:
        return False
    if not isinstance(client, dict):
        return False
    if client.get("type") != expected_type:
        return False
    challenge = str(client.get("challenge", ""))
    return hmac.compare_digest(challenge, _webauthn_challenge(expected_message))


def _parse_attestation(attestation_raw, client_raw, expected_message, rp_id):
    """Parse a WebAuthn attestation response at enrolment.

    Returns (credential_id_b64url, x_b64url, y_b64url) or raises ValueError.
    Attestation statements are not verified: consumer passkeys deliberately
    withhold meaningful attestation, and enrolment authorization comes from
    the single-use token rather than authenticator provenance. What matters
    is the credential public key, the RP binding and user verification.
    """
    if not _check_client_data(client_raw, "webauthn.create", expected_message):
        raise ValueError("client data")
    try:
        top, end = _cbor_decode(bytes(attestation_raw))
    except Exception as exc:
        raise ValueError("attestation cbor") from exc
    if not isinstance(top, dict) or not isinstance(top.get("authData"), bytes):
        raise ValueError("attestation structure")
    auth_data = top["authData"]
    if len(auth_data) < 55:
        raise ValueError("attestation authData short")
    if auth_data[:32] != hashlib.sha256(rp_id.encode("utf-8")).digest():
        raise ValueError("rp")
    flags = auth_data[32]
    if not (flags & 0x01) or not (flags & 0x04):
        raise ValueError("user verification")
    if not (flags & 0x40):
        raise ValueError("attested credential data missing")
    pos = 37
    pos += 16  # AAGUID
    cred_len = struct.unpack(">H", auth_data[pos:pos + 2])[0]
    pos += 2
    cred_id = bytes(auth_data[pos:pos + cred_len])
    pos += cred_len
    if len(cred_id) == 0 or len(cred_id) > 1023:
        raise ValueError("credential id")
    try:
        cose, end = _cbor_decode(auth_data, pos)
    except Exception as exc:
        raise ValueError("cose") from exc
    if not isinstance(cose, dict):
        raise ValueError("cose structure")
    if cose.get(1) != 2 or cose.get(3) != -7 or cose.get(-1) != 1:
        raise ValueError("cose algorithm")
    x_raw = cose.get(-2)
    y_raw = cose.get(-3)
    if (not isinstance(x_raw, bytes) or not isinstance(y_raw, bytes)
            or len(x_raw) != 32 or len(y_raw) != 32):
        raise ValueError("cose coordinates")
    return _b64url_encode(cred_id), _b64url_encode(x_raw), _b64url_encode(y_raw)


async def _webauthn_verify(key_doc, doc, expected_message, rp_id):
    """Verify a WebAuthn assertion against an enrolled credential.

    Returns (True, "ok") only when the relying-party binding, user-presence
    and user-verification flags, exact challenge binding, and the ECDSA
    signature all hold. Any failure returns (False, detail); approval is
    fail-closed.
    """
    try:
        auth_data = _b64url_decode(doc.get("authenticatorData", ""))
        client_raw = _b64url_decode(doc.get("clientDataJSON", ""))
        signature_raw = _b64url_decode(doc.get("signature", ""))
    except Exception:
        return False, "malformed"
    if len(auth_data) < 37:
        return False, "malformed"
    if auth_data[:32] != hashlib.sha256(rp_id.encode("utf-8")).digest():
        return False, "rp"
    flags = auth_data[32]
    if not (flags & 0x01) or not (flags & 0x04):
        return False, "user verification required"
    if not _check_client_data(client_raw, "webauthn.get", expected_message):
        return False, "challenge"
    raw64 = _der_to_raw64(signature_raw)
    if raw64 is None:
        return False, "malformed"
    signed = bytes(auth_data) + hashlib.sha256(bytes(client_raw)).digest()
    ok = await _ecdsa_verify(key_doc["x"], key_doc["y"], raw64.hex(), signed)
    if not ok:
        return False, "signature"
    return True, "ok"


def _valid_key_id(value):
    return (isinstance(value, str) and len(value) == 24
            and all(ch in "0123456789abcdef" for ch in value))


def _valid_approval_id(value):
    return (isinstance(value, str) and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value))


def _fresh_ts(value, now):
    """Parse a decimal-integer timestamp text; -1 when stale or malformed."""
    if not isinstance(value, str) or not value.isdigit() or len(value) > 20:
        return -1
    stamp = int(value, 10)
    if abs(float(now) - float(stamp)) > MAX_SKEW:
        return -1
    return stamp


def _random_hex(byte_count):
    import os
    return os.urandom(int(byte_count)).hex()


def _col(row, name, index):
    try:
        return row[name]
    except Exception:
        pass
    try:
        return row[index]
    except Exception:
        pass
    return getattr(row, name)


def _preview(value, limit=200):
    try:
        text = json.dumps(value, separators=(",", ":"))
    except Exception:
        return ""
    if len(text) > limit:
        return text[:limit] + "..."
    return text



# ── P-256 / secp256r1 arithmetic ──────────────────────────────────────────

_WPP = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
_WPN = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
_WPGX = 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296
_WPGY = 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5


def _wp_wp_inv(x, m):
    return pow(x, m - 2, m)


def _wp_wp_add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and (y1 + y2) % _WPP == 0:
        return None
    if p1 == p2:
        lam = (3 * x1 * x1 - 3) * _wp_inv(2 * y1 % _WPP, _WPP) % _WPP
    else:
        lam = (y2 - y1) * _wp_inv((x2 - x1) % _WPP, _WPP) % _WPP
    x3 = (lam * lam - x1 - x2) % _WPP
    y3 = (lam * (x1 - x3) - y1) % _WPP
    return (x3, y3)


def _wp_wp_mul(k, point):
    result = None
    addend = point
    while k:
        if k & 1:
            result = _wp_add(result, addend)
        addend = _wp_add(addend, addend)
        k >>= 1
    return result


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64u_dec(text: str) -> bytes:
    pad = "=".repeat(0) if False else "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode(text + pad)


def _wp__wp_es256_sign(private_key_b64u: str, message: bytes) -> bytes:
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
        if 1 <= candidate < _WPN:
            kk = candidate
            break
        k = _hmac.new(k, v + b"\x00", hashlib.sha256).digest()
        v = _hmac.new(k, v, hashlib.sha256).digest()
    point = _wp_mul(kk, (_WPGX, _WPGY))
    r = point[0] % _WPN
    s = (_wp_inv(kk, _WPN) * (z + r * d)) % _WPN
    if s > _WPN // 2:  # low-S normalisation (JOSE expectation)
        s = _WPN - s
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def _wp__wp_vapid_jwt(private_key_b64u: str, audience: str, subject: str,
              lifetime: int = 43200) -> str:
    """Build a VAPID ES256 JWT for the push service ``audience``."""
    header = _b64u(json.dumps({"typ": "JWT", "alg": "ES256"},
                              separators=(",", ":")).encode())
    now = int(time.time())
    claims = _b64u(json.dumps(
        {"aud": audience, "exp": now + lifetime, "sub": subject},
        separators=(",", ":")).encode())
    signing_input = (header + "." + claims).encode("ascii")
    return header + "." + claims + "." + _b64u(_wp_es256_sign(private_key_b64u, signing_input))


def send_tickle(endpoint: str, vapid_private_b64u: str, vapid_public_b64u: str,
                subject: str, ttl: int = 900, timeout: float = 15.0) -> int:
    """POST an empty-body push to the subscription endpoint. Returns the push
    service HTTP status. Raises nothing: callers treat non-2xx as a dead or
    transient subscription and never let push failures affect execution."""
    parts = urllib.parse.urlparse(endpoint)
    audience = "%s://%s" % (parts.scheme, parts.netloc)
    token = _wp_vapid_jwt(vapid_private_b64u, audience, subject)
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


def _webpush_tickle(endpoint, private, public, subject, ttl=900):
    """POST an empty-body push tickle to one subscription endpoint."""
    import urllib.parse as _up
    import urllib.request as _ur
    parts = _up.urlparse(endpoint)
    audience = "%s://%s" % (parts.scheme, parts.netloc)
    token = _wp_vapid_jwt(private, audience, subject)
    request = _ur.Request(endpoint, data=b"", method="POST", headers={
        "TTL": str(int(ttl)),
        "Content-Length": "0",
        "Authorization": "vapid t=%s, k=%s" % (token, public),
        "User-Agent": "nixon-remote-approval/1",
    })
    try:
        with _ur.urlopen(request, timeout=8.0) as response:
            return int(response.status)
    except Exception as exc:
        code = getattr(exc, "code", None)
        if code is not None:
            return int(code)
        return 0


_SERVICE_WORKER_JS = """/* Nixon remote approval push receiver. Payload-less
   tickles only: the notification carries no request data. */
self.addEventListener("push", (event) => {
  event.waitUntil(self.registration.showNotification("Nixon remote approval", {
    body: "A remote-execution request is waiting for your approval.",
    tag: "nixon-approval",
    renotify: true,
    data: {url: "./"},
  }));
});
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(clients.matchAll({type: "window", includeUncontrolled: true}).then((list) => {
    for (const client of list) {
      if (client.url.indexOf("workers.dev") >= 0 && "focus" in client) return client.focus();
    }
    return clients.openWindow("./");
  }));
});
"""


_APPROVAL_PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nixon remote approval</title>
<style>
body{font-family:system-ui,sans-serif;margin:1rem auto;max-width:42rem;padding:0 .6rem;color:#17202a}
h1{font-size:1.25rem}.card{border:1px solid #ccd;border-radius:8px;padding:.8rem;margin:.7rem 0}
.fn{font-weight:650}.meta{color:#556;font-size:.82rem;word-break:break-all}
.args{background:#f4f6f8;border-radius:6px;padding:.4rem;font-family:ui-monospace,monospace;font-size:.78rem;word-break:break-all;white-space:pre-wrap}
button{font-size:1rem;padding:.55rem 1.1rem;border-radius:7px;border:1px solid #999;margin:.3rem .4rem .3rem 0;cursor:pointer}
.ok{background:#146c2e;color:#fff;border-color:#146c2e}.no{background:#fff;color:#8a1111;border-color:#8a1111}
  .warn { color: #b00020; font-weight: bold; font-size: 0.9em; margin: 6px 0; }
  .warn-card { border-left: 4px solid #b00020; }
.go{background:#1a4f9c;color:#fff;border-color:#1a4f9c}
#status{padding:.5rem;border-radius:6px;margin:.5rem 0}.info{background:#e8f0fe}.err{background:#fde8e8}.good{background:#e6f4ea}
small{color:#667}</style></head>
<body>
<h1>Remote execution approval</h1>
<div id="status" class="info">loading&hellip;</div>
<div id="enrolbox" class="card" hidden></div>
<div id="keybox" class="card" hidden></div>
<div id="checkwrap" class="card" hidden>
<button id="check" class="go">Check for pending requests</button>
<small>Each check and each decision uses your passkey with biometric or PIN
verification. Nothing is approved silently.</small></div>
<div id="rows"></div>
<div class="card"><small>Only approve requests you expect from your own application.
Approval is cryptographically bound to the exact request by your passkey and cannot
be reused for any other call. If you did not just trigger this action on your
computer, press Deny.</small></div>
<script>
"use strict";
const enc = new TextEncoder();
const dec = new TextDecoder();
const statusEl = document.getElementById("status");
function say(text, cls) { statusEl.textContent = text; statusEl.className = cls || "info"; }
function b64u(buf) {
  const bytes = new Uint8Array(buf);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function b64uDec(text) {
  const pad = text + "=".repeat((4 - text.length % 4) % 4);
  const binary = atob(pad.replace(/-/g, "+").replace(/_/g, "/"));
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}
async function subscribePush(customer) {
  try {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) return;
    const vapid = "__VAPID_PUBLIC__";
    if (!vapid) return;
    if (Notification.permission === "denied") return;
    if (Notification.permission === "default") {
      const perm = await Notification.requestPermission();
      if (perm !== "granted") return;
    }
    const reg = await navigator.serviceWorker.register("sw.js");
    const pad = vapid + "=".repeat((4 - vapid.length % 4) % 4);
    const raw = atob(pad.replace(/-/g, "+").replace(/_/g, "/"));
    const keyBytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) keyBytes[i] = raw.charCodeAt(i);
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true, applicationServerKey: keyBytes});
    await post({type: "subscribe", version: 1, customer: customer,
                endpoint: sub.endpoint});
  } catch (err) { /* push is best-effort: approval works without it */ }
}

async function post(doc) {
  const res = await fetch(location.pathname, {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify(doc)});
  return await res.json();
}
function dbOpen() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open("nixon-remote-approval", 1);
    req.onupgradeneeded = () => req.result.createObjectStore("keys");
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
async function dbPut(id, value) {
  const db = await dbOpen();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("keys", "readwrite");
    tx.objectStore("keys").put(value, id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}
async function dbAll() {
  const db = await dbOpen();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("keys", "readonly");
    const req = tx.objectStore("keys").getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}
function canonical(parts) {
  return enc.encode(parts.join("\x00"));
}
async function challengeOf(parts) {
  return await crypto.subtle.digest("SHA-256", canonical(parts));
}
function ts() { return Math.floor(Date.now() / 1000).toString(); }

async function assertWith(record, parts) {
  /* One WebAuthn assertion bound to the canonical message. The browser places
     base64url(SHA-256(message)) into clientDataJSON.challenge, which is the
     exact value the server reconstructs and compares. */
  if (!record || typeof record.credId !== "string" || record.credId.length === 0) {
    throw new Error("this enrolment predates passkeys or is incomplete — re-enrol with a fresh enrolment link");
  }
  const challenge = await challengeOf(parts);
  const cred = await navigator.credentials.get({publicKey: {
    challenge: challenge,
    rpId: location.hostname,
    allowCredentials: [{type: "public-key", id: b64uDec(record.credId)}],
    userVerification: "required",
  }});
  return {
    authenticatorData: b64u(cred.response.authenticatorData),
    clientDataJSON: b64u(cred.response.clientDataJSON),
    signature: b64u(cred.response.signature),
  };
}

async function enrolFromHash() {
  if (!location.hash || location.hash.indexOf("customer=") < 0) return false;
  const params = new URLSearchParams(location.hash.slice(1));
  const customer = params.get("customer") || "";
  const token = params.get("token") || "";
  const label = (params.get("label") || "phone").slice(0, 40);
  if (!customer || !token) return false;
  const box = document.getElementById("enrolbox");
  box.hidden = false;
  box.textContent = "Enrolling this device for customer " + customer + " ...";
  try {
    const challenge = await challengeOf(["nixon-remote-enrol-v1", customer, token]);
    const userId = enc.encode((customer + ":" + token.slice(0, 16)).slice(0, 64));
    const cred = await navigator.credentials.create({publicKey: {
      challenge: challenge,
      rp: {name: "Nixon remote approval"},
      user: {id: userId, name: customer + " approval", displayName: customer + " approval"},
      pubKeyCredParams: [{type: "public-key", alg: -7}],
      authenticatorSelection: {userVerification: "required", residentKey: "preferred"},
      attestation: "none",
    }});
    if (!cred) throw new Error("enrolment was cancelled");
    const res = await post({
      type: "enrol", version: 1, customer: customer, token: token, label: label,
      attestation: b64u(cred.response.attestationObject),
      clientDataJSON: b64u(cred.response.clientDataJSON)});
    if (!res.enrolled) throw new Error(res.error || "enrolment failed");
    await dbPut(customer + ":" + res.key_id, {
      customer: customer, keyId: res.key_id, label: label,
      credId: b64u(cred.rawId)});
    history.replaceState(null, "", location.pathname);
    box.textContent = "Device enrolled for " + customer + ". Keep this page bookmarked.";
    return true;
  } catch (err) {
    box.textContent = "Enrolment failed: " + err.message;
    throw err;
  }
}

function rowElement(item, record, onDone) {
  const div = document.createElement("div");
  div.className = "card";
  const when = new Date(item.submitted_at * 1000).toLocaleTimeString();
  div.innerHTML = "<div class='fn'></div>"
    + "<div class='meta'></div>"
    + "<div class='warn'></div>"
    + "<div class='args'></div>";
  const anomalyText = {
    "novel-function": "first time this function has ever been approved",
    "high-velocity": "unusually many approvals in the last few minutes",
  };
  const warnings = (item.anomalies || []).map(
    tag => anomalyText[tag] || tag);
  if (warnings.length) {
    div.querySelector(".warn").textContent =
      "warning: " + warnings.join("; ") + " — verify this is really yours";
    div.className = "card warn-card";
  } else {
    div.querySelector(".warn").remove();
  }
  div.querySelector(".fn").textContent = item.function + "  (" + when + ")";
  div.querySelector(".meta").textContent =
    "customer " + item.customer + " · request " + item.request_hash.slice(0, 16) + "…";
  div.querySelector(".args").textContent = item.args_preview || "(no arguments)";
  const yes = document.createElement("button");
  yes.textContent = "Approve"; yes.className = "ok";
  const no = document.createElement("button");
  no.textContent = "Deny"; no.className = "no";
  const decide = async (decision) => {
    yes.disabled = true; no.disabled = true;
    try {
      const stamp = ts();
      const assertion = await assertWith(record, [
        "nixon-remote-approval-v1", item.customer, item.approval_id,
        item.request_hash, decision, stamp]);
      const res = await post(Object.assign({
        type: "approve", version: 1,
        customer: item.customer, key_id: record.keyId,
        approval_id: item.approval_id, request_hash: item.request_hash,
        decision: decision, ts: stamp}, assertion));
      if (res.error) throw new Error(res.error);
      div.querySelector(".args").textContent =
        decision === "approve" ? "approved" : "denied";
      yes.remove(); no.remove();
      say(decision === "approve" ? "Request approved and executed." : "Request denied.", "good");
      if (typeof onDone === "function") onDone(res.pending);
    } catch (err) {
      yes.disabled = false; no.disabled = false;
      say("decision failed: " + err.message, "err");
    }
  };
  yes.onclick = () => decide("approve");
  no.onclick = () => decide("deny");
  div.appendChild(yes); div.appendChild(no);
  return div;
}

function renderItems(items, record) {
  const rows = document.getElementById("rows");
  rows.innerHTML = "";
  const list = items || [];
  if (list.length === 0) {
    say("No pending requests right now. Start your application first, then check again — or wait for the push notification.", "info");
    return;
  }
  say(list.length + " pending request(s). Review each one carefully.", "info");
  for (const item of list) {
    rows.appendChild(rowElement(item, record, renderRefresh));
  }
}
function renderRefresh(items) {
  const rows = document.getElementById("rows");
  const list = items || [];
  if (list.length === 0) return;
  rows.innerHTML = "";
  for (const item of list) {
    rows.appendChild(rowElement(item, currentRecord, renderRefresh));
  }
}
let currentRecord = null;

async function checkPending(record) {
  const stamp = ts();
  const assertion = await assertWith(record, [
    "nixon-remote-pending-v1", record.customer, record.keyId, stamp]);
  const res = await post(Object.assign({
    type: "pending", version: 1, customer: record.customer,
    key_id: record.keyId, ts: stamp}, assertion));
  if (res.error) throw new Error(res.error);
  renderItems(res.pending || [], record);
}

async function main() {
  if (!window.PublicKeyCredential) {
    say("This browser does not support passkeys. Use a current version of Safari, Chrome or Firefox.", "err");
    return;
  }
  try {
    if (await enrolFromHash()) {
      say("Enrolment complete. You can now approve requests.", "good");
    }
  } catch (err) {
    return;
  }
  const records = await dbAll();
  if (records.length === 0) {
    say("No enrolled device keys on this browser. Open the enrolment link provided by your operator.", "err");
    return;
  }
  // Enrolments from before the passkey upgrade have no credential id and can
  // never produce WebAuthn assertions; they must be re-enrolled, not used.
  const valid = records.filter(
    (r) => r && typeof r.credId === "string" && r.credId.length > 0);
  if (valid.length === 0) {
    say("This browser's enrolment predates passkey approval. Ask your operator for a fresh enrolment link and enrol again — the old enrolment cannot be used.", "err");
    return;
  }
  // When the enrolment link's customer is still visible in the fragment,
  // prefer the matching device record over an arbitrary one.
  let chosen = valid[0];
  if (location.hash && location.hash.indexOf("customer=") >= 0) {
    const wanted = new URLSearchParams(location.hash.slice(1)).get("customer");
    const match = valid.filter((r) => r.customer === wanted);
    if (match.length > 0) chosen = match[0];
  }
  const staleNote = valid.length < records.length
    ? " (" + (records.length - valid.length) + " outdated pre-passkey enrolment(s) on this browser are ignored)"
    : "";
  currentRecord = chosen;
  subscribePush(chosen.customer);
  const keybox = document.getElementById("keybox");
  keybox.hidden = false;
  keybox.textContent = "device: " + (currentRecord.label || "phone")
    + " · customer " + currentRecord.customer;
  document.getElementById("checkwrap").hidden = false;
  document.getElementById("check").onclick = async () => {
    try {
      say("authenticating…", "info");
      await checkPending(currentRecord);
    } catch (err) {
      say(err.message || "check failed", "err");
    }
  };
  say("Tap \"Check for pending requests\" and authenticate to review pending operations." + staleNote, "info");
}
main().catch((err) => say(err.message || "setup failed", "err"));
</script></body></html>"""



class SecurityRegistry(DurableObject):
    """Consistent nonce, rate-limit, and quota state in SQLite."""

    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        self.sql = ctx.storage.sql
        self.sql.exec(
            "CREATE TABLE IF NOT EXISTS nonces ("
            "nonce TEXT PRIMARY KEY, expires_at REAL NOT NULL)")
        self.sql.exec(
            "CREATE TABLE IF NOT EXISTS usage_windows ("
            "window_key TEXT PRIMARY KEY, expires_at REAL NOT NULL, "
            "hits INTEGER NOT NULL)")
        self.sql.exec(
            "CREATE TABLE IF NOT EXISTS approval_keys ("
            "customer TEXT NOT NULL, key_id TEXT NOT NULL, x TEXT NOT NULL, "
            "y TEXT NOT NULL, label TEXT NOT NULL, enrolled_at REAL NOT NULL, "
            "cred_id TEXT NOT NULL DEFAULT '', "
            "revoked INTEGER NOT NULL DEFAULT 0, "
            "PRIMARY KEY (customer, key_id))")
        self.sql.exec(
            "CREATE TABLE IF NOT EXISTS enrol_tokens ("
            "token_hash TEXT PRIMARY KEY, customer TEXT NOT NULL, "
            "consumed_at REAL NOT NULL)")
        self.sql.exec(
            "CREATE TABLE IF NOT EXISTS pending_requests ("
            "approval_id TEXT PRIMARY KEY, customer TEXT NOT NULL, "
            "request_json TEXT NOT NULL, request_hash TEXT NOT NULL, "
            "function TEXT NOT NULL, args_preview TEXT NOT NULL, "
            "submitted_at REAL NOT NULL, expires_at REAL NOT NULL, "
            "status TEXT NOT NULL, result_json TEXT NOT NULL, "
            "decided_at REAL NOT NULL)")
        self.sql.exec(
            "CREATE TABLE IF NOT EXISTS customer_state ("
            "customer TEXT PRIMARY KEY, disabled INTEGER NOT NULL)")
        self.sql.exec(
            "CREATE TABLE IF NOT EXISTS decision_log ("
            "customer TEXT NOT NULL, decided_at REAL NOT NULL, "
            "function TEXT NOT NULL)")
        self.sql.exec(
            "CREATE TABLE IF NOT EXISTS approved_functions ("
            "customer TEXT NOT NULL, function TEXT NOT NULL, "
            "first_seen REAL NOT NULL, PRIMARY KEY (customer, function))")
        # Operators upgrading from the WebCrypto approval deployment already
        # have an approval_keys table without cred_id. CREATE TABLE IF NOT
        # EXISTS never adds columns, so the passkey enrolment insert would
        # fail closed on every existing Durable Object. Add the column once;
        # enrolled WebCrypto rows keep the empty credential id and remain
        # unusable for passkey ceremonies, which is the intended fail-closed
        # outcome because only passkeys make approval decisions now.
        try:
            self.sql.exec("SELECT cred_id FROM approval_keys LIMIT 0")
        except Exception:
            self.sql.exec(
                "ALTER TABLE approval_keys ADD COLUMN "
                "cred_id TEXT NOT NULL DEFAULT ''")

    def _hits(self, window_key):
        rows = self.sql.exec(
            "SELECT hits FROM usage_windows WHERE window_key = ?",
            str(window_key)).toArray()
        if len(rows) == 0:
            return 0
        row = rows[0]
        try:
            return int(row["hits"])
        except Exception:
            pass
        try:
            return int(row[0])
        except Exception:
            pass
        try:
            return int(row.hits)
        except Exception as exc:
            raise ValueError("usage accounting row is malformed") from exc

    def _increment(self, window_key, expires_at):
        self.sql.exec(
            "INSERT INTO usage_windows (window_key, expires_at, hits) "
            "VALUES (?, ?, 1) "
            "ON CONFLICT(window_key) DO UPDATE SET "
            "hits = hits + 1, expires_at = excluded.expires_at",
            str(window_key), float(expires_at))

    async def begin_totp_attempt(self, customer, now, failure_limit):
        # Count only HMAC-valid TOTP attempts. Success decrements the
        # provisional count; failure leaves it behind. This throttles online
        # six-digit-code guessing without charging HMAC-invalid spam to a victim.
        now = float(now)
        self.sql.exec("DELETE FROM usage_windows WHERE expires_at < ?", now)
        minute = int(now // 60) * 60
        key = str(customer) + "|af|" + str(minute)
        if self._hits(key) >= int(failure_limit):
            return "auth-rate-limit"
        self._increment(key, float(minute + 120))
        return "ok"

    async def finish_totp_success(self, customer, now):
        now = float(now)
        minute = int(now // 60) * 60
        key = str(customer) + "|af|" + str(minute)
        self.sql.exec(
            "UPDATE usage_windows SET hits = hits - 1 "
            "WHERE window_key = ? AND hits > 0", str(key))
        return "ok"

    async def check_and_store(self, nonce, now, customer, rate_limit, quota,
                              totp_fingerprint="", pair_max_uses=1):
        # Durable Object storage operations are synchronous inside one object,
        # so no request can interleave between the quota checks and inserts.
        now = float(now)
        self.sql.exec("DELETE FROM nonces WHERE expires_at < ?", now)
        self.sql.exec("DELETE FROM usage_windows WHERE expires_at < ?", now)
        rows = self.sql.exec(
            "SELECT nonce FROM nonces WHERE nonce = ?", str(nonce)).toArray()
        if len(rows) != 0:
            return "replayed"
        pair_key = ""
        if totp_fingerprint:
            pair_key = "totp-use|" + str(totp_fingerprint)
            if self._hits(pair_key) >= int(pair_max_uses):
                return "totp-replayed"

        minute = int(now // 60) * 60
        day = int(now // 86400) * 86400
        minute_key = str(customer) + "|m|" + str(minute)
        day_key = str(customer) + "|d|" + str(day)
        if self._hits(minute_key) >= int(rate_limit):
            return "rate-limit"
        if self._hits(day_key) >= int(quota):
            return "quota-exceeded"

        self.sql.exec(
            "INSERT INTO nonces (nonce, expires_at) VALUES (?, ?)",
            str(nonce), now + REPLAY_TTL)
        if pair_key:
            self._increment(pair_key, now + TOTP_PAIR_TTL)
        self._increment(minute_key, float(minute + 120))
        self._increment(day_key, float(day + 172800))
        return "ok"

    async def enrol_key(self, customer, key_id, x, y, label, token_hash, now, cred_id=""):
        # Single-object storage is serial, so the token consumption and key
        # insertion cannot interleave with another enrolment of the same token.
        # Repeat the column migration here as well as in the constructor: an
        # actor whose constructor ran before the upgrade would otherwise keep
        # failing the cred_id insert until the next restart, and a consumed
        # enrolment token must never be stranded by that ordering.
        try:
            self.sql.exec(
                "ALTER TABLE approval_keys ADD COLUMN "
                "cred_id TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass  # column already present
        rows = self.sql.exec(
            "SELECT token_hash FROM enrol_tokens WHERE token_hash = ?",
            str(token_hash)).toArray()
        if len(rows) != 0:
            return "token-consumed"
        rows = self.sql.exec(
            "SELECT key_id FROM approval_keys WHERE customer = ? AND key_id = ?",
            str(customer), str(key_id)).toArray()
        if len(rows) != 0:
            return "exists"
        self.sql.exec(
            "INSERT INTO enrol_tokens (token_hash, customer, consumed_at) "
            "VALUES (?, ?, ?)", str(token_hash), str(customer), float(now))
        self.sql.exec(
            "INSERT INTO approval_keys (customer, key_id, x, y, label, "
            "enrolled_at, cred_id, revoked) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
            str(customer), str(key_id), str(x), str(y),
            str(label or "")[:80], float(now), str(cred_id or ""))
        return "ok"

    async def get_key(self, customer, key_id):
        rows = self.sql.exec(
            "SELECT x, y, revoked, cred_id FROM approval_keys "
            "WHERE customer = ? AND key_id = ?",
            str(customer), str(key_id)).toArray()
        if len(rows) == 0:
            return ""
        row = rows[0]
        return json.dumps({
            "x": str(_col(row, "x", 0)),
            "y": str(_col(row, "y", 1)),
            "revoked": int(_col(row, "revoked", 2)),
            "cred_id": str(_col(row, "cred_id", 3) or ""),
        }, separators=(",", ":"))

    async def has_approval_keys(self, customer):
        rows = self.sql.exec(
            "SELECT key_id FROM approval_keys WHERE customer = ? AND revoked = 0",
            str(customer)).toArray()
        return len(rows) != 0

    async def is_disabled(self, customer):
        rows = self.sql.exec(
            "SELECT disabled FROM customer_state WHERE customer = ?",
            str(customer)).toArray()
        if len(rows) == 0:
            return False
        return bool(int(_col(rows[0], "disabled", 0)))

    async def set_customer_disabled(self, customer, disabled):
        self.sql.exec(
            "INSERT INTO customer_state (customer, disabled) VALUES (?, ?) "
            "ON CONFLICT(customer) DO UPDATE SET disabled = excluded.disabled",
            str(customer), 1 if disabled else 0)
        return "ok"

    async def revoke_key(self, customer, key_id):
        rows = self.sql.exec(
            "SELECT key_id FROM approval_keys WHERE customer = ? AND key_id = ?",
            str(customer), str(key_id)).toArray()
        if len(rows) == 0:
            return "missing"
        self.sql.exec(
            "UPDATE approval_keys SET revoked = 1 WHERE customer = ? AND key_id = ?",
            str(customer), str(key_id))
        return "ok"

    def _push_table(self):
        self.sql.exec(
            "CREATE TABLE IF NOT EXISTS push_subs ("
            "customer TEXT NOT NULL, endpoint TEXT NOT NULL PRIMARY KEY, "
            "created_at REAL NOT NULL)")

    async def add_push_sub(self, customer, endpoint, now):
        self._push_table()
        self.sql.exec(
            "INSERT OR REPLACE INTO push_subs (customer, endpoint, created_at) "
            "VALUES (?, ?, ?)", str(customer), str(endpoint), float(now))
        return "ok"

    async def list_push_subs(self, customer):
        self._push_table()
        rows = self.sql.exec(
            "SELECT endpoint FROM push_subs WHERE customer = ?", str(customer)).toArray()
        out = []
        for row in rows:
            out.append(str(_col(row, "endpoint", 0)))
        return json.dumps(out, separators=(",", ":"))

    async def del_push_sub(self, customer, endpoint):
        self._push_table()
        self.sql.exec(
            "DELETE FROM push_subs WHERE customer = ? AND endpoint = ?",
            str(customer), str(endpoint))
        return "ok"

    async def list_keys(self, customer):
        rows = self.sql.exec(
            "SELECT key_id, label, revoked, enrolled_at, cred_id FROM approval_keys "
            "WHERE customer = ?", str(customer)).toArray()
        out = []
        for row in rows:
            out.append({
                "key_id": str(_col(row, "key_id", 0)),
                "label": str(_col(row, "label", 1)),
                "revoked": bool(int(_col(row, "revoked", 2))),
                "enrolled_at": float(_col(row, "enrolled_at", 3)),
                "cred_id": str(_col(row, "cred_id", 4) or ""),
            })
        return json.dumps(out, separators=(",", ":"))

    def _expire_pending(self, now):
        self.sql.exec(
            "UPDATE pending_requests SET status = 'expired' "
            "WHERE status = 'pending' AND expires_at < ?", float(now))

    async def create_pending(self, approval_id, customer, request_json,
                             request_hash, function, args_preview, now,
                             expires_at, cap):
        self._expire_pending(now)
        rows = self.sql.exec(
            "SELECT approval_id FROM pending_requests "
            "WHERE customer = ? AND status = 'pending'", str(customer)).toArray()
        if len(rows) >= int(cap):
            return "backlog-full"
        rows = self.sql.exec(
            "SELECT approval_id FROM pending_requests WHERE approval_id = ?",
            str(approval_id)).toArray()
        if len(rows) != 0:
            return "exists"
        self.sql.exec(
            "INSERT INTO pending_requests (approval_id, customer, request_json, "
            "request_hash, function, args_preview, submitted_at, expires_at, "
            "status, result_json, decided_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, "
            "'pending', '', 0)",
            str(approval_id), str(customer), str(request_json),
            str(request_hash), str(function), str(args_preview),
            float(now), float(expires_at))
        return "ok"

    def _prune_decisions(self, customer, now, window):
        self.sql.exec(
            "DELETE FROM decision_log WHERE customer = ? AND decided_at < ?",
            str(customer), float(now) - float(window))

    def _recent_approvals(self, customer, now, window):
        rows = self.sql.exec(
            "SELECT COUNT(*) AS n FROM decision_log WHERE customer = ? "
            "AND decided_at >= ?", str(customer),
            float(now) - float(window)).toArray()
        if len(rows) == 0:
            return 0
        return int(_col(rows[0], "n", 0))

    def _anomalies_for(self, customer, function, now, max_approvals, window):
        """Alert-only anomaly signals. Metadata only: the returned tags never
        carry arguments, payloads, or secret material."""
        out = []
        rows = self.sql.exec(
            "SELECT first_seen FROM approved_functions WHERE customer = ? "
            "AND function = ?", str(customer), str(function)).toArray()
        if len(rows) == 0:
            out.append("novel-function")
        recent = self._recent_approvals(customer, now, window)
        if recent >= int(max_approvals):
            out.append("high-velocity")
        return out

    async def list_pending(self, customer, now, max_approvals=0, window=0):
        self._expire_pending(now)
        rows = self.sql.exec(
            "SELECT approval_id, function, args_preview, submitted_at, "
            "request_hash FROM pending_requests WHERE customer = ? AND "
            "status = 'pending' ORDER BY submitted_at", str(customer)).toArray()
        annotate = int(max_approvals) > 0 and float(window) > 0
        if annotate:
            self._prune_decisions(customer, now, window)
        out = []
        for row in rows:
            item = {
                "approval_id": str(_col(row, "approval_id", 0)),
                "customer": str(customer),
                "function": str(_col(row, "function", 1)),
                "args_preview": str(_col(row, "args_preview", 2)),
                "submitted_at": float(_col(row, "submitted_at", 3)),
                "request_hash": str(_col(row, "request_hash", 4)),
            }
            if annotate:
                item["anomalies"] = self._anomalies_for(
                    customer, item["function"], now, max_approvals, window)
            out.append(item)
        return json.dumps(out, separators=(",", ":"))

    async def decide_pending(self, approval_id, customer, decision,
                             expected_hash, now, max_approvals=0, window=0):
        self._expire_pending(now)
        rows = self.sql.exec(
            "SELECT status, request_json, request_hash FROM pending_requests "
            "WHERE approval_id = ? AND customer = ?",
            str(approval_id), str(customer)).toArray()
        if len(rows) == 0:
            return json.dumps({"status": "missing"}, separators=(",", ":"))
        row = rows[0]
        status = str(_col(row, "status", 0))
        if status != "pending":
            return json.dumps({"status": status}, separators=(",", ":"))
        if str(_col(row, "request_hash", 2)) != str(expected_hash):
            # The signed approval does not match the stored request. Recording
            # nothing keeps a mismatched approval from becoming a confused-
            # deputy authorization.
            return json.dumps({"status": "hash-mismatch"}, separators=(",", ":"))
        annotate = int(max_approvals) > 0 and float(window) > 0
        anomalies = []
        function_name = ""
        try:
            function_name = str(json.loads(
                str(_col(row, "request_json", 1)) or "{}").get("function") or "")
        except Exception:
            function_name = ""
        if annotate and decision == "approve":
            self._prune_decisions(customer, now, window)
            # Detection precedes recording so the current decision is judged
            # against prior history rather than inflating it.
            anomalies = self._anomalies_for(
                customer, function_name, now, max_approvals, window)
        new_status = "approved" if decision == "approve" else "denied"
        self.sql.exec(
            "UPDATE pending_requests SET status = ?, decided_at = ? "
            "WHERE approval_id = ? AND status = 'pending'",
            new_status, float(now), str(approval_id))
        if decision == "approve":
            # Approvals are the risk-bearing decisions: they feed the velocity
            # window and mark the function as operator-vouched. Denials leave
            # the function novel so it keeps alerting if re-requested.
            self.sql.exec(
                "INSERT INTO decision_log (customer, decided_at, function) "
                "VALUES (?, ?, ?)",
                str(customer), float(now), str(function_name))
            self.sql.exec(
                "INSERT OR IGNORE INTO approved_functions "
                "(customer, function, first_seen) VALUES (?, ?, ?)",
                str(customer), str(function_name), float(now))
        out = {
            "status": "ok",
            "decision": new_status,
            "request_json": str(_col(row, "request_json", 1)),
            "request_hash": str(_col(row, "request_hash", 2)),
        }
        if annotate:
            out["anomalies"] = anomalies
        return json.dumps(out, separators=(",", ":"))

    async def complete_pending(self, approval_id, final_status, result_json):
        self.sql.exec(
            "UPDATE pending_requests SET status = ?, result_json = ? "
            "WHERE approval_id = ?",
            str(final_status), str(result_json), str(approval_id))
        return "ok"

    async def poll_pending(self, approval_id, customer, now):
        self._expire_pending(now)
        rows = self.sql.exec(
            "SELECT status, result_json FROM pending_requests "
            "WHERE approval_id = ? AND customer = ?",
            str(approval_id), str(customer)).toArray()
        if len(rows) == 0:
            return json.dumps({"status": "missing"}, separators=(",", ":"))
        row = rows[0]
        status = str(_col(row, "status", 0))
        if status in ("pending", "approved"):
            return json.dumps({"status": status}, separators=(",", ":"))
        result_json = str(_col(row, "result_json", 1))
        # Terminal states are delivered exactly once; the row is removed so a
        # later poll cannot distinguish replayed delivery attempts.
        self.sql.exec(
            "DELETE FROM pending_requests WHERE approval_id = ?",
            str(approval_id))
        return json.dumps({
            "status": status, "result_json": result_json,
        }, separators=(",", ":"))


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        try:
            self._host = ""
            try:
                self._host = str(request.headers.get("host") or "")
            except Exception:
                self._host = ""
            if request.method == "GET":
                try:
                    url_path = str(getattr(request, "url", "") or "")
                except Exception:
                    url_path = ""
                if url_path.split("?")[0].rstrip("/").endswith("/sw.js"):
                    return Response(
                        _SERVICE_WORKER_JS,
                        headers=_sec({"Content-Type": "application/javascript; charset=utf-8",
                                      "Cache-Control": "no-store"}))
                page = _APPROVAL_PAGE
                vapid_public = _env(self.env, "NIXON_VAPID_PUBLIC")
                if vapid_public:
                    page = page.replace("__VAPID_PUBLIC__", vapid_public)
                else:
                    page = page.replace("__VAPID_PUBLIC__", "")
                return Response(
                    page,
                    headers=_sec({"Content-Type": "text/html; charset=utf-8",
                                  "Cache-Control": "no-store",
                                  "Content-Security-Policy": _PAGE_CSP}))
            if request.method != "POST":
                return _response({"error": "method not allowed"})
            try:
                # json.loads preserves the Python int/float lexical distinction
                # required by protocol-v1. JavaScript request.json() would not.
                raw = await request.text()
                if len(raw) > MAX_BODY_CHARS:
                    return _response({"error": "bad request: request too large"})
                doc = json.loads(raw)
            except Exception:
                return _response({"error": "bad request: expected JSON object"})
            if not isinstance(doc, dict):
                return _response({"error": "bad request: expected JSON object"})
            if doc.get("version") != PROTOCOL_VERSION:
                return _response({"error": "unsupported remote protocol version"})
            req_type = doc.get("type")
            if req_type in (None, ""):
                return await self._handle_rpc(doc)
            if req_type == "enrol":
                return await self._handle_enrol(doc)
            if req_type == "pending":
                return await self._handle_pending(doc)
            if req_type == "approve":
                return await self._handle_approve(doc)
            if req_type == "poll":
                return await self._handle_poll(doc)
            if req_type == "subscribe":
                return await self._handle_subscribe(doc)
            if req_type == "admin":
                return await self._handle_admin(doc)
            return _response({"error": "bad request: unknown request type"})
        except Exception:
            return _response({"error": "remote service error"})

    def _rp_id(self):
        configured = _env(self.env, "NIXON_REMOTE_RP_ID")
        if configured:
            return configured.strip().lower()
        host = str(getattr(self, "_host", "") or "").strip().lower()
        # WebAuthn relying-party identifiers are bare domains: the port that
        # development servers include in the Host header is never part of one.
        if host.startswith("["):
            closing = host.find("]")
            return host[1:closing] if closing > 0 else host
        return host.split(":", 1)[0]

    def _master(self):
        master_hex = _env(self.env, "NIXON_REMOTE_MASTER_SECRET")
        if not master_hex:
            return None
        try:
            return _hex32(master_hex)
        except ValueError:
            return None

    def _anomaly_cfg(self):
        """Alert-only anomaly detection configuration. Enabled by default;
        NIXON_REMOTE_ANOMALY=0/false/off disables detection entirely."""
        raw = (_env(self.env, "NIXON_REMOTE_ANOMALY") or "1").strip().lower()
        if raw in ("0", "false", "off", "disabled"):
            return None
        return {
            "max_approvals": _positive_int_env(
                self.env, "NIXON_REMOTE_ANOMALY_MAX_APPROVALS",
                DEFAULT_ANOMALY_MAX_APPROVALS),
            "window": _positive_int_env(
                self.env, "NIXON_REMOTE_ANOMALY_WINDOW_SECONDS",
                DEFAULT_ANOMALY_WINDOW_SECONDS),
        }

    def _security_stub(self):
        security_ns = _binding(self.env, "SECURITY")
        if security_ns is None:
            return None
        try:
            return security_ns.get(security_ns.idFromName("global"))
        except Exception:
            return None

    def _policy(self):
        try:
            return {
                "rate_limit": _positive_int_env(
                    self.env, "NIXON_REMOTE_RATE_LIMIT_PER_MINUTE",
                    DEFAULT_RATE_LIMIT_PER_MINUTE),
                "quota": _positive_int_env(
                    self.env, "NIXON_REMOTE_QUOTA_PER_DAY",
                    DEFAULT_QUOTA_PER_DAY),
                "auth_failure_limit": _positive_int_env(
                    self.env, "NIXON_REMOTE_AUTH_FAILURE_LIMIT_PER_MINUTE",
                    DEFAULT_AUTH_FAILURE_LIMIT_PER_MINUTE),
                "pair_max_uses": _positive_int_env(
                    self.env, "NIXON_REMOTE_TOTP_PAIR_MAX_USES",
                    DEFAULT_TOTP_PAIR_MAX_USES),
                "approval_expiry": _positive_int_env(
                    self.env, "NIXON_REMOTE_APPROVAL_EXPIRY_SECONDS",
                    DEFAULT_APPROVAL_EXPIRY_SECONDS),
                "max_pending": _positive_int_env(
                    self.env, "NIXON_REMOTE_MAX_PENDING",
                    DEFAULT_MAX_PENDING_PER_CUSTOMER),
            }
        except ValueError:
            return None

    def _approval_mode(self):
        mode = _env(self.env, "NIXON_REMOTE_APPROVAL_MODE").strip().lower()
        return mode or "enrolled"

    async def _revoked(self, customer, stub):
        disabled_text = _env(self.env, "NIXON_REMOTE_DISABLED_CUSTOMERS")
        if customer in set(
                item.strip() for item in disabled_text.split(",") if item.strip()):
            return True
        if stub is None:
            return False
        try:
            return bool(await stub.is_disabled(customer))
        except Exception:
            # Revocation state is a fail-closed control; if it cannot be read
            # the safest answer is to treat the customer as revoked.
            return True

    async def _active_key(self, stub, customer, key_id):
        try:
            key_json = await stub.get_key(customer, key_id)
        except Exception:
            return None, "unavailable"
        if not key_json:
            return None, "missing"
        try:
            key_doc = json.loads(key_json)
        except Exception:
            return None, "unavailable"
        if int(key_doc.get("revoked", 1)):
            return None, "revoked"
        return key_doc, "active"

    async def _handle_enrol(self, doc):
        master = self._master()
        if master is None:
            return _response({"error": "remote approval enrolment is not configured"})
        customer = doc.get("customer", "")
        if not _valid_customer(customer):
            return _response({"error": "bad request: malformed customer identity"})
        token = doc.get("token", "")
        if (not isinstance(token, str) or len(token) != 64
                or any(ch not in "0123456789abcdef" for ch in token)):
            return _response({"error": "bad request: malformed enrolment token"})
        label = str(doc.get("label", "") or "")[:80]
        now = time.time()
        index_match = -1
        for index in range(ENROL_TOKEN_COUNT):
            if hmac.compare_digest(_enrol_token(master, customer, index), token):
                index_match = index
                break
        if index_match < 0:
            _audit("rejected", customer, "", "enrol-token-invalid")
            return _response({"error": "remote enrolment token invalid"})
        rp_id = self._rp_id()
        if not rp_id:
            return _response({"error": "remote approval relying party is not configured"})
        try:
            attestation_raw = _b64url_decode(doc.get("attestation", ""))
            client_raw = _b64url_decode(doc.get("clientDataJSON", ""))
        except Exception:
            _audit("rejected", customer, "", "enrol-malformed")
            return _response({"error": "bad request: malformed enrolment credential"})
        try:
            cred_id, x, y = _parse_attestation(
                attestation_raw, client_raw,
                _enrol_proof_message(customer, token), rp_id)
        except ValueError:
            _audit("rejected", customer, "", "enrol-proof-invalid")
            return _response({"error": "remote enrolment proof invalid"})
        stub = self._security_stub()
        if stub is None:
            return _response({"error": "remote replay protection is not configured"})
        if await self._revoked(customer, stub):
            _audit("revoked", customer, "", "enrol-disabled")
            return _response({"error": "remote customer access revoked"})
        key_id = _approval_key_id(x, y)
        token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        try:
            status = await stub.enrol_key(
                customer, key_id, x, y, label, token_hash, now, cred_id)
        except Exception:
            return _response({"error": "remote replay protection unavailable"})
        if status == "token-consumed":
            _audit("rejected", customer, "", "enrol-token-consumed")
            return _response({"error": "remote enrolment token already used"})
        if status != "ok":
            return _response({"error": "remote enrolment failed"})
        _audit("enrolled", customer, "", key_id)
        return _response({"enrolled": True, "key_id": key_id})

    async def _handle_pending(self, doc):
        if self._master() is None:
            return _response({"error": "remote approval is not configured"})
        customer = doc.get("customer", "")
        key_id = doc.get("key_id", "")
        if not _valid_customer(customer) or not _valid_key_id(key_id):
            return _response({"error": "bad request: malformed approval identity"})
        now = time.time()
        ts_value = doc.get("ts")
        if _fresh_ts(ts_value, now) < 0:
            return _response({"error": "remote request expired"})
        stub = self._security_stub()
        if stub is None:
            return _response({"error": "remote replay protection is not configured"})
        key_doc, state = await self._active_key(stub, customer, key_id)
        if state == "unavailable":
            return _response({"error": "remote replay protection unavailable"})
        if state != "active":
            return _response({"error": "remote approval key is not active"})
        rp_id = self._rp_id()
        if not rp_id:
            return _response({"error": "remote approval relying party is not configured"})
        message = _pending_message(customer, key_id, ts_value)
        ok, detail = await _webauthn_verify(key_doc, doc, message, rp_id)
        if not ok:
            _audit("rejected", customer, "", "pending-assertion-" + detail)
            return _response({"error": "remote approval signature invalid"})
        try:
            anomaly = self._anomaly_cfg()
            if anomaly is None:
                list_json = await stub.list_pending(customer, now)
            else:
                list_json = await stub.list_pending(
                    customer, now, anomaly["max_approvals"], anomaly["window"])
        except Exception:
            return _response({"error": "remote replay protection unavailable"})
        try:
            items = json.loads(list_json)
        except Exception:
            return _response({"error": "remote service error"})
        return _response({"pending": items})

    async def _pending_response_items(self, stub, customer):
        try:
            anomaly = self._anomaly_cfg()
            if anomaly is None:
                list_json = await stub.list_pending(customer, time.time())
            else:
                list_json = await stub.list_pending(
                    customer, time.time(),
                    anomaly["max_approvals"], anomaly["window"])
            return json.loads(list_json)
        except Exception:
            return []

    async def _handle_approve(self, doc):
        if self._master() is None:
            return _response({"error": "remote approval is not configured"})
        customer = doc.get("customer", "")
        key_id = doc.get("key_id", "")
        approval_id = doc.get("approval_id", "")
        decision = doc.get("decision", "")
        request_hash = doc.get("request_hash", "")
        if not _valid_customer(customer) or not _valid_key_id(key_id):
            return _response({"error": "bad request: malformed approval identity"})
        if not _valid_approval_id(approval_id):
            return _response({"error": "bad request: malformed approval identity"})
        if decision not in ("approve", "deny"):
            return _response({"error": "bad request: malformed approval decision"})
        if (not isinstance(request_hash, str) or len(request_hash) != 64
                or any(ch not in "0123456789abcdef" for ch in request_hash)):
            return _response({"error": "bad request: malformed approval request hash"})
        now = time.time()
        ts_value = doc.get("ts")
        if _fresh_ts(ts_value, now) < 0:
            return _response({"error": "remote request expired"})
        policy = self._policy()
        stub = self._security_stub()
        if policy is None or stub is None:
            return _response({"error": "remote replay protection is not configured"})
        key_doc, state = await self._active_key(stub, customer, key_id)
        if state == "unavailable":
            return _response({"error": "remote replay protection unavailable"})
        if state != "active":
            return _response({"error": "remote approval key is not active"})
        rp_id = self._rp_id()
        if not rp_id:
            return _response({"error": "remote approval relying party is not configured"})
        message = _approval_message(
            customer, approval_id, request_hash, decision, ts_value)
        ok, detail = await _webauthn_verify(key_doc, doc, message, rp_id)
        if not ok:
            _audit("rejected", customer, "", "approval-assertion-" + detail)
            return _response({"error": "remote approval signature invalid"})
        try:
            anomaly_cfg = self._anomaly_cfg()
            if anomaly_cfg is None:
                decided = json.loads(await stub.decide_pending(
                    approval_id, customer, decision, request_hash, now))
            else:
                decided = json.loads(await stub.decide_pending(
                    approval_id, customer, decision, request_hash, now,
                    anomaly_cfg["max_approvals"], anomaly_cfg["window"]))
        except Exception:
            return _response({"error": "remote replay protection unavailable"})
        status = decided.get("status")
        if status == "missing":
            return _response({"error": "remote approval unknown"})
        if status == "hash-mismatch":
            _audit("rejected", customer, "", "approval-hash-mismatch")
            return _response({"error": "remote approval does not match the request"})
        if status != "ok":
            return _response({"error": "remote approval already " + str(status)})
        if decision == "deny":
            function_name = ""
            try:
                function_name = str(json.loads(
                    decided.get("request_json") or "{}").get("function") or "")
            except Exception:
                function_name = ""
            _audit("approval-denied", customer, function_name)
            return _response({
                "denied": True,
                "pending": await self._pending_response_items(stub, customer),
            })

        # Approved: execute the stored request now, consuming the nonce and
        # rate/quota budget at execution time rather than submission time.
        try:
            request_doc = json.loads(decided.get("request_json") or "{}")
        except Exception:
            request_doc = {}
        function = request_doc.get("function", "")
        args = request_doc.get("args", [])
        kwargs = request_doc.get("kwargs", {})
        nonce = request_doc.get("nonce", "")
        anomalies = decided.get("anomalies") or []
        if anomalies:
            # Alert-only: detection never blocks execution, but every anomalous
            # approval leaves operator-visible metadata. Tags are fixed strings
            # and never carry arguments or secret material.
            _audit("anomaly", customer, function, ",".join(
                str(tag) for tag in anomalies))
        result_doc = None
        try:
            consume = await stub.check_and_store(
                nonce, now, customer, policy["rate_limit"], policy["quota"], "", 1)
        except Exception:
            return _response({"error": "remote replay protection unavailable"})
        if consume == "replayed":
            _audit("rejected", customer, function, "replay")
            result_doc = {"error": "remote request replayed"}
        elif consume == "rate-limit":
            _audit("rate-limited", customer, function)
            result_doc = {"error": "remote request rate limit exceeded"}
        elif consume == "quota-exceeded":
            _audit("quota-exceeded", customer, function)
            result_doc = {"error": "remote customer quota exceeded"}
        elif consume != "ok":
            return _response({"error": "remote replay protection unavailable"})
        elif function not in _FUNCTIONS:
            _audit("rejected", customer, function, "unknown-function")
            result_doc = {"error": "unknown remote function %r" % function}
        else:
            try:
                result = _FUNCTIONS[function](*args, **kwargs)
                _audit("success", customer, function)
                result_doc = {"result": result}
            except Exception as exc:
                # Exception messages can contain implementation constants or
                # argument values. Return a generic failure and keep only the
                # exception type in operator metadata.
                _audit("function-error", customer, function, type(exc).__name__)
                result_doc = {"error": "remote function failed"}
        try:
            final_json = json.dumps(result_doc, allow_nan=False, separators=(",", ":"))
        except Exception:
            final_json = json.dumps({"error": "remote function failed"})
            result_doc = {"error": "remote function failed"}
        try:
            await stub.complete_pending(approval_id, "done", final_json)
        except Exception:
            return _response({"error": "remote replay protection unavailable"})
        return _response({
            "approved": True,
            "pending": await self._pending_response_items(stub, customer),
        })

    async def _handle_subscribe(self, doc):
        """Store a push subscription for a customer. Subscriptions are
        low-value capabilities: pushes are payload-less tickles carrying no
        information beyond 'something is pending', and the endpoint URL is
        itself unguessable. Worst-case abuse is a meaningless notification."""
        if self._master() is None:
            return _response({"error": "remote approval is not configured"})
        customer = doc.get("customer", "")
        endpoint = doc.get("endpoint", "")
        if not _valid_customer(customer):
            return _response({"error": "bad request: malformed customer identity"})
        if not isinstance(endpoint, str) or not endpoint.startswith("https://") or len(endpoint) > 1024:
            return _response({"error": "bad request: malformed push endpoint"})
        stub = self._security_stub()
        if stub is None:
            return _response({"error": "remote replay protection is not configured"})
        try:
            await stub.add_push_sub(customer, endpoint, time.time())
        except Exception:
            return _response({"error": "remote replay protection unavailable"})
        return _response({"subscribed": True})

    async def _send_push_tickles(self, stub, customer):
        """Fire payload-less tickles to every push subscription of the
        customer. Push failures never affect execution: dead endpoints are
        pruned, transient ones expire with the tickle TTL."""
        private = _env(self.env, "NIXON_VAPID_PRIVATE")
        public = _env(self.env, "NIXON_VAPID_PUBLIC")
        if not private or not public:
            return
        try:
            endpoints = json.loads(await stub.list_push_subs(customer))
        except Exception:
            return
        subject = _env(self.env, "NIXON_VAPID_SUBJECT") or "mailto:ops@localhost"
        for endpoint in endpoints:
            try:
                status = _webpush_tickle(endpoint, private, public, subject)
            except Exception:
                continue
            if status in (404, 410):
                try:
                    await stub.del_push_sub(customer, endpoint)
                except Exception:
                    pass

    async def _handle_poll(self, doc):
        customer = doc.get("customer", "")
        approval_id = doc.get("approval_id", "")
        if not _valid_customer(customer) or not _valid_approval_id(approval_id):
            return _response({"error": "bad request: malformed approval identity"})
        stub = self._security_stub()
        if stub is None:
            return _response({"error": "remote replay protection is not configured"})
        try:
            out = json.loads(await stub.poll_pending(approval_id, customer, time.time()))
        except Exception:
            return _response({"error": "remote replay protection unavailable"})
        status = out.get("status")
        if status in ("pending", "approved"):
            return _response({"approval_status": status})
        if status == "done":
            try:
                return _response(json.loads(out.get("result_json") or "{}"))
            except Exception:
                return _response({"error": "remote service error"})
        if status == "denied":
            return _response({"error": "remote approval denied"})
        if status == "expired":
            return _response({"error": "remote approval expired"})
        return _response({"error": "remote approval unknown or already delivered"})

    async def _handle_admin(self, doc):
        master = self._master()
        if master is None:
            return _response({"error": "remote administration is not configured"})
        secret = doc.get("secret", "")
        if (not isinstance(secret, str)
                or not hmac.compare_digest(_admin_secret(master), secret)):
            return _response({"error": "remote administration authentication failed"})
        action = doc.get("action", "")
        customer = doc.get("customer", "")
        if not _valid_customer(customer):
            return _response({"error": "bad request: malformed customer identity"})
        stub = self._security_stub()
        if stub is None:
            return _response({"error": "remote replay protection is not configured"})
        try:
            if action == "list-keys":
                keys = json.loads(await stub.list_keys(customer))
                return _response({"keys": keys})
            if action == "revoke-key":
                key_id = doc.get("key_id", "")
                if not _valid_key_id(key_id):
                    return _response({"error": "bad request: malformed key identity"})
                status = await stub.revoke_key(customer, key_id)
                if status != "ok":
                    return _response({"error": "remote approval key not found"})
                _audit("admin-revoke-key", customer, "", key_id)
                return _response({"revoked": True})
            if action in ("disable-customer", "enable-customer"):
                await stub.set_customer_disabled(customer, action == "disable-customer")
                _audit("admin-" + action, customer)
                return _response({"disabled": action == "disable-customer"})
        except Exception:
            return _response({"error": "remote replay protection unavailable"})
        return _response({"error": "bad request: unknown administration action"})

    async def _handle_rpc(self, doc):
        customer = ""
        function = ""
        function = doc.get("function")
        args = doc.get("args", [])
        kwargs = doc.get("kwargs", {})
        nonce = doc.get("nonce")
        timestamp = doc.get("timestamp")
        signature = doc.get("signature")
        customer_value = doc.get("customer", "")
        if customer_value in (None, ""):
            customer = ""
        elif not _valid_customer(customer_value):
            return _response({"error": "bad request: malformed customer identity"})
        else:
            customer = customer_value
        if not isinstance(function, str) or not isinstance(nonce, str):
            return _response({"error": "bad request: function and nonce must be strings"})
        if len(nonce) > 256:
            return _response({"error": "bad request: nonce too long"})
        if not isinstance(args, list) or not isinstance(kwargs, dict):
            return _response({"error": "bad request: args must be an array and kwargs an object"})
        if (not isinstance(timestamp, (int, float))
                or isinstance(timestamp, bool)
                or not math.isfinite(float(timestamp))):
            return _response({"error": "bad request: timestamp must be a finite number"})

        master_present = bool(_env(self.env, "NIXON_REMOTE_MASTER_SECRET"))
        master = self._master()
        if master_present and master is None:
            # A configured but malformed master secret must not silently fall
            # through to shared-secret mode.
            return _response({"error": "remote service authentication is not configured"})
        shared_mode = False
        if master is not None:
            if not customer:
                _audit("rejected", "", function, "customer-required")
                return _response({"error": "remote customer identity is required"})
            secret, totp_secret, totp_secondary_secret = _derive_customer_credentials(
                master, customer)
        else:
            # Shared-secret mode exists only for compatibility with the first
            # Cloudflare target. Production deployments should use the master
            # secret above so each customer receives independent credentials.
            if not _truthy(_env(self.env, "NIXON_REMOTE_ALLOW_SHARED")):
                return _response({"error": "customer-bound remote credentials are not configured"})
            if not customer:
                customer = "shared"
            shared_mode = True
            secret_hex = _env(self.env, "NIXON_REMOTE_SECRET")
            totp_secret = _env(self.env, "NIXON_REMOTE_TOTP_SECRET")
            totp_secondary_secret = _env(self.env, "NIXON_REMOTE_TOTP2_SECRET")
            if not secret_hex or not totp_secret or not totp_secondary_secret:
                return _response({"error": "remote service authentication is not configured"})
            try:
                secret = _hex32(secret_hex)
            except ValueError:
                return _response({"error": "remote service authentication is not configured"})

        policy = self._policy()
        if policy is None:
            return _response({"error": "remote service usage policy is not configured"})
        rate_limit = policy["rate_limit"]
        quota = policy["quota"]
        auth_failure_limit = policy["auth_failure_limit"]
        pair_max_uses = policy["pair_max_uses"]

        try:
            same_totp_seed = hmac.compare_digest(
                _b32_bytes(totp_secret), _b32_bytes(totp_secondary_secret))
        except Exception:
            return _response({"error": "remote service authentication is not configured"})
        if same_totp_seed:
            return _response({"error": "remote service authenticators are not independent"})

        now = time.time()
        try:
            _verify_hmac(secret, function, args, kwargs, nonce,
                         float(timestamp), signature, now)
        except (ValueError, TypeError) as exc:
            detail = "expired" if "expired" in str(exc) else "signature-mismatch"
            _audit("rejected", customer, function, detail)
            return _response({"error": str(exc)})

        stub = self._security_stub()
        if stub is None:
            return _response({"error": "remote replay protection is not configured"})
        if await self._revoked(customer, stub):
            _audit("revoked", customer, function)
            return _response({"error": "remote customer access revoked"})

        approval_mode = self._approval_mode()
        if approval_mode not in ("enrolled", "required", "off"):
            return _response({"error": "remote service usage policy is not configured"})
        enrolled = False
        if not shared_mode and approval_mode != "off":
            try:
                enrolled = bool(await stub.has_approval_keys(customer))
            except Exception:
                return _response({"error": "remote replay protection unavailable"})
        use_approval = (
            not shared_mode and approval_mode != "off"
            and (enrolled or approval_mode == "required"))
        if approval_mode == "required" and not enrolled:
            return _response({"error": "remote approval enrolment is required"})

        totp_required = (
            not use_approval
            or _truthy(_env(self.env, "NIXON_REMOTE_TOTP_WITH_APPROVAL")))
        totp_fingerprint = ""
        if totp_required:
            try:
                attempt_status = await stub.begin_totp_attempt(
                    customer, now, auth_failure_limit)
            except Exception:
                return _response({"error": "remote replay protection unavailable"})
            if attempt_status == "auth-rate-limit":
                _audit("auth-rate-limited", customer, function)
                return _response({"error": "remote authentication failure limit exceeded"})
            if attempt_status != "ok":
                return _response({"error": "remote replay protection unavailable"})

            totp_valid = (
                _valid_totp(totp_secret, doc.get("totp"), now)
                and _valid_totp(totp_secondary_secret, doc.get("totp_secondary"), now))
            if totp_valid:
                try:
                    finished = await stub.finish_totp_success(customer, now)
                except Exception:
                    return _response({"error": "remote replay protection unavailable"})
                if finished != "ok":
                    return _response({"error": "remote replay protection unavailable"})
            else:
                _audit("rejected", customer, function, "totp-authentication-failed")
                return _response({"error": "remote request authentication failed"})
            totp_fingerprint = _totp_pair_fingerprint(
                secret, customer, doc.get("totp"), doc.get("totp_secondary"))

        if use_approval:
            # The request is authenticated, but execution waits for request-
            # bound phone approval. The nonce and usage budget are consumed at
            # execution time inside the approval handler, and the stored copy
            # never contains the short-lived authenticator codes.
            stored = dict(doc)
            stored.pop("totp", None)
            stored.pop("totp_secondary", None)
            try:
                request_json = json.dumps(
                    stored, allow_nan=False, separators=(",", ":"))
            except Exception:
                return _response({"error": "bad request: request is not JSON-compatible"})
            approval_id = _random_hex(32)
            try:
                created = await stub.create_pending(
                    approval_id, customer, request_json, signature, function,
                    _preview({"args": args, "kwargs": kwargs}), now,
                    now + policy["approval_expiry"], policy["max_pending"])
            except Exception:
                return _response({"error": "remote replay protection unavailable"})
            if created == "backlog-full":
                _audit("rejected", customer, function, "approval-backlog-full")
                return _response({"error": "remote approval backlog is full"})
            if created != "ok":
                return _response({"error": "remote replay protection unavailable"})
            _audit("approval-pending", customer, function)
            try:
                await self._send_push_tickles(stub, customer)
            except Exception:
                pass
            return _response({
                "approval_pending": True,
                "approval_id": approval_id,
                "approval_expires_in": policy["approval_expiry"],
            })

        try:
            status = await stub.check_and_store(
                nonce, now, customer, rate_limit, quota,
                totp_fingerprint, pair_max_uses)
        except Exception:
            return _response({"error": "remote replay protection unavailable"})
        if status == "replayed":
            _audit("rejected", customer, function, "replay")
            return _response({"error": "remote request replayed"})
        if status == "totp-replayed":
            _audit("rejected", customer, function, "totp-replay")
            return _response({"error": "remote authenticator code replayed"})
        if status == "rate-limit":
            _audit("rate-limited", customer, function)
            return _response({"error": "remote request rate limit exceeded"})
        if status == "quota-exceeded":
            _audit("quota-exceeded", customer, function)
            return _response({"error": "remote customer quota exceeded"})
        if status != "ok":
            return _response({"error": "remote replay protection unavailable"})

        if function not in _FUNCTIONS:
            _audit("rejected", customer, function, "unknown-function")
            return _response({"error": "unknown remote function %r" % function})
        try:
            result = _FUNCTIONS[function](*args, **kwargs)
            _audit("success", customer, function)
            return _response({"result": result})
        except Exception as exc:
            # Exception messages can contain implementation constants or
            # argument values. Return a generic failure and keep only the
            # exception type in operator metadata.
            _audit("function-error", customer, function, type(exc).__name__)
            return _response({"error": "remote function failed"})

'''

_WRANGLER_TEMPLATE = '''{{
  "name": "{worker_name}",
  "main": "src/entry.py",
  "compatibility_date": "{compatibility_date}",
  "compatibility_flags": ["python_workers"],
  "durable_objects": {{
    "bindings": [
      {{ "name": "SECURITY", "class_name": "SecurityRegistry" }}
    ]
  }},
  "migrations": [
    {{ "tag": "v1", "new_sqlite_classes": ["SecurityRegistry"] }}
  ]
}}
'''


_PYPROJECT_TEMPLATE = '''[project]
name = "{worker_name}"
version = "0.1.0"
description = "Generated Nixon remote-execution Python Worker"
requires-python = ">=3.13"
dependencies = []

[dependency-groups]
dev = [
    "workers-py",
    "workers-runtime-sdk",
]
'''


_GITIGNORE = '''.dev.vars
.venv-workers/
.wrangler/
python_modules/
pylock.toml
uv.lock
*provisioning*.json
# remote_impl.py contains the confidential operator-side implementations.
src/remote_impl.py
'''

_DEPLOYMENT_TEMPLATE = '''# Cloudflare remote-execution worker deployment

This directory is operator-side material. It contains the confidential
`@remote` implementations in `src/remote_impl.py`. Never ship it inside a
customer artifact or repository release. The generated `.gitignore` excludes
that file and local provisioning material as a guardrail; do not force-add
them.

## 1. Provision customer-bound credentials (recommended)

Generate the operator master secret once:

```bash
python3 -m obfuscator.cloudflare_remote provision-master master-provisioning.json
```

The master secret stays operator-side. For each customer, derive independent
credentials without exposing the master secret to that customer:

```bash
python3 -m obfuscator.cloudflare_remote provision-customer \\
  customer-acme-provisioning.json \\
  --customer-id acme \\
  --master-secret-file master-provisioning.json
```

The customer provisioning file is owner-only and contains:

- the customer-specific `hmac_secret` for `NIXON_REMOTE_SECRET`
- independent primary and secondary TOTP seeds
- otpauth URIs for enrolment

Enrol the primary seed in Google Authenticator and the secondary seed in
Microsoft Authenticator. Use manual entry or a trusted local QR tool; do not
use an untrusted online QR generator. Transfer customer material through a
secure channel. Delete or securely archive both provisioning files after use.
Do not commit them.

The customer provisioning file also contains single-use `enrolment_tokens`
for request-bound phone approval (see section 5). TOTP remains the
authentication layer for customers without an enrolled phone.

Because credentials are derived per customer, one customer's extracted HMAC or
TOTP seed does not become another customer's credential. This fixes shared
credential identity, but it does not prove physical device separation or host
integrity. Treat the customer ID as a unique customer/deployment/credential
issuance identifier (for example `acme-2026-01` rather than merely `acme`). To
rotate one customer's credentials, provision a new identifier, migrate that
customer, and add the old identifier to `NIXON_REMOTE_DISABLED_CUSTOMERS`.

## 2. Test locally (optional but recommended)

Create an owner-only `.dev.vars` in this directory:

```text
NIXON_REMOTE_MASTER_SECRET=<64-character lowercase hex master secret>
```

Optional usage-policy overrides:

```text
NIXON_REMOTE_RATE_LIMIT_PER_MINUTE=60
NIXON_REMOTE_QUOTA_PER_DAY=10000
NIXON_REMOTE_AUTH_FAILURE_LIMIT_PER_MINUTE=10
NIXON_REMOTE_TOTP_PAIR_MAX_USES=1
NIXON_REMOTE_DISABLED_CUSTOMERS=former-customer,abusive-customer
```

Then run:

```bash
uvx --from workers-py pywrangler dev
```

`.dev.vars` is ignored by the generated `.gitignore`, but it is still secret
material. Do not commit or share it.

## 3. Deploy the Worker

From this directory:

```bash
uvx --from workers-py pywrangler deploy
```

Configure the master secret:

```bash
uvx --from workers-py pywrangler secret put NIXON_REMOTE_MASTER_SECRET
```

Optional policy values can also be configured as secrets:

```bash
uvx --from workers-py pywrangler secret put NIXON_REMOTE_RATE_LIMIT_PER_MINUTE
uvx --from workers-py pywrangler secret put NIXON_REMOTE_QUOTA_PER_DAY
uvx --from workers-py pywrangler secret put NIXON_REMOTE_AUTH_FAILURE_LIMIT_PER_MINUTE
uvx --from workers-py pywrangler secret put NIXON_REMOTE_TOTP_PAIR_MAX_USES
uvx --from workers-py pywrangler secret put NIXON_REMOTE_DISABLED_CUSTOMERS
```

Defaults are 60 accepted requests per customer per minute, 10,000 accepted
requests per customer per day, and 10 HMAC-valid TOTP failures per customer
per minute. By default a successfully verified pair of TOTP codes may be
used for only one request (`NIXON_REMOTE_TOTP_PAIR_MAX_USES=1`). Raising that
value permits controlled bursts but also gives a captured code pair a larger
oracle window. Limiters use fixed windows in the strongly consistent Durable
Object. Failed authentication attempts do not consume the accepted-request
quota, but they do consume the separate authentication-failure budget.
Static revocation requires updating
`NIXON_REMOTE_DISABLED_CUSTOMERS`; it is operational revocation, not dynamic
fraud detection.

Do not place secret values in `wrangler.jsonc`; it is not a secret store.

## 4. Configure the customer artifact environment

Set `NIXON_REMOTE_URL` to the deployed Worker URL, for example:

```text
https://{worker_name}.<your-subdomain>.workers.dev/
```

Set these customer-specific values:

```text
NIXON_REMOTE_CUSTOMER_ID=acme
NIXON_REMOTE_SECRET=<derived customer hmac_secret>
```

The identity can also be supplied for one call with the reserved keyword
`_nx_customer`. TOTP codes remain per-call authentication inputs:

```python
result = pricing_engine(
    units, tier,
    _nx_totp=primary_code,
    _nx_totp_secondary=secondary_code,
)
```

The transport consumes `_nx_customer`, `_nx_totp`, and
`_nx_totp_secondary`; none is forwarded to the remote implementation or signed
as application kwargs. Interactive launchers may set
`NIXON_REMOTE_TOTP_PROMPT=1`. Controlled non-interactive tests may use
`NIXON_REMOTE_TOTP` and `NIXON_REMOTE_TOTP_SECONDARY`, but those codes expire
and are not a production user interface.

When the customer has an enrolled approval phone, the stub automatically
polls for the decision. `NIXON_REMOTE_APPROVAL_TIMEOUT` (seconds, default
150) bounds how long the client waits before failing closed; choose it above
`NIXON_REMOTE_APPROVAL_EXPIRY_SECONDS` on the server.

## Anomaly detection

The Worker tracks two alert-only approval-time signals per customer and shows
them as warning cards in the approval page before the user signs:

- `novel-function`: the function has never been approved for this customer
- `high-velocity`: approvals within a sliding window reached the threshold
  (`NIXON_REMOTE_ANOMALY_MAX_APPROVALS` per
  `NIXON_REMOTE_ANOMALY_WINDOW_SECONDS`; defaults 5 per 600)

Detection never blocks execution; it exists to warn the human approver, and
it also emits `anomaly` audit events carrying fixed tags only. It is enabled
by default; set `NIXON_REMOTE_ANOMALY=0` on the Worker to disable it.

## Legacy shared-secret compatibility mode

The first Cloudflare target used one shared HMAC secret and two shared TOTP
seeds. That mode does not identify customers and is not recommended. It is
available only by explicit operator opt-in:

```text
NIXON_REMOTE_ALLOW_SHARED=1
NIXON_REMOTE_SECRET=<shared 64-hex secret>
NIXON_REMOTE_TOTP_SECRET=<shared primary seed>
NIXON_REMOTE_TOTP2_SECRET=<shared secondary seed>
```

If `NIXON_REMOTE_MASTER_SECRET` is configured, customer-bound mode is used and
these shared values are not needed. New deployments should not enable shared
mode.

## Audit telemetry

The Worker emits metadata-only audit events to Cloudflare worker logs:
outcome, customer identity, function name, detail, and timestamp. It does not
log arguments, keyword arguments, nonces, TOTP codes, HMAC secrets, TOTP seeds,
or remote results. Implementation exception messages are not returned to the
client because they can contain confidential constants or arguments.

## 5. Request-bound phone approval (recommended)

Typed TOTP is structurally copyable: anything typed on a malware-controlled
machine can be captured, and a TOTP code is not bound to the exact request.
Phone approval removes both weaknesses. The phone holds a hardware-backed
passkey (WebAuthn) — on modern phones the private key lives in the Secure
Enclave / StrongBox and is non-exportable even to the phone's own OS. Every
check and every decision is a passkey signature requiring biometric or PIN
user verification, bound to the exact request; nothing reusable ever transits
the customer machine, and a stolen or unattended phone cannot approve.

Enrolment is per device and uses the single-use tokens in the customer
provisioning file:

1. Choose one unused token per device.
2. Send the user their enrolment link in this form:

   ```text
   https://{worker_name}.<your-subdomain>.workers.dev/#customer=<customer-id>&token=<token>&label=phone-name
   ```

   The token travels in the URL fragment, which browsers never send to the
   server; it is used only by the page running locally on the phone.
3. The user opens the link on the phone. The browser performs a WebAuthn
   enrolment ceremony: the phone creates a hardware-backed passkey with
   biometric/PIN user verification, and only the public credential registers
   with the worker. Each token enrols exactly one device and then becomes
   useless.
4. Keep the page bookmarked or pinned on the phone. When the application makes
   a remote call, the user taps "Check for pending requests" and authenticates;
   the page lists each pending request (function, customer, time, argument
   preview) and every approve/deny decision is its own passkey signature.
   Passkeys never sign silently, so there is no automatic polling: each check
   and each decision is a deliberate authenticated action.

Approval policy:

```text
NIXON_REMOTE_APPROVAL_MODE=enrolled   # default: approval once a key exists
NIXON_REMOTE_APPROVAL_MODE=required   # fail closed until every customer enrols
NIXON_REMOTE_APPROVAL_MODE=off        # typed TOTP only
NIXON_REMOTE_APPROVAL_EXPIRY_SECONDS=120
NIXON_REMOTE_MAX_PENDING=8
NIXON_REMOTE_TOTP_WITH_APPROVAL=1     # optional defense-in-depth: both layers
```

Passkey assertions are bound to the relying-party identifier the browser used
during enrolment. The worker derives it from the request Host header by
default, which is correct when the approval page is opened on the worker's
own domain. If the page is reached through a custom domain or an alias, pin
the value explicitly so enrolment and approval always agree:

```text
NIXON_REMOTE_RP_ID={worker_name}.<your-subdomain>.workers.dev
```

Customers without an enrolled key keep the dual-TOTP path. Once a key exists,
approval replaces typed codes for that customer because it is strictly
stronger: it cannot be captured in transit (no secret crosses the customer
machine), the passkey never leaves the phone's secure hardware, user
verification is enforced server-side on every signature, and each signature
is bound to the exact request hash, so approval of one call is useless for
any other. The client artifact polls automatically; the user experience is
"tap approve on the phone" with no typing.

Note: consumer passkeys deliberately do not provide meaningful attestation,
so the worker verifies signatures, user-verification flags, and relying-party
binding but cannot prove which authenticator model created a key. Synced
passkeys (iCloud/Google account sync) inherit those accounts' security;
requiring hardware security keys instead is a device-policy choice made at
enrolment time, not something the server can enforce.

Operator administration uses the derived admin secret:

```bash
python3 -m obfuscator.cloudflare_remote admin-secret \
  --master-secret-file master-provisioning.json
```

POST it as `{{"type": "admin", "version": 1, "secret": ..., "action": ...}}`
with actions `list-keys`, `revoke-key`, `disable-customer`, and
`enable-customer`. Revoke the key of a lost phone immediately; enrolment
creates new keys and never revives revoked ones. Customer disable/enable is
dynamic state in the Durable Object and takes effect at once, unlike the
static `NIXON_REMOTE_DISABLED_CUSTOMERS` list.

Residual approval limits, honestly:

- approval proves possession of the enrolled phone key, not the integrity of
  the customer machine; there is still no host attestation
- a legitimate user can still be deceived into approving a malicious request;
  the page shows exactly what is being approved so the decision is informed
- if an unused enrolment token is intercepted before use, an attacker can
  enrol their own device; treat tokens as secrets, watch for unexpected
  `enrolled` audit events, and revoke unexpected keys

## 6. Cloudflare account hygiene

- Use a scoped API token for deployment rather than the global API key:
  Workers Scripts edit permission on the single account (or single Worker)
  is sufficient.
- Prefer `pywrangler secret put` over variables in `wrangler.jsonc`.
- Restrict dashboard access with the strongest available MFA, and review
  account audit logs after provisioning changes.
- Rotate `NIXON_REMOTE_MASTER_SECRET` only as a last resort: rotation
  invalidates every derived customer credential and enrolment token at once.
  Per-customer rotation (new customer identifier) is the normal mechanism.

## Security boundary

- The implementation remains in Cloudflare; the customer artifact contains only
  the remote-call stub.
- Cloudflare and anyone with access to the Cloudflare account are inside the
  trust boundary.
- Customer-bound credentials, quotas, rate limits, revocation, and phone
  approval are complete server-side controls within their narrow scope. They
  cannot make a compromised customer machine trustworthy.
- Request-bound phone approval fixes typed-code capture and request-independ-
  ent piggybacking for enrolled customers: no typed secret exists to capture,
  and each approval authorizes exactly one displayed request. It does not
  prove physical device separation beyond key possession and cannot stop a
  user from approving a malicious request.
- Unmarked client-side plaintext remains extractable. Move every genuinely
  confidential operation behind `@remote` or accept that it is client-visible.
- Cloudflare free-tier request/CPU limits make this appropriate for lightweight
  remote functions, not heavy computation or high-frequency loops.
'''


def validate_worker_name(name: str) -> str:
    """Validate the DNS/Cloudflare-safe Worker name."""
    candidate = str(name or DEFAULT_WORKER_NAME).strip().lower()
    if not _WORKER_NAME_RE.fullmatch(candidate):
        raise ValueError(
            "Cloudflare worker name must be lowercase alphanumeric with hyphens")
    return candidate


def _validate_master_secret(master_secret: str) -> bytes:
    """Return the raw 32-byte master secret or raise for malformed input."""
    text = str(master_secret or "").strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError("master secret must be 64 lowercase hexadecimal characters")
    return bytes.fromhex(text)


def _customer_material(master: bytes, customer: str, purpose: str) -> bytes:
    material = (
        b"nixon-remote-customer-v1\x00" + purpose.encode("ascii")
        + b"\x00" + customer.encode("utf-8"))
    return hmac.new(master, material, hashlib.sha256).digest()


def derive_customer_credentials(master_secret: str, customer_id: str) -> dict:
    """Derive independent customer-bound HMAC and TOTP credentials.

    The server stores only the master secret. The customer receives the derived
    HMAC secret, and the customer-facing authenticators enrol the derived TOTP
    seeds. Compromise of one customer's derived material does not reveal the
    master secret or another customer's credentials.
    """
    customer = validate_customer_id(customer_id)
    master = _validate_master_secret(master_secret)
    primary_digest = _customer_material(master, customer, "totp-primary")
    secondary_digest = _customer_material(master, customer, "totp-secondary")
    return {
        "customer_id": customer,
        "hmac_secret": _customer_material(master, customer, "hmac").hex(),
        "totp_primary_secret": base64.b32encode(
            primary_digest[:20]).decode("ascii").rstrip("="),
        "totp_secondary_secret": base64.b32encode(
            secondary_digest[:20]).decode("ascii").rstrip("="),
    }


ENROL_TOKEN_COUNT = 8


def derive_enrol_tokens(master_secret: str, customer_id: str,
                        count: int = ENROL_TOKEN_COUNT) -> list:
    """Derive single-use phone-enrolment tokens for one customer.

    The derivation matches the generated Worker exactly. Each token can enrol
    one device; the Durable Object records consumed token hashes.
    """
    customer = validate_customer_id(customer_id)
    master = _validate_master_secret(master_secret)
    tokens = []
    for index in range(int(count)):
        material = (
            b"nixon-remote-enrol-v1\x00" + customer.encode("utf-8")
            + b"\x00" + str(index).encode("ascii"))
        tokens.append({
            "index": index,
            "token": hmac.new(master, material, hashlib.sha256).hexdigest(),
        })
    return tokens


def derive_admin_secret(master_secret: str) -> str:
    """Derive the operator administration secret matching the Worker."""
    master = _validate_master_secret(master_secret)
    return hmac.new(
        master, b"nixon-remote-admin-v1\x00", hashlib.sha256).hexdigest()


def write_master_provisioning(path: str) -> dict:
    """Write a new owner-only customer-credential master secret."""
    target = os.path.abspath(path)
    if os.path.exists(target):
        raise FileExistsError("master provisioning path already exists: %s" % target)
    doc = {
        "master_secret": os.urandom(32).hex(),
        "warning": (
            "This master secret derives every customer credential. Configure it "
            "only as the Cloudflare Worker secret NIXON_REMOTE_MASTER_SECRET, "
            "then delete or securely archive this file. Do not commit it."
        ),
    }
    parent = os.path.dirname(target) or "."
    os.makedirs(parent, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    return doc


def write_customer_provisioning(path: str, *, master_secret: str,
                                customer_id: str,
                                label_prefix: str = "nixon-remote") -> dict:
    """Write owner-only derived credentials for one customer.

    The output contains the customer HMAC secret and both authenticator
    enrolment seeds. It must be transferred to that customer through a secure
    channel and then deleted or securely archived.
    """
    target = os.path.abspath(path)
    if os.path.exists(target):
        raise FileExistsError(
            "customer provisioning path already exists: %s" % target)
    credentials = derive_customer_credentials(master_secret, customer_id)
    customer = credentials["customer_id"]
    doc = {
        "customer_id": customer,
        "hmac_secret": credentials["hmac_secret"],
        "primary": {
            "app": "Google Authenticator",
            "secret": credentials["totp_primary_secret"],
            "otpauth_uri": otpauth_uri(
                credentials["totp_primary_secret"],
                label=label_prefix + "-" + customer + "-primary"),
        },
        "secondary": {
            "app": "Microsoft Authenticator",
            "secret": credentials["totp_secondary_secret"],
            "otpauth_uri": otpauth_uri(
                credentials["totp_secondary_secret"],
                label=label_prefix + "-" + customer + "-secondary"),
        },
        "enrolment_tokens": derive_enrol_tokens(master_secret, customer),
        "enrolment_url_format": (
            "https://<worker>.<subdomain>.workers.dev/"
            "#customer=<customer-id>&token=<token>&label=<device-name>"
        ),
        "warning": (
            "Transfer this customer material over a secure channel, enrol both "
            "authenticators, then delete or securely archive this file. Do not "
            "commit it. Each enrolment token enrols exactly one phone for "
            "request-bound approval and becomes useless once consumed; deliver "
            "one token per device and never reuse them."
        ),
    }
    parent = os.path.dirname(target) or "."
    os.makedirs(parent, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    return doc


def _write_private(path: str, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def _chmod_tree_private(root: str) -> None:
    for current, directories, files in os.walk(root):
        os.chmod(current, 0o700)
        for directory in directories:
            os.chmod(os.path.join(current, directory), 0o700)
        for filename in files:
            os.chmod(os.path.join(current, filename), 0o600)


def cloudflare_worker_source(remote_functions: Iterable[ExtractedFunction]) -> str:
    """Render the self-contained Worker Python source."""
    functions = list(remote_functions)
    if not functions:
        raise ValueError("at least one @remote function is required")
    names = [func.name for func in functions]
    if len(names) != len(set(names)):
        raise ValueError("duplicate remote function names")
    function_map = "\n".join(
        "    %r: _remote_impl.%s," % (func.name, func.name) for func in functions)
    return _WORKER_TEMPLATE.replace("__FUNCTION_MAP__", function_map)


def cloudflare_remote_implementation_source(
        remote_functions: Iterable[ExtractedFunction]) -> str:
    """Render the isolated module containing operator-side implementations."""
    functions = list(remote_functions)
    if not functions:
        raise ValueError("at least one @remote function is required")
    parts = [
        '"""Operator-side @remote implementations. DO NOT SHIP THIS FILE."""\n',
        "\n",
        "def remote(fn):\n",
        "    return fn\n",
        "\n\n",
    ]
    parts.extend(func.source.rstrip() + "\n\n" for func in functions)
    return "".join(parts)


def write_cloudflare_worker(remote_functions: Iterable[ExtractedFunction],
                            path: str,
                            *, worker_name: str = DEFAULT_WORKER_NAME) -> str:
    """Write a deployable Python Worker project atomically.

    ``path`` must not already exist. Refusing to replace an existing directory
    is deliberate: the generated tree contains confidential implementation
    material and silently deleting user files would be worse than failing the
    build.
    """
    functions = list(remote_functions)
    source = cloudflare_worker_source(functions)
    compile(source, "<cloudflare-worker>", "exec")
    name = validate_worker_name(worker_name)
    target = os.path.abspath(path)
    if os.path.exists(target):
        raise FileExistsError(
            "Cloudflare worker output path already exists: %s" % target)
    parent = os.path.dirname(target) or "."
    os.makedirs(parent, exist_ok=True)
    staging = tempfile.mkdtemp(prefix=".cloudflare-worker-", dir=parent)
    try:
        os.mkdir(os.path.join(staging, "src"), 0o700)
        implementation_source = cloudflare_remote_implementation_source(functions)
        compile(implementation_source, "<cloudflare-remote-impl>", "exec")
        _write_private(os.path.join(staging, "src", "entry.py"), source)
        _write_private(
            os.path.join(staging, "src", "remote_impl.py"), implementation_source)
        _write_private(
            os.path.join(staging, "wrangler.jsonc"),
            _WRANGLER_TEMPLATE.format(
                worker_name=name, compatibility_date=COMPATIBILITY_DATE))
        _write_private(
            os.path.join(staging, "pyproject.toml"),
            _PYPROJECT_TEMPLATE.format(worker_name=name))
        _write_private(os.path.join(staging, ".gitignore"), _GITIGNORE)
        _write_private(
            os.path.join(staging, "DEPLOYMENT.md"),
            _DEPLOYMENT_TEMPLATE.format(worker_name=name))
        _write_private(os.path.join(staging, WORKER_MARKER), "generated\n")
        _chmod_tree_private(staging)
        os.replace(staging, target)
        os.chmod(target, 0o700)
        return target
    except Exception:
        # The staging tree was created by this function and is incomplete;
        # removing it cannot affect pre-existing user data because the final
        # target was never replaced.
        shutil.rmtree(staging, ignore_errors=True)
        raise


def write_totp_provisioning(path: str, *, label_prefix: str = "nixon-remote") -> dict:
    """Write two independent authenticator enrolment secrets owner-only.

    The file is sensitive enrolment material. It is intentionally written to a
    caller-selected path rather than printed to terminal logs.
    """
    target = os.path.abspath(path)
    if os.path.exists(target):
        raise FileExistsError("TOTP provisioning path already exists: %s" % target)
    primary = new_base32_secret()
    secondary = new_base32_secret()
    while secondary == primary:
        secondary = new_base32_secret()
    doc = {
        "primary": {
            "app": "Google Authenticator",
            "secret": primary,
            "otpauth_uri": otpauth_uri(
                primary, label=label_prefix + "-primary"),
        },
        "secondary": {
            "app": "Microsoft Authenticator",
            "secret": secondary,
            "otpauth_uri": otpauth_uri(
                secondary, label=label_prefix + "-secondary"),
        },
        "warning": (
            "Enrol both secrets, configure them as Cloudflare Worker secrets, "
            "then delete or securely archive this file. Do not commit it."
        ),
    }
    parent = os.path.dirname(target) or "."
    os.makedirs(parent, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    return doc


def _read_master_secret(path: str = "") -> str:
    """Read the master secret from an owner-only JSON/raw file or environment."""
    if path:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read().strip()
        if text.startswith("{"):
            try:
                text = str(json.loads(text).get("master_secret", ""))
            except (TypeError, ValueError) as exc:
                raise ValueError("master secret file is not valid JSON") from exc
    else:
        text = os.environ.get("NIXON_REMOTE_MASTER_SECRET", "").strip()
    _validate_master_secret(text)
    return text.lower()


def admin_call(worker_url, action, master_secret, customer, key_id=""):
    """Call the Worker admin endpoint. Raises RemoteError on failure."""
    import json as _json
    import urllib.request as _u

    doc = {
        "type": "admin", "version": 1, "action": action,
        "customer": customer, "secret": derive_admin_secret(master_secret),
    }
    if key_id:
        doc["key_id"] = key_id
    body = _json.dumps(doc, separators=(",", ":")).encode("utf-8")
    request = _u.Request(
        worker_url, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "User-Agent": "Mozilla/5.0"})
    try:
        with _u.urlopen(request, timeout=30.0) as response:
            out = _json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RemoteError("admin request failed: %s" % (exc,)) from exc
    if not isinstance(out, dict):
        raise RemoteError("admin response was not an object")
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Cloudflare remote-execution helper utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    provision = sub.add_parser(
        "provision", help="write owner-only shared dual-TOTP enrolment material")
    provision.add_argument("path")
    provision.add_argument("--label-prefix", default="nixon-remote")

    master = sub.add_parser(
        "provision-master",
        help="write an owner-only customer-credential master secret")
    master.add_argument("path")

    customer = sub.add_parser(
        "provision-customer",
        help="derive owner-only credentials for one customer")
    customer.add_argument("path")
    customer.add_argument("--customer-id", required=True)
    customer.add_argument(
        "--master-secret-file", default="",
        help="owner-only master JSON/raw hex file; default: NIXON_REMOTE_MASTER_SECRET")
    customer.add_argument("--label-prefix", default="nixon-remote")

    admin = sub.add_parser(
        "admin-secret",
        help="derive the operator administration secret for the Worker admin endpoint")
    admin.add_argument(
        "--master-secret-file", default="",
        help="owner-only master JSON/raw hex file; default: NIXON_REMOTE_MASTER_SECRET")

    for name, helptext in (
            ("list-keys", "list enrolled approval keys for a customer on a live Worker"),
            ("revoke-key", "revoke one enrolled approval key on a live Worker"),
            ("revoke-stale-keys",
             "revoke every enrolled key that has no passkey credential id "
             "(pre-upgrade WebCrypto enrolments, which can never sign again)")):
        cmd = sub.add_parser(name, help=helptext)
        cmd.add_argument("--worker-url", required=True,
                         help="full Worker URL, e.g. https://name.workers.dev/")
        cmd.add_argument("--customer-id", required=True)
        cmd.add_argument(
            "--master-secret-file", default="",
            help="owner-only master JSON/raw hex file; default: NIXON_REMOTE_MASTER_SECRET")
        if name == "revoke-key":
            cmd.add_argument("--key-id", required=True)

    args = parser.parse_args(argv)
    if args.command == "provision":
        write_totp_provisioning(args.path, label_prefix=args.label_prefix)
        print("wrote owner-only shared TOTP provisioning material: %s" % args.path)
        print("enrol it, configure Worker secrets, then delete or secure it")
        return 0
    if args.command == "provision-master":
        write_master_provisioning(args.path)
        print("wrote owner-only master provisioning material: %s" % args.path)
        print("configure it as NIXON_REMOTE_MASTER_SECRET, then delete or secure it")
        return 0
    if args.command == "provision-customer":
        try:
            master_secret = _read_master_secret(args.master_secret_file)
            write_customer_provisioning(
                args.path, master_secret=master_secret,
                customer_id=args.customer_id, label_prefix=args.label_prefix)
        except (OSError, ValueError, RemoteError) as exc:
            parser.error(str(exc))
        print("wrote owner-only customer provisioning material: %s" % args.path)
        print("transfer it securely, enrol both authenticators, then delete or secure it")
        return 0
    if args.command == "admin-secret":
        try:
            master_secret = _read_master_secret(args.master_secret_file)
        except (OSError, ValueError, RemoteError) as exc:
            parser.error(str(exc))
        print(derive_admin_secret(master_secret))
        return 0
    if args.command == "list-keys":
        try:
            master_secret = _read_master_secret(args.master_secret_file)
            out = admin_call(
                args.worker_url, "list-keys", master_secret, args.customer_id)
        except (OSError, ValueError, RemoteError) as exc:
            parser.error(str(exc))
        if out.get("error"):
            parser.error(out["error"])
        keys = out.get("keys", [])
        if not keys:
            print("no enrolled keys for customer %s" % args.customer_id)
            return 0
        for key in keys:
            cred = key.get("cred_id") or ""
            kind = "passkey" if cred else "pre-passkey (cannot sign)"
            print("%s  %s  label=%s  revoked=%s" % (
                key.get("key_id", "?"), kind,
                key.get("label", ""), key.get("revoked", "?")))
        return 0
    if args.command == "revoke-key":
        try:
            master_secret = _read_master_secret(args.master_secret_file)
            out = admin_call(
                args.worker_url, "revoke-key", master_secret,
                args.customer_id, key_id=args.key_id)
        except (OSError, ValueError, RemoteError) as exc:
            parser.error(str(exc))
        if out.get("revoked") is True:
            print("revoked key %s for customer %s" % (args.key_id, args.customer_id))
            return 0
        parser.error(out.get("error", "revocation failed"))
    if args.command == "revoke-stale-keys":
        try:
            master_secret = _read_master_secret(args.master_secret_file)
            keys = admin_call(
                args.worker_url, "list-keys", master_secret, args.customer_id)
        except (OSError, ValueError, RemoteError) as exc:
            parser.error(str(exc))
        if keys.get("error"):
            parser.error(keys["error"])
        revoked = 0
        for key in keys.get("keys", []):
            if key.get("cred_id") or int(key.get("revoked", 0)):
                continue
            out = admin_call(
                args.worker_url, "revoke-key", master_secret,
                args.customer_id, key_id=key["key_id"])
            if out.get("revoked") is True:
                revoked += 1
                print("revoked stale key %s" % key["key_id"])
        print("revoked %d stale key(s)" % revoked)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
