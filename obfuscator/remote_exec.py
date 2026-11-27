"""Level-5 split execution: keep selected functions off the client.

Every other protection in this project hides code.  This one **removes** it:
a function marked ``@remote`` is not compiled into the artefact at all.  The
artefact carries a stub that calls the operator's service, and only the
service holds the implementation.  An analyst who fully reverses the artefact
still does not have the algorithm.

Design (each point is a test):

* **The implementation never ships.**  The build replaces the function body
  with a stub; the original source goes to the operator as a separate
  artifact.  A test greps the built artefact for the implementation's
  distinctive constants and requires them to be absent.
* **Fail closed.**  If the service is unreachable, the stub raises rather
  than returning a plausible default.  A silent wrong answer is worse than a
  refusal.
* **Authenticated and replay-resistant.**  Protocol-v1 requests carry an
  HMAC over (function name, typed canonical args, typed canonical kwargs,
  nonce, binary64 timestamp); the server rejects a stale timestamp or a
  reused nonce.
* **Explicit opt-in per function.**  Nothing is remote unless marked, so the
  default build is unchanged.

Network transport is HTTPS JSON. Plain HTTP is accepted only for the
loopback reference relay, where traffic does not leave the host. The secret
comes from the environment, never from source. Customer identity and TOTP
codes are reserved transport fields, not implementation kwargs; customer-bound
services use the identity to select customer-derived credentials and enforce
accounting policy.
"""
from __future__ import annotations

import ast
import builtins
import getpass
import hashlib
import hmac
import json
import math
import os
import re
import struct
import symtable
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

#: Environment variable holding the shared HMAC secret.
SECRET_ENV = "NIXON_REMOTE_SECRET"
#: Environment variable holding the service base URL.
URL_ENV = "NIXON_REMOTE_URL"
#: Optional first authenticator code for server-side step-up authentication.
TOTP_ENV = "NIXON_REMOTE_TOTP"
#: Optional second independent authenticator code.
TOTP_SECONDARY_ENV = "NIXON_REMOTE_TOTP_SECONDARY"
#: Optional customer/deployment identity used by customer-bound services.
CUSTOMER_ENV = "NIXON_REMOTE_CUSTOMER_ID"
#: Reserved per-call keyword arguments. They are consumed by the transport
#: and are never forwarded to the remote implementation.
TOTP_KWARG = "_nx_totp"
TOTP_SECONDARY_KWARG = "_nx_totp_secondary"
#: Reserved per-call customer identity. It is consumed by the transport and
#: is never forwarded to the remote implementation.
CUSTOMER_KWARG = "_nx_customer"
#: Optional client-side ceiling (seconds) for phone-approval polling.
APPROVAL_TIMEOUT_ENV = "NIXON_REMOTE_APPROVAL_TIMEOUT"
#: Requests older than this are rejected (seconds).
MAX_SKEW = 300.0
#: Wire/signing protocol version. Version 1 uses the typed canonical form
#: below, so Python and Rust agree on integers, binary64 values and strings.
REMOTE_PROTOCOL_VERSION = 1

_CUSTOMER_ID_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,127})?$")


def validate_customer_id(value: str) -> str:
    """Validate the non-secret customer/deployment identity.

    The identity is routing/accounting metadata, not authentication by itself.
    Customer-bound services derive the request key from this value, so keeping
    it ASCII and delimiter-free prevents quota/revocation ambiguity.
    """
    if not isinstance(value, str) or not _CUSTOMER_ID_RE.fullmatch(value):
        raise RemoteError(
            "remote customer identity must be 1-128 ASCII letters, digits, "
            "underscore, dot, or hyphen and start alphanumeric")
    return value


class RemoteError(RuntimeError):
    """The remote call could not be completed.  Always fail closed."""


# ── client side ──────────────────────────────────────────────────────────

def _utf8_hex(value: str) -> str:
    return value.encode("utf-8").hex()


