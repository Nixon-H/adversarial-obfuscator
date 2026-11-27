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


def _response(doc):
    # Remote clients intentionally read the JSON error body. Non-200 statuses
    # would be collapsed by urllib into a transport error before that body is
    # available, so protocol/authentication failures remain JSON responses.
    return Response.json(doc)


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


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        customer = ""
        function = ""
        try:
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

            master_hex = _env(self.env, "NIXON_REMOTE_MASTER_SECRET")
            if master_hex:
                if not customer:
                    _audit("rejected", "", function, "customer-required")
                    return _response({"error": "remote customer identity is required"})
                try:
                    master = _hex32(master_hex)
                    secret, totp_secret, totp_secondary_secret = _derive_customer_credentials(
                        master, customer)
                except ValueError:
                    return _response({"error": "remote service authentication is not configured"})
            else:
                # Shared-secret mode exists only for compatibility with the first
                # Cloudflare target. Production deployments should use the master
                # secret above so each customer receives independent credentials.
                if not _truthy(_env(self.env, "NIXON_REMOTE_ALLOW_SHARED")):
                    return _response({"error": "customer-bound remote credentials are not configured"})
                if not customer:
                    customer = "shared"
                secret_hex = _env(self.env, "NIXON_REMOTE_SECRET")
                totp_secret = _env(self.env, "NIXON_REMOTE_TOTP_SECRET")
                totp_secondary_secret = _env(self.env, "NIXON_REMOTE_TOTP2_SECRET")
                if not secret_hex or not totp_secret or not totp_secondary_secret:
                    return _response({"error": "remote service authentication is not configured"})
                try:
                    secret = _hex32(secret_hex)
                except ValueError:
                    return _response({"error": "remote service authentication is not configured"})

            try:
                rate_limit = _positive_int_env(
                    self.env, "NIXON_REMOTE_RATE_LIMIT_PER_MINUTE",
                    DEFAULT_RATE_LIMIT_PER_MINUTE)
                quota = _positive_int_env(
                    self.env, "NIXON_REMOTE_QUOTA_PER_DAY",
                    DEFAULT_QUOTA_PER_DAY)
                auth_failure_limit = _positive_int_env(
                    self.env, "NIXON_REMOTE_AUTH_FAILURE_LIMIT_PER_MINUTE",
                    DEFAULT_AUTH_FAILURE_LIMIT_PER_MINUTE)
                pair_max_uses = _positive_int_env(
                    self.env, "NIXON_REMOTE_TOTP_PAIR_MAX_USES",
                    DEFAULT_TOTP_PAIR_MAX_USES)
            except ValueError:
                return _response({"error": "remote service usage policy is not configured"})

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

            disabled_text = _env(self.env, "NIXON_REMOTE_DISABLED_CUSTOMERS")
            disabled = set(item.strip() for item in disabled_text.split(",") if item.strip())
            if customer in disabled:
                _audit("revoked", customer, function)
                return _response({"error": "remote customer access revoked"})

            security_ns = _binding(self.env, "SECURITY")
            if security_ns is None:
                return _response({"error": "remote replay protection is not configured"})
            try:
                object_id = security_ns.idFromName("global")
                stub = security_ns.get(object_id)
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
        except Exception:
            return _response({"error": "remote service error"})
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

## Security boundary

- The implementation remains in Cloudflare; the customer artifact contains only
  the remote-call stub.
- Cloudflare and anyone with access to the Cloudflare account are inside the
  trust boundary.
- Customer-bound credentials, quotas, rate limits, and revocation are complete
  server-side abuse controls within their narrow scope. They cannot make a
  compromised customer machine trustworthy.
- TOTP is an additional server-side authentication gate. Replay of a verified
  code pair is limited server-side, but because TOTP is typed and not bound to
  the exact request, malware can still capture codes, race legitimate use, or
  piggyback on user-approved execution. Request-bound FIDO2/passkey approval would be
  stronger, but requires platform/hardware integration and is not implemented
  by this generated Worker.
- The server can require two independently derived seeds, but it cannot prove
  which authenticator apps or physical devices the user enrolled.
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
        "warning": (
            "Transfer this customer material over a secure channel, enrol both "
            "authenticators, then delete or securely archive this file. Do not "
            "commit it."
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
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
