"""§9 remote attestation: the artefact proves what it IS to a verifier.

The review asks for "remote attestation" and this module's honest scope has to
be stated before any code, because the phrase carries more weight than a Python
payload can bear:

  * This is NOT hardware attestation. There is no TPM, no secure enclave, no
    measured boot. A host that controls the CPU and the OS can lie to any
    process running on it, and nothing here changes that.
  * What it DOES provide is a challenge-response in which the artefact proves
    possession of a build-specific secret and states the identity of the code it
    is running, bound together in one signed statement with a fresh nonce. That
    defeats three concrete attacks which are otherwise free:
      - a stale recorded response replayed from an earlier session (nonce);
      - a response minted by a DIFFERENT build being presented as this one
        (build id + artefact digest are inside the signed payload);
      - a response with the payload swapped after signing (the digest covers
        the shipped bytes, and the verifier compares against its own copy of
        what it shipped).

A verifier that accepts a statement without checking the nonce it issued has
implemented a log line, not attestation, so :func:`verify_response` requires
the challenge to be passed in and refuses a mismatch.

Threat model, stated once and not softened below: an attacker who can run code
inside the process can extract the signing key (it is in the artefact) and
forge any statement. This raises the cost of *impersonating a build you do not
have*; it cannot make a compromised host honest.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time

SCHEMA = "nx-attestation/v1"

#: How far a response's timestamp may sit from the verifier's clock before the
#: response is refused. Bounded because a nonce alone does not stop a response
#: that was recorded live and replayed within its validity window if the
#: verifier's nonce store is lost.
MAX_CLOCK_SKEW_SECONDS = 300


class AttestationError(Exception):
    """A response that must not be accepted as evidence."""


def _canonical(payload):
    """Stable bytes to sign.

    Deliberately re-implemented here rather than imported from ``licensing``:
    this module must be usable by a verifier that has none of the build
    toolchain installed, and a shared implementation that drifts is worse than
    two that are each tested. The format is JSON with sorted keys and no
    whitespace, which is what the tests pin.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      default=str).encode("utf-8")


def artefact_digest(data):
    """sha256 of the shipped bytes, hex."""
    return hashlib.sha256(bytes(data)).hexdigest()


def make_challenge(verifier_id="", nonce=None):
    """A nonce the verifier issues and later requires back.

    ``verifier_id`` is free-form (a hostname, an engagement id) and is echoed
    inside the signed payload so a response cannot be re-pointed at a different
    verifier without invalidating the signature.
    """
    return {
        "schema": SCHEMA + "/challenge",
        "nonce": nonce or os.urandom(16).hex(),
        "verifier_id": str(verifier_id or ""),
        "issued_at": int(time.time()),
    }


def response_payload(challenge, artefact_bytes, build_id, *, key_id="",
                     extra=None):
    """The statement that gets signed. Separate from signing so it is testable.

    Every field here is inside the signature. In particular ``nonce`` binds the
    statement to one challenge, and ``artefact_sha256`` binds it to the bytes
    the verifier shipped -- a response cannot be transplanted onto a different
    artefact without the signature failing.
    """
    if not isinstance(challenge, dict) or not challenge.get("nonce"):
        raise AttestationError("no challenge nonce to respond to")
    payload = {
        "schema": SCHEMA,
        "nonce": str(challenge["nonce"]),
        "verifier_id": str(challenge.get("verifier_id", "")),
        "build_id": str(build_id or ""),
        "artefact_sha256": artefact_digest(artefact_bytes),
        "key_id": str(key_id or ""),
        "responded_at": int(time.time()),
    }
    if extra:
        payload["extra"] = dict(extra)
    return payload


def sign_response(payload, private_key):
    """Sign the statement, returning the wire form (payload + signature hex)."""
    signature = private_key.sign(_canonical(payload))
    return {"payload": payload, "signature": signature.hex()}


def sign_response_hmac(payload, secret):
    """HMAC variant for a shared-secret deployment.

    Ed25519 is preferred: a verifier holding an HMAC secret can also MINT
    responses, so HMAC only distinguishes "someone with the secret" from
    "someone without". Offered because a symmetric key is what many build
    pipelines already have, and refusing to support it would push operators to
    something worse (a static shared string).
    """
    mac = hmac.new(bytes(secret), _canonical(payload), hashlib.sha256)
    return {"payload": payload, "mac": mac.hexdigest(), "scheme": "hmac-sha256"}


