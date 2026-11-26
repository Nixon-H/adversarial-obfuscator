"""Regression tests for the second-round adversarial findings.

Every test here asserts the correct behaviour. AI-CRYPTO-004 was fixed by
operator-keyed decoy derivation; the remaining protocol/parser findings are
covered directly rather than hidden behind permanent xfail markers.

The one finding that is only a documentation error (AI-CRYPTO-005) was fixed in
the same pass, so its test now passes. AI-CRYPTO-004 is fixed by operator-keyed
decoy derivation and its regression test now passes directly. No test in this
module remains xfailed.

Finding -> test:
  AI-CRYPTO-004  test_decoy_key_is_not_derivable_from_the_artefact
  AI-CRYPTO-005  test_documents_state_the_true_pack_id_size        (FIXED: passes)
  AI-PROTO-006   test_unwritable_ledger_fails_closed
  AI-PROTO-008   test_rollback_refuses_when_the_mark_cannot_be_written
  AI-PROTO-009   test_revocation_rollback_guard_is_wired
  AI-PARSE-010   test_legacy_manifest_fingerprint_cannot_be_forged
  AI-PARSE-011   test_stream_join_raises_valuederror_for_every_malformed_class

AI-PROTO-007 (the concurrent-ledger race) lives in its own file,
tests/test_ledger_race_deterministic.py: the interleaving is FORCED with a
multiprocessing barrier rather than relied on, so it is deterministic. An earlier
revision of this docstring said the race could not be tested because "a test that
passes today would be proving scheduler luck". That was half right -- natural
timing is flaky -- but forcing every reader to finish before any writer starts
makes the window reproducible, and the measured result is 6/6 acceptances where 1
is required.
"""
import base64
import hashlib
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ── AI-CRYPTO-004: decoy key derivable from the artefact ──────────────────

def test_decoy_key_is_not_derivable_from_the_artefact():
    """The decoy's key must not be recoverable from published values.

    AI-CRYPTO-004 is fixed by keying decoy-key derivation with operator-held
    secret material.  This test preserves the original attack: derive the old
    key solely from the emitted section pack and show that it no longer matches
    the decoy pack's key hint.  The operator-secret derivation is checked too,
    proving the test is exercising the real replacement rather than merely a
    broken decoy build.
    """
    from obfuscator.honeypayload import build_honey_pack, decoy_key
    from obfuscator.section_split import pack_json

    operator_secret = "test-only-honey-secret"
    real_js, _real_key = pack_json(b"REAL" * 40, sections=2)
    pack_text = base64.b85encode(real_js).decode("ascii")   # == _NX_SECTION_PACK

    seed = hashlib.sha256(str(pack_text).encode("utf-8")).digest()
    build_id = seed[:16].hex()
    hp = build_honey_pack(seed, build_id, operator_secret=operator_secret)
    emitted_hint = hp["key_hint"]

    analyst_key = hashlib.sha256(
        b"nx-honey-decoy:" + build_id.encode("utf-8")).digest()
    analyst_hint = hashlib.sha256(analyst_key).hexdigest()[:16]
    assert analyst_hint != emitted_hint, (
        "the old artefact-public decoy-key derivation still reproduces the "
        "emitted key hint")

    operator_hint = hashlib.sha256(
        decoy_key(build_id, operator_secret)).hexdigest()[:16]
    assert operator_hint == emitted_hint, (
        "precondition: the operator-secret key must actually seal this pack")
    assert operator_secret not in hp["pack_b85"]
    assert operator_secret not in hp["source"]


# ── AI-CRYPTO-005: documented pack_id size ────────────────────────────────

def test_documents_state_the_true_pack_id_size():
    """The packages call pack_id one of three 64-bit truncations. It is 128."""
    from obfuscator.section_split import PACK_ID_BYTES, _pack_id

    actual_bits = len(_pack_id(b"K" * 32, b"N" * PACK_ID_BYTES)) * 8
    assert actual_bits == PACK_ID_BYTES * 8
    assert actual_bits == 128, "pack_id changed size; update the documents"

    docs = [
        os.path.join(ROOT, "docs", "security", "CRYPTO_REVIEW_PACKAGE.md"),
        os.path.join(ROOT, "docs", "security",
                     "CRYPTO_REVIEW_BUNDLE_STANDALONE.md"),
    ]
    offenders = []
    for path in docs:
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if "pack_id" not in line:
                    continue
                if re.search(r"\b64 bits?\b", line):
                    offenders.append("%s:%d: %s"
                                     % (os.path.basename(path), lineno,
                                        line.strip()))
    assert not offenders, (
        "these lines state pack_id is 64 bits; it is %d bits:\n  %s"
        % (actual_bits, "\n  ".join(offenders)))


# ── AI-PROTO-006: replay ledger fails open when it cannot persist ─────────

def test_unwritable_ledger_fails_closed(tmp_path):
    """A ledger that cannot be written must not silently accept replays."""
    from obfuscator.licence_replay import ReplayLedger

    # A DIRECTORY occupying the ledger pathname: every write fails with
    # EISDIR, which _store() swallows.
    blocked = tmp_path / "seen.json"
    blocked.mkdir()
    ledger = ReplayLedger(path=str(blocked), window_s=300)

    first = ledger.check_and_record("identity-x")
    second = ledger.check_and_record("identity-x")

    assert first is False, (
        "a ledger that cannot persist must fail closed on the first use; "
        "accepting it would run with replay enforcement disarmed")
    assert second is False, "an unwritable ledger must keep failing closed"


