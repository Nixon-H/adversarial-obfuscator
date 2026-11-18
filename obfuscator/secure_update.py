"""§9 secure update: an update the client can refuse, not merely receive.

A "secure update" that only checks a signature is a secure *download*. The
attacks that matter against an updater are different:

  * **Downgrade** -- serve the previous, vulnerable release. Its signature is
    genuine, so a signature check passes. Defeated here with a monotonic
    ``sequence`` the client persists and a signed ``minimum_sequence`` the
    publisher raises after a bad release; a client refuses anything below
    either.
  * **Freeze** -- keep the client on an old but validly-signed release forever.
    Not fully solvable without a trusted clock, so this module does not claim
    it. It records ``published_at`` and lets the verifier supply a maximum age;
    a client with no clock cannot use that and the limitation is stated.
  * **Cross-artefact transplant** -- swap in a signed update for another
    product/channel. Defeated by signing ``artefact`` (name), ``channel`` and
    ``version`` together.
  * **Keystore rollback** -- serve an update signed by a retired key. The
    ``key_id`` is inside the signed payload and compared to the caller's
    accepted set.
  * **Partial write** -- an interrupted update leaving a half-written binary.
    :func:`verify_update` takes the bytes and a precomputed digest, so a caller
    can verify before moving into place, and :func:`stage_update` writes to a
    temporary name in the same directory and renames, so the destination is
    either the old file or the complete new one.

What this module does NOT do: it does not fetch anything, and it does not run
anything. Fetching and swapping are policy the operator owns (and an updater
that downloads and executes automatically is a remote-code-execution surface by
design). Everything here is decision logic over bytes the caller already has,
which is what makes it testable without a network or an update server.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time

SCHEMA = "nx-update-manifest/v1"

#: How long a client will accept an update whose ``published_at`` is in the
#: future. A clock skewed forward must not let a publisher schedule an update
#: the client will later be forced to accept.
MAX_FUTURE_SKEW_SECONDS = 900


class UpdateError(Exception):
    """An update that must not be applied."""


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      default=str).encode("utf-8")


def make_manifest(artefact_name, artefact_bytes, version, sequence, *,
                  channel="stable", product="", minimum_sequence=0,
                  published_at=None, key_id="", notes="", extra=None):
    """Build an unsigned update manifest describing one artefact.

    ``sequence`` is monotonic across releases and is what stops a downgrade;
    ``minimum_sequence`` is the publisher's own floor ("never install anything
    below this again"), which is how a bad release is retired without
    invalidating the keys.
    """
    if int(sequence) < int(minimum_sequence):
        raise UpdateError(
            "manifest sequence %s is below its own minimum_sequence %s"
            % (sequence, minimum_sequence))
    payload = {
        "schema": SCHEMA,
        "product": str(product or ""),
        "channel": str(channel or ""),
        "artefact": str(artefact_name or ""),
        "version": str(version or ""),
        "sequence": int(sequence),
        "minimum_sequence": int(minimum_sequence),
        "sha256": hashlib.sha256(bytes(artefact_bytes)).hexdigest(),
        "size": len(bytes(artefact_bytes)),
        "published_at": int(published_at if published_at is not None
                            else time.time()),
        "key_id": str(key_id or ""),
        "notes": str(notes or ""),
    }
    if extra:
        payload["extra"] = dict(extra)
    return payload


def sign_manifest(manifest, private_key):
    """Return the wire form: the payload plus an Ed25519 signature."""
    if manifest.get("schema") != SCHEMA:
        raise UpdateError("refusing to sign a manifest with schema %r"
                          % (manifest.get("schema"),))
    return {"payload": manifest,
            "signature": private_key.sign(_canonical(manifest)).hex()}


def verify_update(manifest, artefact_bytes, *, public_key=None,
                  accepted_key_ids=(), current_sequence=0,
                  minimum_sequence=None, expected_product=None,
                  expected_channel=None, expected_artefact=None,
                  max_age_seconds=None, now=None):
    """Decide whether this update may be applied. Returns ``{"ok", "problems"}``.

    The DEFAULT is refuse. Every check below has to pass, and a caller that
    passes no ``public_key`` gets a refusal rather than an unverified install --
    an update mechanism that trusts an unsigned manifest is a delivery channel
    for anyone who can write to the update location.

    ``current_sequence`` is the client's own record of what it has installed.
    It is the client's job to persist it, because the manifest cannot know it;
    passing 0 disables downgrade protection and the result says so under
    ``warnings`` rather than pretending the check ran.
    """
    problems = []
    warnings = []
    if not isinstance(manifest, dict):
        return {"ok": False, "problems": ["no manifest"], "warnings": []}
    payload = manifest.get("payload", manifest)
    if not isinstance(payload, dict):
        return {"ok": False, "problems": ["manifest carries no payload"],
                "warnings": []}

    if payload.get("schema") != SCHEMA:
        problems.append("unexpected schema %r" % (payload.get("schema"),))

    # ── signature ────────────────────────────────────────────────────────
    signature = manifest.get("signature")
    if public_key is None:
        problems.append("no public key supplied: refusing to apply an "
                        "unverified update")
    elif not signature:
        problems.append("manifest is not signed")
    else:
        try:
            public_key.verify(bytes.fromhex(str(signature)),
                              _canonical(payload))
        except Exception as exc:
            problems.append("signature does not verify: %s"
                            % (str(exc)[:120],))

    # ── identity: this update is for THIS client and THIS artefact ───────
    for field, expected in (("product", expected_product),
                            ("channel", expected_channel),
                            ("artefact", expected_artefact)):
        if expected is not None and str(payload.get(field, "")) != str(expected):
            problems.append(
                "%s mismatch: manifest is for %r, client expects %r"
                % (field, payload.get(field), expected))

    key_id = str(payload.get("key_id", ""))
    accepted = tuple(str(k) for k in (accepted_key_ids or ()))
    if accepted and key_id not in accepted:
        problems.append("key_id %r is not in the accepted set (retired key?)"
                        % (key_id,))

    # ── integrity of the bytes actually handed over ──────────────────────
    body = bytes(artefact_bytes)
    want = str(payload.get("sha256", ""))
    have = hashlib.sha256(body).hexdigest()
    if not want:
        problems.append("manifest records no sha256")
    elif want != have:
        problems.append("artefact digest mismatch: manifest %s, bytes %s"
                        % (want[:16], have[:16]))
    size = payload.get("size")
    if isinstance(size, int) and size != len(body):
        problems.append("size mismatch: manifest %d, bytes %d"
                        % (size, len(body)))

    # ── downgrade ────────────────────────────────────────────────────────
    try:
        seq = int(payload.get("sequence", 0))
    except (TypeError, ValueError):
        seq = 0
        problems.append("sequence is not an integer")
    try:
        floor = int(payload.get("minimum_sequence", 0))
    except (TypeError, ValueError):
        floor = 0
        problems.append("minimum_sequence is not an integer")
    if minimum_sequence is not None:
        floor = max(floor, int(minimum_sequence))
    if seq < floor:
        problems.append("downgrade refused: sequence %d is below the accepted "
                        "minimum %d" % (seq, floor))
    if int(current_sequence or 0) <= 0:
        warnings.append("client supplied no current_sequence, so the "
                        "installed-version downgrade check did not run")
    elif seq <= int(current_sequence):
        problems.append("downgrade refused: sequence %d is not newer than the "
                        "installed %d" % (seq, int(current_sequence)))

    # ── freshness ────────────────────────────────────────────────────────
    try:
        published = int(payload.get("published_at", 0))
    except (TypeError, ValueError):
        published = 0
    current = int(time.time() if now is None else now)
    if not published:
        problems.append("manifest has no usable published_at")
    else:
        if published - current > MAX_FUTURE_SKEW_SECONDS:
            problems.append("published_at is %ds in the future (limit %ds)"
                            % (published - current, MAX_FUTURE_SKEW_SECONDS))
        if max_age_seconds is not None and current - published > int(max_age_seconds):
            problems.append("update is %ds old, beyond the %ds limit"
                            % (current - published, int(max_age_seconds)))
    if max_age_seconds is None:
        warnings.append("no max_age_seconds supplied: a validly signed but "
                        "very old manifest is acceptable (freeze attack)")

    return {"ok": not problems, "problems": problems, "warnings": warnings}


def stage_update(destination, artefact_bytes, *, mode=0o644):
    """Write ``artefact_bytes`` next to ``destination`` and rename into place.

    The rename is atomic within a filesystem, so a crash leaves either the old
    file or the complete new one -- never a half-written binary that the next
    start would try to execute. The temporary file is created in the SAME
    directory for exactly that reason (``tempfile`` elsewhere may cross a
    mount point, where rename is not atomic).

    Returns the path written. The caller is expected to have verified the bytes
    first with :func:`verify_update`; this function does not verify, because it
    must stay usable for a first install where there is nothing to compare to.
    """
    destination = os.path.abspath(destination)
    directory = os.path.dirname(destination) or "."
    fd, temporary = tempfile.mkstemp(prefix=".nx-update-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(bytes(artefact_bytes))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, destination)
        temporary = None
        return destination
    finally:
        if temporary and os.path.exists(temporary):
            try:
                os.unlink(temporary)
            except OSError:
                pass