def _canonical(value) -> str:
    """Encode a JSON value in the language-neutral v1 canonical form.

    The representation is deliberately typed: integers and floats never
    collide, strings/object keys are UTF-8 hex (avoiding JSON escaping
    differences), and floats are their exact big-endian IEEE-754 bits.
    """
    if value is None:
        return '["n"]'
    if isinstance(value, bool):
        return '["b","1"]' if value else '["b","0"]'
    if isinstance(value, int):
        if value < -(1 << 63) or value > (1 << 64) - 1:
            raise RemoteError("remote protocol integer out of range")
        return '["i","%s"]' % value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise RemoteError("remote protocol numbers must be finite")
        return '["f","%s"]' % struct.pack(">d", value).hex()
    if isinstance(value, str):
        return '["s","%s"]' % _utf8_hex(value)
    if isinstance(value, (list, tuple)):
        return '["a",[%s]]' % ",".join(_canonical(item) for item in value)
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise RemoteError("remote protocol object keys must be strings")
        parts = []
        for key in sorted(value, key=lambda item: item.encode("utf-8")):
            parts.append("[%s,%s]" % (_canonical(key), _canonical(value[key])))
        return '["o",[%s]]' % ",".join(parts)
    raise RemoteError("remote protocol value is not JSON-compatible")


def sign_request(secret: bytes, function: str, args: list,
                 nonce: str, timestamp: float,
                 kwargs: Optional[dict] = None) -> str:
    """HMAC over the versioned canonical request.

    ``kwargs`` is part of the signed material: a request that drops or
    alters keyword arguments must fail verification.
    """
    if not isinstance(function, str) or not isinstance(nonce, str):
        raise RemoteError("remote function and nonce must be strings")
    if kwargs is not None and not isinstance(kwargs, dict):
        raise RemoteError("remote kwargs must be an object")
    try:
        timestamp = float(timestamp)
    except (TypeError, ValueError) as exc:
        raise RemoteError("remote timestamp must be a finite number") from exc
    if not math.isfinite(timestamp):
        raise RemoteError("remote timestamp must be a finite number")
    material = "\n".join([
        "nixon-remote-v1",
        _canonical(function),
        _canonical(list(args)),
        _canonical(dict(kwargs or {})),
        _canonical(nonce),
        _canonical(timestamp),
    ]).encode("utf-8")
    return hmac.new(bytes(secret), material, hashlib.sha256).hexdigest()


def verify_request(secret: bytes, function: str, args: list, nonce: str,
                   timestamp: float, signature: str,
                   kwargs: Optional[dict] = None,
                   *, now: Optional[float] = None,
                   max_skew: float = MAX_SKEW) -> None:
    """Raise RemoteError unless the request is authentic and fresh."""
    current = time.time() if now is None else float(now)
    timestamp = float(timestamp)
    if not math.isfinite(current) or not math.isfinite(timestamp):
        raise RemoteError("remote request expired")
    if abs(current - timestamp) > max_skew:
        raise RemoteError("remote request expired")
    expected = sign_request(secret, function, args, nonce, timestamp, kwargs)
    if (not isinstance(signature, str) or len(signature) != 64
            or any(ch not in "0123456789abcdef" for ch in signature)):
        raise RemoteError("remote request signature mismatch")
    if not hmac.compare_digest(expected, signature):
        raise RemoteError("remote request signature mismatch")


def _loopback_host(host: str) -> bool:
    """True only for a literal loopback address or localhost resolving there."""
    import ipaddress
    import socket

    if not host:
        return False
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        pass
    if host.lower() != "localhost":
        return False
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except OSError:
        return False
    if not infos:
        return False
    try:
        return all(ipaddress.ip_address(info[4][0]).is_loopback for info in infos)
    except ValueError:
        return False


def validate_endpoint(url: str) -> None:
    """Validate the remote endpoint before any request is emitted.

    Network endpoints must use HTTPS. Plain HTTP is accepted only for the
    loopback reference relay, where the traffic does not leave the host; this
    is what allows a production-shaped end-to-end validation without adding a
    TLS dependency to the Rust relay.
    """
    parsed = urllib.parse.urlsplit(str(url or ""))
    scheme = parsed.scheme.lower()
    if scheme == "https" and parsed.hostname:
        return
    if scheme == "http" and parsed.hostname and _loopback_host(parsed.hostname):
        return
    raise RemoteError(
        "remote endpoint must be HTTPS, or loopback HTTP for the reference relay")



def _totp_prompt_enabled() -> bool:
    return os.environ.get("NIXON_REMOTE_TOTP_PROMPT", "").strip().lower() in {
        "1", "true", "yes", "on"}


