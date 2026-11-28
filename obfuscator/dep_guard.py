"""§7 dependency pinning, verified at BUILD time — not just declared.

`requirements.lock` already pins the full transitive closure with artifact
hashes, and CI installs from it with `--require-hashes`. What was missing is a
check on the *environment that actually builds the artefact*: nothing compared
the installed packages against the lock, so a build could run against a
substituted or drifted version and produce an artefact whose manifest recorded
the drift only after the fact.

Measured 2026-11-18 on the development machine, which is exactly why this
matters:

    package       lock        installed
    requests      2.33.0      2.34.2      <- mismatch
    cython        3.0.12      3.2.1       <- mismatch
    cryptography  50.0.0      50.0.0      ok

Both mismatches were silent. Neither broke the build, which is the point: a
different Cython emits different C, and a different requests changes the HTTP
path the farm talks over. A protection pipeline that cannot say which compiler
produced an artefact has no provenance, which is §7's own argument.

What this can and cannot check
------------------------------
  * **Versions: fully checkable.** `importlib.metadata.version()` against the
    lock's `name==version`, no network, no wheel access.
  * **Wheel hashes: NOT checkable after install.** The lock's hashes describe
    distribution ARTEFACTS (a `.whl`), and a wheel's hash is not recorded in the
    installed tree — `RECORD` holds per-file hashes in a different format, and
    `direct_url.json` is absent for index installs. Verifying artifact hashes
    requires the installer (`pip --require-hashes`), which is why CI does it
    there. This module does not pretend otherwise.
  * **Per-file integrity: checkable, and done.** `RECORD` is hashed for each
    installed file and compared, which catches an edited module even when the
    version string is unchanged. That is the check a version comparison misses.

So the split is deliberate: the installer owns artifact hashes, this owns
"what is on disk right now".
"""
from __future__ import annotations

import base64
import hashlib
import os
import re

DEFAULT_LOCK = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "requirements.lock")


def parse_lock(path=None):
    """Return ``{canonical_name: {"version": str, "hashes": [hex, ...]}}``."""
    path = path or DEFAULT_LOCK
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    entries = re.findall(
        r"^([A-Za-z0-9_.\-]+)==([^\s;\\]+)(.*?)(?=^[A-Za-z0-9_.\-]+==|\Z)",
        text, re.M | re.S)
    out = {}
    for name, version, body in entries:
        out[name.lower().replace("_", "-")] = {
            "version": version,
            "hashes": re.findall(r"--hash=sha256:([0-9a-f]{64})", body),
        }
    return out


def check_installed(lock=None, packages=None):
    """Compare installed versions against the lock.

    Returns a structured verdict; never raises for a missing package, because
    a build must be able to report the whole picture rather than dying on the
    first gap. ``ok`` is False if anything drifted.

    ``packages`` limits the check to named distributions (useful for CI where
    only the build-critical set is installed).
    """
    import importlib.metadata as md

    lock = lock or parse_lock()
    names = sorted(packages) if packages else sorted(lock)
    missing, mismatched, matched = [], [], []
    for name in names:
        want = lock.get(name.lower().replace("_", "-"))
        if want is None:
            missing.append({"name": name, "reason": "not in the lock"})
            continue
        try:
            have = md.version(name)
        except Exception:
            missing.append({"name": name, "reason": "not installed",
                            "want": want["version"]})
            continue
        if have != want["version"]:
            mismatched.append({"name": name, "want": want["version"],
                               "have": have})
        else:
            matched.append(name)
    return {
        "ok": not mismatched and not missing,
        "checked": len(names),
        "matched": matched,
        "mismatched": mismatched,
        "missing": missing,
        "note": ("versions are compared, not wheel hashes: an artefact hash "
                 "is only checkable by the installer"),
    }


def _record_digest(entry_hash, entry_size, file_path):
    """Recompute a RECORD row's digest, supporting both hash forms.

    PEP 376 allows ``sha256=<urlsafe-b64>``; some tools write ``sha256=<hex>``.
    Both are accepted, and a row that matches neither is reported as unverified
    rather than passed.
    """
    algo, _, value = entry_hash.partition("=")
    if algo != "sha256" or not value:
        return None
    try:
        with open(file_path, "rb") as fh:
            data = fh.read()
    except OSError:
        return None
    if entry_size:
        try:
            if int(entry_size) != len(data):
                return False
        except ValueError:
            pass
    digest = hashlib.sha256(data).digest()
    if re.fullmatch(r"[0-9a-f]{64}", value):
        return digest.hex() == value
    # urlsafe base64 without padding, as RECORD writes it
    want = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return want == value.rstrip("=")


def verify_record(dist_name):
    """Verify an installed distribution's own RECORD hashes.

    Catches a module edited in place, which a version comparison cannot see.
    Returns (checked, failed) counts plus the failing paths.
    """
    import importlib.metadata as md

    try:
        dist = md.distribution(dist_name)
        record = dist.read_text("RECORD")
    except Exception as exc:
        return {"checked": 0, "failed": 0,
                "error": "no RECORD (%s)" % (type(exc).__name__,)}
    if not record:
        return {"checked": 0, "failed": 0, "error": "no RECORD"}
    root = str(dist.locate_file(""))
    checked = failed = 0
    bad = []
    for line in record.splitlines():
        parts = line.rsplit(",", 2)
        if len(parts) != 3:
            continue
        rel, dig, size = parts
        if not dig or rel.endswith(".pyc") or rel.startswith("__pycache__"):
            continue
        verdict = _record_digest(dig, size, os.path.join(root, rel))
        checked += 1
        if verdict is not True:
            # Missing/unreadable files and RECORD rows this verifier cannot
            # authenticate must fail closed. Treating them as absent evidence
            # let an attacker delete a module and leave the integrity report
            # green.
            failed += 1
            bad.append(rel)
    return {"checked": checked, "failed": failed, "bad": bad[:10]}


def guard_build(lock=None, packages=None, fail=True):
    """Run the checks and, with ``fail``, refuse the build on drift.

    Called from the protection compiler so an artefact cannot be produced by an
    environment the lock does not describe. ``fail=False`` returns the report
    for callers that want to warn instead (the opt-out used by packaging tests).
    """
    report = check_installed(lock, packages)
    if not report["ok"] and fail:
        detail = []
        for row in report["mismatched"]:
            detail.append("%s: lock %s, installed %s"
                          % (row["name"], row["want"], row["have"]))
        for row in report["missing"]:
            detail.append("%s: %s" % (row.get("name"), row.get("reason")))
        raise RuntimeError(
            "dependency drift: this environment does not match "
            "requirements.lock, so an artefact built here would have "
            "unverifiable provenance. Reinstall from the lock, or set "
            "NIXON_ALLOW_DEP_DRIFT=1 to build anyway and record the drift. "
            + "; ".join(detail[:8]))
    return report
