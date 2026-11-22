"""The incident-response runbook's checkable claims, enforced.

`docs/security/INCIDENT_RESPONSE.md` is a procedure document, and a procedure
document drifts: a step says "the pin is a refusal when missing" long after
somebody makes it a warning again. Each step that CAN be checked in code is
checked here, so the document failing to match the implementation fails a
test.

The steps that require a human — generating a key out of band, updating a
protected environment, notifying customers — are deliberately NOT simulated.
A drill that fakes the human step proves nothing about whether the human step
is documented, and this project has already been burned once by treating a
plausible-looking record as evidence.
"""
import inspect
import json
import os
import secrets
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from obfuscator.build_manifest import (  # noqa: E402
    MANIFEST_PIN_ENV, MANIFEST_SUFFIX, build_manifest, sign_manifest,
    verify_manifest,
)
from obfuscator.rollback import (  # noqa: E402
    MARK_NAME, check_rollback, read_mark, write_mark,
)

RUNBOOK = os.path.join(REPO, "docs", "security", "INCIDENT_RESPONSE.md")

pytestmark = pytest.mark.skipif(
    __import__("importlib").util.find_spec("cryptography") is None,
    reason="Ed25519 signing needs the cryptography package")

ARTEFACT_BODY = 'MARKER = "IR-ACCEPT"\n'


def _key():
    from obfuscator.licensing import private_key_from_hex
    return private_key_from_hex(secrets.token_hex(32))


def _signed(tmp_path, key, name="payload_protected.py"):
    """A minimal signed artefact plus manifest, via the project's own code."""
    art = tmp_path / name
    art.write_text(ARTEFACT_BODY, encoding="utf-8")
    manifest = sign_manifest(build_manifest(str(art), transforms=["data"]), key)
    (tmp_path / (name + MANIFEST_SUFFIX)).write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return art, manifest


# ── §0 triage: the fingerprint scopes the affected set ───────────────────

def test_the_fingerprint_scopes_the_affected_set(tmp_path):
    """§0: 'which artefacts did the compromised key sign?' is answerable
    from the artefacts, without a build database.
    """
    key = _key()
    art, manifest = _signed(tmp_path, key)

    from cryptography.hazmat.primitives import serialization
    raw = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw)
    expected = __import__("hashlib").sha256(raw).hexdigest()[:16]

    # The SIGNED copy is the one triage must read.
    assert manifest.get("signed_key_fingerprint") == expected, (
        "the manifest's signed_key_fingerprint must identify the signing key, "
        "or an incident cannot be scoped from the released files")
    assert (manifest.get("signature") or {}).get(
        "key_fingerprint") == expected

    tampered = json.loads(json.dumps(manifest))
    tampered["signature"]["key_fingerprint"] = "0" * 16
    (tmp_path / (art.name + MANIFEST_SUFFIX)).write_text(
        json.dumps(tampered, sort_keys=True), encoding="utf-8")
    assert verify_manifest(str(art), key.public_key()).get("ok") is not True, (
        "re-attributing the signing key left the manifest valid")


def test_the_signed_fingerprint_cannot_be_re_attributed(tmp_path):
    """REGRESSION (defect found 2026-11-22 while writing this runbook).

    The fingerprint was only ever stored at ``signature.key_fingerprint``, and
    the whole ``signature`` object is excluded from the signed body — so
    editing it left ``verify_manifest`` returning ok:True while its docstring
    claimed the field was signature-covered. Anyone able to write a manifest
    could re-attribute an artefact signed by a compromised key to a clean one,
    which is precisely the §0 triage step below.

    Both tampering directions must now fail: editing the nested copy (caught
    by the mismatch check) and editing the top-level signed copy (caught by
    the signature itself).
    """
    key = _key()
    art, manifest = _signed(tmp_path, key)
    manifest_path = tmp_path / (art.name + MANIFEST_SUFFIX)

    # Control: unmodified manifest verifies.
    assert verify_manifest(str(art), key.public_key()).get("ok") is True

    # Direction 1: edit the unsigned nested copy.
    nested = json.loads(json.dumps(manifest))
    nested["signature"]["key_fingerprint"] = "0" * 16
    manifest_path.write_text(json.dumps(nested, sort_keys=True),
                             encoding="utf-8")
    result = verify_manifest(str(art), key.public_key())
    assert result.get("ok") is not True
    assert "fingerprint" in (result.get("reason") or "").lower(), (
        "the refusal must say the fingerprints disagree: %r"
        % (result.get("reason"),))

    # Direction 2: edit the signed top-level copy — the signature breaks.
    signed_copy = json.loads(json.dumps(manifest))
    signed_copy["signed_key_fingerprint"] = "0" * 16
    manifest_path.write_text(json.dumps(signed_copy, sort_keys=True),
                             encoding="utf-8")
    assert verify_manifest(str(art), key.public_key()).get("ok") is not True, (
        "editing the signed fingerprint copy left the signature valid")


