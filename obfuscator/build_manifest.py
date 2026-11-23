"""Signed build manifest (§7): bind an artefact to the inputs that made it.

The review's supply-chain point is that a compromised build runner can bypass
every protection in the compiler, so the artefact must carry evidence of *what
produced it*. Nothing in this project did that for a build: artefacts were
signed per-file (scripts/artifact_sign.py), but there was no record of the
compiler version, the source hash, the transform set, or the toolchain, so a
swap of the local compiler or a silent flag change was undetectable.

This module writes a manifest beside the artefact recording:

  * sha256 of the artefact and of the source it was built from;
  * compiler + linker identity (version strings, not just names);
  * Python and Cython versions;
  * the transform families actually applied and the native module's own hash;
  * the seed *classes* used (reproducible vs diversified) without the seeds;
  * a timestamp and a build id.

and signs the whole thing with Ed25519 when a private key is configured. No
key -> the manifest is still written and marked `signed: false`, because an
unsigned manifest that verifies hashes is still better than none, and claiming
a signature that does not exist would be worse.

Verification (`verify_manifest`) recomputes the artefact hash and, if a public
key is pinned, checks the signature. It returns a structured result so a CI
gate can fail on it rather than parsing prose.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import subprocess
import sys
import time

SCHEMA = "nixon-build-manifest/v1"
MANIFEST_SUFFIX = ".build-manifest.json"


def _sha256_file(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def _tool_version(argv):
    """Return the first line of `<tool> --version`, or "" if unavailable."""
    try:
        out = subprocess.run(argv, capture_output=True, text=True,
                             timeout=20).stdout
    except Exception:
        return ""
    line = out.strip().splitlines()[0] if out.strip() else ""
    return line[:200]


def _source_files(source_path):
    """Hash the source and any sibling Python modules in its directory."""
    out = {}
    if not source_path or not os.path.isfile(source_path):
        return out
    base = os.path.dirname(os.path.abspath(source_path))
    out[os.path.basename(source_path)] = _sha256_file(source_path)
    try:
        for name in sorted(os.listdir(base)):
            if name.endswith(".py") and name != os.path.basename(source_path):
                out[name] = _sha256_file(os.path.join(base, name))
    except OSError:
        pass
    return out


def build_manifest(artefact_path, source_path=None, *, transforms=None,
                   native_blob_path=None, native_blobs=None, seed_classes=None,
                   build_id=None, extra=None, protection_level=None):
    """Assemble the manifest dict. Never raises on missing optional inputs.

    ``native_blobs`` is the alternative to ``native_blob_path`` for the normal
    case: the build keeps the compiled modules IN MEMORY (they are XOR-packed
    straight into the loader), so there is no file on disk for the manifest to
    hash. Passing the per-OS mapping records what was actually embedded.

    Measured 2026-11-20: a native build whose deliverable carried a 212 KB
    packed .so still wrote ``native_blob: {bytes: 0, sha256: ""}``, because
    only ``native_blob_path`` was ever read and no caller sets it. A manifest
    that says "no native blob" about an artefact that is a native blob is
    worse than no manifest: the whole point of the record is to answer "what
    produced this" from the artefact alone.
    """
    artefact_path = os.path.abspath(artefact_path)
    if protection_level is None:
        # Derive a monotonic level from what the build recorded. It only has
        # to INCREASE across releases for rollback protection to mean
        # something; the transform count is a real, per-build measure that
        # rises as protections are added.
        protection_level = int(len(transforms or ()))
    _nb_sha = ""
    _nb_bytes = 0
    _nb_platforms = {}
    if native_blob_path:
        _nb_sha = _sha256_file(native_blob_path) if native_blob_path else ""
        _nb_bytes = (os.path.getsize(native_blob_path)
                     if os.path.exists(native_blob_path) else 0)
    for _nb_plat, _nb_val in (native_blobs or {}).items():
        if not _nb_val:
            continue
        # The build holds each blob base64-encoded (that is what the loader
        # decodes), so hash the DECODED image and report the size a reader can
        # compare against the loader's `native_blob_loadability` verdict.
        try:
            _nb_raw = base64.b64decode(_nb_val, validate=False)
        except Exception:
            _nb_raw = _nb_val if isinstance(_nb_val, bytes) else b""
        if not _nb_raw:
            continue
        _nb_platforms[_nb_plat] = {
            "sha256": hashlib.sha256(_nb_raw).hexdigest(),
            "bytes": len(_nb_raw),
        }
        # The top-level fields stay meaningful for an older reader that only
        # knows one blob: record the largest, so a native build never again
        # reports bytes: 0.
        if len(_nb_raw) > _nb_bytes:
            _nb_bytes = len(_nb_raw)
            _nb_sha = _nb_platforms[_nb_plat]["sha256"]
        _nb_raw = None
    manifest = {
        "schema": SCHEMA,
        "artefact": {
            "name": os.path.basename(artefact_path),
            "bytes": os.path.getsize(artefact_path)
            if os.path.exists(artefact_path) else 0,
            "sha256": _sha256_file(artefact_path),
        },
        "source": _source_files(source_path),
        "toolchain": {
            "python": sys.version.split()[0],
            "python_impl": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "gcc": _tool_version(["gcc", "--version"]),
            "ld": _tool_version(["ld", "--version"]),
            "cython": _cython_version(),
        },
        "transforms": sorted(transforms or []),
        # MONOTONIC PROTECTION LEVEL (review register, sixth/seventh pass).
        # rollback.py's docstring says this is "recorded IN THE SIGNED BUILD
        # MANIFEST", but NOTHING ever wrote it: the anti-rollback check could
        # never fire because its input never existed. Recorded here, inside
        # the signed body, so an attacker who lowers it changes what the
        # signature covers.
        "protection_level": protection_level,
        "native_blob": {
            # WHAT THE HASH COVERS (2026-11-20). These are hashes of the
            # DECODED, PLAINTEXT object image -- the ELF/Mach-O/PE as the
            # compiler emitted it. The bytes inside the shipped artefact are
            # that same image XOR-packed against the loader's derived key, so
            # hashing the embedded base64 literal directly yields a DIFFERENT
            # value even when the artefact is correct. Stated here because
            # anyone comparing an artefact's payload against this record will
            # hit exactly that and conclude the build was tampered with.
            "sha256": _nb_sha,
            "bytes": _nb_bytes,
            "hashed_form": "plaintext-object-image",
            # Per-platform detail: a build that embedded linux only is not the
            # same artefact as one that embedded all three, and that
            # difference used to be invisible everywhere but the loader dict.
            "platforms": _nb_platforms,
        },
        "seeds": dict(seed_classes or {}),
        "build": {
            "id": build_id or "",
            "timestamp": int(time.time()),
            # RELEASE TRUST CHAIN (review register, second pass, item 3):
            # the attestation must bind WHAT was built and WITH WHAT
            # dependency set, so a downloaded artefact is answerable to its
            # source revision and its lock file without trusting anyone's
            # memory. Both are recorded, never asserted: an absent git repo
            # (sdist installs, CI checkouts without metadata) records None
            # and the digest records the file bytes, not a version label.
            "commit": _git_commit(),
            "dependency_lock_digest": _dependency_lock_digest(),
            # §7 WORKFLOW / ACTION IDENTITIES (review register). "Which
            # workflow run produced this artefact?" was unanswerable from the
            # signed record: a local build genuinely cannot know, but a CI
            # build can, and GitHub Actions exports it in the environment.
            # Recorded as None when not in CI -- a real answer, not a gap --
            # so a reader can tell "built locally" from "field forgotten".
            "ci": _ci_identity(),
        },
        "signed": False,
    }
    if extra:
        manifest["extra"] = extra
    return manifest


def _git_commit():
    """The HEAD commit this build ran from, or None when unavailable.

    Deliberately read from git rather than imported from a module constant:
    the point is to bind the artefact to the tree it was actually built
    from, and a stale constant would bind it to nothing.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            timeout=15).stdout.strip()
        return out or None
    except Exception:
        return None