def _prompt_totp(field: str) -> str:
    """Interactively collect one fresh authenticator code when opted in."""
    if not sys.stdin.isatty():
        raise RemoteError(
            "%s is required but interactive TOTP entry is unavailable" % field)
    label = "Google Authenticator code: " if field == "totp" else (
        "Microsoft Authenticator code: ")
    return getpass.getpass(label)


def _consume_transport_fields(kwargs: dict) -> dict:
    """Remove reserved transport kwargs and return top-level request fields.

    TOTP codes and customer identity are transport/authentication inputs, not
    function arguments. They are therefore carried beside the signed body
    rather than inside ``kwargs``; including them in kwargs would both change
    the implementation signature and confuse authentication with application
    data. The optional environment fallback exists for tests and tightly
    controlled launchers; interactive applications should either pass fresh
    codes per call or opt in to prompting with ``NIXON_REMOTE_TOTP_PROMPT=1``.
    """
    fields = {}
    customer = kwargs.pop(CUSTOMER_KWARG, None)
    if customer is None:
        customer = os.environ.get(CUSTOMER_ENV, "")
    if customer not in (None, ""):
        fields["customer"] = validate_customer_id(customer)
    for kwarg, env_name, field in (
            (TOTP_KWARG, TOTP_ENV, "totp"),
            (TOTP_SECONDARY_KWARG, TOTP_SECONDARY_ENV, "totp_secondary")):
        value = kwargs.pop(kwarg, None)
        if value is None:
            value = os.environ.get(env_name, "")
        if value in (None, "") and _totp_prompt_enabled():
            value = _prompt_totp(field)
        if value in (None, ""):
            continue
        if not isinstance(value, str):
            raise RemoteError("%s must be a six-digit text code" % field)
        compact = "".join(value.strip().split())
        if len(compact) != 6 or not compact.isdigit():
            raise RemoteError("%s must be a six-digit text code" % field)
        fields[field] = compact
    return fields


# Backward-compatible private alias for tests and tightly integrated callers.
_consume_totp_fields = _consume_transport_fields


