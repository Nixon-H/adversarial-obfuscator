"""Tests for the per-farm Ed25519 artifact signature path.

The shared HMAC key had a property the design did not want: every
verifier that held the key could MINT a sidecar for any farm, so a
verifier was also a forger.  The Ed25519 path fixes that -- the farm
holds a private key, the operator pins the public one, and a verifier
holding only the public key can check an artifact but cannot forge
one.

The HMAC path is unchanged: it still works, and it is still the
fallback when no Ed25519 key is configured.
"""

import base64
import json

import pytest

from scripts import artifact_sign as A

pytest.importorskip("cryptography")
from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # noqa: E402
    Ed25519PrivateKey,
)


@pytest.fixture
def farm_key():
    return Ed25519PrivateKey.generate()


def _write(tmp_path, data=b"artifact-bytes"):
    target = tmp_path / "artifact.bin"
    target.write_bytes(data)
    return str(target)


def test_ed25519_roundtrip_with_public_key_only(tmp_path, farm_key):
    """The verifier needs only the public key."""
    path = _write(tmp_path)
    meta = A.default_metadata(extra={"farm": "farm-a"})
    sig = A.sign_artifact_ed25519(path, farm_key, meta)
    assert sig["algo"] == A.ED25519_ALGO
    assert sig["key_id"]
    pub = bytes.fromhex(A.ed25519_public_hex(farm_key))
    assert A.verify_artifact(path, pub, sig) is True


def test_ed25519_forgery_with_another_key_is_rejected(tmp_path, farm_key):
    """A sidecar signed by a different private key must not verify.

    This is the property the shared HMAC key could not give: the
    verifier cannot mint a sidecar it will later accept.
    """
    path = _write(tmp_path)
    meta = A.default_metadata(extra={"farm": "farm-a"})
    pub = bytes.fromhex(A.ed25519_public_hex(farm_key))

    forged = A.sign_artifact_ed25519(path, Ed25519PrivateKey.generate(), meta)
    assert A.verify_artifact(path, pub, forged) is False


def test_ed25519_tampered_metadata_is_rejected(tmp_path, farm_key):
    """The signature covers the metadata, not just the bytes."""
    path = _write(tmp_path)
    meta = A.default_metadata(extra={"farm": "farm-a"})
    sig = A.sign_artifact_ed25519(path, farm_key, meta)
    pub = bytes.fromhex(A.ed25519_public_hex(farm_key))
    tampered = dict(sig, metadata=dict(sig["metadata"], farm="farm-b"))
    assert A.verify_artifact(path, pub, tampered) is False


def test_ed25519_tampered_bytes_are_rejected(tmp_path, farm_key):
    """Changing the artifact invalidates the signature."""
    path = _write(tmp_path)
    sig = A.sign_artifact_ed25519(path, farm_key)
    pub = bytes.fromhex(A.ed25519_public_hex(farm_key))
    with open(path, "wb") as f:
        f.write(b"tampered bytes")
    assert A.verify_artifact(path, pub, sig) is False


def test_ed25519_expired_sidecar_is_rejected(tmp_path, farm_key, monkeypatch):
    """The replay window still applies to the asymmetric path."""
    path = _write(tmp_path)
    meta = A.default_metadata(extra={"farm": "farm-a"})
    meta["expires_at"] = 1
    sig = A.sign_artifact_ed25519(path, farm_key, meta)
    pub = bytes.fromhex(A.ed25519_public_hex(farm_key))
    assert A.verify_artifact(path, pub, sig) is False


def test_ed25519_metadata_pin_is_enforced(tmp_path, farm_key):
    """A pinned farm that does not match is a mismatch, not a pass."""
    path = _write(tmp_path)
    sig = A.sign_artifact_ed25519(path, farm_key,
                                  A.default_metadata(extra={"farm": "farm-a"}))
    pub = bytes.fromhex(A.ed25519_public_hex(farm_key))
    assert A.verify_artifact(path, pub, sig, {"farm": "farm-a"}) is True
    assert A.verify_artifact(path, pub, sig, {"farm": "farm-b"}) is False


def test_ed25519_malformed_signature_is_rejected(tmp_path, farm_key):
    """A malformed signature must not raise or pass."""
    path = _write(tmp_path)
    sig = A.sign_artifact_ed25519(path, farm_key)
    pub = bytes.fromhex(A.ed25519_public_hex(farm_key))
    for bad in ("not-base64!!", base64.b64encode(b"short").decode(), ""):
        assert A.verify_artifact(path, pub, dict(sig, sig=bad)) is False


def test_public_key_resolution_single_and_map(farm_key):
    """Both pinning forms resolve to the same key id."""
    pub_hex = A.ed25519_public_hex(farm_key)
    expected = A.ed25519_key_id(bytes.fromhex(pub_hex))

    env = {A.ED25519_PUBLIC_KEY_ENV: pub_hex}
    assert list(A.resolve_ed25519_public_keys(env)) == [expected]

    env = {A.ED25519_KEYS_ENV: json.dumps({"farm-a": pub_hex})}
    assert list(A.resolve_ed25519_public_keys(env)) == [expected]


