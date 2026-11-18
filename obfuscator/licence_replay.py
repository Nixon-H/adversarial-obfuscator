"""§2 licence-token replay protection and key versioning.

Two gaps the review names explicitly:

  * **licence-token replay protection** — a captured token can currently be
    presented again indefinitely. The TTL on *artefact sidecars*
    (`scripts/artifact_sign.py`) does not cover the licence itself, and a token
    has no per-use state.
  * **key versioning** — nothing records which key generation sealed a build,
    so a rotated key cannot be distinguished from a wrong one, and a
    revoked-but-unexpired token still verifies.

Design, and why each part is where it is:

  * ``key_version`` is a signed payload field. A loader built for generation N
    refuses a token for generation M. Without the signature binding it, an
    attacker would simply edit the number -- so it goes through
    ``Licence.to_payload()`` and therefore through ``canonical()`` and the
    Ed25519 signature.
  * ``nonce`` is a signed per-token random value. It gives every issued token a
    distinct identity, so replay can be detected by *identity* rather than by
    timing.
  * Replay state lives in a small on-disk ledger (``ReplayLedger``), keyed by
    token identity. A token seen once is recorded; a second presentation inside
    the acceptance window is refused.
  * The window is bounded twice: by the token's own ``expires_at`` and by an
    optional ``max_age`` so an old token cannot be replayed after a rotation.

**Honest limit, stated up front.** A ledger on the client is only as trustworthy
as the client. An attacker who deletes the ledger file, runs in a fresh
container, or patches the check gets a replayed token accepted. This raises
replay from "free" to "requires an extra local step", which is the same kind of
improvement as the CFI chain -- not a server-side guarantee. Real replay
protection needs the issuer to track use, and that is out of scope for a
client-side artefact. The code says so; it does not pretend otherwise.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time

SCHEMA = "nx-replay/v1"

#: How long a token presentation is remembered. Long enough to cover a clock
#: skew retry, short enough that the ledger does not grow without bound.
DEFAULT_WINDOW_S = 300


def token_identity(payload: dict) -> str:
    """Stable identity for a token: its signed nonce, else its signature-free
    canonical payload. Never call this on an unverified token."""
    nonce = str(payload.get("nonce") or "")
    if nonce:
        return hashlib.sha256(b"nx-token-nonce:" + nonce.encode()).hexdigest()
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(b"nx-token-body:" + body.encode()).hexdigest()


class ReplayLedger:
    """A tiny on-disk record of token identities already presented.

    Deliberately simple: a JSON object of identity -> first-seen timestamp,
    written atomically, pruned on every write. Not a database, and not
    tamper-proof -- see the module docstring.
    """

    def __init__(self, path=None, window_s=DEFAULT_WINDOW_S):
        self.path = path or os.path.join(
            tempfile.gettempdir(), ".nx-licence-seen.json")
        self.window_s = int(window_s)

    # -- storage ---------------------------------------------------------
    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                return {str(k): float(v) for k, v in data.items()}
        except (OSError, ValueError, TypeError):
            pass
        return {}

    def _store(self, data):
        # Atomic replace so a crash mid-write cannot truncate the ledger into
        # something that silently forgets everything (which would be a replay
        # hole rather than a durability problem).
        directory = os.path.dirname(os.path.abspath(self.path)) or "."
        try:
            fd, tmp = tempfile.mkstemp(dir=directory, prefix=".nx-seen-")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, sort_keys=True)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def _prune(self, data, now):
        cutoff = now - self.window_s
        return {k: v for k, v in data.items() if v >= cutoff}

    # -- public ----------------------------------------------------------
    def seen(self, identity, now=None):
        moment = now if now is not None else time.time()
        return identity in self._prune(self._load(), moment)

    def record(self, identity, now=None):
        moment = now if now is not None else time.time()
        data = self._prune(self._load(), moment)
        data[identity] = moment
        self._store(data)

    def check_and_record(self, identity, now=None):
        """Return True if this identity is fresh; record it and return False
        if it was already seen inside the window."""
        moment = now if now is not None else time.time()
        data = self._prune(self._load(), moment)
        if identity in data:
            return False
        data[identity] = moment
        self._store(data)
        return True


def check_key_version(token_version, expected_version) -> None:
    """Raise ValueError when a token is for a different key generation.

    ``expected_version`` of None means "this build does not pin a generation",
    which is the pre-versioning behaviour and is allowed for compatibility.
    """
    if expected_version is None:
        return
    if token_version is None:
        raise ValueError(
            "licence has no key_version but this build requires generation %r"
            % (expected_version,))
    try:
        got = int(token_version)
        want = int(expected_version)
    except (TypeError, ValueError):
        raise ValueError(
            "malformed key_version: token=%r expected=%r"
            % (token_version, expected_version))
    if got != want:
        raise ValueError(
            "licence is for key generation %d but this artefact requires %d"
            % (got, want))
