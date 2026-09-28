#!/usr/bin/env python3
"""Artifact signing via HMAC-SHA256 (Phase 5 hygiene).

``sign_file(path, key)`` computes HMAC-SHA256 over raw file bytes and
returns ``{'algo': 'hmac-sha256', 'hex': ...}``. ``verify_file`` uses
constant-time :func:`hmac.compare_digest`.

Bound signatures (ADR-0005): ``sign_artifact(path, key, metadata)``
binds file bytes + repo/commit/build-id/platform metadata
(``hmac-sha256-binding-v1``); ``verify_artifact`` verifies bound and
legacy sigs; ``verify_zip_sidecars`` / ``enforce_dir_sidecars`` are the
download-side fail-closed gates.

CLI::

    python3 -m scripts.artifact_sign <file> [--verify HEX]
"""

from __future__ import annotations

import argparse
import hmac
import json
import logging
import os
import platform
import sys
import zipfile

LOG = logging.getLogger(__name__)

#: Algo tag for metadata-bound signatures (ADR-0005). Legacy bytes-only
#: signatures keep ``hmac-sha256`` and still verify via
#: :func:`verify_artifact` (weaker: no metadata binding — documented).
BINDING_ALGO = "hmac-sha256-binding-v1"

#: Sidecar filename suffix (``<artifact>.sig.json``), shared by the
#: package step, the farm upload path, and the download verifier.
SIDECAR_SUFFIX = ".sig.json"

#: Key env vars, precedence order. ``NIXON_SIGN_KEY`` is the pre-existing
#: convention (CLI default, ``SECURITY.md``); ``NIXON_ARTIFACT_KEY_HEX``
#: is the explicit farm-artifact name (ADR-0005). Both hold hex.
ARTIFACT_KEY_ENVS = ("NIXON_ARTIFACT_KEY_HEX", "NIXON_SIGN_KEY")


def sign_file(path: str, key: bytes) -> dict:
    """HMAC-SHA256 sign ``path`` with ``key``; return sig dict."""
    if not isinstance(key, (bytes, bytearray)) or not key:
        raise ValueError("key must be non-empty bytes")
    with open(path, "rb") as f:
        data = f.read()
    digest = hmac.new(bytes(key), data, "sha256").hexdigest()
    return {"algo": "hmac-sha256", "hex": digest}


def verify_file(path: str, key: bytes, sig: dict) -> bool:
    """Constant-time verify of a sig dict against ``path`` + ``key``."""
    if not isinstance(sig, dict) or sig.get("algo") != "hmac-sha256":
        return False
    expected = sig.get("hex")
    if not isinstance(expected, str) or not expected:
        return False
    try:
        actual = sign_file(path, key)["hex"]
    except (OSError, ValueError):
        return False
    return hmac.compare_digest(actual, expected)


class SignatureMismatchError(ValueError):
    """Raised when a present signature fails verification (fail closed)."""


def resolve_key(env_names: tuple = ARTIFACT_KEY_ENVS,
                env=None) -> bytes | None:
    """Return the artifact HMAC key or ``None`` when unconfigured/unusable.

    First non-empty hex value in ``env_names`` wins. Missing, empty, or
    malformed-hex values are skipped (never raise — the callers decide
    between opportunistic signing and loud-warning proceed). ``env``
    defaults to :data:`os.environ` and exists for testability.
    """
    source = os.environ if env is None else env
    for name in env_names:
        try:
            raw = source.get(name, "")
        except Exception:
            continue
        if not raw or not str(raw).strip():
            continue
        try:
            key = bytes.fromhex(str(raw).strip())
        except (ValueError, TypeError):
            continue
        if key:
            return key
    return None


def _canonical_metadata_bytes(metadata: dict) -> bytes:
    """Canonical JSON encoding of the bound metadata (MAC input)."""
    return json.dumps(metadata, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, default=str).encode("utf-8")


def _bound_hex(data: bytes, key: bytes, metadata: dict) -> str:
    """HMAC-SHA256 over ``data + 0x00 + canonical(metadata)``."""
    bound = _canonical_metadata_bytes(metadata)
    return hmac.new(bytes(key), data + b"\x00" + bound, "sha256").hexdigest()


def default_metadata(extra: dict | None = None) -> dict:
    """Best-effort repo/commit/build-id/platform binding (ADR-0005).

    Sourced from the environment (``GITHUB_REPOSITORY``, ``GITHUB_SHA``,
    ``NIXON_BUILD_ID``) plus host facts. Unknown fields are ``""`` —
    documented: the MAC authenticates the *claim*, it cannot make an
    empty environment truthful. ``extra`` overrides on collision.
    """
    meta = {
        "repo": os.environ.get("GITHUB_REPOSITORY", ""),
        "commit": os.environ.get("GITHUB_SHA", ""),
        "build_id": os.environ.get("NIXON_BUILD_ID", ""),
        "platform": sys.platform,
        "python": platform.python_version(),
    }
    if extra:
        for k, v in dict(extra).items():
            meta[str(k)] = v
    return meta