# ── AI-PROTO-008: rollback ignores write_mark() failure ───────────────────

def test_rollback_refuses_when_the_mark_cannot_be_written(tmp_path):
    """An unarmed anti-rollback mark is a failed check, not a silent pass."""
    from obfuscator.rollback import MARK_NAME, check_rollback, write_mark

    artefact = tmp_path / "app.py"
    artefact.write_text("print('app')\n", encoding="utf-8")
    mark = tmp_path / MARK_NAME

    key = b"\x77" * 32
    # A directory occupying the mark pathname makes the final os.replace fail
    # even when the suite runs as root (where chmod(0555) is still writable).
    mark.mkdir()
    assert write_mark(str(mark), key, 5, "app.py") is False, (
        "precondition: the mark must be unwritable for this test")
    with pytest.raises(RuntimeError, match="mark could not be written"):
        check_rollback(str(artefact), 5, key)

    assert mark.is_dir()
    assert not list(tmp_path.glob(".nx-rb-*")), (
        "a failed atomic mark write must not leave temporary mark files behind")


# ── AI-PROTO-009: revocation rollback guard must be reachable ─────────────

def test_revocation_rollback_guard_is_wired():
    """licensing.verify must pass a high-water mark, or the guard is dead."""
    import inspect

    from obfuscator import licensing

    source = inspect.getsource(licensing.verify)
    assert "check_revoked(" in source, (
        "licensing.verify no longer calls check_revoked at all")
    assert "previous_issued_at=previous_revocation_issued_at" in source, (
        "licensing.verify calls check_revoked without the caller-supplied "
        "high-water mark, so the argument defaults to 0 and the rollback "
        "guard can never fire")


# ── AI-PARSE-010: legacy manifest fingerprint forgery ─────────────────────

def test_legacy_manifest_fingerprint_cannot_be_forged(tmp_path):
    """A manifest with no top-level fingerprint must not be re-attributable."""
    from cryptography.hazmat.primitives.asymmetric import ed25519

    from obfuscator.build_manifest import (
        MANIFEST_SUFFIX, build_manifest, sign_manifest, verify_manifest,
    )

    artefact = tmp_path / "payload.py"
    artefact.write_bytes(b"print('real')\n")
    mpath = tmp_path / ("payload.py" + MANIFEST_SUFFIX)

    real_key = ed25519.Ed25519PrivateKey.generate()
    other_key = ed25519.Ed25519PrivateKey.generate()

    def fp(pub):
        return hashlib.sha256(pub.public_bytes_raw()).hexdigest()[:16]

    # A VALID legacy manifest: signed, but predating the top-level field.
    legacy = sign_manifest(build_manifest(str(artefact)), private_key=real_key)
    legacy.pop("signed_key_fingerprint", None)
    body = {k: v for k, v in legacy.items() if k not in ("signature", "signed")}
    payload = json.dumps(body, sort_keys=True,
                         separators=(",", ":")).encode()
    legacy["signature"] = {
        "algo": "ed25519",
        "key_fingerprint": fp(real_key.public_key()),
        "sig": base64.b64encode(real_key.sign(payload)).decode(),
    }
    legacy["signed"] = True
    mpath.write_text(json.dumps(legacy), encoding="utf-8")
    assert verify_manifest(str(artefact),
                           public_key=real_key.public_key())["ok"] is True

    # Rewrite ONLY the unauthenticated nested fingerprint.
    legacy["signature"]["key_fingerprint"] = fp(other_key.public_key())
    mpath.write_text(json.dumps(legacy), encoding="utf-8")
    result = verify_manifest(str(artefact), public_key=real_key.public_key())

    assert result["ok"] is False, (
        "a legacy manifest's signing-key fingerprint was rewritable to a key "
        "that never signed it, and verify_manifest still reported ok: True; "
        "incident triage would attribute this artefact to the wrong key")


# ── AI-PARSE-011: stream_join contract ────────────────────────────────────

def test_stream_join_raises_valuederror_for_every_malformed_class():
    """The docstring promises ValueError; TypeError escapes for 4 classes."""
    from obfuscator.section_split import pack_json, stream_join

    key = b"\x42" * 32
    js, _ = pack_json(b"payload" * 16, sections=2, key=key)
    base = json.loads(js)

    cases = {}

    def count_as_string():
        p = json.loads(json.dumps(base))
        p["count"] = str(p["count"])
        from obfuscator.pack_state import state_digest
        p["state"] = state_digest(p["sections"], p["count"], p["total"])
        return p

    cases["count as numeric string"] = count_as_string
    cases["pack is a list"] = lambda: []
    cases["pack is None"] = lambda: None
    cases["sections is None"] = _sections_none(base)

    bad = []
    for label, make in cases.items():
        try:
            stream_join(make(), key)
        except ValueError:
            continue
        except Exception as exc:                      # noqa: BLE001
            bad.append("%s -> %s" % (label, type(exc).__name__))
    assert not bad, (
        "stream_join's docstring says it raises ValueError, but these inputs "
        "raised something else:\n  %s" % "\n  ".join(bad))


def _sections_none(base):
    def make():
        p = json.loads(json.dumps(base))
        p["sections"] = None
        return p
    return make
