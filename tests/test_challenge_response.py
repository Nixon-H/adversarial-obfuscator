"""Challenge-response must work between two instances with a shared key.

The original per-instance random salt meant two peers could never derive
the same secret, so every cross-party verification failed.
"""
from scripts.runtime.challenge_response import ChallengeResponse


def test_shared_secret_roundtrip():
    key = b"pre-shared-key"
    challenger = ChallengeResponse(shared_secret=key)
    responder = ChallengeResponse(shared_secret=key)

    challenge = challenger.create_challenge("peer-A")
    assert challenge is not None
    response = responder.respond_to_challenge("peer-A", challenge)
    assert response is not None and response.success is True
    assert challenger.verify_response(challenge, response) is True


def test_without_shared_secret_cross_party_fails():
    challenger = ChallengeResponse()
    responder = ChallengeResponse()
    challenge = challenger.create_challenge("peer-A")
    response = responder.respond_to_challenge("peer-A", challenge)
    assert response is not None and response.success is False


def test_tampered_response_is_rejected():
    key = b"pre-shared-key"
    challenger = ChallengeResponse(shared_secret=key)
    responder = ChallengeResponse(shared_secret=key)
    challenge = challenger.create_challenge("peer-A")
    response = responder.respond_to_challenge("peer-A", challenge)
    response.response_data = response.response_data[:-1] + b"\x00"
    assert challenger.verify_response(challenge, response) is False