def sign_artifact(path: str, key: bytes, metadata: dict | None = None) -> dict:
    """HMAC-SHA256 sign ``path`` bound to ``metadata``; return sig dict.

    The MAC covers ``file bytes + 0x00 + canonical(metadata)`` so a
    signature cannot be transplanted onto different bytes *or* different
    metadata (repo/commit/build-id/platform). ``metadata`` defaults to
    :func:`default_metadata`. Shape: ``{"algo", "hex", "metadata",
    "file"}``.
    """
    if not isinstance(key, (bytes, bytearray)) or not key:
        raise ValueError("key must be non-empty bytes")
    meta = dict(metadata) if isinstance(metadata, dict) else default_metadata()
    with open(path, "rb") as f:
        data = f.read()
    return {
        "algo": BINDING_ALGO,
        "hex": _bound_hex(data, bytes(key), meta),
        "metadata": meta,
        "file": os.path.basename(path),
    }


def verify_artifact(path: str, key: bytes, sig: dict,
                     expected: dict | None = None) -> bool:
    """Verify a bound (or legacy) sig dict against ``path`` + ``key``.

    ``BINDING_ALGO`` sigs recompute the metadata-bound MAC; the bound
    ``metadata`` must be a dict or verification fails. Legacy
    ``hmac-sha256`` sigs (bytes-only, no binding) still verify via
    :func:`verify_file` — weaker, documented in ADR-0005. When
    ``expected`` is given, every ``expected`` item must equal the sig's
    bound metadata (subset match, e.g. pin ``build_id``).
    """
    if not isinstance(sig, dict):
        return False
    algo = sig.get("algo")
    if algo == BINDING_ALGO:
        meta = sig.get("metadata")
        if not isinstance(meta, dict):
            return False
        if expected:
            try:
                for k, v in dict(expected).items():
                    if meta.get(k) != v:
                        return False
            except Exception:
                return False
        expected_hex = sig.get("hex")
        if not isinstance(expected_hex, str) or not expected_hex:
            return False
        try:
            with open(path, "rb") as f:
                data = f.read()
        except (OSError, ValueError):
            return False
        try:
            actual = _bound_hex(data, bytes(key), meta)
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(actual, expected_hex)
    if algo == "hmac-sha256":
        if expected:
            # Legacy sigs carry no binding, so they can never satisfy a
            # metadata pin — fail closed rather than silently downgrade.
            return False
        return verify_file(path, key, sig)
    return False


def sidecar_path_for(path: str) -> str:
    """Return the ``<path>.sig.json`` sidecar path."""
    return path + SIDECAR_SUFFIX


def write_sidecar(path: str, sig: dict) -> str:
    """Write ``sig`` JSON to ``<path>.sig.json``; return the sidecar path."""
    sidecar = sidecar_path_for(path)
    with open(sidecar, "w", encoding="utf-8") as f:
        json.dump(sig, f, sort_keys=True, indent=2)
    return sidecar


def read_sidecar(sidecar_path: str) -> dict | None:
    """Read a sidecar file; ``None`` when missing/unparseable/not-a-dict."""
    try:
        with open(sidecar_path, "r", encoding="utf-8") as f:
            sig = json.load(f)
    except (OSError, ValueError):
        return None
    return sig if isinstance(sig, dict) else None


def zip_sidecar_names(zip_path: str) -> list:
    """Names of ``*.sig.json`` members inside ``zip_path`` (``[]`` on error)."""
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            return [n for n in z.namelist() if n.endswith(SIDECAR_SUFFIX)]
    except Exception:
        return []


def verify_zip_sidecars(zip_path: str, key: bytes) -> int:
    """Verify every ``*.sig.json`` member against its sibling zip member.

    The sibling of ``foo.sig.json`` is ``foo`` (same directory inside the
    zip). Returns the number of verified sidecars (``0`` when the zip
    carries none). Raises :class:`SignatureMismatchError` fail-closed on
    any mismatch, unreadable sidecar, or missing sibling — the caller
    must not extract on raise.
    """
    if not isinstance(key, (bytes, bytearray)) or not key:
        raise ValueError("key must be non-empty bytes")
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            members = set(z.namelist())
            sidecars = sorted(n for n in members if n.endswith(SIDECAR_SUFFIX))
            count = 0
            for sidecar_name in sidecars:
                sibling = sidecar_name[: -len(SIDECAR_SUFFIX)]
                try:
                    raw = z.read(sidecar_name)
                    sig = json.loads(raw.decode("utf-8"))
                except Exception as e:
                    raise SignatureMismatchError(
                        f"unreadable sidecar {sidecar_name!r}: {e}")
                if sibling not in members:
                    raise SignatureMismatchError(
                        f"sidecar {sidecar_name!r} has no sibling {sibling!r}")
                if not isinstance(sig, dict):
                    raise SignatureMismatchError(
                        f"sidecar {sidecar_name!r} is not a sig dict")
                try:
                    data = z.read(sibling)
                except Exception as e:
                    raise SignatureMismatchError(
                        f"unreadable sibling {sibling!r}: {e}")
                algo = sig.get("algo")
                if algo == BINDING_ALGO:
                    meta = sig.get("metadata")
                    if not isinstance(meta, dict):
                        raise SignatureMismatchError(
                            f"sidecar {sidecar_name!r} has no metadata binding")
                    actual = _bound_hex(data, bytes(key), meta)
                elif algo == "hmac-sha256":
                    actual = hmac.new(bytes(key), data, "sha256").hexdigest()
                else:
                    raise SignatureMismatchError(
                        f"sidecar {sidecar_name!r} has unknown algo "
                        f"{algo!r}")
                claimed = sig.get("hex")
                if (not isinstance(claimed, str) or not claimed
                        or not hmac.compare_digest(actual, claimed)):
                    raise SignatureMismatchError(
                        f"signature mismatch for {sibling!r}")
                count += 1
            return count
    except SignatureMismatchError:
        raise
    except Exception as e:
        raise SignatureMismatchError(f"cannot verify {zip_path!r}: {e}")


