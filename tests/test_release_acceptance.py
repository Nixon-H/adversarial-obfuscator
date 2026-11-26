"""Replay/rollback acceptance against a REAL built artefact.

Review register, P1 row "Real artefact replay/rollback acceptance". The
seventh pass covered rows 4-7 against the manifest/rollback machinery with
synthetic inputs; this module is stricter about where the artefact comes
from: it builds one through the project's own transform pipeline, signs it
with an EPHEMERAL Ed25519 key generated at runtime, and then attacks THOSE
bytes.

Two things this pins that a unit test on hand-made fixtures cannot:

  * the manifest that `build_manifest` actually produces for a real
    artefact carries a protection level, a commit, a dependency-lock digest
    and a key fingerprint -- all four are what the register's §7 asks for,
    and all four are read from the artefact rather than passed in;
  * the downgrade, forged-mark and metadata-edit rows still hold when the
    manifest is the real one. A forged mark is only interesting against a
    genuine high-water mark; against a fabricated one the test can pass for
    the wrong reason.

Why in-process rather than shelling out to `pipeline build`: the build and
verify path is Python functions (``build_pipeline``, ``build_manifest``,
``sign_manifest``, ``verify_manifest``, ``rollback.*``), so invoking them
directly exercises the same code the CLI does without a second interpreter,
and without the test needing to construct a subprocess argv from a path.
``tests/test_release_acceptance_exec.py`` covers the CLI-level matrix that
genuinely needs a separate process; this module covers the trust logic.

No credential literal appears here: the signing key is minted with `secrets`
per test and exists only in that test's frame.
"""
import hashlib
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
    MANIFEST_SUFFIX, build_manifest, sign_manifest, verify_manifest,
)
from obfuscator.rollback import (  # noqa: E402
    MARK_NAME, check_rollback, read_mark, write_mark,
)

PAYLOAD = '''\
MARKER = "RC-ACCEPT-MARKER-7f3a"


def report():
    return MARKER


if __name__ == "__main__":
    print(report())
'''

pytestmark = pytest.mark.skipif(
    __import__("importlib").util.find_spec("cryptography") is None,
    reason="Ed25519 signing needs the cryptography package")


def _ephemeral_key():
    """A throwaway signing key. Minted per call, never stored, never printed."""
    from obfuscator.licensing import private_key_from_hex
    return private_key_from_hex(secrets.token_hex(32))


def _real_artefact(tmp_path):
    """Build, sign and return a real artefact plus its manifest.

    The transforms run in-process through the same entry point the CLI uses;
    the result is written where a build would put it, and the manifest is
    produced by the project's own builder so its fields are the real ones.
    """
    from obfuscator.core.pipeline import build_pipeline

    source = build_pipeline(PAYLOAD, seed=20261122)
    assert source and source != PAYLOAD, "the transform produced nothing"

    artefact = tmp_path / "payload_protected.py"
    artefact.write_text(source, encoding="utf-8")

    key = _ephemeral_key()
    manifest = build_manifest(str(artefact), transforms=["data"])
    manifest = sign_manifest(manifest, key)
    (tmp_path / (artefact.name + MANIFEST_SUFFIX)).write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return artefact, manifest, key


@pytest.mark.nixon_timeout(180)
def test_a_real_artefact_carries_the_register_section7_fields(tmp_path):
    """The manifest must bind commit, lock digest, level and key identity."""
    artefact, manifest, key = _real_artefact(tmp_path)

    build = manifest.get("build") or {}
    assert build.get("commit"), (
        "the manifest must bind the source commit it was built from")
    assert build.get("dependency_lock_digest"), (
        "the manifest must bind a dependency-lock digest")

    level = manifest.get("protection_level")
    assert isinstance(level, int) and level >= 0, (
        "the manifest must record a protection level, or anti-rollback has "
        "nothing to compare: %r" % (level,))

    assert manifest.get("signed") is True
    fingerprint = (manifest.get("signature") or {}).get("key_fingerprint")
    assert fingerprint, (
        "the manifest must identify WHICH key signed it")

    # The fingerprint must be the one the key actually has, not a constant.
    from cryptography.hazmat.primitives import serialization
    raw = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw)
    assert fingerprint == hashlib.sha256(raw).hexdigest()[:16], (
        "the recorded fingerprint does not match the signing key")


def test_the_published_bytes_verify_under_the_matching_key(tmp_path):
    """The control: a genuine artefact verifies. Refusals below mean something
    only because this succeeds."""
    artefact, _manifest, key = _real_artefact(tmp_path)
    result = verify_manifest(str(artefact), key.public_key())
    assert result.get("ok") is True, (
        "a genuine artefact did not verify: %r" % (result,))


