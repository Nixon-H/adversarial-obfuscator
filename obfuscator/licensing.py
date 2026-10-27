"""licensing.py

Purpose:
    A licence token you can sign, hand to a customer, and verify
    offline — the client half of "the client cannot do useful work
    without a server-issued key".

Design:
    A token is a small JSON document plus an Ed25519 signature over its
    canonical form::

        {"payload": {...}, "sig": "<hex>"}

    Canonical means ``json.dumps(payload, sort_keys=True,
    separators=(",", ":"))`` — the same bytes on both sides, no
    whitespace ambiguity.

    Signing is asymmetric on purpose. The build (or a licence server)
    holds the private key; the verifier holds only the public key. A
    customer who extracts the public key from an artefact can check a
    token but cannot mint one — which is the whole point, and the reason
    this does not use the shared HMAC key.

Why offline first:
    A server-issued token needs the customer to reach the server. A
    signed, expiring token works on an air-gapped machine today, and is
    the same token a server would issue later — only the issuer changes.

Not done here:
    * Issuing from a service, revocation lists, and per-customer
      accounts. Those need a deployment, not a module.
    * Checking the token *inside the artefact*. The emitted loader runs
      in the customer's interpreter with no third-party packages, so it
      cannot import ``cryptography``; the loader needs a small
      pure-Python Ed25519 verify (or the check stays build-side). Stated
      plainly rather than pretended.
"""

from __future__ import annotations

import argparse
import hashlib
import json

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Iterable, Optional

SCHEMA = "nixon-licence/1"

#: Env var holding the issuer's Ed25519 private key (hex 32-byte seed).
PRIVATE_KEY_ENV = "NIXON_LICENCE_PRIVATE_KEY"
#: Env var holding the pinned Ed25519 public key (hex 32 bytes).
PUBLIC_KEY_ENV = "NIXON_LICENCE_PUBLIC_KEY"


class LicenceError(Exception):
    """A token that must not be accepted, with the reason why."""


@dataclass(frozen=True)
class Licence:
    licence_id: str
    customer: str
    issued_at: float
    expires_at: float
    features: tuple = field(default_factory=tuple)
    hwid: Optional[str] = None
    watermark: Optional[str] = None
    notes: Optional[str] = None
    # Per-licence secret.  The payload key is bound to it at build time
    # (--licence-token) and re-derived from it at run time, so an artefact
    # without its token decrypts to garbage.  It is a *capability*, not a
    # claim: forging a token with other material just yields a key that
    # does not match the ciphertext, so the signature is what stops
    # re-issuing, not what stops decryption.
    key_material: Optional[str] = None

    def to_payload(self) -> dict:
        payload = {
            "schema": SCHEMA,
            "licence_id": self.licence_id,
            "customer": self.customer,
            "issued_at": int(self.issued_at),
            "expires_at": int(self.expires_at),
            "features": sorted(self.features),
        }
        if self.hwid:
            payload["hwid"] = self.hwid
        if self.watermark:
            payload["watermark"] = self.watermark
        if self.notes:
            payload["notes"] = self.notes
        if self.key_material:
            payload["key_material"] = self.key_material
        return payload

    @classmethod
    def from_payload(cls, payload: dict) -> "Licence":
        try:
            return cls(
                licence_id=payload["licence_id"],
                customer=payload["customer"],
                issued_at=float(payload["issued_at"]),
                expires_at=float(payload["expires_at"]),
                features=tuple(payload.get("features", ())),
                hwid=payload.get("hwid"),
                watermark=payload.get("watermark"),
                notes=payload.get("notes"),
                key_material=payload.get("key_material"),
            )
        except (KeyError, TypeError, ValueError) as e:
            raise LicenceError(f"malformed licence payload: {e}") from e

    def expired(self, now: Optional[float] = None) -> bool:
        return (now if now is not None else time.time()) >= self.expires_at


