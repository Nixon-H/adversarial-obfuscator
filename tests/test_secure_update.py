"""§9 secure update: the client must be able to REFUSE, not just receive.

An updater that verifies a signature has done the easy half. The attacks that
actually hurt are downgrade (serve the old, vulnerable release -- its signature
is genuine), keystore rollback (a retired key), transplant (a signed update for
a different product), and the partial write (a crash mid-install leaves a
truncated binary that the next start tries to execute). Each test below is one
of those, and each asserts a refusal.
"""
import hashlib
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator import secure_update as su  # noqa: E402

BODY = b"\x7fELF fake update payload\n"
NEXT = b"\x7fELF newer payload\n"


def _key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey)
    return Ed25519PrivateKey.generate()


def _signed(*, body=BODY, version="2.0.0", sequence=2, channel="stable",
            product="widget", key_id="k1", minimum_sequence=0, key=None,
            published_at=None, artefact="widget.bin"):
    private = key or _key()
    manifest = su.make_manifest(
        artefact, body, version, sequence, channel=channel, product=product,
        minimum_sequence=minimum_sequence, key_id=key_id,
        published_at=published_at)
    return su.sign_manifest(manifest, private), private


def _verify(wire, *, body=BODY, **overrides):
    private = overrides.pop("private", None)
    kwargs = dict(public_key=private.public_key(), current_sequence=1,
                  expected_product="widget", expected_channel="stable",
                  expected_artefact="widget.bin", max_age_seconds=86400)
    kwargs.update(overrides)
    return su.verify_update(wire, body, **kwargs)


# ── the genuine update applies ───────────────────────────────────────────

def test_a_genuine_update_verifies():
    wire, private = _signed()
    result = _verify(wire, private=private)
    assert result["ok"] is True, result["problems"]


def test_warnings_name_the_checks_that_did_not_run():
    """A silent skip is how a security check becomes decoration."""
    wire, private = _signed()
    result = su.verify_update(wire, BODY, public_key=private.public_key())
    assert result["ok"] is True
    assert any("current_sequence" in w for w in result["warnings"])
    assert any("max_age" in w for w in result["warnings"])


# ── downgrade: the attack a signature check alone cannot stop ────────────

def test_an_older_sequence_is_refused():
    wire, private = _signed(sequence=2)
    result = _verify(wire, private=private, current_sequence=5)
    assert result["ok"] is False
    assert any("downgrade" in p for p in result["problems"])


def test_the_same_sequence_is_refused():
    """Reinstalling the current version is not an update; it is a rollback."""
    wire, private = _signed(sequence=3)
    result = _verify(wire, private=private, current_sequence=3)
    assert result["ok"] is False
    assert any("not newer" in p for p in result["problems"])


def test_a_manifest_below_its_own_minimum_is_refused():
    """How a bad release is retired without revoking the signing key."""
    wire, private = _signed(sequence=4)
    result = _verify(wire, private=private, current_sequence=1,
                     minimum_sequence=9)
    assert result["ok"] is False
    assert any("downgrade refused" in p for p in result["problems"])


def test_a_manifest_cannot_declare_itself_below_its_own_floor():
    with pytest.raises(su.UpdateError):
        su.make_manifest("a.bin", BODY, "1.0", 2, minimum_sequence=5)


# ── identity: a signed update for something else ─────────────────────────

@pytest.mark.parametrize("field,expected", [
    ("product", "other-product"),
    ("channel", "nightly"),
    ("artefact", "other.bin"),
])
def test_an_update_for_another_target_is_refused(field, expected):
    wire, private = _signed()
    result = _verify(wire, private=private, **{
        "expected_" + field: expected})
    assert result["ok"] is False
    assert any(field + " mismatch" in p for p in result["problems"])


def test_a_retired_key_id_is_refused():
    wire, private = _signed(key_id="k-old")
    result = _verify(wire, private=private, accepted_key_ids=("k-new",))
    assert result["ok"] is False
    assert any("key_id" in p for p in result["problems"])


