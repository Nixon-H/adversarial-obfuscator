#!/usr/bin/env python3
"""Artifact signing: HMAC-SHA256 (shared key) and Ed25519 (per-farm key).

``sign_file(path, key)`` computes HMAC-SHA256 over raw file bytes and
returns ``{'algo': 'hmac-sha256', 'hex': ...}``. ``verify_file`` uses
constant-time :func:`hmac.compare_digest`.

Bound signatures (ADR-0005): ``sign_artifact(path, key, metadata)``
binds file bytes + repo/commit/build-id/platform metadata
(``hmac-sha256-binding-v1``); ``verify_artifact`` verifies bound and
legacy sigs; ``verify_zip_sidecars`` / ``enforce_dir_sidecars`` are the
download-side fail-closed gates.

Ed25519 (the per-farm key fix): ``sign_artifact_ed25519`` signs the
same ``file bytes + 0x00 + canonical(metadata)`` with a FARM's PRIVATE
key; the operator pins the farm's PUBLIC key.  A verifier that holds
only public keys can check an artifact but cannot MINT one -- which is
exactly what the shared HMAC key could not guarantee, because every
verifier that held the shared key could forge a sidecar for any farm.

CLI::

    python3 -m scripts.artifact_sign <file> [--verify HEX]
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import logging
import os
import platform
import sys
import time
import zipfile

LOG = logging.getLogger(__name__)

#: Algo tag for metadata-bound signatures (ADR-0005). Legacy bytes-only
#: signatures keep ``hmac-sha256`` and still verify via
#: :func:`verify_artifact` (weaker: no metadata binding — documented).
BINDING_ALGO = "hmac-sha256-binding-v1"

#: Algo tag for Ed25519 metadata-bound signatures.  Asymmetric: the
#: signer holds a private key, the verifier holds only the public one.
ED25519_ALGO = "ed25519-binding-v1"

#: Sidecar filename suffix (``<artifact>.sig.json``), shared by the
#: package step, the farm upload path, and the download verifier.
SIDECAR_SUFFIX = ".sig.json"

#: How long a signed artifact sidecar stays valid.  Bounds replay: a
#: captured sidecar cannot be presented indefinitely.  Override with
#: NIXON_ARTIFACT_TTL (seconds); 0 means "no expiry".
DEFAULT_ARTIFACT_TTL_SECONDS = 30 * 24 * 3600

#: Key env vars, precedence order. ``NIXON_SIGN_KEY`` is the pre-existing
#: convention (CLI default, ``SECURITY.md``); ``NIXON_ARTIFACT_KEY_HEX``
#: is the explicit farm-artifact name (ADR-0005). Both hold hex.
ARTIFACT_KEY_ENVS = ("NIXON_ARTIFACT_KEY_HEX", "NIXON_SIGN_KEY")

#: Env var holding the farm's Ed25519 PRIVATE key (hex 32-byte seed).
ED25519_PRIVATE_KEY_ENV = "NIXON_ARTIFACT_ED25519_KEY"

#: Env var holding the pinned Ed25519 PUBLIC key (hex 32 bytes).
ED25519_PUBLIC_KEY_ENV = "NIXON_ARTIFACT_ED25519_PUBKEY"

#: Env var holding a JSON map of farm id -> hex public key.  A verifier
#: pins the farms it trusts; a sidecar from an unknown farm fails.
ED25519_KEYS_ENV = "NIXON_ARTIFACT_ED25519_KEYS"


def _ed25519():
    """Return the Ed25519 primitives, or ``None`` when unavailable.

    ``cryptography`` is a pinned dependency, but the import is lazy so
    the module stays importable without it (the HMAC path still works).
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            PublicFormat,
        )
    except Exception:
        return None
    return (Ed25519PrivateKey, Ed25519PublicKey, Encoding, PublicFormat)


def ed25519_key_id(public_key: bytes) -> str:
    """A short, stable fingerprint of an Ed25519 public key.

    The id travels in the sidecar so a verifier can tell WHICH farm
    signed without holding anything secret.
    """
    return hashlib.sha256(bytes(public_key)).hexdigest()[:16]


def _ed25519_private_from_hex(seed_hex: str):
    """Build a private key from a hex seed; ``None`` when unusable."""
    parts = _ed25519()
    if parts is None:
        return None
    Ed25519PrivateKey = parts[0]
    try:
        seed = bytes.fromhex(str(seed_hex).strip())
    except (ValueError, TypeError):
        return None
    if len(seed) != 32:
        return None
    try:
        return Ed25519PrivateKey.from_private_bytes(seed)
    except Exception:
        return None


