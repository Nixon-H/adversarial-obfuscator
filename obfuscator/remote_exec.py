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
* **Authenticated and replay-resistant.**  Requests carry an HMAC over
  (function name, canonical args, nonce, timestamp); the server rejects a
  stale timestamp or a reused nonce.
* **Explicit opt-in per function.**  Nothing is remote unless marked, so the
  default build is unchanged.

Transport is HTTPS JSON; the reference server is stdlib-only so it can run
anywhere.  The secret comes from the environment, never from source.
"""
from __future__ import annotations

import ast
import hashlib
import hmac
import json
import os
import time
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

#: Environment variable holding the shared HMAC secret.
SECRET_ENV = "NIXON_REMOTE_SECRET"
#: Environment variable holding the service base URL.
URL_ENV = "NIXON_REMOTE_URL"
#: Requests older than this are rejected (seconds).
MAX_SKEW = 300.0


class RemoteError(RuntimeError):
    """The remote call could not be completed.  Always fail closed."""


# ── client side ──────────────────────────────────────────────────────────

def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      default=repr)


def sign_request(secret: bytes, function: str, args: list,
                 nonce: str, timestamp: float) -> str:
    """HMAC over the canonical request.  Deterministic and testable."""
    material = "\n".join([
        str(function),
        _canonical(list(args)),
        str(nonce),
        repr(float(timestamp)),
    ]).encode("utf-8")
    return hmac.new(bytes(secret), material, hashlib.sha256).hexdigest()


def verify_request(secret: bytes, function: str, args: list, nonce: str,
                   timestamp: float, signature: str,
                   *, now: Optional[float] = None,
                   max_skew: float = MAX_SKEW) -> None:
    """Raise RemoteError unless the request is authentic and fresh."""
    current = time.time() if now is None else float(now)
    if abs(current - float(timestamp)) > max_skew:
        raise RemoteError("remote request expired")
    expected = sign_request(secret, function, args, nonce, timestamp)
    if not hmac.compare_digest(expected, str(signature)):
        raise RemoteError("remote request signature mismatch")


def call_remote(function: str, args: list, *,
                url: Optional[str] = None,
                secret: Optional[bytes] = None,
                timeout: float = 10.0,
                opener: Optional[Callable] = None):
    """Invoke a remote function.  Fails closed on any problem.

    ``opener`` lets a test inject a transport without a live server; the
    default uses ``urllib`` over HTTPS only.
    """
    url = url or os.environ.get(URL_ENV, "").strip()
    if not url:
        raise RemoteError(
            "remote function %r is not available: %s is not set"
            % (function, URL_ENV))
    if not url.lower().startswith("https://"):
        raise RemoteError("remote endpoint must be HTTPS")
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
    body = json.dumps({
        "function": function,
        "args": list(args),
        "nonce": nonce,
        "timestamp": timestamp,
        "signature": sign_request(raw_secret, function, list(args),
                                  nonce, timestamp),
    }).encode("utf-8")

    if opener is not None:
        payload = opener(url, body)
    else:
        request = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read()
        except Exception as exc:  # network, TLS, HTTP status
            raise RemoteError("remote call failed: %s" % (exc,)) from exc

    try:
        doc = json.loads(payload.decode("utf-8"))
    except (ValueError, AttributeError) as exc:
        raise RemoteError("remote response was not JSON") from exc
    if not isinstance(doc, dict) or "result" not in doc:
        raise RemoteError("remote response missing 'result'")
    if doc.get("error"):
        raise RemoteError("remote function failed: %s" % (doc["error"],))
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
            function = doc["function"]
            args = doc.get("args", [])
            nonce = str(doc["nonce"])
            timestamp = float(doc["timestamp"])
            signature = str(doc["signature"])
            verify_request(self._secret, function, args, nonce, timestamp,
                           signature, now=current)
            self._prune(current)
            if nonce in self._seen_nonces:
                raise RemoteError("remote request replayed")
            self._seen_nonces[nonce] = current
            if function not in self._functions:
                raise RemoteError("unknown remote function %r" % (function,))
            result = self._functions[function](*args)
            return json.dumps({"result": result}).encode("utf-8")
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


@dataclass
class ExtractedFunction:
    name: str
    source: str
    lineno: int


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
        if not any(
                (isinstance(d, ast.Name) and d.id == MARKER)
                or (isinstance(d, ast.Attribute) and d.attr == MARKER)
                for d in node.decorator_list):
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
        "    from obfuscator.remote_exec import call_remote\n"
        "    return call_remote(%r, list(args))\n"
        % (func.name, func.name))


def split_module(source: str) -> tuple:
    """Replace every ``@remote`` function body with a stub.

    Returns ``(client_source, [ExtractedFunction, ...])``.  The extracted
    list is what the operator deploys; it must never be shipped.
    """
    tree = ast.parse(source)
    remote = extract_remote_functions(tree, source)
    if not remote:
        return source, []

    lines = source.splitlines(keepends=True)
    # Replace from the bottom up so earlier line numbers stay valid.
    for func in sorted(remote, key=lambda f: f.lineno, reverse=True):
        node = next(n for n in ast.walk(tree)
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and n.name == func.name
                    and getattr(n, "lineno", 0) == func.lineno)
        start = node.lineno - 1
        end = getattr(node, "end_lineno", node.lineno)
        lines[start:end] = [stub_source(func) + "\n"]
    return "".join(lines), remote


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
    _req = json.loads(sys.stdin.read() or "{}")
    _registry = build_registry()
    _fn = _req.get("function", "")
    _args = _req.get("args", [])
    try:
        _impl = _registry._functions.get(_fn)
        if _impl is None:
            _out = {"error": "unknown remote function %r" % (_fn,)}
        else:
            _out = {"result": _impl(*_args)}
    except Exception as _exc:
        _out = {"error": str(_exc)}
    sys.stdout.write(json.dumps(_out))
''')
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("".join(parts))