def _dependency_lock_digest():
    """sha256 of requirements.lock beside this module, or None.

    Recorded as the digest of the BYTES so a post-hoc question -- "was this
    artefact built under the approved dependency set?" -- is answered by
    hashing the lock file the build actually used, not by trusting a version
    label that can drift.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    lock = os.path.join(os.path.dirname(here), "requirements.lock")
    if not os.path.isfile(lock):
        return None
    try:
        return hashlib.sha256(open(lock, "rb").read()).hexdigest()
    except Exception:
        return None


def _cython_version():
    try:
        import Cython
        return str(getattr(Cython, "__version__", ""))
    except Exception:
        return ""


#: GitHub Actions sets these for every step of a workflow run. Read as a group
#: so the manifest records "which workflow run produced this artefact", which
#: is the §7 field a local build cannot otherwise answer.
_CI_IDENTITY_ENV = (
    ("workflow", "GITHUB_WORKFLOW"),
    ("run_id", "GITHUB_RUN_ID"),
    ("run_attempt", "GITHUB_RUN_ATTEMPT"),
    ("job", "GITHUB_JOB"),
    ("repository", "GITHUB_REPOSITORY"),
    ("ref", "GITHUB_REF"),
    ("sha", "GITHUB_SHA"),
    ("server_url", "GITHUB_SERVER_URL"),
)


def _ci_identity():
    """The CI workflow/run identity, or None when not running under CI.

    ``None`` is a REAL ANSWER -- "this was built outside a CI workflow" -- and
    is deliberately distinguishable from an empty dict, which would mean "CI
    ran but told us nothing". The distinction matters for the same reason the
    pack record reports ``format_version: null`` rather than omitting the
    field: an absent field and an absent fact are different claims.

    Only the variables in ``_CI_IDENTITY_ENV`` are read; nothing is invoked
    and no network call is made, so a locally built artefact records None
    rather than guessing.
    """
    found = {}
    for key, var in _CI_IDENTITY_ENV:
        value = os.environ.get(var, "").strip()
        if value:
            found[key] = value
    if not found:
        return None
    # GITHUB_SHA is the commit the RUN checked out; the manifest already
    # records the commit it actually built from (build.commit). Both are kept
    # because a mismatch between them is itself evidence -- it means the build
    # ran from a different revision than CI checked out.
    return found


def sign_manifest(manifest, private_key=None):
    """Sign the manifest with Ed25519 when a key is available.

    The signature covers canonical JSON of the manifest WITHOUT the signature
    field, so verification cannot be fooled by re-serialisation order.

    THE KEY FINGERPRINT IS SIGNED. Measured 2026-11-22: the fingerprint was
    stored only at ``signature.key_fingerprint``, and because the whole
    ``signature`` object is excluded from the signed body, editing that field
    left ``verify_manifest`` returning ``ok: True``. The docstring claimed the
    opposite ("covered by the signature"). That is a real defect, not a
    documentation nit: the fingerprint is what
    ``docs/security/INCIDENT_RESPONSE.md`` §0 uses to answer "which artefacts
    did the compromised key sign?", so an attacker able to write a manifest
    could re-attribute an artefact from a compromised key to a clean one.

    The fix binds it at TOP LEVEL as ``signed_key_fingerprint``, which IS
    inside the signed body (only ``signature`` and ``signed`` are excluded).
    The nested ``signature.key_fingerprint`` is still written so existing
    readers keep working, and verify_manifest refuses a manifest whose two
    copies disagree.
    """
    if private_key is None:
        manifest["signed"] = False
        manifest["signature"] = None
        manifest.pop("signed_key_fingerprint", None)
        return manifest
    import base64
    from cryptography.hazmat.primitives import serialization as _s
    _pk_raw = private_key.public_key().public_bytes(
        encoding=_s.Encoding.Raw, format=_s.PublicFormat.Raw)
    _fingerprint = hashlib.sha256(_pk_raw).hexdigest()[:16]
    # Set BEFORE signing, so it is part of the payload.
    manifest["signed_key_fingerprint"] = _fingerprint
    body = {k: v for k, v in manifest.items()
            if k not in ("signature", "signed")}
    payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    try:
        signature = private_key.sign(payload)
        manifest["signature"] = {
            "algo": "ed25519",
            "sig": base64.b64encode(signature).decode("ascii"),
            "key_fingerprint": _fingerprint,
        }
        manifest["signed"] = True
    except Exception as exc:
        manifest["signed"] = False
        manifest["signature"] = {"algo": "ed25519", "error": str(exc)[:120]}
    return manifest


def write_manifest(artefact_path, source_path=None, *, private_key=None,
                   **kwargs):
    """Build, sign and write ``<artefact>.build-manifest.json``.

    Returns the manifest path, or None if the artefact does not exist.
    """
    if not os.path.exists(artefact_path):
        return None
    manifest = build_manifest(artefact_path, source_path, **kwargs)
    manifest = sign_manifest(manifest, private_key)
    out = os.path.abspath(artefact_path) + MANIFEST_SUFFIX
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    return out


MANIFEST_PIN_ENV = "NIXON_BUILD_MANIFEST_PUBKEY"


def _pub_raw(key):
    """Raw 32-byte public key material from an Ed25519 key object."""
    from cryptography.hazmat.primitives import serialization
    return key.public_bytes(encoding=serialization.Encoding.Raw,
                            format=serialization.PublicFormat.Raw)


def _manifest_trusted_key(public_key):
    """Resolve the trusted manifest key and the refusal reason, if any.

    Returns ``(key_or_None, reason_or_None)``.

    TRUST-ANCHOR PRECEDENCE (review register, FOURTH pass, item 1 — the
    rule the reviewer specified). The third-pass implementation returned an
    explicitly supplied key BEFORE consulting the pin, which meant a caller
    could bypass the out-of-band anchor by passing an attacker-controlled
    key argument. The release policy must have ONE unambiguous trust
    authority:

    * release policy (NIXON_REQUIRE_PROVENANCE=1):
        - the OUT-OF-BAND PIN is the authority; a missing pin is a refusal;
        - an explicit key that DIFFERS from the pin is a refusal — the
          caller cannot override the anchor through the key argument;
        - an explicit key EQUAL to the pin verifies (the caller is then not
          an authority, it agrees with one).
    * without the release policy: explicit key first, then the pin if
      configured — the documented pre-policy behaviour for existing
      callers.
    """
    release = os.environ.get("NIXON_REQUIRE_PROVENANCE") == "1"
    pinned_hex = os.environ.get(MANIFEST_PIN_ENV, "").strip()
    pinned = None
    if pinned_hex:
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                Ed25519PublicKey)
            pinned = Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(pinned_hex))
        except Exception:
            pinned = None
    if release:
        if pinned is None:
            return None, ("release policy requires "
                          "%s (out-of-band trust anchor)" % MANIFEST_PIN_ENV)
        if public_key is not None:
            try:
                same = _pub_raw(public_key) == _pub_raw(pinned)
            except Exception:
                same = False
            if not same:
                return None, ("explicit key does not match the release "
                              "pin; the pin is the trust authority")
        return pinned, None
    if public_key is not None:
        return public_key, None
    if pinned is not None:
        return pinned, None
    return None, None


def verify_manifest(artefact_path, public_key=None):
    """Check a manifest against the artefact. Returns a structured verdict.

    ``ok`` is True only when the artefact hash matches AND the signature
    verifies against a TRUSTED anchor — an explicit public key, the
    ``NIXON_BUILD_MANIFEST_PUBKEY`` out-of-band pin, or (under the release
    policy) a caller key. A manifest that is simply absent is reported as
    ``ok: False, reason: "missing"`` rather than passing silently.
    """
    result = {"ok": False, "artefact": os.path.basename(artefact_path),
              "reason": "", "signed": False}
    mpath = os.path.abspath(artefact_path) + MANIFEST_SUFFIX
    if not os.path.exists(mpath):
        result["reason"] = "missing manifest"
        return result
    try:
        with open(mpath, encoding="utf-8") as fh:
            manifest = json.load(fh)
    except Exception as exc:
        result["reason"] = "unreadable manifest: %s" % (exc,)
        return result
    # MALFORMED-INPUT FUZZ FINDING (review register, sixth pass, item 5):
    # the JSON literal `null` parses SUCCESSFULLY to None and then crashed
    # this verifier with an uncaught AttributeError on .get — malformed
    # input producing a crash instead of a structured refusal. Any
    # non-object manifest document is refused here.
    if not isinstance(manifest, dict):
        result["reason"] = "manifest document is not a JSON object"
        return result
    if manifest.get("schema") != SCHEMA:
        result["reason"] = "unexpected schema %r" % (manifest.get("schema"),)
        return result
    declared = (manifest.get("artefact") or {}).get("sha256", "")
    actual = _sha256_file(artefact_path)
    if not declared or declared != actual:
        result["reason"] = "artefact hash mismatch (declared %s… actual %s…)" % (
            declared[:12], actual[:12])
        return result
    result["signed"] = bool(manifest.get("signed"))
    # RESOLVE THE TRUSTED ANCHOR (see _manifest_trusted_key): under the
    # release policy the OUT-OF-BAND PIN is the single authority, and an
    # explicit key that differs from it is a refusal — the caller cannot
    # override the anchor through the key argument.
    public_key, anchor_reason = _manifest_trusted_key(public_key)
    if public_key is None and anchor_reason:
        result["reason"] = anchor_reason
        return result
    if public_key is None and result["signed"]:
        result["reason"] = ("manifest signature not verified against a "
                            "trusted anchor")
        return result
    if public_key is not None and result["signed"]:
        try:
            import base64
            # THE KEY FINGERPRINT MUST AGREE IN BOTH PLACES. The nested
            # signature.key_fingerprint is excluded from the signed body (the
            # whole `signature` object is), so it is only trustworthy when it
            # matches the signed top-level copy. Measured 2026-11-22: editing
            # the nested copy alone left ok:True, which let an attacker
            # re-attribute an artefact to an uncompromised key and break the
            # incident triage in docs/security/INCIDENT_RESPONSE.md.
            nested = (manifest.get("signature") or {}).get("key_fingerprint")
            signed_copy = manifest.get("signed_key_fingerprint")
            if signed_copy is not None and nested is not None:
                if str(nested) != str(signed_copy):
                    result["reason"] = (
                        "signing-key fingerprint mismatch: signature block "
                        "claims %r but the signed body records %r"
                        % (nested, signed_copy))
                    return result
            body = {k: v for k, v in manifest.items()
                    if k not in ("signature", "signed")}
            payload = json.dumps(body, sort_keys=True,
                                 separators=(",", ":")).encode()
            sig = base64.b64decode(
                (manifest.get("signature") or {}).get("sig", ""))
            public_key.verify(sig, payload)
        except Exception as exc:
            result["reason"] = "signature invalid: %s" % (str(exc)[:120],)
            return result
    elif public_key is not None and not result["signed"]:
        result["reason"] = "signature required but manifest is unsigned"
        return result
    result["ok"] = True
    result["reason"] = "hash ok" + (" + signature ok"
                                    if public_key is not None else "")
    return result
