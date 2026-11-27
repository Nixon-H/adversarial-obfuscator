"""Cloudflare Workers deployment artifacts for server-side split execution.

The Rust reference relay is the self-hosted deployment target. This module is
the serverless target: it generates a self-contained Python Worker that keeps
``@remote`` implementations in Cloudflare, verifies the existing protocol-v1
HMAC envelope, requires two independent authenticator TOTP codes, and uses a
SQLite-backed Durable Object for strongly consistent nonce replay rejection.

The generator deliberately does not embed any secret. The HMAC secret and the
two TOTP seeds are deployed as Cloudflare Worker secrets.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
from typing import Iterable

from obfuscator.remote_exec import ExtractedFunction
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
PROTOCOL_VERSION = 1
MAX_BODY_CHARS = 1000000


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


def _response(doc):
    # Remote clients intentionally read the JSON error body. Non-200 statuses
    # would be collapsed by urllib into a transport error before that body is
    # available, so protocol/authentication failures remain JSON responses.
    return Response.json(doc)


class ReplayRegistry(DurableObject):
    """Strongly consistent nonce registry backed by the object's SQLite store."""

    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        self.sql = ctx.storage.sql
        self.sql.exec(
            "CREATE TABLE IF NOT EXISTS nonces ("
            "nonce TEXT PRIMARY KEY, expires_at REAL NOT NULL)")

    async def check_and_store(self, nonce, now):
        # These operations are synchronous, so no other request can interleave
        # between the lookup and insert. Expired rows are pruned opportunistically.
        self.sql.exec("DELETE FROM nonces WHERE expires_at < ?", float(now))
        rows = self.sql.exec(
            "SELECT nonce FROM nonces WHERE nonce = ?", str(nonce)).toArray()
        if len(rows) != 0:
            return False
        self.sql.exec(
            "INSERT INTO nonces (nonce, expires_at) VALUES (?, ?)",
            str(nonce), float(now) + REPLAY_TTL)
        return True