def test_a_lowered_protection_level_breaks_the_signature(tmp_path):
    """protection_level is inside the signed body; editing it must fail.

    This is the "modify version metadata" row. It matters because the level
    is the input to anti-rollback: if it could be edited independently of the
    signature, an attacker could lower it and then replay an older artefact
    that the high-water mark would otherwise refuse.
    """
    artefact, manifest, key = _real_artefact(tmp_path)
    tampered = json.loads(json.dumps(manifest))
    tampered["protection_level"] = 0
    (tmp_path / (artefact.name + MANIFEST_SUFFIX)).write_text(
        json.dumps(tampered), encoding="utf-8")

    result = verify_manifest(str(artefact), key.public_key())
    assert result.get("ok") is not True, (
        "a manifest with a lowered protection_level still verified; the "
        "level is not covered by the signature")


def test_an_artefact_below_the_high_water_mark_is_refused(tmp_path):
    """The "restore an older signed artefact" row, against real bytes.

    ``check_rollback`` RAISES on a downgrade rather than returning a verdict:
    a lower level than the recorded high-water mark is a refusal, full stop,
    and a caller that ignored a boolean could otherwise continue. The test
    asserts the raise, which is the stronger contract.

    The mark's key is a raw bytes HMAC key -- rollback.py MACs the level, it
    does not sign it -- and is distinct from the Ed25519 manifest key.
    """
    artefact, manifest, _key = _real_artefact(tmp_path)
    level = manifest["protection_level"]
    mac_key = secrets.token_bytes(32)
    mark_dir = tmp_path / "mark"
    mark_dir.mkdir()
    mark_file = mark_dir / MARK_NAME
    write_mark(str(mark_file), mac_key, level + 1, artefact.name)

    with pytest.raises(RuntimeError, match="refusing to downgrade"):
        check_rollback(str(artefact), level, mac_key,
                       override_path=str(mark_file))


def test_a_forged_high_water_mark_is_not_trusted(tmp_path):
    """Editing the recorded level downward breaks the MAC; read returns 0.

    Without MAC verification on READ, an attacker who can write the mark file
    could lower it and then replay an old artefact unchallenged. The read must
    therefore refuse a mark it cannot authenticate, and "refuse" here means
    reporting a fresh install (0), never a trusted lower level.
    """
    artefact, manifest, _key = _real_artefact(tmp_path)
    level = manifest["protection_level"]
    mac_key = secrets.token_bytes(32)
    mark_dir = tmp_path / "forged"
    mark_dir.mkdir()
    mark_file = mark_dir / MARK_NAME
    assert write_mark(str(mark_file), mac_key, level + 5, artefact.name) is True

    raw = json.loads(mark_file.read_text(encoding="utf-8"))
    assert "level" in raw, "the mark format has no editable level field"
    assert raw["level"] == level + 5
    raw["level"] = 0
    mark_file.write_text(json.dumps(raw), encoding="utf-8")

    observed = read_mark(str(mark_file), key=mac_key,
                         artefact_name=artefact.name)
    assert observed == 0, (
        "a forged mark with a lowered level was trusted as %r" % (observed,))


def test_the_offline_revocation_limit_is_asserted_not_claimed_away(tmp_path):
    """Rotation retires the old key's future; it does not reach offline clients.

    The register requires this limitation be tested rather than papered over.
    Concretely: an artefact signed by a compromised key KEEPS VERIFYING on a
    client whose pin is still the old one. Only a client that received the new
    pin refuses it. Asserting both halves keeps the documentation honest.
    """
    artefact, _manifest, old_key = _real_artefact(tmp_path)
    new_key = _ephemeral_key()

    # Un-updated client, old pin: still accepts. This IS the limitation.
    assert verify_manifest(str(artefact), old_key.public_key()).get(
        "ok") is True, "precondition: the genuine artefact verifies"

    # Updated client, new pin: refuses. That IS the revocation mechanism.
    assert verify_manifest(str(artefact), new_key.public_key()).get(
        "ok") is not True, (
        "an artefact signed by the retired key verified under the new pin; "
        "pin rotation would not revoke anything")

    # Re-signing with the retired key must not satisfy the new pin either,
    # which is what stops a compromised signer from minting fresh artefacts.
    body = {k: v for k, v in json.loads(
        (tmp_path / (artefact.name + MANIFEST_SUFFIX)).read_text(
            encoding="utf-8")).items() if k not in ("signature", "signed")}
    payload = json.dumps(body, sort_keys=True,
                         separators=(",", ":")).encode()
    body["signature"] = {
        "algo": "ed25519",
        "sig": __import__("base64").b64encode(old_key.sign(payload)).decode(),
        "key_fingerprint": (json.loads(
            (tmp_path / (artefact.name + MANIFEST_SUFFIX)).read_text(
                encoding="utf-8")).get("signature") or {}).get(
                    "key_fingerprint"),
    }
    body["signed"] = True
    (tmp_path / (artefact.name + MANIFEST_SUFFIX)).write_text(
        json.dumps(body), encoding="utf-8")
    assert verify_manifest(str(artefact), new_key.public_key()).get(
        "ok") is not True, (
        "content re-signed with the retired key verified under the new pin")