# ── §1 revocation: pin replacement is the mechanism ─────────────────────

def test_a_retired_key_is_refused_under_the_new_pin(tmp_path):
    """§1: rotation retires the old key's future."""
    old_key = _key()
    art, _manifest = _signed(tmp_path, old_key)
    new_key = _key()

    assert verify_manifest(str(art), new_key.public_key()).get("ok") is not True
    assert verify_manifest(str(art), old_key.public_key()).get("ok") is True


def test_an_unupdated_client_still_accepts_the_old_key(tmp_path):
    """§1: THE OFFLINE LIMIT, asserted rather than claimed away.

    A disconnected client cannot learn about revocation until it receives the
    new pin, so it keeps accepting the compromised key's signature. The
    runbook says this; here it is as a measurement.
    """
    old_key = _key()
    art, _manifest = _signed(tmp_path, old_key)

    # The stale client holds the old pin and has received no update.
    stale_pin = old_key.public_key()
    assert verify_manifest(str(art), stale_pin).get("ok") is True, (
        "this is the documented limitation: an un-updated client accepts a "
        "signature by the now-compromised key")


# ── §2 emergency pin replacement ────────────────────────────────────────

def test_a_missing_pin_is_a_refusal_under_release_policy(monkeypatch):
    """§2: under NIXON_REQUIRE_PROVENANCE=1 a missing pin fails closed."""
    from obfuscator import build_manifest as bm

    monkeypatch.setenv("NIXON_REQUIRE_PROVENANCE", "1")
    monkeypatch.delenv(MANIFEST_PIN_ENV, raising=False)
    trusted, reason = bm._manifest_trusted_key(None)
    assert trusted is None, (
        "with release policy on and no pin, the resolver must refuse")
    assert reason and MANIFEST_PIN_ENV in reason, (
        "the refusal must name the missing pin variable so an operator knows "
        "what to set: %r" % (reason,))


def test_an_explicit_key_cannot_override_the_pin(monkeypatch):
    """§2: the pin is the authority; an explicit key that disagrees loses."""
    from obfuscator import build_manifest as bm
    from cryptography.hazmat.primitives import serialization

    pinned = _key()
    other = _key()
    pinned_hex = pinned.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw).hex()

    monkeypatch.setenv("NIXON_REQUIRE_PROVENANCE", "1")
    monkeypatch.setenv(MANIFEST_PIN_ENV, pinned_hex)

    trusted, reason = bm._manifest_trusted_key(other.public_key())
    assert trusted is None, (
        "an explicit key different from the pin was accepted; the pin is not "
        "the authority")
    assert reason and "pin" in reason.lower(), reason

    # The matching key IS accepted, so the rule is "must match", not "always
    # refuse".
    trusted_ok, reason_ok = bm._manifest_trusted_key(pinned.public_key())
    assert trusted_ok is not None and reason_ok is None


# ── §3 manifest-key rotation ────────────────────────────────────────────

def test_rotating_the_manifest_pin_retires_the_old_manifests(tmp_path,
                                                             monkeypatch):
    """§3: the manifest key rotates independently of the artefact key."""
    old_key = _key()
    art, _manifest = _signed(tmp_path, old_key)
    new_key = _key()

    from cryptography.hazmat.primitives import serialization
    new_hex = new_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw).hex()
    monkeypatch.setenv("NIXON_REQUIRE_PROVENANCE", "1")
    monkeypatch.setenv(MANIFEST_PIN_ENV, new_hex)

    result = verify_manifest(str(art))
    assert result.get("ok") is not True, (
        "a manifest signed by the retired manifest key verified under the "
        "new pin; rotation would not retire anything")


# ── §4 old-artefact retirement ──────────────────────────────────────────

def test_lowering_the_protection_level_breaks_the_signature(tmp_path):
    """§4: the level is inside the signed body."""
    key = _key()
    art, manifest = _signed(tmp_path, key)
    assert isinstance(manifest.get("protection_level"), int), (
        "the runbook's retirement step assumes a signed protection_level")

    tampered = json.loads(json.dumps(manifest))
    tampered["protection_level"] = 0
    (tmp_path / (art.name + MANIFEST_SUFFIX)).write_text(
        json.dumps(tampered, sort_keys=True), encoding="utf-8")
    assert verify_manifest(str(art), key.public_key()).get("ok") is not True


