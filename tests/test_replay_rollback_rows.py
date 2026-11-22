"""§3 replay/rollback rows 4-7, measured (review register, seventh pass).

The first three rows of the register's attack table are measured against a
REAL signed artefact in the research log (§6f). These four are the rest:

  restore an older manifest           -> reject under the version policy
  restore an older signed artefact    -> reject when rollback is enabled
  replay after key rotation           -> follow the retirement policy, and
                                         assert the documented OFFLINE limit
  remove / corrupt persistent state   -> fail closed or documented recovery

Every case uses the real machinery (build_manifest / sign_manifest /
verify_manifest, rollback.check_rollback / read_mark) and pytest's tmp_path,
addressed through pathlib so no path is built by string concatenation.
"""
import hashlib
import hmac
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from obfuscator.build_manifest import (  # noqa: E402
    MANIFEST_PIN_ENV, verify_manifest, write_manifest,
)
from obfuscator.rollback import (  # noqa: E402
    MARK_NAME, SCHEMA, check_rollback, read_mark, write_mark,
)

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey)
except ImportError:  # pragma: no cover
    Ed25519PrivateKey = None

pytestmark = pytest.mark.skipif(
    Ed25519PrivateKey is None, reason="cryptography absent")

BODY = "print('rb-row')\n"


def _new_artefact(tmp_path):
    handle = tmp_path / "payload_protected.py"
    handle.write_text(BODY, encoding="utf-8")
    return handle


def _read_json(path):
    return json.loads(open(path, "r", encoding="utf-8").read())


def _write_json(path, doc):
    from pathlib import Path
    Path(path).write_text(json.dumps(doc, indent=2, sort_keys=True),
                          encoding="utf-8")


# ── ROW 4: restore an older manifest ─────────────────────────────────────

def test_row4_a_lowered_protection_level_breaks_the_signature(tmp_path):
    """The level is inside the signed body, so lowering it is a forgery."""
    art = _new_artefact(tmp_path)
    publisher = Ed25519PrivateKey.generate()
    mpath = write_manifest(str(art), private_key=publisher,
                           transforms=["dead-blocks(3)", "junk-functions(3)"])
    current = _read_json(mpath)
    level_now = current.get("protection_level")
    assert isinstance(level_now, int) and level_now > 0, (
        "the manifest does not record a protection_level at all")
    assert verify_manifest(str(art), publisher.public_key())["ok"] is True

    current["protection_level"] = 1
    _write_json(mpath, current)
    res = verify_manifest(str(art), publisher.public_key())
    assert res["ok"] is False, (
        "a lowered protection_level still verified — the level is not "
        "covered by the signature")
    assert "signature invalid" in res["reason"], res["reason"]


def test_row4_an_older_manifest_is_refused_under_the_publisher_pin(
        tmp_path, monkeypatch):
    """A genuinely older manifest, re-signed by another key, is refused."""
    art = _new_artefact(tmp_path)
    publisher = Ed25519PrivateKey.generate()
    write_manifest(str(art), private_key=publisher, transforms=["t1"])
    attacker = Ed25519PrivateKey.generate()
    write_manifest(str(art), private_key=attacker, transforms=["t1"],
                   protection_level=1)
    monkeypatch.setenv(MANIFEST_PIN_ENV,
                       publisher.public_key().public_bytes_raw().hex())
    res = verify_manifest(str(art))
    assert res["ok"] is False, (
        "an older manifest re-signed by an untrusted key was accepted under "
        "the publisher pin")
    assert "signature invalid" in res["reason"], res["reason"]


# ── ROW 5: restore an older signed artefact ──────────────────────────────

def test_row5_a_downgrade_below_the_high_water_mark_is_refused(tmp_path):
    art = str(_new_artefact(tmp_path))
    mark = str(tmp_path / MARK_NAME)
    key = os.urandom(32)
    check_rollback(art, 5, key, override_path=mark)
    raised = None
    try:
        check_rollback(art, 3, key, override_path=mark)
    except RuntimeError as exc:
        raised = exc
    assert raised is not None, "an older artefact was ACCEPTED"
    assert "refusing to downgrade" in str(raised)
    assert check_rollback(art, 5, key,
                          override_path=mark)["previous"] == 5