def verify_response(response, challenge, expected_artefact_bytes=None,
                    public_key=None, secret=None, max_skew=None,
                    now=None):
    """Verifier side. Returns ``{"ok", "problems", "payload"}``.

    Refuses, in this order and for these reasons:

      * no response / no payload        -- nothing was attested;
      * the challenge nonce does not match the one WE issued -- a stale
        recorded response cannot be re-presented;
      * ``verifier_id`` differs         -- cannot re-point at another verifier;
      * the artefact digest differs     -- the bytes we hold are not the bytes
        that were attested, so the statement describes something else;
      * timestamp outside ``max_skew``  -- a response captured long ago;
      * the signature/mac does not verify -- the statement was edited.

    ``expected_artefact_bytes`` is optional only for a verifier that genuinely
    cannot hold the artefact. Passing it is what makes the digest check
    meaningful: without it the verifier is trusting the responder's own claim
    about which bytes it is.
    """
    problems = []
    if not isinstance(response, dict):
        return {"ok": False, "problems": ["no attestation response"],
                "payload": None}
    payload = response.get("payload")
    if not isinstance(payload, dict):
        return {"ok": False, "problems": ["response carries no payload"],
                "payload": None}

    if payload.get("schema") != SCHEMA:
        problems.append("unexpected schema %r" % (payload.get("schema"),))

    issued = str((challenge or {}).get("nonce", ""))
    if not issued:
        problems.append("verifier passed no challenge nonce (refusing: a "
                        "nonce is what makes this a challenge-response)")
    elif str(payload.get("nonce", "")) != issued:
        problems.append("nonce mismatch: response answers a different "
                        "challenge (replay or wrong session)")

    want_verifier = str((challenge or {}).get("verifier_id", ""))
    if str(payload.get("verifier_id", "")) != want_verifier:
        problems.append("verifier_id mismatch: response was addressed to %r"
                        % (payload.get("verifier_id"),))

    if expected_artefact_bytes is not None:
        want = artefact_digest(expected_artefact_bytes)
        if str(payload.get("artefact_sha256", "")) != want:
            problems.append(
                "artefact digest mismatch: attested %s, verifier holds %s"
                % (str(payload.get("artefact_sha256", ""))[:16], want[:16]))

    skew = MAX_CLOCK_SKEW_SECONDS if max_skew is None else int(max_skew)
    try:
        responded = int(payload.get("responded_at", 0))
    except (TypeError, ValueError):
        responded = 0
    if not responded:
        problems.append("response has no usable timestamp")
    else:
        current = int(time.time() if now is None else now)
        if abs(current - responded) > skew:
            problems.append("response is %ds from the verifier's clock "
                            "(limit %ds)" % (abs(current - responded), skew))

    problems.extend(_check_signature(response, payload, public_key, secret))
    return {"ok": not problems, "problems": problems, "payload": payload}


def _check_signature(response, payload, public_key, secret):
    """Return a list of signature problems (empty when one scheme verified)."""
    sig_hex = response.get("signature")
    mac_hex = response.get("mac")
    if public_key is not None and sig_hex:
        try:
            public_key.verify(bytes.fromhex(str(sig_hex)), _canonical(payload))
            return []
        except Exception as exc:
            return ["signature does not verify: %s" % (str(exc)[:120],)]
    if secret is not None and mac_hex:
        want = hmac.new(bytes(secret), _canonical(payload),
                        hashlib.sha256).hexdigest()
        if hmac.compare_digest(want, str(mac_hex)):
            return []
        return ["HMAC does not verify"]
    if public_key is None and secret is None:
        return ["no verification key supplied: refusing to trust an "
                "unverified statement"]
    return ["response carries no signature or mac for the supplied key"]


def summary(response):
    """One line for logs (never raises)."""
    if not isinstance(response, dict):
        return "no attestation"
    payload = response.get("payload") or {}
    return "build=%s artefact=%s nonce=%s" % (
        str(payload.get("build_id", "?"))[:12],
        str(payload.get("artefact_sha256", ""))[:12] or "?",
        str(payload.get("nonce", ""))[:8] or "?")