def enforce_dir_sidecars(output_dir: str, key: bytes | None = None,
                         logger=None) -> dict:
    """Policy gate for sidecars already on disk (download backstop).

    - Sidecars present + key configured → verify each with
      :func:`verify_artifact`; any mismatch raises
      :class:`SignatureMismatchError` (fail closed).
    - Sidecars present + NO key → loud ``warning`` (auditable, not
      silent) + proceed unverified (``status: "unverified-no-key"``).
    - No sidecars + NO key → explicit ``warning`` + proceed
      (``status: "no-key-no-signatures"``). Never silently downgrade:
      an unsigned download without a key is a logged event.
    - No sidecars + key → ``info`` (nothing to enforce;
      ``status: "no-signatures"``). Farm-runner binaries are normally
      unsigned (runners never hold the key — ADR-0005), so this is
      routine, not a failure.

    Returns a ``{"status", "count"}`` summary dict.
    """
    log = logger or LOG
    sidecars: list = []
    try:
        for root, _dirs, files in os.walk(output_dir):
            for f in files:
                if f.endswith(SIDECAR_SUFFIX):
                    sidecars.append(os.path.join(root, f))
    except OSError:
        sidecars = []
    sidecars.sort()
    if sidecars and key is not None:
        for sidecar in sidecars:
            sibling = sidecar[: -len(SIDECAR_SUFFIX)]
            sig = read_sidecar(sidecar)
            if sig is None or not os.path.isfile(sibling):
                raise SignatureMismatchError(
                    f"unreadable sidecar or missing sibling: {sidecar!r}")
            if not verify_artifact(sibling, key, sig):
                raise SignatureMismatchError(
                    f"signature mismatch for {sibling!r}")
        log.info("artifact signatures verified: %d sidecar(s) in %s",
                 len(sidecars), output_dir)
        return {"status": "verified", "count": len(sidecars)}
    if sidecars:
        log.warning(
            "ARTIFACT-AUTH: %d signature sidecar(s) present in %s but no "
            "signing key configured (%s) — proceeding WITHOUT verification. "
            "Set a key to enforce.",
            len(sidecars), output_dir, ",".join(ARTIFACT_KEY_ENVS))
        return {"status": "unverified-no-key", "count": len(sidecars)}
    if key is None:
        log.warning(
            "ARTIFACT-AUTH: no signing key configured (%s) and no "
            "signatures present in %s — proceeding without verification "
            "(auditable downgrade).",
            ",".join(ARTIFACT_KEY_ENVS), output_dir)
        return {"status": "no-key-no-signatures", "count": 0}
    log.info("ARTIFACT-AUTH: no signature sidecars in %s (farm-runner "
             "binaries are unsigned by design); channel (authenticated "
             "TLS) is the integrity mechanism.", output_dir)
    return {"status": "no-signatures", "count": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HMAC-SHA256 artifact signer")
    parser.add_argument("file", help="file to sign/verify")
    parser.add_argument("--verify", metavar="HEX", default=None,
                        help="verify against this hex digest instead of signing")
    parser.add_argument("--key-env", default="NIXON_SIGN_KEY",
                        help="env var holding the hex-encoded key (default: NIXON_SIGN_KEY)")
    parser.add_argument("--key-hex", default=None,
                        help="hex-encoded key (overrides --key-env; testing only)")
    args = parser.parse_args(argv)
    if args.key_hex is not None:
        key = bytes.fromhex(args.key_hex)
    else:
        raw = os.environ.get(args.key_env, "")
        if not raw:
            parser.error(f"set --key-hex or env {args.key_env} with hex-encoded key")
            return 2
        key = bytes.fromhex(raw)
    if args.verify is None:
        sig = sign_file(args.file, key)
        sys.stdout.write(sig["hex"] + "\n")
        return 0
    ok = verify_file(args.file, key, {"algo": "hmac-sha256", "hex": args.verify})
    sys.stdout.write("OK\n" if ok else "FAIL\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