def canonical(payload: dict) -> bytes:
    """The exact bytes that get signed — same on both sides."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


# ── keys ─────────────────────────────────────────────────────────────────

def _ed25519():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )
    except ImportError as e:  # pragma: no cover - dependency is pinned
        raise LicenceError(
            "licensing needs the 'cryptography' package (it is in requirements.lock)"
        ) from e
    return Ed25519PrivateKey, Ed25519PublicKey


def private_key_from_hex(seed_hex: str):
    Ed25519PrivateKey, _ = _ed25519()
    raw = bytes.fromhex(seed_hex.strip())
    if len(raw) != 32:
        raise LicenceError(f"private key must be 32 bytes, got {len(raw)}")
    return Ed25519PrivateKey.from_private_bytes(raw)


def public_key_from_hex(pub_hex: str):
    _, Ed25519PublicKey = _ed25519()
    raw = bytes.fromhex(pub_hex.strip())
    if len(raw) != 32:
        raise LicenceError(f"public key must be 32 bytes, got {len(raw)}")
    return Ed25519PublicKey.from_public_bytes(raw)


def public_key_hex(private_key) -> str:
    from cryptography.hazmat.primitives import serialization
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def resolve_private_key(explicit: Optional[str] = None):
    raw = explicit or os.environ.get(PRIVATE_KEY_ENV, "")
    if not raw:
        raise LicenceError(
            f"no private key: pass --key-hex or set {PRIVATE_KEY_ENV}"
        )
    return private_key_from_hex(raw)


def resolve_public_key(explicit: Optional[str] = None):
    raw = explicit or os.environ.get(PUBLIC_KEY_ENV, "")
    if not raw:
        raise LicenceError(
            f"no public key: pass --pubkey-hex or set {PUBLIC_KEY_ENV}"
        )
    return public_key_from_hex(raw)


# ── issue / verify ───────────────────────────────────────────────────────

def issue(licence: Licence, private_key) -> str:
    """Sign a licence and return the token.

    A licence without key material gets a fresh 32-byte secret here, so
    every issued token can bind a payload key.  Pass an explicit value
    only when re-issuing the same licence (the key material is what an
    already-shipped artefact was built against; changing it invalidates
    that build).
    """
    payload = licence.to_payload()
    if not payload.get("key_material"):
        # Derived, not random: issuing the same licence twice must produce
        # the same token (the documented property), and the material has to
        # stay secret -- both hold when it is a hash of the issuer's seed.
        # Licence is frozen, so the value lives in the payload we sign.
        try:
            seed = private_key.private_bytes_raw()
        except Exception:  # pragma: no cover - non-cryptography key objects
            seed = b""
        if not seed:  # pragma: no cover - keeps the derivation total
            raise LicenceError("issuer key exposes no raw seed to derive from")
        payload["key_material"] = hashlib.sha256(
            b"nx-licence-key:" + licence.licence_id.encode("utf-8")
            + b":" + licence.customer.encode("utf-8") + b":" + seed).hexdigest()
    signed = canonical(payload)
    signature = private_key.sign(signed)
    return json.dumps({
        "payload": payload,
        "sig": signature.hex(),
    }, separators=(",", ":"))


def verify(
    token: str,
    public_key,
    *,
    now: Optional[float] = None,
    hwid: Optional[str] = None,
    required_features: Iterable[str] = (),
) -> Licence:
    """Verify a token or raise LicenceError saying exactly why."""
    try:
        doc = json.loads(token)
        payload = doc["payload"]
        signature = bytes.fromhex(doc["sig"])
    except (ValueError, KeyError, TypeError) as e:
        raise LicenceError(f"not a licence token: {e}") from e

    if payload.get("schema") != SCHEMA:
        raise LicenceError(f"unsupported licence schema: {payload.get('schema')!r}")

    try:
        public_key.verify(signature, canonical(payload))
    except Exception as e:  # InvalidSignature and friends
        raise LicenceError("signature does not verify") from e

    licence = Licence.from_payload(payload)
    moment = now if now is not None else time.time()

    if licence.issued_at > moment + 300:
        raise LicenceError(
            f"licence is not valid yet (issued {int(licence.issued_at)}, now {int(moment)})"
        )
    if licence.expired(moment):
        raise LicenceError(
            f"licence expired at {int(licence.expires_at)} (now {int(moment)})"
        )
    if licence.hwid and hwid is not None and licence.hwid != hwid:
        raise LicenceError(
            f"licence is bound to a different machine (want {licence.hwid!r})"
        )
    missing = sorted(set(required_features) - set(licence.features))
    if missing:
        raise LicenceError(f"licence does not grant: {', '.join(missing)}")
    return licence


# ── files ────────────────────────────────────────────────────────────────

def load_token(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def save_token(token: str, path: str) -> str:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(token + "\n")
    os.replace(tmp, path)
    return path


# ── CLI ──────────────────────────────────────────────────────────────────

def _parse_features(text: Optional[str]) -> tuple:
    if not text:
        return ()
    return tuple(sorted({f.strip() for f in text.split(",") if f.strip()}))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m obfuscator.licensing",
        description="Issue and verify offline licence tokens (Ed25519).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_issue = sub.add_parser("issue", help="sign a licence token")
    p_issue.add_argument("--key-hex", default=None, help=f"issuer seed (hex); default ${PRIVATE_KEY_ENV}")
    p_issue.add_argument("--customer", required=True)
    p_issue.add_argument("--licence-id", default=None, help="default: generated from customer+time")
    p_issue.add_argument("--days", type=float, default=30.0, help="validity in days (default 30)")
    p_issue.add_argument("--features", default=None, help="comma-separated")
    p_issue.add_argument("--hwid", default=None, help="bind to this machine id")
    p_issue.add_argument("--watermark", default=None, help="per-customer watermark id")
    p_issue.add_argument("--notes", default=None)
    p_issue.add_argument("--out", default=None, help="write the token here")

    p_verify = sub.add_parser("verify", help="check a token")
    p_verify.add_argument("token", help="token file")
    p_verify.add_argument("--pubkey-hex", default=None, help=f"pinned public key; default ${PUBLIC_KEY_ENV}")
    p_verify.add_argument("--hwid", default=None)
    p_verify.add_argument("--require", default=None, help="comma-separated features required")

    p_show = sub.add_parser("pubkey", help="print the public key for a seed")
    p_show.add_argument("--key-hex", default=None)

    opts = parser.parse_args(argv)

    try:
        if opts.cmd == "issue":
            private_key = resolve_private_key(opts.key_hex)
            now = time.time()
            licence_id = opts.licence_id or f"{opts.customer}-{int(now)}"
            licence = Licence(
                licence_id=licence_id,
                customer=opts.customer,
                issued_at=now,
                expires_at=now + opts.days * 86400,
                features=_parse_features(opts.features),
                hwid=opts.hwid,
                watermark=opts.watermark,
                notes=opts.notes,
            )
            token = issue(licence, private_key)
            if opts.out:
                save_token(token, opts.out)
                print(f"wrote {opts.out} (licence {licence_id}, expires {int(licence.expires_at)})")
            else:
                print(token)
            return 0

        if opts.cmd == "verify":
            public_key = resolve_public_key(opts.pubkey_hex)
            licence = verify(
                load_token(opts.token),
                public_key,
                hwid=opts.hwid,
                required_features=_parse_features(opts.require),
            )
            print(
                f"OK licence={licence.licence_id} customer={licence.customer!r} "
                f"expires={int(licence.expires_at)} features={','.join(licence.features) or '-'}"
            )
            return 0

        if opts.cmd == "pubkey":
            print(public_key_hex(resolve_private_key(opts.key_hex)))
            return 0
    except LicenceError as e:
        print(f"REJECTED: {e}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
