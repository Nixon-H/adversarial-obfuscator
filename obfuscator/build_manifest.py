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
                   native_blob_path=None, seed_classes=None,
                   build_id=None, extra=None):
    """Assemble the manifest dict. Never raises on missing optional inputs."""
    artefact_path = os.path.abspath(artefact_path)
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
        "native_blob": {
            "sha256": _sha256_file(native_blob_path) if native_blob_path else "",
            "bytes": os.path.getsize(native_blob_path)
            if native_blob_path and os.path.exists(native_blob_path) else 0,
        },
        "seeds": dict(seed_classes or {}),
        "build": {
            "id": build_id or "",
            "timestamp": int(time.time()),
        },
        "signed": False,
    }
    if extra:
        manifest["extra"] = extra
    return manifest


def _cython_version():
    try:
        import Cython
        return str(getattr(Cython, "__version__", ""))
    except Exception:
        return ""


def sign_manifest(manifest, private_key=None):
    """Sign the manifest with Ed25519 when a key is available.

    The signature covers canonical JSON of the manifest WITHOUT the signature
    field, so verification cannot be fooled by re-serialisation order.
    """
    if private_key is None:
        manifest["signed"] = False
        manifest["signature"] = None
        return manifest
    body = {k: v for k, v in manifest.items()
            if k not in ("signature", "signed")}
    payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    try:
        signature = private_key.sign(payload)
        import base64
        manifest["signature"] = {
            "algo": "ed25519",
            "sig": base64.b64encode(signature).decode("ascii"),
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


def verify_manifest(artefact_path, public_key=None):
    """Check a manifest against the artefact. Returns a structured verdict.

    ``ok`` is True only when the artefact hash matches AND, if a public key is
    supplied, the signature verifies. A manifest that is simply absent is
    reported as ``ok: False, reason: "missing"`` rather than passing silently.
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
    if public_key is not None and result["signed"]:
        try:
            import base64
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
