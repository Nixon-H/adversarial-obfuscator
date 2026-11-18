"""§2 licence replay protection and key versioning.

Two gaps the review names: a captured token could be presented again
indefinitely, and nothing recorded which key generation sealed a build so a
revoked-but-unexpired token still verified.

The properties that matter, and why each is tested:

  * key_version and nonce are SIGNED. An unsigned version number is a label an
    attacker edits, not a constraint -- so the first thing to prove is that
    editing either field breaks verification.
  * a version mismatch is refused, and an unversioned token is refused when the
    build pins a generation (fails closed, does not skip).
  * a re-presented token is refused, while a different token from the same
    licence still passes (identity is the nonce, not the licence id).

Honest limit, asserted so nobody forgets it: the ledger is client-side. Deleting
it, running in a fresh container, or patching the check defeats replay
detection. This raises replay from free to "one extra step".
"""
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.licence_replay import (  # noqa: E402
    ReplayLedger, check_key_version, token_identity,
)
from obfuscator.licensing import (  # noqa: E402
    Licence, LicenceError, issue, resolve_private_key, verify,
)


@pytest.fixture
def keys():
    key = resolve_private_key("11" * 32)
    return key, key.public_key()


def _token(key, **overrides):
    now = time.time()
    base = dict(licence_id="L1", customer="acme", issued_at=now,
                expires_at=now + 3600)
    base.update(overrides)
    return issue(Licence(**base), key)


def test_matching_key_version_is_accepted(keys):
    key, pub = keys
    tok = _token(key, key_version=2, nonce="n-a")
    assert verify(tok, pub, required_key_version=2).key_version == 2


def test_wrong_key_version_is_refused(keys):
    key, pub = keys
    tok = _token(key, key_version=2, nonce="n-a")
    with pytest.raises(LicenceError, match="key generation"):
        verify(tok, pub, required_key_version=3)


def test_unversioned_token_fails_closed_when_version_required(keys):
    """A token with no generation must not be treated as "any generation"."""
    key, pub = keys
    tok = _token(key, nonce="n-b")
    with pytest.raises(LicenceError, match="no key_version"):
        verify(tok, pub, required_key_version=1)


def test_edited_key_version_breaks_the_signature(keys):
    """The version is signed; editing it must not be a way to satisfy the check."""
    key, pub = keys
    tok = _token(key, key_version=2, nonce="n-a")
    doc = json.loads(tok)
    doc["payload"]["key_version"] = 9
    with pytest.raises(LicenceError, match="signature"):
        verify(json.dumps(doc), pub, required_key_version=9)


def test_edited_nonce_breaks_the_signature(keys):
    """Editing the nonce must not be a way to dodge replay detection."""
    key, pub = keys
    tok = _token(key, key_version=1, nonce="n-a")
    doc = json.loads(tok)
    doc["payload"]["nonce"] = "n-other"
    with pytest.raises(LicenceError, match="signature"):
        verify(json.dumps(doc), pub)


def test_replayed_token_is_refused(keys, tmp_path):
    key, pub = keys
    ledger = ReplayLedger(path=str(tmp_path / "seen.json"), window_s=300)
    tok = _token(key, nonce="n-replay")
    assert verify(tok, pub, replay_ledger=ledger).licence_id == "L1"
    with pytest.raises(LicenceError, match="replayed"):
        verify(tok, pub, replay_ledger=ledger)


def test_distinct_token_from_same_licence_still_passes(keys, tmp_path):
    """Identity is the nonce: a legitimate re-issue must not look like a replay."""
    key, pub = keys
    ledger = ReplayLedger(path=str(tmp_path / "seen.json"), window_s=300)
    verify(_token(key, nonce="n-one"), pub, replay_ledger=ledger)
    verify(_token(key, nonce="n-two"), pub, replay_ledger=ledger)


def test_ledger_window_expiry_allows_the_identity_again(tmp_path):
    """A remember-window is not a permanent ban; the window bounds it."""
    ledger = ReplayLedger(path=str(tmp_path / "seen.json"), window_s=10)
    identity = "abc123"
    assert ledger.check_and_record(identity, now=1000.0) is True
    assert ledger.check_and_record(identity, now=1005.0) is False
    assert ledger.check_and_record(identity, now=1020.0) is True


def test_token_identity_prefers_the_signed_nonce():
    a = token_identity({"nonce": "x", "licence_id": "L"})
    b = token_identity({"nonce": "x", "licence_id": "OTHER"})
    c = token_identity({"nonce": "y", "licence_id": "L"})
    assert a == b, "the nonce must dominate: same token, same identity"
    assert a != c


def test_check_key_version_is_lenient_only_when_unpinned():
    check_key_version(None, None)          # unpinned build, unversioned token
    check_key_version(3, None)             # unpinned build, versioned token
    with pytest.raises(ValueError):
        check_key_version(None, 3)
    with pytest.raises(ValueError):
        check_key_version("nonsense", 3)
