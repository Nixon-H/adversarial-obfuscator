"""§9 remote attestation: a challenge-response that can actually refuse.

The review asks for remote attestation. The temptation is to implement
"artefact emits a signed blob, verifier checks the signature" and call it done —
but that passes a recorded blob from an earlier session, and it passes a blob
from a different build. Both are free for an attacker. So every test below is
about a REFUSAL, and the refusals are the feature.

The loopback test at the end runs a real sign/verify round trip with a real
Ed25519 key, because the point of the module is that the two halves agree on
the same canonical bytes.
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator import remote_attest as ra  # noqa: E402

ARTEFACT = b"# artefact bytes\nprint('payload')\n"


def _keys():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey)
    return Ed25519PrivateKey.generate(), None


def _signed(challenge, *, artefact=ARTEFACT, build_id="build-abc", key=None):
    private = key or _keys()[0]
    payload = ra.response_payload(challenge, artefact, build_id, key_id="k1")
    return ra.sign_response(payload, private), private


# ── the happy path must actually work ────────────────────────────────────

def test_a_genuine_response_verifies():
    challenge = ra.make_challenge("verifier-1")
    response, private = _signed(challenge)
    result = ra.verify_response(response, challenge,
                               expected_artefact_bytes=ARTEFACT,
                               public_key=private.public_key())
    assert result["ok"] is True, result["problems"]
    assert result["payload"]["build_id"] == "build-abc"


def test_hmac_scheme_works_for_a_shared_secret_deployment():
    challenge = ra.make_challenge("v")
    payload = ra.response_payload(challenge, ARTEFACT, "b1")
    response = ra.sign_response_hmac(payload, b"shared-secret")
    result = ra.verify_response(response, challenge,
                               expected_artefact_bytes=ARTEFACT,
                               secret=b"shared-secret")
    assert result["ok"] is True, result["problems"]


# ── and every way a responder can cheat must be refused ──────────────────

def test_a_replayed_response_does_not_verify_against_a_new_challenge():
    """The whole point of a nonce: a recorded response is worthless later."""
    first = ra.make_challenge("v")
    response, private = _signed(first)
    second = ra.make_challenge("v")          # different nonce
    result = ra.verify_response(response, second,
                               expected_artefact_bytes=ARTEFACT,
                               public_key=private.public_key())
    assert result["ok"] is False
    assert any("nonce mismatch" in p for p in result["problems"])


def test_a_response_answering_no_challenge_is_refused():
    challenge = ra.make_challenge("v")
    response, private = _signed(challenge)
    result = ra.verify_response(response, None,
                               expected_artefact_bytes=ARTEFACT,
                               public_key=private.public_key())
    assert result["ok"] is False
    assert any("no challenge" in p.lower() for p in result["problems"])


def test_a_response_addressed_to_a_different_verifier_is_refused():
    challenge = ra.make_challenge("verifier-A")
    response, private = _signed(challenge)
    other = dict(challenge)
    other["verifier_id"] = "verifier-B"
    result = ra.verify_response(response, other,
                               expected_artefact_bytes=ARTEFACT,
                               public_key=private.public_key())
    assert result["ok"] is False
    assert any("verifier_id" in p for p in result["problems"])


def test_a_response_for_different_bytes_is_refused():
    """The statement must describe the artefact the verifier holds."""
    challenge = ra.make_challenge("v")
    response, private = _signed(challenge, artefact=b"other bytes")
    result = ra.verify_response(response, challenge,
                               expected_artefact_bytes=ARTEFACT,
                               public_key=private.public_key())
    assert result["ok"] is False
    assert any("artefact digest mismatch" in p for p in result["problems"])


def test_an_edited_payload_breaks_the_signature():
    challenge = ra.make_challenge("v")
    response, private = _signed(challenge)
    response["payload"]["build_id"] = "build-EVIL"
    result = ra.verify_response(response, challenge,
                               expected_artefact_bytes=ARTEFACT,
                               public_key=private.public_key())
    assert result["ok"] is False
    assert any("signature does not verify" in p for p in result["problems"])


def test_a_response_from_a_stale_clock_is_refused():
    challenge = ra.make_challenge("v")
    response, private = _signed(challenge)
    long_ago = int(time.time()) - (ra.MAX_CLOCK_SKEW_SECONDS + 10)
    response["payload"]["responded_at"] = long_ago
    # re-sign so only the clock is wrong, not the signature
    response["signature"] = private.sign(
        ra._canonical(response["payload"])).hex()
    result = ra.verify_response(response, challenge,
                               expected_artefact_bytes=ARTEFACT,
                               public_key=private.public_key())
    assert result["ok"] is False
    assert any("clock" in p for p in result["problems"])


def test_no_verification_key_is_a_refusal_not_a_warning():
    """An unverified statement is not evidence."""
    challenge = ra.make_challenge("v")
    response, _private = _signed(challenge)
    result = ra.verify_response(response, challenge,
                               expected_artefact_bytes=ARTEFACT)
    assert result["ok"] is False
    assert any("no verification key" in p for p in result["problems"])


def test_a_signature_from_the_wrong_key_is_refused():
    challenge = ra.make_challenge("v")
    response, _private = _signed(challenge)
    other = _keys()[0]
    result = ra.verify_response(response, challenge,
                               expected_artefact_bytes=ARTEFACT,
                               public_key=other.public_key())
    assert result["ok"] is False
    assert any("signature does not verify" in p for p in result["problems"])


@pytest.mark.parametrize("absent", [None, {}, "text", 0, []])
def test_a_missing_response_is_a_refusal(absent):
    challenge = ra.make_challenge("v")
    result = ra.verify_response(absent, challenge)
    assert result["ok"] is False


def test_an_unsigned_response_is_refused_when_a_key_is_supplied():
    challenge = ra.make_challenge("v")
    payload = ra.response_payload(challenge, ARTEFACT, "b")
    private = _keys()[0]
    result = ra.verify_response({"payload": payload}, challenge,
                               expected_artefact_bytes=ARTEFACT,
                               public_key=private.public_key())
    assert result["ok"] is False
    assert any("no signature" in p for p in result["problems"])


def test_a_weak_nonce_is_not_silently_accepted():
    """make_challenge must not produce a guessable nonce."""
    nonces = {ra.make_challenge("v")["nonce"] for _ in range(50)}
    assert len(nonces) == 50, "nonces repeat across challenges"
    assert all(len(n) >= 32 for n in nonces), "nonce is too short"


def test_summary_never_raises():
    assert ra.summary(None) == "no attestation"
    challenge = ra.make_challenge("v")
    response, _ = _signed(challenge)
    assert "build=" in ra.summary(response)
