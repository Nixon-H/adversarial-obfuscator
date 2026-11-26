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
import sqlite3
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
    """A small SQLite-backed record of token identities already presented.

    The replay check must be atomic across processes. The original JSON
    load-modify-write ledger was correct for a single caller but had a wide
    check-and-record race: concurrent presenters could all read an empty
    ledger before any wrote, and every one was accepted. SQLite's
    ``BEGIN IMMEDIATE`` transaction serializes the read and write halves of
    the check, so exactly one presenter can claim an identity inside the
    acceptance window.

    Storage failure is fail-closed: if the ledger cannot be opened or
    written, ``check_and_record`` returns False. This is deliberately
    availability-affecting; silently continuing without replay state would
    disable the control entirely.
    """

    def __init__(self, path=None, window_s=DEFAULT_WINDOW_S):
        self.path = path or os.path.join(
            tempfile.gettempdir(), ".nx-licence-seen.json")
        self.window_s = int(window_s)
        self._legacy_migrated = False

    # -- storage ---------------------------------------------------------
    def _is_sqlite_file(self):
        try:
            with open(self.path, "rb") as fh:
                return fh.read(16) == b"SQLite format 3\x00"
        except OSError:
            return False

    def _migrate_legacy_json(self):
        """Import a pre-SQLite JSON ledger once, preserving it as a backup.

        First-use is multiprocess-racy: ``sqlite3.connect`` itself creates a
        zero-byte file before the SQLite header is written. Treating that
        transient empty file as a legacy JSON ledger made concurrent creators
        rename it underneath one another (measured as intermittent
        FileNotFoundError/disk-I/O initialization failures). Only a non-empty,
        non-SQLite file is a migration candidate, and a rename lost to another
        process is benign.
        """
        if self._legacy_migrated or not os.path.exists(self.path):
            return
        try:
            if os.path.getsize(self.path) == 0:
                return
        except OSError:
            return
        if self._is_sqlite_file():
            self._legacy_migrated = True
            return
        try:
            with open(self.path, "rb") as fh:
                if fh.read(1) != b"{":
                    # Either a partially initialised SQLite file or foreign
                    # data. Neither is a legacy JSON ledger; fail closed in
                    # the latter case rather than renaming live SQLite state.
                    return
        except OSError:
            return
        try:
            with open(self.path, encoding="utf-8") as fh:
                raw = json.load(fh)
            if not isinstance(raw, dict):
                raw = {}
            data = {str(k): float(v) for k, v in raw.items()}
        except (OSError, ValueError, TypeError):
            data = {}
        backup = self.path + ".legacy-json"
        try:
            os.replace(self.path, backup)
        except FileNotFoundError:
            # Another process won the migration/create race. Its ledger is the
            # authoritative one now; the loser simply connects to it.
            return
        self._legacy_migrated = True
        if data:
            try:
                with self._connect() as conn:
                    conn.executemany(
                        "INSERT OR REPLACE INTO seen(identity, first_seen) VALUES (?, ?)",
                        sorted(data.items()))
            except sqlite3.Error:
                # The next operation will fail closed; the preserved backup is
                # intentionally left untouched for operators to inspect.
                pass

    def _connect(self):
        directory = os.path.dirname(os.path.abspath(self.path)) or "."
        os.makedirs(directory, exist_ok=True)
        if os.path.isdir(self.path):
            raise sqlite3.OperationalError("replay ledger path is a directory")
        self._migrate_legacy_json()
        conn = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS seen("
            "identity TEXT PRIMARY KEY, first_seen REAL NOT NULL)")
        return conn

    def _load(self):
        try:
            with self._connect() as conn:
                return {str(k): float(v) for k, v in
                        conn.execute("SELECT identity, first_seen FROM seen")}
        except (sqlite3.Error, OSError):
            return {}

    def _store(self, data):
        try:
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("DELETE FROM seen")
                conn.executemany(
                    "INSERT INTO seen(identity, first_seen) VALUES (?, ?)",
                    sorted((str(k), float(v)) for k, v in data.items()))
                conn.execute("COMMIT")
        except (sqlite3.Error, OSError):
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
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO seen(identity, first_seen) VALUES (?, ?)",
                    (str(identity), float(moment)))
        except (sqlite3.Error, OSError):
            pass

    def check_and_record(self, identity, now=None):
        """Atomically claim ``identity`` inside the replay window.

        Returns True only for the first presenter inside the window. Any
        storage error returns False: replay enforcement must fail closed
        rather than silently disappear on unwritable media.
        """
        moment = now if now is not None else time.time()
        cutoff = float(moment) - self.window_s
        conn = None
        try:
            conn = self._connect()
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT first_seen FROM seen WHERE identity = ?",
                (str(identity),)).fetchone()
            if row is not None and float(row[0]) >= cutoff:
                conn.execute("ROLLBACK")
                return False
            conn.execute(
                "INSERT OR REPLACE INTO seen(identity, first_seen) VALUES (?, ?)",
                (str(identity), float(moment)))
            conn.execute(
                "DELETE FROM seen WHERE first_seen < ?", (cutoff,))
            conn.execute("COMMIT")
            return True
        except (sqlite3.Error, OSError, ValueError, TypeError):
            try:
                if conn is not None:
                    conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            return False
        finally:
            try:
                if conn is not None:
                    conn.close()
            except sqlite3.Error:
                pass


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