class Default(WorkerEntrypoint):
    async def fetch(self, request):
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

            secret_hex = _env(self.env, "NIXON_REMOTE_SECRET")
            totp_secret = _env(self.env, "NIXON_REMOTE_TOTP_SECRET")
            totp_secondary_secret = _env(self.env, "NIXON_REMOTE_TOTP2_SECRET")
            if not secret_hex or not totp_secret or not totp_secondary_secret:
                return _response({"error": "remote service authentication is not configured"})
            try:
                secret = bytes.fromhex(secret_hex)
            except ValueError:
                return _response({"error": "remote service authentication is not configured"})
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
                return _response({"error": str(exc)})

            if (not _valid_totp(totp_secret, doc.get("totp"), now)
                    or not _valid_totp(
                        totp_secondary_secret, doc.get("totp_secondary"), now)):
                return _response({"error": "remote request authentication failed"})

            replay_ns = _binding(self.env, "REPLAY")
            if replay_ns is None:
                return _response({"error": "remote replay protection is not configured"})
            try:
                object_id = replay_ns.idFromName("global")
                stub = replay_ns.get(object_id)
                accepted = await stub.check_and_store(nonce, now)
            except Exception:
                return _response({"error": "remote replay protection unavailable"})
            if accepted is not True:
                return _response({"error": "remote request replayed"})

            if function not in _FUNCTIONS:
                return _response({"error": "unknown remote function %r" % function})
            try:
                result = _FUNCTIONS[function](*args, **kwargs)
                return _response({"result": result})
            except Exception as exc:
                return _response({"error": "remote function failed: %s" % exc})
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
      {{ "name": "REPLAY", "class_name": "ReplayRegistry" }}
    ]
  }},
  "migrations": [
    {{ "tag": "v1", "new_sqlite_classes": ["ReplayRegistry"] }}
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
totp-provisioning.json
# remote_impl.py contains the confidential operator-side implementations.
src/remote_impl.py
'''

_DEPLOYMENT_TEMPLATE = '''# Cloudflare remote-execution worker deployment

This directory is operator-side material. It contains the confidential
`@remote` implementations in `src/remote_impl.py`. Never ship it inside a
customer artifact or repository release. The generated `.gitignore` excludes
that file and local secret material as a guardrail; do not force-add them.

## 1. Provision two independent authenticators

Generate enrolment material once from the repository checkout (or another
environment where the `obfuscator` package is installed):

```bash
python3 -m obfuscator.cloudflare_remote provision totp-provisioning.json
```

Open the resulting owner-only JSON file and enrol:

- `primary` in Google Authenticator
- `secondary` in Microsoft Authenticator

Use manual entry or convert the otpauth URI to a QR code with a trusted local
tool. Do not use an untrusted online QR generator. Delete or securely archive
the provisioning file after enrolment. Do not commit it.

The two seeds must be independent. The worker rejects requests if both
server-side secrets are identical.

## 2. Test locally (optional but recommended)

Create an owner-only `.dev.vars` in this directory:

```text
NIXON_REMOTE_SECRET=<64-character lowercase hex secret>
NIXON_REMOTE_TOTP_SECRET=<primary base32 seed>
NIXON_REMOTE_TOTP2_SECRET=<secondary base32 seed>
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

Then configure three Worker secrets:

```bash
uvx --from workers-py pywrangler secret put NIXON_REMOTE_SECRET
uvx --from workers-py pywrangler secret put NIXON_REMOTE_TOTP_SECRET
uvx --from workers-py pywrangler secret put NIXON_REMOTE_TOTP2_SECRET
```

- `NIXON_REMOTE_SECRET`: the same 64-character lowercase hex secret used by
  the customer artifact environment.
- `NIXON_REMOTE_TOTP_SECRET`: the base32 `primary` seed.
- `NIXON_REMOTE_TOTP2_SECRET`: the base32 `secondary` seed.

Do not place these values in `wrangler.jsonc`; it is not a secret store.

## 4. Configure the customer artifact environment

Set `NIXON_REMOTE_URL` to the deployed Worker URL, for example:

```text
https://{worker_name}.<your-subdomain>.workers.dev/
```

Set `NIXON_REMOTE_SECRET` to the same 64-character hex value configured in the
Worker.

TOTP codes are per-call authentication inputs. A fresh code can be supplied by
the protected application through the reserved keyword arguments:

```python
result = pricing_engine(
    units, tier,
    _nx_totp=primary_code,
    _nx_totp_secondary=secondary_code,
)
```

The transport consumes those reserved keys and does not forward them to the
remote implementation. Interactive launchers may instead set
`NIXON_REMOTE_TOTP_PROMPT=1`, which prompts for the Google Authenticator and
Microsoft Authenticator codes when per-call codes were not supplied. For
controlled non-interactive tests only, the client also reads
`NIXON_REMOTE_TOTP` and `NIXON_REMOTE_TOTP_SECONDARY`; because they expire
after roughly 30 seconds, those environment variables are not a general user
interface.

## Security boundary

- The implementation remains in Cloudflare; the customer artifact contains only
  the remote-call stub.
- Cloudflare and anyone with access to the Cloudflare account are inside the
  trust boundary.
- TOTP is an additional server-side authentication gate. It does not prove the
  customer machine is uncompromised and does not protect plaintext that is
  client-side. The server can require two independent seeds, but it cannot
  prove which authenticator apps or devices the user actually enrolled.
- A customer-machine attacker who possesses the HMAC secret can still attempt
  oracle calls, but now also needs fresh codes from both authenticators within
  their short validity windows.
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Cloudflare remote-execution helper utilities")
    sub = parser.add_subparsers(dest="command", required=True)
    provision = sub.add_parser(
        "provision", help="write owner-only dual-TOTP enrolment material")
    provision.add_argument("path")
    provision.add_argument("--label-prefix", default="nixon-remote")
    args = parser.parse_args(argv)
    if args.command == "provision":
        write_totp_provisioning(args.path, label_prefix=args.label_prefix)
        print("wrote owner-only TOTP provisioning material: %s" % args.path)
        print("enrol it, configure Worker secrets, then delete or secure it")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
