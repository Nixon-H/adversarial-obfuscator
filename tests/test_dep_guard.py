"""§7 dependency pinning verified at build time, not just declared.

`requirements.lock` already pins the full closure with artifact hashes and CI
installs from it. What was missing is a check on the environment that ACTUALLY
builds: nothing compared installed packages against the lock, so a build could
run against a substituted version and the drift would only surface afterwards.

Measured 2026-11-18 on the development machine, which is the finding:

    package       lock        installed
    requests      2.33.0      2.34.2      mismatch, silent
    cython        3.0.12      3.2.1       mismatch, silent
    setuptools    84.2.0      84.2.1      mismatch, silent
    cryptography  50.0.0      50.0.0      ok

A different Cython emits different C, so that drift alone means an artefact
built there has unverifiable provenance.

Scope, asserted here so it cannot be overstated:
  * versions ARE checkable from the installed environment;
  * wheel hashes are NOT -- they describe an artifact, and only the installer
    can check them (which is why CI uses --require-hashes);
  * per-file integrity IS checkable, via each distribution's RECORD.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator import dep_guard  # noqa: E402


def test_lock_parses_with_versions_and_hashes():
    lock = dep_guard.parse_lock()
    assert len(lock) >= 15, "the lock looks truncated: %d packages" % len(lock)
    for name, entry in lock.items():
        assert entry["version"], "%s has no version" % name
        assert entry["hashes"], "%s has no artifact hash" % name


def test_the_known_transitives_are_pinned():
    """A lock that stops at the direct requirements is not a lock."""
    lock = dep_guard.parse_lock()
    for name in ("certifi", "idna", "cffi", "urllib3"):
        assert name in lock, "%s is not pinned" % name


def test_version_comparison_reports_drift_not_a_bare_boolean():
    report = dep_guard.check_installed(
        packages=("cryptography", "cython", "requests", "setuptools"))
    assert report["checked"] == 4
    # Every row must name the package and say what differs; a bare False gives
    # an operator nothing to act on.
    for row in report["mismatched"]:
        assert {"name", "want", "have"} <= set(row)
    assert set(report) >= {"ok", "checked", "matched", "mismatched", "missing"}


def test_a_package_outside_the_lock_is_reported_missing():
    report = dep_guard.check_installed(packages=("definitely-not-locked",))
    assert report["ok"] is False
    assert report["missing"], "an unlisted package must be reported"


def test_record_verification_detects_an_edited_file(tmp_path):
    """RECORD hashes catch an in-place edit that a version check cannot."""
    import hashlib
    body = b"payload = 1\n"
    target = tmp_path / "mod.py"
    target.write_bytes(body)
    digest = hashlib.sha256(body).digest()
    import base64
    b64 = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    assert dep_guard._record_digest("sha256=" + b64, str(len(body)),
                                    str(target)) is True
    target.write_bytes(b"payload = 2\n")   # edited, same version
    assert dep_guard._record_digest("sha256=" + b64, str(len(body)),
                                    str(target)) is False


def test_record_digest_accepts_hex_and_rejects_other_algos(tmp_path):
    import hashlib
    body = b"x" * 32
    target = tmp_path / "m.py"
    target.write_bytes(body)
    hex_digest = hashlib.sha256(body).hexdigest()
    assert dep_guard._record_digest("sha256=" + hex_digest, "", str(target)) is True
    assert dep_guard._record_digest("sha384=abc", "", str(target)) is None


def test_record_verification_runs_on_a_real_distribution():
    result = dep_guard.verify_record("cryptography")
    assert result.get("error") is None, result.get("error")
    assert result["checked"] > 0, "no files were checked"
    assert result["failed"] == 0, result["bad"]


def test_guard_can_warn_instead_of_failing():
    """The default build path must not hard-fail on a patch-level bump."""
    report = dep_guard.guard_build(packages=("cython",), fail=False)
    assert "ok" in report


def test_guard_refuses_when_asked_and_explains_why():
    """With fail=True the message must name the drift, not just say no."""
    # Find a package that is genuinely drifted on this machine, if any; else
    # assert the mechanism by forcing a bogus expectation.
    fake_lock = {"cython": {"version": "0.0.1", "hashes": ["0" * 64]}}
    with pytest.raises(RuntimeError) as excinfo:
        dep_guard.guard_build(lock=fake_lock, packages=("cython",), fail=True)
    message = str(excinfo.value)
    assert "0.0.1" in message and "cython" in message
