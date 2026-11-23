"""Regression tests for the second-round adversarial findings.

Every test here asserts the CORRECT behaviour, not the current behaviour. Six of
them cover defects that are NOT yet fixed, so they are marked
``xfail(strict=True)``: they execute on every gate run, report as `xfailed`, and
the moment the defect is fixed the test XPASSes and a strict xfail turns that
into a FAILURE demanding the marker be removed. A defect can therefore never be
fixed silently, and none of these can rot unnoticed.

The one finding that is only a documentation error (AI-CRYPTO-005) was fixed in
the same pass, so its test now PASSES and is not xfailed.

Honest note on the earlier reasoning: this module first argued against xfail on
the grounds that "a strict xfail that nobody runs is the same as no test". That
objection does not apply here -- the file is inside tests/, so the derived shard
gate assigns and executes it every run, which the aggregate proves (7 xfailed
appear in the shard output). The objection was right in general and wrong for
this file.

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

@pytest.mark.xfail(
    strict=True,
    reason="AI-CRYPTO-004 open: the decoy key is derivable from the emitted "
           "artefact (sha256 of _NX_SECTION_PACK) and confirmable against "
           "_NX_HONEY_HINT, so the bait is identifiable")
def test_decoy_key_is_not_derivable_from_the_artefact():
    """The decoy's key must not be recoverable from published values.

    The shipped path derives the decoy key from sha256(_section_pack_val) and
    publishes _section_pack_val verbatim as _NX_SECTION_PACK, then publishes
    the decoy hint as _NX_HONEY_HINT. An analyst who reads the file can
    therefore do exactly this:

        bid = sha256(pack_text.encode()).digest()[:16].hex()
        key = decoy_key(bid)                  # honeypayload.decoy_key
        assert sha256(key).hexdigest()[:16] == emitted_hint

    The assertion below is the security property: that derivation must NOT
    reproduce the emitted hint. It does today, so this test fails.
    """
    from obfuscator.honeypayload import build_honey_pack, decoy_key
    from obfuscator.section_split import pack_json

    real_js, _real_key = pack_json(b"REAL" * 40, sections=2)
    pack_text = base64.b85encode(real_js).decode("ascii")   # == _NX_SECTION_PACK

    seed = hashlib.sha256(str(pack_text).encode("utf-8")).digest()
    hp = build_honey_pack(seed, seed[:16].hex())
    emitted_hint = hp["key_hint"]                            # == _NX_HONEY_HINT

    analyst_build_id = hashlib.sha256(pack_text.encode("utf-8")).digest()[:16].hex()
    analyst_key = decoy_key(analyst_build_id)
    analyst_hint = hashlib.sha256(analyst_key).hexdigest()[:16]

    assert analyst_hint != emitted_hint, (
        "the decoy key is derivable from the emitted artefact: an analyst who "
        "computes sha256(_NX_SECTION_PACK) obtains the decoy key and confirms "
        "it against _NX_HONEY_HINT, which identifies the real payload")


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

@pytest.mark.xfail(
    strict=True,
    reason="AI-PROTO-006 open: ReplayLedger._store swallows OSError and "
           "check_and_record ignores its result, so an unwritable ledger "
           "accepts every replay with no error")
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

    assert first is True, "the first presentation of a fresh token must pass"
    assert second is False, (
        "a ledger that cannot persist accepted a replay: the second "
        "presentation of the same token returned True, so replay protection "
        "is absent on unwritable media and the caller is told nothing")


# ── AI-PROTO-008: rollback ignores write_mark() failure ───────────────────

@pytest.mark.xfail(
    strict=True,
    reason="AI-PROTO-008 open: check_rollback discards write_mark's False, so "
           "an unarmed anti-rollback mark accepts every protection level")
def test_rollback_refuses_when_the_mark_cannot_be_written(tmp_path):
    """An unarmed anti-rollback mark is a failed check, not a silent pass."""
    from obfuscator.rollback import MARK_NAME, check_rollback, write_mark

    artefact = tmp_path / "app.py"
    artefact.write_text("print('app')\n", encoding="utf-8")
    mark = tmp_path / MARK_NAME

    key = b"\x77" * 32
    # Prove the mark cannot be armed here, then assert check_rollback says so.
    tmp_path.chmod(0o555)
    try:
        assert write_mark(str(mark), key, 5, "app.py") is False, (
            "precondition: the mark must be unwritable for this test")
        with pytest.raises(Exception):
            check_rollback(str(artefact), 5, key)
    finally:
        tmp_path.chmod(0o755)

    assert not mark.exists()


# ── AI-PROTO-009: revocation rollback guard must be reachable ─────────────

@pytest.mark.xfail(
    strict=True,
    reason="AI-PROTO-009 open: licensing.verify calls check_revoked without "
           "previous_issued_at, so the rolled-back-list guard can never fire")
def test_revocation_rollback_guard_is_wired():
    """licensing.verify must pass a high-water mark, or the guard is dead."""
    import inspect

    from obfuscator import licensing

    source = inspect.getsource(licensing.verify)
    call = [ln.strip() for ln in source.splitlines()
            if "check_revoked(" in ln and "import" not in ln]
    assert call, "licensing.verify no longer calls check_revoked at all"
    joined = " ".join(call)
    assert "previous_issued_at" in joined, (
        "licensing.verify calls check_revoked without previous_issued_at, so "
        "the argument defaults to 0 and 'issued < previous_issued_at' can "
        "never be true: an old signed revocation list un-revokes a licence. "
        "Call was: %s" % joined)


# ── AI-PARSE-010: legacy manifest fingerprint forgery ─────────────────────

@pytest.mark.xfail(
    strict=True,
    reason="AI-PARSE-010 open: without a top-level signed_key_fingerprint the "
           "nested copy is unauthenticated, so a genuine artefact can be "
           "re-attributed to another key and still verify ok: True")
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

@pytest.mark.xfail(
    strict=True,
    reason="AI-PARSE-011 open: stream_join raises TypeError for non-dict packs, "
           "None sections and numeric-string framing fields while its docstring "
           "promises ValueError")
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