def test_a_forged_high_water_mark_is_not_trusted(tmp_path):
    """§4: read_mark verifies the MAC and returns 0 for anything it cannot
    authenticate, so a downward edit is a fresh install, never a trust."""
    artefact, manifest = _signed(tmp_path, _key())
    level = manifest["protection_level"]
    mac_key = secrets.token_bytes(32)
    mark = tmp_path / MARK_NAME
    assert write_mark(str(mark), mac_key, level + 5, artefact.name) is True

    raw = json.loads(mark.read_text(encoding="utf-8"))
    raw["level"] = 0
    mark.write_text(json.dumps(raw), encoding="utf-8")

    assert read_mark(str(mark), key=mac_key,
                     artefact_name=artefact.name) == 0


def test_a_downgrade_is_a_raise_not_a_verdict(tmp_path):
    """§4: check_rollback RAISES, so a caller cannot ignore a boolean."""
    artefact, manifest = _signed(tmp_path, _key())
    level = manifest["protection_level"]
    mac_key = secrets.token_bytes(32)
    mark = tmp_path / MARK_NAME
    write_mark(str(mark), mac_key, level + 1, artefact.name)

    with pytest.raises(RuntimeError, match="refusing to downgrade"):
        check_rollback(str(artefact), level, mac_key,
                       override_path=str(mark))


# ── §5 compromised dependency discovery ─────────────────────────────────

def test_the_lock_digest_distinguishes_dependency_sets(tmp_path):
    """§5: the digest is over the lock BYTES, so a corrected lock differs."""
    import hashlib

    first = tmp_path / "requirements-a.lock"
    second = tmp_path / "requirements-b.lock"
    first.write_text("requests==2.31.0\nurllib3==2.0.7\n", encoding="utf-8")
    second.write_text("requests==2.31.0\nurllib3==2.2.2\n", encoding="utf-8")

    a = hashlib.sha256(first.read_bytes()).hexdigest()
    b = hashlib.sha256(second.read_bytes()).hexdigest()
    assert a != b, (
        "a one-package change must change the lock digest, or §5 cannot "
        "distinguish the affected build from the corrected one")

    # And the manifest records that digest for a real build.
    art, manifest = _signed(tmp_path, _key())
    build = manifest.get("build") or {}
    assert "dependency_lock_digest" in build, (
        "the manifest must record a dependency-lock digest for §5 to key on")


# ── §6 revocation is pin replacement, not a list ────────────────────────

def test_revocation_is_pin_replacement_not_a_list():
    """§6: assert the documented mechanism is the implemented one.

    The runbook says there is no online revocation list because the design is
    local and offline. If someone adds a network fetch to the verification
    path, the document becomes false, so the verification module is checked
    for network calls and for a revocation-list artefact.
    """
    import obfuscator.build_manifest as bm

    source = inspect.getsource(bm)
    for forbidden in ("urlopen", "requests.get", "socket.socket",
                      "httpx.", "urllib.request"):
        assert forbidden not in source, (
            "verify_manifest's module made a network call (%r); the runbook "
            "documents offline verification and pin replacement as THE "
            "revocation mechanism" % (forbidden,))

    assert "REVOCATION_LIST" not in source.upper(), (
        "a revocation-list concept appeared in the manifest module; §6 "
        "documents pin replacement instead and must be updated deliberately")

    # And _manifest_trusted_key is what enforces the pin, not a remote check.
    assert callable(getattr(bm, "_manifest_trusted_key", None))


def test_the_runbook_still_documents_what_the_code_does():
    """Guard against the document and the implementation drifting apart."""
    with open(RUNBOOK, encoding="utf-8") as fh:
        text = fh.read()
    for required in (MANIFEST_PIN_ENV, "NIXON_ARTEFACT_SIGN_KEY",
                     "NIXON_BUILD_MANIFEST_KEY", "protection_level",
                     "dependency_lock_digest", "key_fingerprint",
                     "refusing to downgrade", "offline"):
        assert required in text, (
            "the runbook no longer mentions %r, which the implementation "
            "depends on" % (required,))
    assert "NOT covered here" in text, (
        "the runbook must keep its explicit list of what it does not cover")
    for external in ("Authenticode", "Apple Developer ID", "cryptographic"):
        assert external in text, (
            "the runbook must keep naming the external dependencies it "
            "cannot close")
