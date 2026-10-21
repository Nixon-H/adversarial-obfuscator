"""The artifact sidecar needs a farm identity and a replay window.

ADR-0005 recorded the limits of the shared-secret scheme: a sidecar
carried no per-farm identity, no rotation and no replay expiry, so a
captured sidecar could be replayed indefinitely and one farm's sidecar
could be presented as another's.

Two of those are now closed:

* the signed metadata carries the **farm** that minted it, so a verifier
  can pin it (``expected={"farm": ...}``) and a sidecar from one farm
  does not verify as another's;
* the signed metadata carries **issued_at / expires_at**, so a sidecar
  past its window no longer verifies.  The MAC covers both, so neither
  can be edited forward.
"""
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.artifact_sign import (  # noqa: E402
    default_metadata,
    sign_artifact,
    verify_artifact,
)

KEY = bytes(range(32))


@pytest.fixture
def artifact(tmp_path):
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"artifact-bytes")
    return str(path)


def test_the_metadata_carries_the_farm(artifact, monkeypatch):
    monkeypatch.setenv("NIXON_FARM_ID", "farm-eu-1")
    sig = sign_artifact(artifact, KEY)
    assert sig["metadata"]["farm"] == "farm-eu-1"


def test_a_sidecar_from_another_farm_does_not_verify(artifact, monkeypatch):
    monkeypatch.setenv("NIXON_FARM_ID", "farm-eu-1")
    sig = sign_artifact(artifact, KEY)
    # The same bytes, presented as another farm's artifact.
    assert verify_artifact(artifact, KEY, sig, expected={"farm": "farm-eu-2"}) is False
    assert verify_artifact(artifact, KEY, sig, expected={"farm": "farm-eu-1"}) is True


def test_the_metadata_carries_a_replay_window(artifact):
    meta = default_metadata()
    assert isinstance(meta["issued_at"], int)
    assert meta["expires_at"] > meta["issued_at"]


def test_an_expired_sidecar_does_not_verify(artifact, monkeypatch):
    monkeypatch.setenv("NIXON_ARTIFACT_TTL", "60")
    sig = sign_artifact(artifact, KEY)
    assert verify_artifact(artifact, KEY, sig) is True
    # Move the window into the past.  The MAC covers expires_at, so the
    # only honest way to expire a sidecar is to re-sign it.
    past = dict(sig["metadata"])
    past["expires_at"] = int(time.time()) - 1
    resigned = sign_artifact(artifact, KEY, metadata=past)
    assert verify_artifact(artifact, KEY, resigned) is False, (
        "a sidecar past its replay window still verified")


def test_the_expiry_cannot_be_edited_forward(artifact, monkeypatch):
    """The MAC covers expires_at, so it cannot be pushed out."""
    monkeypatch.setenv("NIXON_ARTIFACT_TTL", "60")
    sig = sign_artifact(artifact, KEY)
    tampered = dict(sig)
    tampered["metadata"] = dict(sig["metadata"])
    tampered["metadata"]["expires_at"] = int(time.time()) + 10 ** 9
    assert verify_artifact(artifact, KEY, tampered) is False


def test_a_zero_ttl_means_no_expiry(artifact, monkeypatch):
    monkeypatch.setenv("NIXON_ARTIFACT_TTL", "0")
    sig = sign_artifact(artifact, KEY)
    assert sig["metadata"]["expires_at"] == sig["metadata"]["issued_at"]
    assert verify_artifact(artifact, KEY, sig) is True


def test_a_malformed_expiry_fails_closed(artifact, monkeypatch):
    monkeypatch.setenv("NIXON_ARTIFACT_TTL", "60")
    sig = sign_artifact(artifact, KEY)
    broken = dict(sig)
    broken["metadata"] = dict(sig["metadata"])
    broken["metadata"]["expires_at"] = "not-a-number"
    assert verify_artifact(artifact, KEY, broken) is False