def _ed25519_public_from_hex(pub_hex: str):
    """Build a public key from hex; ``None`` when unusable."""
    parts = _ed25519()
    if parts is None:
        return None
    Ed25519PublicKey = parts[1]
    try:
        raw = bytes.fromhex(str(pub_hex).strip())
    except (ValueError, TypeError):
        return None
    if len(raw) != 32:
        return None
    try:
        return Ed25519PublicKey.from_public_bytes(raw)
    except Exception:
        return None


def ed25519_public_hex(private_key) -> str:
    """The hex-encoded public key for a private key (for pinning)."""
    parts = _ed25519()
    if parts is None:
        return ""
    (_, _, Encoding, PublicFormat) = parts
    return private_key.public_key().public_bytes(
        Encoding.Raw, PublicFormat.Raw).hex()


def resolve_ed25519_private_key(env=None):
    """The configured farm private key, or ``None``.

    Reads :data:`ED25519_PRIVATE_KEY_ENV` (hex 32-byte seed).  Never
    raises: an unconfigured or malformed key means "sign with HMAC or
    not at all", decided by the caller.
    """
    source = os.environ if env is None else env
    try:
        raw = source.get(ED25519_PRIVATE_KEY_ENV, "")
    except Exception:
        return None
    if not raw or not str(raw).strip():
        return None
    return _ed25519_private_from_hex(str(raw).strip())