# ── integrity of the bytes ───────────────────────────────────────────────

def test_bytes_that_do_not_match_the_manifest_are_refused():
    wire, private = _signed(body=BODY)
    result = _verify(wire, body=NEXT, private=private)
    assert result["ok"] is False
    assert any("digest mismatch" in p for p in result["problems"])


def test_a_truncated_body_is_also_caught_by_size():
    wire, private = _signed(body=BODY)
    result = _verify(wire, body=BODY[:-4], private=private)
    assert result["ok"] is False
    assert any("digest mismatch" in p or "size mismatch" in p
               for p in result["problems"])


# ── signature ────────────────────────────────────────────────────────────

def test_an_unsigned_manifest_is_refused():
    wire, private = _signed()
    result = su.verify_update({"payload": wire["payload"]}, BODY,
                              public_key=private.public_key())
    assert result["ok"] is False
    assert any("not signed" in p for p in result["problems"])


def test_no_public_key_is_a_refusal():
    wire, _private = _signed()
    result = su.verify_update(wire, BODY, current_sequence=1)
    assert result["ok"] is False
    assert any("no public key" in p for p in result["problems"])


def test_an_edited_manifest_breaks_the_signature():
    wire, private = _signed(sequence=2)
    wire["payload"]["version"] = "99.0.0-malicious"
    result = _verify(wire, private=private)
    assert result["ok"] is False
    assert any("signature does not verify" in p for p in result["problems"])


def test_a_signature_from_another_key_is_refused():
    wire, _ = _signed()
    result = _verify(wire, private=_key())
    assert result["ok"] is False
    assert any("signature does not verify" in p for p in result["problems"])


# ── freshness / freeze ───────────────────────────────────────────────────

def test_an_old_manifest_is_refused_when_a_max_age_is_given():
    old = int(time.time()) - 10 * 86400
    wire, private = _signed(published_at=old)
    result = _verify(wire, private=private, max_age_seconds=86400)
    assert result["ok"] is False
    assert any("old" in p for p in result["problems"])


def test_a_manifest_dated_far_in_the_future_is_refused():
    future = int(time.time()) + su.MAX_FUTURE_SKEW_SECONDS + 60
    wire, private = _signed(published_at=future)
    result = _verify(wire, private=private)
    assert result["ok"] is False
    assert any("future" in p for p in result["problems"])


# ── staging: never leave a half-written binary ───────────────────────────

def test_stage_update_writes_the_bytes_and_leaves_no_temporary(tmp_path):
    target = tmp_path / "widget.bin"
    written = su.stage_update(str(target), NEXT)
    assert written == str(target)
    assert target.read_bytes() == NEXT
    leftovers = [n for n in os.listdir(tmp_path) if n.startswith(".nx-update-")]
    assert leftovers == [], "a temporary file survived the rename"


def test_stage_update_replaces_an_existing_file_atomically(tmp_path):
    target = tmp_path / "widget.bin"
    target.write_bytes(BODY)
    su.stage_update(str(target), NEXT, mode=0o600)
    assert target.read_bytes() == NEXT
    assert oct(os.stat(target).st_mode & 0o777) == oct(0o600)


def test_a_refused_update_is_never_staged(tmp_path):
    """The refusal has to come BEFORE the disk is touched."""
    target = tmp_path / "widget.bin"
    target.write_bytes(BODY)
    wire, private = _signed(sequence=2)
    result = _verify(wire, private=private, current_sequence=99)
    assert result["ok"] is False
    assert target.read_bytes() == BODY, "a refused update replaced the file"


def test_manifest_records_the_digest_of_the_bytes_it_describes():
    manifest = su.make_manifest("w.bin", NEXT, "1.0", 1)
    assert manifest["sha256"] == hashlib.sha256(NEXT).hexdigest()
    assert manifest["size"] == len(NEXT)


def test_signing_a_foreign_schema_is_refused():
    with pytest.raises(su.UpdateError):
        su.sign_manifest({"schema": "something-else"}, _key())