def test_row5_the_level_comes_from_the_signed_manifest(tmp_path):
    """The level the rollback check consumes is the one the build signed."""
    art = str(_new_artefact(tmp_path))
    mpath = write_manifest(art, transforms=["a", "b", "c", "d"])
    level = _read_json(mpath).get("protection_level")
    assert level == 4, (
        "protection_level is not derived from the build's transforms: %r"
        % (level,))
    mark = str(tmp_path / MARK_NAME)
    key = os.urandom(32)
    check_rollback(art, level, key, override_path=mark)
    with pytest.raises(RuntimeError):
        check_rollback(art, level - 1, key, override_path=mark)


# ── ROW 6: replay after key rotation ─────────────────────────────────────

def test_row6_retired_key_refused_by_rotated_pin_but_old_pin_still_accepts(
        tmp_path, monkeypatch):
    """Rotation is pin replacement; the OFFLINE limit is asserted."""
    art = str(_new_artefact(tmp_path))
    retired = Ed25519PrivateKey.generate()
    write_manifest(art, private_key=retired)
    old_pin = retired.public_key().public_bytes_raw().hex()
    new_pin = Ed25519PrivateKey.generate().public_key() \
        .public_bytes_raw().hex()
    monkeypatch.setenv("NIXON_REQUIRE_PROVENANCE", "1")
    monkeypatch.setenv(MANIFEST_PIN_ENV, new_pin)
    assert verify_manifest(art)["ok"] is False, (
        "a retired-key artefact was accepted under the rotated pin")
    monkeypatch.setenv(MANIFEST_PIN_ENV, old_pin)
    assert verify_manifest(art)["ok"] is True, (
        "the documented old-pin limitation no longer holds — verification "
        "is offline, so an un-updated client keeps accepting")


# ── ROW 7: remove / corrupt persistent state ─────────────────────────────

def test_row7_removed_state_is_a_fresh_install(tmp_path):
    art = str(_new_artefact(tmp_path))
    mark = str(tmp_path / MARK_NAME)
    res = check_rollback(art, 4, os.urandom(32), override_path=mark)
    assert res["previous"] == 0, "a removed mark was not a fresh install"
    assert os.path.exists(mark), "the mark was not re-created"


def test_row7_corrupt_state_falls_back_to_fresh_install_semantics(tmp_path):
    art = str(_new_artefact(tmp_path))
    handle = tmp_path / MARK_NAME
    handle.write_text("{not json", encoding="utf-8")
    res = check_rollback(art, 4, os.urandom(32), override_path=str(handle))
    assert res["previous"] == 0, "corrupt state produced a trusted level"


def test_row7_a_forged_mac_cannot_lower_the_mark(tmp_path):
    """THE DEFECT THIS ROW FOUND (2026-11-22).

    read_mark returned the stored level WITHOUT verifying the MAC, so an
    attacker who edited the level downward was obeyed — write_mark MAC'd the
    value but nothing ever checked it. The MAC is now verified on read: a
    forged mark reads as 0 (fresh-install), never as a trusted lower level.
    """
    art = str(_new_artefact(tmp_path))
    mark = str(tmp_path / MARK_NAME)
    key = os.urandom(32)
    check_rollback(art, 50, key, override_path=mark)
    data = _read_json(mark)
    data["level"] = 1
    _write_json(mark, data)
    assert read_mark(mark, key=key,
                     artefact_name=os.path.basename(art)) == 0, (
        "a forged MAC was trusted as a real level")
    res = check_rollback(art, 2, key, override_path=mark)
    assert res["previous"] == 0, res
    rewritten = _read_json(mark)
    expected = hmac.new(
        key,
        ("%s:2:%s" % (SCHEMA, os.path.basename(art))).encode(),
        hashlib.sha256).hexdigest()
    assert rewritten["level"] == 2 and rewritten["mac"] == expected, rewritten


def test_row7_a_valid_mac_is_still_honoured(tmp_path):
    """The MAC check must not break the legitimate path."""
    art = str(_new_artefact(tmp_path))
    mark = str(tmp_path / MARK_NAME)
    key = os.urandom(32)
    write_mark(mark, key, 9, os.path.basename(art))
    assert read_mark(mark, key=key,
                     artefact_name=os.path.basename(art)) == 9
    with pytest.raises(RuntimeError):
        check_rollback(art, 8, key, override_path=mark)