def resolve_ed25519_public_keys(env=None) -> dict:
    """The pinned public keys, as ``{key_id: public_key_bytes}``.

    Two sources: :data:`ED25519_PUBLIC_KEY_ENV` (a single hex public
    key) and :data:`ED25519_KEYS_ENV` (a JSON map of farm id -> hex
    public key).  Both may be set; the map wins on collision.
    """
    source = os.environ if env is None else env
    keys: dict = {}
    try:
        single = source.get(ED25519_PUBLIC_KEY_ENV, "")
    except Exception:
        single = ""
    if single and str(single).strip():
        try:
            raw = bytes.fromhex(str(single).strip())
        except (ValueError, TypeError):
            raw = b""
        if len(raw) == 32:
            keys[ed25519_key_id(raw)] = raw
    try:
        blob = source.get(ED25519_KEYS_ENV, "")
    except Exception:
        blob = ""
    if blob and str(blob).strip():
        try:
            mapping = json.loads(str(blob).strip())
        except (ValueError, TypeError):
            mapping = {}
        if isinstance(mapping, dict):
            for farm_id, value in mapping.items():
                try:
                    raw = bytes.fromhex(str(value).strip())
                except (ValueError, TypeError):
                    continue
                if len(raw) == 32:
                    keys[ed25519_key_id(raw)] = raw
    return keys


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
    ``NIXON_BUILD_ID``, ``NIXON_FARM_ID``) plus host facts. Unknown
    fields are ``""`` — documented: the MAC authenticates the *claim*,
    it cannot make an empty environment truthful. ``extra`` overrides
    on collision.

    Two fields close the limits ADR-0005 recorded:

    * ``farm`` — which farm produced the artifact.  The MAC covers it,
      so a sidecar minted by one farm cannot be presented as another
      farm's, and a verifier can pin it with
      ``expected={"farm": "..."}``.
    * ``issued_at`` / ``expires_at`` — a replay window.  ``expires_at``
      is ``issued_at`` plus ``NIXON_ARTIFACT_TTL`` seconds (default 30
      days).  A sidecar past its window no longer verifies, so a
      captured sidecar cannot be replayed indefinitely.
    """
    issued = int(time.time())
    ttl = os.environ.get("NIXON_ARTIFACT_TTL", "")
    try:
        ttl_s = int(ttl) if ttl else DEFAULT_ARTIFACT_TTL_SECONDS
    except (TypeError, ValueError):
        ttl_s = DEFAULT_ARTIFACT_TTL_SECONDS
    meta = {
        "repo": os.environ.get("GITHUB_REPOSITORY", ""),
        "commit": os.environ.get("GITHUB_SHA", ""),
        "build_id": os.environ.get("NIXON_BUILD_ID", ""),
        "farm": os.environ.get("NIXON_FARM_ID", ""),
        "platform": sys.platform,
        "python": platform.python_version(),
        "issued_at": issued,
        "expires_at": issued + max(0, ttl_s),
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


def sign_artifact_ed25519(path: str, private_key, metadata: dict | None = None) -> dict:
    """Sign ``path`` bound to ``metadata`` with an Ed25519 PRIVATE key.

    The signed message is the same as the HMAC path's
    ``file bytes + 0x00 + canonical(metadata)``, so the two schemes
    cover the same material; only the key handling differs.  Shape:
    ``{"algo", "sig", "key_id", "metadata", "file"}``.

    A verifier needs only the matching PUBLIC key, so it can check an
    artifact without being able to mint one.
    """
    if private_key is None:
        raise ValueError("private_key is required")
    meta = dict(metadata) if isinstance(metadata, dict) else default_metadata()
    with open(path, "rb") as f:
        data = f.read()
    message = data + b"\x00" + _canonical_metadata_bytes(meta)
    signature = private_key.sign(message)
    pub = ed25519_public_hex(private_key)
    return {
        "algo": ED25519_ALGO,
        "sig": base64.b64encode(signature).decode("ascii"),
        "key_id": ed25519_key_id(bytes.fromhex(pub)) if pub else "",
        "metadata": meta,
        "file": os.path.basename(path),
    }


def _ed25519_message(data: bytes, meta: dict) -> bytes:
    """The signed message: file bytes + 0x00 + canonical(metadata)."""
    return data + b"\x00" + _canonical_metadata_bytes(meta)


def verify_ed25519_bytes(data: bytes, public_key: bytes, sig: dict,
                         expected: dict | None = None) -> bool:
    """Verify an Ed25519 sidecar over raw artifact bytes.

    Fails closed: a wrong key, a malformed signature, an unknown algo,
    a missing metadata binding, an expired sidecar, or a metadata pin
    mismatch all return ``False``.
    """
    parts = _ed25519()
    if parts is None:
        return False
    Ed25519PublicKey = parts[1]
    if not isinstance(sig, dict) or sig.get("algo") != ED25519_ALGO:
        return False
    meta = sig.get("metadata")
    if not isinstance(meta, dict):
        return False
    expires = meta.get("expires_at")
    if expires is not None:
        try:
            if int(expires) < int(time.time()):
                return False
        except (TypeError, ValueError):
            return False
    if expected:
        try:
            for k, v in dict(expected).items():
                if meta.get(k) != v:
                    return False
        except Exception:
            return False
    encoded = sig.get("sig")
    if not isinstance(encoded, str) or not encoded:
        return False
    try:
        signature = base64.b64decode(encoded, validate=True)
    except Exception:
        return False
    if not isinstance(public_key, (bytes, bytearray)) or len(public_key) != 32:
        return False
    try:
        key = Ed25519PublicKey.from_public_bytes(bytes(public_key))
    except Exception:
        return False
    try:
        key.verify(signature, _ed25519_message(bytes(data), meta))
    except Exception:
        return False
    return True


def verify_artifact_ed25519(path: str, public_key: bytes, sig: dict,
                            expected: dict | None = None) -> bool:
    """Verify an Ed25519 sidecar with a pinned PUBLIC key.

    Fails closed: see :func:`verify_ed25519_bytes`.
    """
    try:
        with open(path, "rb") as f:
            data = f.read()
    except (OSError, ValueError):
        return False
    return verify_ed25519_bytes(data, public_key, sig, expected)


def sign_artifact_auto(path: str, key: bytes | None = None,
                        metadata: dict | None = None) -> dict | None:
    """Sign with Ed25519 when a private key is configured, else HMAC.

    Returns ``None`` when neither key is available, so the caller can
    proceed unsigned (auditable) rather than fail.
    """
    private_key = resolve_ed25519_private_key()
    if private_key is not None:
        return sign_artifact_ed25519(path, private_key, metadata)
    if key:
        return sign_artifact(path, key, metadata)
    return None


def verify_artifact(path: str, key: bytes, sig: dict,
                     expected: dict | None = None) -> bool:
    """Verify a bound (or legacy) sig dict against ``path`` + ``key``.

    ``BINDING_ALGO`` sigs recompute the metadata-bound MAC; the bound
    ``metadata`` must be a dict or verification fails. Legacy
    ``hmac-sha256`` sigs (bytes-only, no binding) still verify via
    :func:`verify_file` — weaker, documented in ADR-0005. When
    ``expected`` is given, every ``expected`` item must equal the sig's
    bound metadata (subset match, e.g. pin ``build_id``).

    ``ED25519_ALGO`` sigs are verified with the pinned PUBLIC key
    (``key``): the same call shape, a different key kind.  The algo tag
    decides, so a caller cannot accidentally check an Ed25519 sidecar
    with an HMAC key.
    """
    if not isinstance(sig, dict):
        return False
    algo = sig.get("algo")
    if algo == ED25519_ALGO:
        return verify_artifact_ed25519(path, key, sig, expected)
    if algo == BINDING_ALGO:
        meta = sig.get("metadata")
        if not isinstance(meta, dict):
            return False
        # Replay window: a sidecar past its expiry no longer verifies.
        # The MAC covers ``expires_at``, so it cannot be edited forward.
        expires = meta.get("expires_at")
        if expires is not None:
            try:
                if int(expires) < int(time.time()):
                    return False
            except (TypeError, ValueError):
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


def verify_zip_sidecars(zip_path: str, key: bytes,
                        expected: dict | None = None) -> int:
    """Verify every ``*.sig.json`` member against its sibling zip member.

    The sibling of ``foo.sig.json`` is ``foo`` (same directory inside the
    zip). Returns the number of verified sidecars (``0`` when the zip
    carries none). Raises :class:`SignatureMismatchError` fail-closed on
    any mismatch, unreadable sidecar, or missing sibling — the caller
    must not extract on raise.

    ``expected`` is an optional metadata pin (e.g. ``{"farm": "..."}``):
    every sidecar must carry those values, so a sidecar minted by a
    different farm is a mismatch rather than a pass.
    """
    if not isinstance(key, (bytes, bytearray)) or not key:
        # An HMAC key is not required when the sidecars are Ed25519
        # signed and a public key is pinned: the asymmetric path needs
        # no shared secret.
        if not resolve_ed25519_public_keys():
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
                if algo == ED25519_ALGO:
                    # Asymmetric: the pinned PUBLIC key verifies, and
                    # the key id in the sidecar must be one we pin.
                    pinned = resolve_ed25519_public_keys()
                    claimed_id = sig.get("key_id")
                    if not pinned:
                        raise SignatureMismatchError(
                            f"sidecar {sidecar_name!r} is Ed25519-signed but no "
                            f"public key is pinned ({ED25519_PUBLIC_KEY_ENV} / "
                            f"{ED25519_KEYS_ENV})")
                    pub = pinned.get(claimed_id)
                    if pub is None:
                        raise SignatureMismatchError(
                            f"sidecar {sidecar_name!r} is signed by an unpinned "
                            f"key {claimed_id!r}")
                    if not verify_ed25519_bytes(data, pub, sig, expected):
                        raise SignatureMismatchError(
                            f"Ed25519 signature mismatch for {sibling!r}")
                    count += 1
                    continue
                if algo == BINDING_ALGO:
                    if not key:
                        raise SignatureMismatchError(
                            f"sidecar {sidecar_name!r} is HMAC-signed but no "
                            f"HMAC key is configured")
                    meta = sig.get("metadata")
                    if not isinstance(meta, dict):
                        raise SignatureMismatchError(
                            f"sidecar {sidecar_name!r} has no metadata binding")
                    # Replay window: a sidecar past its expiry does not
                    # verify.  The MAC covers expires_at, so it cannot be
                    # edited forward.
                    expires = meta.get("expires_at")
                    if expires is not None:
                        try:
                            if int(expires) < int(time.time()):
                                raise SignatureMismatchError(
                                    f"sidecar {sidecar_name!r} expired")
                        except (TypeError, ValueError):
                            raise SignatureMismatchError(
                                f"sidecar {sidecar_name!r} has a malformed expiry")
                    if expected:
                        try:
                            for _k, _v in dict(expected).items():
                                if meta.get(_k) != _v:
                                    raise SignatureMismatchError(
                                        f"sidecar {sidecar_name!r} does not "
                                        f"match the pinned {_k!r}")
                        except SignatureMismatchError:
                            raise
                        except Exception as _e:
                            raise SignatureMismatchError(
                                f"sidecar {sidecar_name!r} pin check failed: {_e}")
                    actual = _bound_hex(data, bytes(key), meta)
                elif algo == "hmac-sha256":
                    if not key:
                        raise SignatureMismatchError(
                            f"sidecar {sidecar_name!r} is HMAC-signed but no "
                            f"HMAC key is configured")
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
    if sidecars and (key is not None or resolve_ed25519_public_keys()):
        pinned = resolve_ed25519_public_keys()
        for sidecar in sidecars:
            sibling = sidecar[: -len(SIDECAR_SUFFIX)]
            sig = read_sidecar(sidecar)
            if sig is None or not os.path.isfile(sibling):
                raise SignatureMismatchError(
                    f"unreadable sidecar or missing sibling: {sidecar!r}")
            if isinstance(sig, dict) and sig.get("algo") == ED25519_ALGO:
                pub = pinned.get(sig.get("key_id"))
                if pub is None:
                    raise SignatureMismatchError(
                        f"sidecar {sidecar!r} is signed by an unpinned key "
                        f"{sig.get('key_id')!r}")
                if not verify_artifact_ed25519(sibling, pub, sig):
                    raise SignatureMismatchError(
                        f"Ed25519 signature mismatch for {sibling!r}")
                continue
            if key is None:
                raise SignatureMismatchError(
                    f"sidecar {sidecar!r} needs the HMAC key, which is not "
                    f"configured")
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
