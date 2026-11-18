"""§7.9 farm-runner integrity: verify what the runner claims it built.

The review's argument: *"A compromised build runner can potentially bypass
every protection you carefully implemented in the compiler."* A runner that
swaps the payload, edits the transform layer, or ships a different compiler
produces a blob indistinguishable from a genuine one -- unless it has to state
what it did, and the controller checks that statement.

This module is deliberately PURE: no file access, no process spawning. The
runner emits ``runner-attestation.json`` (see ``obfuscator/build_manifest.py``,
which owns the reading and writing) and the controller passes the parsed record
here. Keeping the decision logic separate from the I/O is what makes it
testable without a farm.

Attestation shape (schema ``nx-runner-attestation/v1``)::

    {
      "schema": "nx-runner-attestation/v1",
      "runner": {"os": ..., "release": ..., "machine": ...,
                 "python": ..., "cython": ..., "cc": ..., "gcc": ..., "clang": ...},
      "payload_sha256": "...",   # the bytes the runner was GIVEN
      "c_sha256": "...",         # the C it transformed and compiled
      "seed": {"reproducible": ..., "diversified": ..., "mode": ...},
      "transforms": [...],
      "artifacts": {"payload.so": "..."}   # hash of every blob
    }

**Honest limit, stated here and in the tests.** This catches a runner that
diverged from the expected payload, or that hands back bytes different from
what it attested. It does NOT catch a runner that attests honestly and then
compromises the *compiler* while leaving payload and C hashes unchanged --
that needs a reproducible build or a signed toolchain (§7.7), out of scope.
"""
from __future__ import annotations

import hashlib

SCHEMA = "nx-runner-attestation/v1"


def payload_digest(payload_bytes):
    """The value the controller records before upload."""
    return hashlib.sha256(bytes(payload_bytes)).hexdigest()


def verify(attestation, expected_payload_sha256, downloaded=(),
           require_artifacts=True, require_toolchain=()):
    """Controller side: does this runner's claim match what we expected?

    ``downloaded`` is a sequence of ``(name, sha256_hex)`` pairs the controller
    computed itself from the bytes it received. ``require_toolchain`` names
    fields under ``runner`` that must be present and non-empty (e.g.
    ``("cython", "gcc")``) when the build is expected to have used them.

    Returns ``{"ok": bool, "problems": [str, ...]}``. A missing or unparseable
    attestation is a FAILURE, not "no objection": a runner that omits the file
    has attested to nothing.
    """
    problems = []
    if not isinstance(attestation, dict):
        return {"ok": False, "problems": ["no attestation"]}
    if attestation.get("schema") != SCHEMA:
        problems.append("unexpected schema %r" % (attestation.get("schema"),))

    got = str(attestation.get("payload_sha256", ""))
    if got != str(expected_payload_sha256):
        problems.append(
            "payload hash mismatch: runner built %s, controller sent %s"
            % (got[:16] or "(none)", str(expected_payload_sha256)[:16]))
    if not attestation.get("c_sha256"):
        problems.append("runner did not record the transformed C hash")

    runner = attestation.get("runner") or {}
    if not runner.get("python"):
        problems.append("runner did not record its Python version")
    for field in require_toolchain:
        if not str(runner.get(field, "") or "").strip():
            problems.append("runner did not record %s, which this build "
                            "requires" % (field,))

    recorded = attestation.get("artifacts") or {}
    if require_artifacts and not recorded:
        problems.append("runner recorded no artifact hashes")
    for name, have in downloaded:
        want = recorded.get(name)
        if want is None:
            problems.append("downloaded %s was never attested by the runner"
                            % (name,))
            continue
        if str(have) != str(want):
            problems.append(
                "artifact %s does not match the runner's attestation" % (name,))
    return {"ok": not problems, "problems": problems}


def summary(attestation):
    """A one-line human summary for build logs (never raises)."""
    if not isinstance(attestation, dict):
        return "no attestation"
    runner = attestation.get("runner") or {}
    return "%s/%s py%s cython%s payload=%s" % (
        runner.get("os", "?"), runner.get("machine", "?"),
        runner.get("python", "?"), runner.get("cython", "?"),
        str(attestation.get("payload_sha256", ""))[:12] or "?")
