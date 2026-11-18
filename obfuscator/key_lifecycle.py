"""§2 explicit key rotation and licence revocation.

Two mechanisms the review names that the existing code did not have. Both are
issuer-controlled, both are SIGNED by the same Ed25519 key that signs licences,
and both are checked by ``licensing.verify`` so a caller cannot skip them by
forgetting to pass an argument twice.

**Key rotation.** ``key_version`` (already signed into each licence) says which
key generation a token was issued for. This module adds the *policy* side: a
signed ``KeyPolicy`` document naming the current generation and the minimum
accepted one. A token for a retired generation is refused even though its
signature still verifies — that is the difference between "validly signed" and
"currently accepted", and it is the whole point of rotation.

    generation 3 is current, minimum 2
      token for 3  -> accepted
      token for 2  -> accepted (grace)
      token for 1  -> refused (retired)

Rotation itself is an operational act: mint a new signing key, bump the
generation, re-issue. ``rotate_keys`` models the derivation so a rotation can be
*tested* without a deployment.

**Revocation.** A signed ``RevocationList`` of licence ids (and optionally
nonces) with an issued-at stamp. ``verify`` refuses a token whose id or nonce
appears. Lists are versioned by ``issued_at`` so a stale list cannot be
replayed to un-revoke a licence: the highest ``issued_at`` seen wins.

**Honest limit, stated here and in the tests.** Both documents are checked
against a public key the *verifier* was given. An attacker who controls the
verification environment can drop the list, point at an old one (defeated by
the issued_at ordering, but only if the newer one is reachable), or patch the
call. This is enforcement by an honest client. Genuine revocation needs the
artefact to reach an issuer — which is the same boundary §4's memory finding and
§9's anti-rollback hit.
"""
from __future__ import annotations

import json
import time

POLICY_SCHEMA = "nx-key-policy/v1"
REVOCATION_SCHEMA = "nx-revocation/v1"


def _sign(payload, private_key):
    from obfuscator.licensing import canonical
    return private_key.sign(canonical(payload))


def _hex(value):
    return value.hex() if isinstance(value, (bytes, bytearray)) else value


class KeyPolicyError(Exception):
    """A key policy that must not be accepted."""


class RevocationError(Exception):
    """A revocation list that must not be accepted, or a revoked token."""


# ── key rotation ─────────────────────────────────────────────────────────

def make_key_policy(current: int, minimum: int, private_key,
                    rotated_at=None) -> str:
    """Sign a key-generation policy. ``current`` >= ``minimum`` >= 0."""
    if not isinstance(current, int) or not isinstance(minimum, int):
        raise KeyPolicyError("current and minimum must be integers")
    if minimum < 0 or current < minimum:
        raise KeyPolicyError(
            "invalid generations: current=%r minimum=%r (need 0 <= minimum "
            "<= current)" % (current, minimum))
    payload = {
        "schema": POLICY_SCHEMA,
        "current": current,
        "minimum": minimum,
        "rotated_at": int(rotated_at if rotated_at is not None else time.time()),
    }
    return json.dumps({"payload": payload, "sig": _hex(_sign(payload, private_key))},
                      separators=(",", ":"))


def read_key_policy(token: str, public_key) -> dict:
    """Verify a policy document and return its payload."""
    from obfuscator.licensing import canonical
    try:
        doc = json.loads(token)
        payload = doc["payload"]
        signature = bytes.fromhex(doc["sig"])
    except (ValueError, KeyError, TypeError) as exc:
        raise KeyPolicyError("not a key policy: %s" % (exc,)) from exc
    if payload.get("schema") != POLICY_SCHEMA:
        raise KeyPolicyError("unexpected schema %r" % (payload.get("schema"),))
    try:
        public_key.verify(signature, canonical(payload))
    except Exception as exc:
        raise KeyPolicyError("policy signature does not verify") from exc
    return payload


