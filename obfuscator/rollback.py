"""§9 anti-rollback: refuse to run an older, weaker build.

The review's row: *"Anti-rollback protection — prevent downgrade to vulnerable
versions."* The threat is concrete: once a protection flaw is fixed in build
N+1, an attacker who can substitute files re-installs build N, which still runs
and still has the flaw. Version numbers in a manifest do not stop that on their
own, because the attacker edits them too.

Design.

  * A monotonic ``protection_level`` is recorded IN THE SIGNED BUILD MANIFEST
    (obfuscator/build_manifest.py). It is an integer, not a marketing version,
    so ordering is unambiguous and comparison cannot be gamed by string forms
    like "2.0.0-rc1".
  * At runtime the loader compares its own level against a high-water mark kept
    beside the artefact. If the artefact's level is BELOW the mark, it refuses
    to run -- that is the downgrade case.
  * If it is above, the mark is raised.
  * The mark is HMAC'd with the build key so a hand-edited mark cannot lower it
    without also knowing the key.

**Honest limit, stated here and in the tests.** A high-water mark stored on the
client protects only against an attacker who does not delete it. Someone who
removes the file, or runs the artefact in a clean directory, gets the old build
to run again. Real anti-rollback requires the issuer (or a server) to refuse
old builds. This implementation raises a downgrade from "copy a file" to
"delete a file AND know you had to" -- useful against casual rollback, useless
against a determined local attacker. Saying that is more valuable than
pretending the mark is authoritative.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile

SCHEMA = "nx-rollback/v1"

#: Filename of the high-water mark, stored beside the artefact by default.
MARK_NAME = ".nx-rollback-mark"


def mark_path(artefact_path, override=None):
    """Where the high-water mark lives for ``artefact_path``.

    Default: beside the artefact, so a move of the artefact moves its mark.
    The result is realpath-normalised and asserted to sit in the artefact's own
    directory, so a crafted ``artefact_path`` cannot redirect the mark outside
    it. ``override`` exists for tests and for callers keeping state elsewhere.
    """
    if override:
        return os.path.realpath(os.path.abspath(override))
    base = os.path.dirname(os.path.realpath(os.path.abspath(artefact_path)))
    candidate = os.path.join(base, MARK_NAME)
    if os.path.dirname(os.path.realpath(candidate)) != base:
        raise ValueError("rollback mark path escaped the artefact directory")
    return candidate


def _mac(key: bytes, level: int, artefact_name: str) -> str:
    """Bind the mark to the level and the artefact name.

    Without the name, a mark raised for one product would block a different
    one at a lower level; without the key, the mark is editable.
    """
    body = ("%s:%d:%s" % (SCHEMA, int(level), artefact_name)).encode()
    return hmac.new(bytes(key), body, hashlib.sha256).hexdigest()


def read_mark(path, key=None, artefact_name=None):
    """Return the recorded level, or 0 when absent/unreadable/corrupt.

    Absent means "first run here", not "attack": treating a missing mark as a
    failure would brick every fresh install.

    MAC VERIFIED ON READ (review register, seventh pass -- found while
    measuring the §3 restore-state rows). This function used to return the
    stored level WITHOUT checking the MAC, so the MAC bound the mark but
    nothing ever verified it: an attacker who edited the level downward was
    obeyed, and write_mark's documented purpose ("a hand-edited mark cannot
    lower it without also knowing the key") was not implemented on the read
    path. When ``key`` and ``artefact_name`` are supplied the MAC is
    verified and a mismatch reads as 0 (corrupt), which the caller treats as
    fresh-install semantics -- never as a trusted lower level.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("schema") != SCHEMA:
            return 0
        level = int(data.get("level", 0))
        if key is not None and artefact_name is not None:
            expected = _mac(key, level, artefact_name)
            if not hmac.compare_digest(str(data.get("mac", "")), expected):
                # A forged or corrupted MAC is NOT a trustworthy level.
                return 0
        return level
    except (OSError, ValueError, TypeError):
        return 0


def write_mark(path, key, level, artefact_name):
    """Atomically record a new level, MAC'd with the build key."""
    payload = {
        "schema": SCHEMA,
        "level": int(level),
        "mac": _mac(key, level, artefact_name),
    }
    directory = os.path.dirname(os.path.abspath(path)) or "."
    try:
        fd, tmp = tempfile.mkstemp(dir=directory, prefix=".nx-rb-")
    except OSError:
        return False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, sort_keys=True)
        os.replace(tmp, path)
        return True
    except OSError:
        # A failed replace must not leave a readable stray mark candidate in
        # the artefact directory; atomic-write cleanup is part of the contract.
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return False


def check_rollback(artefact_path, level, key, override_path=None):
    """Raise RuntimeError on a downgrade; otherwise raise the mark.

    Returns a small dict describing what happened, so a caller can log it
    without re-reading the mark.
    """
    if not isinstance(level, int) or level < 0:
        raise RuntimeError("anti-rollback: level must be a non-negative int, "
                           "got %r" % (level,))
    name = os.path.basename(os.path.abspath(artefact_path))
    path = mark_path(artefact_path, override_path)
    seen = read_mark(path, key=key, artefact_name=name)
    if level < seen:
        raise RuntimeError(
            "anti-rollback: this artefact is protection level %d but level %d "
            "was already installed here; refusing to downgrade"
            % (level, seen))
    if level > seen or not os.path.exists(path):
        if not write_mark(path, key, level, name):
            raise RuntimeError(
                "anti-rollback: protection mark could not be written; "
                "refusing to run with rollback enforcement disarmed")
    return {"level": level, "previous": seen, "mark": path}