def test_public_key_resolution_ignores_garbage():
    """A malformed pin is ignored, not fatal."""
    env = {
        A.ED25519_PUBLIC_KEY_ENV: "not-hex",
        A.ED25519_KEYS_ENV: "{not json",
    }
    assert A.resolve_ed25519_public_keys(env) == {}


def test_private_key_resolution(farm_key):
    """The private key is read from its env var."""
    env = {A.ED25519_PRIVATE_KEY_ENV: "00" * 32}
    assert A.resolve_ed25519_private_key(env) is not None
    assert A.resolve_ed25519_private_key({}) is None
    bad = {A.ED25519_PRIVATE_KEY_ENV: "00" * 8}
    assert A.resolve_ed25519_private_key(bad) is None


def test_sign_auto_prefers_ed25519(tmp_path, monkeypatch, farm_key):
    """With a private key configured, the asymmetric scheme is used."""
    path = _write(tmp_path)
    monkeypatch.setenv(A.ED25519_PRIVATE_KEY_ENV, "00" * 32)
    monkeypatch.delenv(A.ED25519_PUBLIC_KEY_ENV, raising=False)
    sig = A.sign_artifact_auto(path, b"hmac-key")
    assert sig["algo"] == A.ED25519_ALGO


def test_sign_auto_falls_back_to_hmac(tmp_path, monkeypatch):
    """Without an Ed25519 key the HMAC path still works."""
    path = _write(tmp_path)
    monkeypatch.delenv(A.ED25519_PRIVATE_KEY_ENV, raising=False)
    sig = A.sign_artifact_auto(path, b"hmac-key")
    assert sig["algo"] == A.BINDING_ALGO


def test_sign_auto_returns_none_without_any_key(tmp_path, monkeypatch):
    """No key at all means "sign nothing" -- the caller decides."""
    path = _write(tmp_path)
    monkeypatch.delenv(A.ED25519_PRIVATE_KEY_ENV, raising=False)
    assert A.sign_artifact_auto(path, None) is None


def test_zip_sidecars_verify_ed25519(tmp_path, monkeypatch, farm_key):
    """The download gate accepts an Ed25519-signed zip."""
    import zipfile

    pub_hex = A.ed25519_public_hex(farm_key)
    artifact = tmp_path / "a.bin"
    artifact.write_bytes(b"artifact-bytes")
    sig = A.sign_artifact_ed25519(str(artifact), farm_key)

    zip_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("a.bin", b"artifact-bytes")
        z.writestr("a.bin.sig.json", json.dumps(sig))

    monkeypatch.setenv(A.ED25519_PUBLIC_KEY_ENV, pub_hex)
    assert A.verify_zip_sidecars(str(zip_path), None) == 1


def test_zip_sidecars_reject_unpinned_key(tmp_path, monkeypatch, farm_key):
    """A sidecar from an unknown farm is a mismatch, not a pass."""
    import zipfile

    artifact = tmp_path / "a.bin"
    artifact.write_bytes(b"artifact-bytes")
    sig = A.sign_artifact_ed25519(str(artifact), farm_key)

    zip_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("a.bin", b"artifact-bytes")
        z.writestr("a.bin.sig.json", json.dumps(sig))

    # A different farm's public key is pinned: this sidecar is not from it.
    other_hex = A.ed25519_public_hex(Ed25519PrivateKey.generate())
    monkeypatch.setenv(A.ED25519_PUBLIC_KEY_ENV, other_hex)
    with pytest.raises(A.SignatureMismatchError):
        A.verify_zip_sidecars(str(zip_path), None)


def test_zip_sidecars_need_the_hmac_key_for_hmac_sidecars(tmp_path, monkeypatch):
    """An HMAC sidecar with no HMAC key is a mismatch, not a crash."""
    import zipfile

    artifact = tmp_path / "a.bin"
    artifact.write_bytes(b"artifact-bytes")
    sig = A.sign_artifact(str(artifact), b"hmac-key")

    zip_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("a.bin", b"artifact-bytes")
        z.writestr("a.bin.sig.json", json.dumps(sig))

    # An Ed25519 public key is pinned, but this sidecar is HMAC.
    monkeypatch.setenv(A.ED25519_PUBLIC_KEY_ENV,
                       A.ed25519_public_hex(Ed25519PrivateKey.generate()))
    with pytest.raises(A.SignatureMismatchError):
        A.verify_zip_sidecars(str(zip_path), None)


def test_zip_sidecars_need_a_key_to_verify_at_all(tmp_path, monkeypatch, farm_key):
    """With no key of any kind the gate refuses to run.

    This is the pre-existing contract: a caller that cannot verify
    must not be handed a "verified" count.
    """
    import zipfile

    artifact = tmp_path / "a.bin"
    artifact.write_bytes(b"artifact-bytes")
    sig = A.sign_artifact_ed25519(str(artifact), farm_key)

    zip_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("a.bin", b"artifact-bytes")
        z.writestr("a.bin.sig.json", json.dumps(sig))

    monkeypatch.delenv(A.ED25519_PUBLIC_KEY_ENV, raising=False)
    monkeypatch.delenv(A.ED25519_KEYS_ENV, raising=False)
    with pytest.raises(ValueError):
        A.verify_zip_sidecars(str(zip_path), None)
