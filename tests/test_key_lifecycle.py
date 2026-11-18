"""§2 explicit key rotation and licence revocation.

Rotation is not "a token whose signature still verifies": it is "a token for a
generation that is still accepted". A signed-but-retired token must fail, and
so must one from a generation the verifier has not seen yet (accepting it would
let a revoked key keep working).

Revocation is an issuer-signed list of licence ids and/or token nonces. An
unsigned list is refused, because an attacker who can edit one could revoke
everyone or un-revoke themselves, and a list OLDER than one already seen is
refused so a rollback cannot un-revoke.

Honest limit, asserted below: both documents are checked by an honest client.
Dropping the list, or patching the call, defeats them. Genuine revocation needs
the artefact to reach an issuer.
"""
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator import key_lifecycle as kl  # noqa: E402
from obfuscator.licensing import (  # noqa: E402
    Licence, LicenceError, issue, resolve_private_key, verify,
)

KEY = resolve_private_key("33" * 32)


def _policy(current=3, minimum=2):
    return kl.read_key_policy(kl.make_key_policy(current, minimum, KEY),
                              KEY.public_key())


def _token(generation, licence_id="L1", nonce="n1"):
    now = time.time()
    return issue(Licence(licence_id=licence_id, customer="acme",
                         issued_at=now, expires_at=now + 3600,
                         key_version=generation, nonce=nonce), KEY)


def _revocation(ids=(), nonces=(), issued_at=None):
    raw = kl.make_revocation_list(ids, nonces, KEY, issued_at=issued_at)
    return kl.read_revocation_list(raw, KEY.public_key())


# ── key rotation ────────────────────────────────────────────────────────

def test_current_generation_accepted():
    assert verify(_token(3), KEY.public_key(), key_policy=_policy()).key_version == 3


def test_grace_generation_accepted():
    assert verify(_token(2, nonce="n2"), KEY.public_key(),
                  key_policy=_policy()).key_version == 2


def test_retired_generation_refused():
    with pytest.raises(LicenceError, match="retired"):
        verify(_token(1, nonce="n3"), KEY.public_key(), key_policy=_policy())


def test_future_generation_refused():
    """A token newer than the policy means the verifier holds a stale policy."""
    with pytest.raises(LicenceError, match="newer than this build"):
        verify(_token(9, nonce="n9"), KEY.public_key(), key_policy=_policy())


def test_unversioned_token_refused_under_policy():
    with pytest.raises(LicenceError, match="no key_version"):
        verify(_token(None), KEY.public_key(), key_policy=_policy())


def test_edited_policy_breaks_the_signature():
    raw = kl.make_key_policy(3, 2, KEY)
    doc = json.loads(raw)
    doc["payload"]["minimum"] = 0
    with pytest.raises(kl.KeyPolicyError, match="signature"):
        kl.read_key_policy(json.dumps(doc), KEY.public_key())


def test_invalid_generation_pairs_are_refused():
    for current, minimum in ((2, 3), (-1, 0), ("3", 2)):
        with pytest.raises(kl.KeyPolicyError):
            kl.make_key_policy(current, minimum, KEY)


def test_rotate_keys_produces_an_independent_key():
    rotated = kl.rotate_keys("44" * 32, "55" * 32, 4)
    assert rotated["new_key"].public_key().public_bytes_raw() != \
        rotated["old_key"].public_key().public_bytes_raw()
    assert kl.read_key_policy(rotated["policy"],
                              rotated["new_key"].public_key())["current"] == 4


def test_rotate_keys_refuses_a_no_op_rotation():
    """Rotating to the same key changes nothing and must be rejected."""
    with pytest.raises(kl.KeyPolicyError, match="DIFFERENT key"):
        kl.rotate_keys("44" * 32, "44" * 32, 2)


# ── revocation ──────────────────────────────────────────────────────────

def test_revoked_licence_refused_through_verify():
    with pytest.raises(LicenceError, match="revoked"):
        verify(_token(3), KEY.public_key(),
               revocation_list=_revocation(ids=["L1"]))


def test_clean_licence_passes_a_revocation_list():
    lic = verify(_token(3, licence_id="L9", nonce="n9"), KEY.public_key(),
                 revocation_list=_revocation(ids=["L1"]))
    assert lic.licence_id == "L9"


def test_revoked_nonce_refused():
    with pytest.raises(kl.RevocationError, match="nonce match"):
        kl.check_revoked({"licence_id": "L9", "nonce": "n1"},
                         _revocation(nonces=["n1"]))


def test_unsigned_revocation_list_refused():
    raw = kl.make_revocation_list(["L1"])  # no private_key => no signature
    with pytest.raises(kl.RevocationError, match="unsigned"):
        kl.read_revocation_list(raw, KEY.public_key())


def test_rolled_back_revocation_list_refused():
    """An older list must not be usable to un-revoke a licence."""
    newer = _revocation(issued_at=2000)
    with pytest.raises(kl.RevocationError, match="rolled-back"):
        kl.check_revoked({"licence_id": "L9"}, newer, previous_issued_at=3000)


def test_edited_revocation_list_breaks_the_signature():
    raw = kl.make_revocation_list([], [], KEY, issued_at=1000)
    doc = json.loads(raw)
    doc["payload"]["licence_ids"] = []
    with pytest.raises(kl.RevocationError, match="signature"):
        # Re-sign nothing: the attacker cannot produce a valid sig for an edit.
        forged = json.loads(raw)
        forged["payload"]["licence_ids"] = ["L9"]
        kl.read_revocation_list(json.dumps(forged), KEY.public_key())


@pytest.mark.parametrize("field", ["licence_ids", "nonces"])
def test_empty_fields_are_valid(field):
    payload = _revocation()
    assert payload[field] == []


def test_dropping_the_list_defeats_revocation():
    """Documented limit: a client that omits the list enforces nothing.

    Pinned as a test so it cannot be quietly forgotten. If this ever fails
    because revocation became issuer-enforced, update key_lifecycle's docstring
    -- do not delete the test.
    """
    assert verify(_token(3), KEY.public_key()).licence_id == "L1"
