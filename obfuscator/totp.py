"""Small RFC 6238 TOTP implementation used by server-side access gates.

This module intentionally implements only the interoperable authenticator-app
profile: base32 seed, SHA-1, 30-second steps and six digits. Google
Authenticator and Microsoft Authenticator both understand that profile. TOTP
is an additional authentication gate; it is not a substitute for keeping
confidential implementations off the customer machine.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time

TOTP_STEP = 30
TOTP_DIGITS = 6
TOTP_WINDOW = 1


class TOTPError(ValueError):
    """A TOTP seed or code is malformed."""


def normalize_base32_secret(secret: str) -> str:
    """Return a canonical padded uppercase base32 seed, or raise TOTPError."""
    if not isinstance(secret, str):
        raise TOTPError("TOTP secret must be base32 text")
    compact = "".join(secret.strip().split()).replace("-", "").upper()
    if not compact:
        raise TOTPError("TOTP secret is empty")
    padded = compact + "=" * ((8 - len(compact) % 8) % 8)
    try:
        base64.b32decode(padded, casefold=False)
    except Exception as exc:
        raise TOTPError("TOTP secret is not valid base32") from exc
    return padded


def _secret_bytes(secret) -> bytes:
    if isinstance(secret, bytes):
        if not secret:
            raise TOTPError("TOTP secret is empty")
        return secret
    return base64.b32decode(normalize_base32_secret(secret), casefold=False)


def normalize_totp_code(code, digits: int = TOTP_DIGITS) -> str:
    """Normalize user-entered digits, accepting the spaces apps display."""
    if not isinstance(code, str):
        raise TOTPError("TOTP code must be text")
    compact = "".join(code.strip().split())
    if len(compact) != digits or not compact.isdigit():
        raise TOTPError("TOTP code must be %d digits" % digits)
    return compact


def totp_code(secret, *, at=None, step: int = TOTP_STEP,
              digits: int = TOTP_DIGITS) -> str:
    """Generate the RFC 6238 code for ``secret`` at ``at``.

    ``secret`` is normally a base32 authenticator seed; raw bytes are accepted
    for fixed test vectors and for deployments that store binary seeds.
    """
    if step <= 0:
        raise TOTPError("TOTP step must be positive")
    if digits <= 0 or digits > 10:
        raise TOTPError("TOTP digit count is unsupported")
    timestamp = time.time() if at is None else float(at)
    counter = int(timestamp // step)
    if counter < 0:
        raise TOTPError("TOTP timestamp must be non-negative")
    digest = hmac.new(
        _secret_bytes(secret), struct.pack(">Q", counter), hashlib.sha1
    ).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % (10 ** digits)).zfill(digits)


def verify_totp(secret, code, *, at=None, step: int = TOTP_STEP,
                digits: int = TOTP_DIGITS, window: int = TOTP_WINDOW) -> bool:
    """Verify a code with the small clock-skew window authenticators need.

    ``window=1`` accepts the previous, current and next 30-second step. This
    does not weaken the second factor into a static password: the code still
    expires quickly and the server-side replay registry prevents reuse of the
    exact signed remote request.
    """
    try:
        candidate = normalize_totp_code(code, digits=digits)
        timestamp = time.time() if at is None else float(at)
        if window < 0:
            raise TOTPError("TOTP window must be non-negative")
        for offset in range(-window, window + 1):
            when = timestamp + offset * step
            if when >= 0 and hmac.compare_digest(
                    totp_code(secret, at=when, step=step, digits=digits), candidate):
                return True
        return False
    except (TOTPError, TypeError, ValueError):
        return False


def new_base32_secret() -> str:
    """Generate a 160-bit base32 seed suitable for authenticator enrolment."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def otpauth_uri(secret: str, *, label: str, issuer: str = "Nixon Remote") -> str:
    """Build an otpauth:// URI understood by Google/Microsoft Authenticator."""
    import urllib.parse

    normalized = normalize_base32_secret(secret).rstrip("=")
    quoted_label = urllib.parse.quote(label)
    query = urllib.parse.urlencode({
        "secret": normalized,
        "issuer": issuer,
        "algorithm": "SHA1",
        "digits": str(TOTP_DIGITS),
        "period": str(TOTP_STEP),
    })
    return "otpauth://totp/%s?%s" % (quoted_label, query)