def call_remote(function: str, args: list, kwargs: Optional[dict] = None, *,
                url: Optional[str] = None,
                secret: Optional[bytes] = None,
                timeout: float = 10.0,
                opener: Optional[Callable] = None):
    """Invoke a remote function.  Fails closed on any problem.

    ``opener`` lets a test inject a transport without a live server; the
    default uses ``urllib``. Network endpoints are HTTPS-only; plain HTTP is
    accepted only when it resolves to the loopback reference relay.
    """
    url = url or os.environ.get(URL_ENV, "").strip()
    if not url:
        raise RemoteError(
            "remote function %r is not available: %s is not set"
            % (function, URL_ENV))
    validate_endpoint(url)
    raw_secret = secret
    if raw_secret is None:
        env = os.environ.get(SECRET_ENV, "").strip()
        if not env:
            raise RemoteError(
                "remote function %r is not available: %s is not set"
                % (function, SECRET_ENV))
        raw_secret = bytes.fromhex(env)
    nonce = os.urandom(16).hex()
    timestamp = time.time()
    kwargs = dict(kwargs or {})
    transport_fields = _consume_transport_fields(kwargs)
    request_doc = {
        "version": REMOTE_PROTOCOL_VERSION,
        "function": function,
        "args": list(args),
        "kwargs": kwargs,
        "nonce": nonce,
        "timestamp": timestamp,
        "signature": sign_request(raw_secret, function, list(args),
                                  nonce, timestamp, kwargs),
    }
    request_doc.update(transport_fields)
    body = json.dumps(
        request_doc, allow_nan=False, separators=(",", ":")).encode("utf-8")

    def post(payload_body):
        if opener is not None:
            return opener(url, payload_body)
        request = urllib.request.Request(
            url, data=payload_body, method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as exc:  # network, TLS, HTTP status
            raise RemoteError("remote call failed: %s" % (exc,)) from exc

    def decode(payload):
        try:
            parsed = json.loads(payload.decode("utf-8"))
        except (ValueError, AttributeError) as exc:
            raise RemoteError("remote response was not JSON") from exc
        if not isinstance(parsed, dict):
            raise RemoteError("remote response was not a JSON object")
        return parsed

    doc = decode(post(body))
    if doc.get("approval_pending") is True and isinstance(doc.get("approval_id"), str):
        # Customer-bound services may hold the request for request-bound phone
        # approval. Polling uses the unguessable approval id as a capability;
        # it authorizes collection of this request's own result only.
        approval_id = doc["approval_id"]
        customer = str(transport_fields.get("customer", "") or "")
        try:
            ceiling = float(os.environ.get(APPROVAL_TIMEOUT_ENV, "") or 150.0)
        except (TypeError, ValueError):
            ceiling = 150.0
        deadline = time.time() + max(5.0, ceiling)
        while True:
            if time.time() >= deadline:
                raise RemoteError(
                    "remote approval was not completed before the timeout")
            time.sleep(2.0)
            poll_body = json.dumps({
                "type": "poll",
                "version": REMOTE_PROTOCOL_VERSION,
                "customer": customer,
                "approval_id": approval_id,
            }, separators=(",", ":")).encode("utf-8")
            doc = decode(post(poll_body))
            if doc.get("approval_status") in ("pending", "approved"):
                continue
            break
    if doc.get("error"):
        raise RemoteError("remote function failed: %s" % (doc["error"],))
    if "result" not in doc:
        raise RemoteError("remote response missing 'result'")
    return doc["result"]


# ── server side (reference implementation) ───────────────────────────────

class RemoteRegistry:
    """Holds the implementations that never ship to the client."""

    def __init__(self, secret: bytes):
        self._secret = bytes(secret)
        self._functions: dict = {}
        self._seen_nonces: dict = {}

    def register(self, name: str, fn: Callable) -> None:
        self._functions[name] = fn

    def _prune(self, now: float) -> None:
        for nonce, stamp in list(self._seen_nonces.items()):
            if now - stamp > MAX_SKEW * 2:
                del self._seen_nonces[nonce]

    def handle(self, body: bytes, *, now: Optional[float] = None) -> bytes:
        """Process one request body; always returns a JSON response."""
        current = time.time() if now is None else float(now)
        try:
            doc = json.loads(body.decode("utf-8"))
            if not isinstance(doc, dict):
                raise RemoteError("bad request: expected a JSON object")
            if doc.get("version") != REMOTE_PROTOCOL_VERSION:
                raise RemoteError("unsupported remote protocol version")
            function = doc["function"]
            args = doc.get("args", [])
            kwargs = doc.get("kwargs", {})
            nonce = doc["nonce"]
            timestamp = doc["timestamp"]
            signature = doc["signature"]
            if not isinstance(function, str) or not isinstance(nonce, str):
                raise RemoteError("bad request: function and nonce must be strings")
            if not isinstance(args, list) or not isinstance(kwargs, dict):
                raise RemoteError("bad request: args must be an array and kwargs an object")
            if (not isinstance(timestamp, (int, float))
                    or isinstance(timestamp, bool)):
                raise RemoteError("bad request: timestamp must be a number")
            if not isinstance(signature, str):
                raise RemoteError("bad request: signature must be a string")
            verify_request(self._secret, function, args, nonce, timestamp,
                           signature, kwargs, now=current)
            self._prune(current)
            if nonce in self._seen_nonces:
                raise RemoteError("remote request replayed")
            self._seen_nonces[nonce] = current
            if function not in self._functions:
                raise RemoteError("unknown remote function %r" % (function,))
            result = self._functions[function](*args, **kwargs)
            return json.dumps({"result": result}, allow_nan=False).encode("utf-8")
        except RemoteError as exc:
            return json.dumps({"error": str(exc)}).encode("utf-8")
        except Exception as exc:
            return json.dumps({"error": "bad request: %s" % (exc,)}).encode(
                "utf-8")


# ── build side: replace a marked function with a stub ────────────────────

#: Marker decorator name that marks a function as remote.
MARKER = "remote"


def remote(func):
    """Mark a function for split execution.

    At build time the decorated function's body is replaced by a stub and the
    original is written to the operator bundle.  At run time (in a build that
    did NOT split it) the decorator is a no-op, so importing it is always
    safe.
    """
    return func


#: Self-contained client runtime embedded beside the stubs. The artefact must
#: not import this build package at run time: the operator-side package is not
#: part of the shipped trust boundary and may not exist on the customer host.
EMBEDDED_CLIENT_SOURCE = r'''
def _nx_call_remote(function, args, kwargs):
    import getpass as _nx_getpass
    import hashlib as _nx_hashlib
    import hmac as _nx_hmac
    import ipaddress as _nx_ipaddress
    import json as _nx_json
    import math as _nx_math
    import os as _nx_os
    import socket as _nx_socket
    import struct as _nx_struct
    import sys as _nx_sys
    import time as _nx_time
    import urllib.parse as _nx_uparse
    import urllib.request as _nx_ureq

    def _canon(value):
        if value is None:
            return '["n"]'
        if isinstance(value, bool):
            return '["b","1"]' if value else '["b","0"]'
        if isinstance(value, int):
            if value < -(1 << 63) or value > (1 << 64) - 1:
                raise RuntimeError("remote protocol integer out of range")
            return '["i","%s"]' % value
        if isinstance(value, float):
            if not _nx_math.isfinite(value):
                raise RuntimeError("remote protocol numbers must be finite")
            return '["f","%s"]' % _nx_struct.pack(">d", value).hex()
        if isinstance(value, str):
            return '["s","%s"]' % value.encode("utf-8").hex()
        if isinstance(value, (list, tuple)):
            return '["a",[%s]]' % ",".join(_canon(item) for item in value)
        if isinstance(value, dict):
            if not all(isinstance(key, str) for key in value):
                raise RuntimeError("remote protocol object keys must be strings")
            parts = []
            for key in sorted(value, key=lambda item: item.encode("utf-8")):
                parts.append("[%s,%s]" % (_canon(key), _canon(value[key])))
            return '["o",[%s]]' % ",".join(parts)
        raise RuntimeError("remote protocol value is not JSON-compatible")

    def _sign(secret, name, positional, named, nonce, timestamp):
        material = "\n".join([
            "nixon-remote-v1",
            _canon(name),
            _canon(list(positional)),
            _canon(dict(named or {})),
            _canon(nonce),
            _canon(timestamp),
        ]).encode("utf-8")
        return _nx_hmac.new(bytes(secret), material, _nx_hashlib.sha256).hexdigest()

    def _loopback(host):
        if not host:
            return False
        try:
            return _nx_ipaddress.ip_address(host).is_loopback
        except ValueError:
            pass
        if host.lower() != "localhost":
            return False
        try:
            infos = _nx_socket.getaddrinfo(host, None, proto=_nx_socket.IPPROTO_TCP)
        except OSError:
            return False
        if not infos:
            return False
        try:
            return all(_nx_ipaddress.ip_address(info[4][0]).is_loopback for info in infos)
        except ValueError:
            return False

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

    url = _nx_os.environ.get("NIXON_REMOTE_URL", "").strip()
    if not url:
        raise RuntimeError("remote function is not available: NIXON_REMOTE_URL is not set")
    try:
        parsed = _nx_uparse.urlsplit(url)
        host = parsed.hostname
    except ValueError as exc:
        raise RuntimeError("remote endpoint URL is malformed") from exc
    scheme = parsed.scheme.lower()
    if not ((scheme == "https" and host) or
            (scheme == "http" and host and _loopback(host))):
        raise RuntimeError(
            "remote endpoint must be HTTPS, or loopback HTTP for the reference relay")
    raw_secret = _nx_os.environ.get("NIXON_REMOTE_SECRET", "").strip()
    if not raw_secret:
        raise RuntimeError("remote function is not available: NIXON_REMOTE_SECRET is not set")
    try:
        secret = bytes.fromhex(raw_secret)
    except ValueError as exc:
        raise RuntimeError("NIXON_REMOTE_SECRET must be hex") from exc
    nonce = _nx_os.urandom(16).hex()
    timestamp = _nx_time.time()
    kwargs = dict(kwargs or {})
    totp_fields = {}
    for kwarg, env_name, field in (
            ("_nx_totp", "NIXON_REMOTE_TOTP", "totp"),
            ("_nx_totp_secondary", "NIXON_REMOTE_TOTP_SECONDARY", "totp_secondary")):
        value = kwargs.pop(kwarg, None)
        if value is None:
            value = _nx_os.environ.get(env_name, "")
        if value in (None, "") and _nx_os.environ.get(
                "NIXON_REMOTE_TOTP_PROMPT", "").strip().lower() in ("1", "true", "yes", "on"):
            if not _nx_sys.stdin.isatty():
                raise RuntimeError(field + " is required but interactive TOTP entry is unavailable")
            if field == "totp":
                value = _nx_getpass.getpass("Google Authenticator code: ")
            else:
                value = _nx_getpass.getpass("Microsoft Authenticator code: ")
        if value in (None, ""):
            continue
        if not isinstance(value, str):
            raise RuntimeError(field + " must be a six-digit text code")
        compact = "".join(value.strip().split())
        if len(compact) != 6 or not compact.isdigit():
            raise RuntimeError(field + " must be a six-digit text code")
        totp_fields[field] = compact
    customer = kwargs.pop("_nx_customer", None)
    if customer is None:
        customer = _nx_os.environ.get("NIXON_REMOTE_CUSTOMER_ID", "")
    if customer not in (None, ""):
        if not _valid_customer(customer):
            raise RuntimeError("remote customer identity is malformed")
        totp_fields["customer"] = customer
    request_doc = {
        "version": 1,
        "function": function,
        "args": list(args),
        "kwargs": kwargs,
        "nonce": nonce,
        "timestamp": timestamp,
        "signature": _sign(secret, function, list(args), kwargs, nonce, timestamp),
    }
    request_doc.update(totp_fields)
    body = _nx_json.dumps(
        request_doc, allow_nan=False, separators=(",", ":")).encode("utf-8")
    def _post(payload_body):
        request = _nx_ureq.Request(
            url, data=payload_body, method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        try:
            with _nx_ureq.urlopen(request, timeout=10.0) as response:
                return response.read()
        except Exception as exc:
            raise RuntimeError("remote call failed: %s" % (exc,)) from exc

    def _decode(payload):
        try:
            parsed = _nx_json.loads(payload.decode("utf-8"))
        except (ValueError, AttributeError) as exc:
            raise RuntimeError("remote response was not JSON") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("remote response was not a JSON object")
        return parsed

    doc = _decode(_post(body))
    if doc.get("approval_pending") is True and isinstance(doc.get("approval_id"), str):
        # The service is holding this authenticated request for request-bound
        # phone approval. The approval id is an unguessable capability that
        # authorizes collecting only this request's own result.
        approval_id = doc["approval_id"]
        try:
            ceiling = float(_nx_os.environ.get("NIXON_REMOTE_APPROVAL_TIMEOUT", "") or 150.0)
        except (TypeError, ValueError):
            ceiling = 150.0
        deadline = _nx_time.time() + max(5.0, ceiling)
        while True:
            if _nx_time.time() >= deadline:
                raise RuntimeError("remote approval was not completed before the timeout")
            _nx_time.sleep(2.0)
            poll_body = _nx_json.dumps({
                "type": "poll",
                "version": 1,
                "customer": str(customer or ""),
                "approval_id": approval_id,
            }, separators=(",", ":")).encode("utf-8")
            doc = _decode(_post(poll_body))
            if doc.get("approval_status") in ("pending", "approved"):
                continue
            break
    if doc.get("error"):
        raise RuntimeError("remote function failed: %s" % (doc["error"],))
    if "result" not in doc:
        raise RuntimeError("remote response missing 'result'")
    return doc["result"]

'''


@dataclass
class ExtractedFunction:
    name: str
    source: str
    lineno: int


def _has_remote_marker(node) -> bool:
    return any(
        (isinstance(d, ast.Name) and d.id == MARKER)
        or (isinstance(d, ast.Attribute) and d.attr == MARKER)
        for d in node.decorator_list)


def extract_remote_functions(tree: ast.AST, source: str = "") -> list:
    """Return the functions decorated with ``@remote``.

    ``source`` is the module text.  It is needed to capture the function's
    original body for the operator bundle; without it the extraction still
    works (the name and line are enough for the stub), but the bundle cannot
    be written.
    """
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _has_remote_marker(node):
            continue
        segment = ""
        if source:
            try:
                segment = ast.get_source_segment(source, node) or ""
            except (IndexError, ValueError):
                segment = ""
        found.append(ExtractedFunction(
            name=node.name,
            source=segment,
            lineno=getattr(node, "lineno", 0)))
    return found


def stub_source(func: ExtractedFunction) -> str:
    """The client-side stub: no implementation, fails closed."""
    return (
        "def %s(*args, **kwargs):\n"
        '    """Executed on the operator\'s service; not present in this build."""\n'
        "    return _nx_call_remote(%r, list(args), kwargs=kwargs)\n"
        % (func.name, func.name))


def _assert_self_contained_remote_functions(source: str, marked: list) -> None:
    """Reject remote implementations that depend on unbundled module globals.

    The operator bundle contains the marked implementations, not arbitrary
    module-level helpers/constants. Symtable analysis covers function bodies;
    the AST pass below covers defaults and annotations because those are
    evaluated in module scope when the operator bundle defines the function.
    Both passes are conservative: builtins and other bundled remote functions
    are allowed, but any other global read fails the build instead of becoming
    a server-side NameError after release.
    """
    builtin_names = set(dir(builtins))
    names = [node.name for node in marked]
    remote_names = set(names)
    root = symtable.symtable(source, "<remote-split>", "exec")
    module_names = {symbol.get_name() for symbol in root.get_symbols()}
    # A module-level assignment/import shadowing a builtin is itself an
    # unbundled global dependency, so the builtin name is not safe merely
    # because it normally exists.
    allowed_builtins = builtin_names - module_names

    def check_external_names(expr, owner: str, what: str) -> None:
        if expr is None:
            return
        for node in ast.walk(expr):
            if isinstance(node, ast.Name) and (
                    node.id not in allowed_builtins
                    and node.id not in remote_names):
                raise RemoteError(
                    "@remote function %r uses module global %r in %s, which "
                    "is not included in the operator bundle; make the function "
                    "self-contained or move the dependency inside it"
                    % (owner, node.id, what))

    for node in marked:
        arguments = (
            list(node.args.posonlyargs) + list(node.args.args)
            + list(node.args.kwonlyargs))
        if node.args.vararg:
            arguments.append(node.args.vararg)
        if node.args.kwarg:
            arguments.append(node.args.kwarg)
        for argument in arguments:
            check_external_names(
                argument.annotation, node.name, "an argument annotation")
        check_external_names(node.returns, node.name, "the return annotation")
        for default in list(node.args.defaults) + list(node.args.kw_defaults):
            check_external_names(default, node.name, "a default value")

    children = {child.get_name(): child for child in root.get_children()}

    def check_scope(scope, owner: str) -> None:
        for symbol in scope.get_symbols():
            name = symbol.get_name()
            if symbol.is_global() and (
                    name not in allowed_builtins
                    and name not in remote_names):
                raise RemoteError(
                    "@remote function %r depends on module global %r, which "
                    "is not included in the operator bundle; make the function "
                    "self-contained or move the dependency inside it"
                    % (owner, name))
        for child in scope.get_children():
            check_scope(child, owner)

    for name in names:
        scope = children.get(name)
        if scope is None:
            raise RemoteError("cannot analyse @remote function %r safely" % name)
        check_scope(scope, name)


def _marker_import_edits(tree: ast.AST) -> list:
    """Return line edits removing the no-op marker import.

    The marker import is required, not inferred from the name alone: otherwise
    an unrelated local decorator that happens to be called ``remote`` would be
    reinterpreted as a split-execution marker. Any other use of this package
    from client payload code would make the shipped artefact depend on the
    build environment, so that is refused too.
    """
    edits = []
    imports = 0
    module_name = "obfuscator.remote_exec"
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == module_name:
            marker_only = all(
                alias.name == MARKER and alias.asname in (None, MARKER)
                for alias in node.names)
            if not marker_only:
                raise RemoteError(
                    "client payload may import only the @remote marker from "
                    "obfuscator.remote_exec; the runtime is embedded by the build")
            imports += 1
            edits.append((node.lineno - 1, node.end_lineno, []))
        elif isinstance(node, ast.Import) and any(
                alias.name == module_name for alias in node.names):
            raise RemoteError(
                "use 'from obfuscator.remote_exec import remote' for the "
                "split-execution marker; module imports are not shippable")
    if not imports:
        raise RemoteError(
            "@remote split execution requires "
            "'from obfuscator.remote_exec import remote'")
    return edits


def split_module(source: str) -> tuple:
    """Replace every module-level ``@remote`` function body with a stub.

    Returns ``(client_source, [ExtractedFunction, ...])``. Unsupported shapes
    fail closed: silently leaving a decorator import, a nested implementation,
    or an async/sync mismatch in the artefact would either break standalone
    execution or ship the very implementation this pass exists to remove.
    """
    tree = ast.parse(source)
    marked = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and _has_remote_marker(node)
    ]
    if not marked:
        return source, []

    top_level = {
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    names = [node.name for node in marked]
    if len(names) != len(set(names)):
        raise RemoteError("duplicate @remote function names cannot be split safely")
    for node in marked:
        if node not in top_level:
            raise RemoteError(
                "@remote split execution supports module-level functions only")
        if isinstance(node, ast.AsyncFunctionDef):
            raise RemoteError("@remote does not support async functions yet")
        if len(node.decorator_list) != 1:
            raise RemoteError(
                "@remote cannot be combined with other decorators in a split build")
        marker = node.decorator_list[0]
        if not (isinstance(marker, ast.Name) and marker.id == MARKER):
            raise RemoteError(
                "@remote split execution requires the direct '@remote' marker")

    _assert_self_contained_remote_functions(source, marked)

    remote = []
    edits = []
    insert_at = len(source.splitlines())
    for node in marked:
        segment = ast.get_source_segment(source, node) or ""
        if not segment:
            raise RemoteError("cannot recover source for @remote function %r" % node.name)
        func = ExtractedFunction(node.name, segment, node.lineno)
        remote.append(func)
        marker = node.decorator_list[0]
        insert_at = min(insert_at, marker.lineno - 1)
        edits.append((marker.lineno - 1, marker.end_lineno, []))
        edits.append((node.lineno - 1, node.end_lineno,
                      [stub_source(func) + "\n"]))
    edits.extend(_marker_import_edits(tree))

    replacement_starts = {}
    deletion_ranges = []
    for start, end, replacement in edits:
        if replacement:
            if start in replacement_starts:
                raise RemoteError("overlapping remote split edits")
            replacement_starts[start] = (end, replacement)
        else:
            deletion_ranges.append((start, end))

    lines = source.splitlines(keepends=True)
    out = []
    index = 0
    while index < len(lines):
        if index == insert_at:
            out.append(EMBEDDED_CLIENT_SOURCE)
        if index in replacement_starts:
            end, replacement = replacement_starts[index]
            out.extend(replacement)
            index = end
            continue
        deletion_end = None
        for start, end in deletion_ranges:
            if start <= index < end:
                deletion_end = end if deletion_end is None else max(deletion_end, end)
        if deletion_end is not None:
            index = deletion_end
            continue
        out.append(lines[index])
        index += 1
    if insert_at >= len(lines):
        out.append(EMBEDDED_CLIENT_SOURCE)
    client = "".join(out)
    try:
        compile(client, "<remote-client>", "exec")
    except SyntaxError as exc:
        raise RemoteError("remote split produced invalid client source: %s" % exc) from exc
    return client, remote


def write_remote_bundle(remote: list, path: str) -> None:
    """Write the operator-side bundle (the code that must NOT ship)."""
    parts = [
        '"""Operator-side implementations.  DO NOT SHIP THIS FILE."""\n',
        "import hashlib\n",
        "import hmac\n",
        "import json\n",
        "import os\n",
        "import time\n",
        "\n",
        "from obfuscator.remote_exec import RemoteRegistry, SECRET_ENV\n",
        "\n",
    ]
    for func in remote:
        parts.append(func.source.rstrip() + "\n\n")
    parts.append(
        "def build_registry():\n"
        "    secret = bytes.fromhex(os.environ[SECRET_ENV])\n"
        "    registry = RemoteRegistry(secret)\n")
    for func in remote:
        parts.append("    registry.register(%r, %s)\n" % (func.name, func.name))
    parts.append("    return registry\n")
    # The Rust relay forwards verified requests here via
    # `python3 <bundle> --call <function>` with the request JSON on stdin.
    # This is what makes Level-5 split execution actually execute: the
    # implementation runs on the service side and only the result travels
    # back to the client.
    parts.append('''
if __name__ == "__main__":
    import sys
    _registry = build_registry()
    # Use the same verification and kwargs-aware dispatch as the reference
    # registry. The Rust relay authenticates first, but the bundle remains
    # safe when invoked directly.
    _out = _registry.handle(sys.stdin.buffer.read())
    sys.stdout.buffer.write(_out)
''')
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, temp_path = tempfile.mkstemp(
        prefix=".remote-bundle-", suffix=".py", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("".join(parts))
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