def check_generation(token_version, policy: dict) -> None:
    """Raise KeyPolicyError if a token's generation is retired or future-dated.

    A token NEWER than the policy is also refused: it means the verifier is
    holding an stale policy, and accepting a generation it has not seen would
    let a revoked key keep working.
    """
    current = int(policy["current"])
    minimum = int(policy["minimum"])
    if token_version is None:
        raise KeyPolicyError(
            "licence has no key_version but a key policy is in force "
            "(current=%d)" % (current,))
    got = int(token_version)
    if got < minimum:
        raise KeyPolicyError(
            "licence key generation %d is retired (minimum accepted is %d)"
            % (got, minimum))
    if got > current:
        raise KeyPolicyError(
            "licence key generation %d is newer than this build knows about "
            "(%d); update the artefact" % (got, current))


def rotate_keys(old_seed_hex: str, new_seed_hex: str, generation: int):
    """Derive the next-generation signing key and its policy.

    Models the operational act so a rotation can be tested: the new key is
    independent (a fresh seed, not derived from the old one), the policy names
    the new generation, and the previous generation is accepted for one grace
    step.
    """
    from obfuscator.licensing import private_key_from_hex
    if generation < 1:
        raise KeyPolicyError("generation must be >= 1")
    old_key = private_key_from_hex(old_seed_hex)
    new_key = private_key_from_hex(new_seed_hex)
    if old_key.public_key().public_bytes_raw() == \
            new_key.public_key().public_bytes_raw():
        raise KeyPolicyError(
            "rotation needs a DIFFERENT key: the new seed produced the same "
            "public key as the old one")
    policy = make_key_policy(generation, generation - 1, new_key)
    return {"old_key": old_key, "new_key": new_key, "policy": policy}


# ── revocation ───────────────────────────────────────────────────────────

def make_revocation_list(licence_ids=(), nonces=(), private_key=None,
                         issued_at=None) -> str:
    """Sign a revocation list. Empty lists are allowed and still signed."""
    payload = {
        "schema": REVOCATION_SCHEMA,
        "issued_at": int(issued_at if issued_at is not None else time.time()),
        "licence_ids": sorted(str(x) for x in licence_ids),
        "nonces": sorted(str(x) for x in nonces),
    }
    if private_key is None:
        return json.dumps({"payload": payload, "sig": ""},
                          separators=(",", ":"))
    return json.dumps({"payload": payload,
                       "sig": _hex(_sign(payload, private_key))},
                      separators=(",", ":"))


def read_revocation_list(token: str, public_key) -> dict:
    """Verify a revocation list and return its payload.

    An unsigned list is refused: an attacker who can edit an unsigned list
    could revoke everyone, or un-revoke themselves.
    """
    from obfuscator.licensing import canonical
    try:
        doc = json.loads(token)
        payload = doc["payload"]
        raw_sig = doc["sig"]
    except (ValueError, KeyError, TypeError) as exc:
        raise RevocationError("not a revocation list: %s" % (exc,)) from exc
    if not raw_sig:
        raise RevocationError("revocation list is unsigned")
    if payload.get("schema") != REVOCATION_SCHEMA:
        raise RevocationError(
            "unexpected schema %r" % (payload.get("schema"),))
    try:
        public_key.verify(bytes.fromhex(raw_sig), canonical(payload))
    except Exception as exc:
        raise RevocationError("revocation list signature does not verify") from exc
    return payload


def check_revoked(payload: dict, revocation: dict,
                  previous_issued_at: int = 0) -> None:
    """Raise RevocationError if this licence is revoked.

    ``previous_issued_at`` guards against replaying an OLDER list to
    un-revoke: a list stamped before the newest one seen is refused instead of
    being trusted. That is the only defence a client can offer against list
    rollback, and it only works if the newer list is reachable.
    """
    issued = int(revocation.get("issued_at", 0))
    if issued < int(previous_issued_at):
        raise RevocationError(
            "revocation list is older (%d) than one already seen (%d); "
            "refusing to accept a rolled-back list"
            % (issued, int(previous_issued_at)))
    lid = str(payload.get("licence_id", ""))
    nonce = str(payload.get("nonce", ""))
    if lid and lid in revocation.get("licence_ids", ()):
        raise RevocationError("licence %r is revoked" % (lid,))
    if nonce and nonce in revocation.get("nonces", ()):
        raise RevocationError("licence token is revoked (nonce match)")
