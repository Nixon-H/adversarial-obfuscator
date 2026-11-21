"""§7: the manifest must record the native blob the artefact actually carries.

Measured 2026-11-20. A `--package native` build produced a deliverable whose
`NATIVE_BLOBS` held a 110,488-byte .so, and running it loaded that module from
a temp `_nx_*.so` (module origin proved the native path, not bytecode). The
build manifest beside the very same artefact said:

    "native_blob": {"bytes": 0, "sha256": ""}

Two independent facts were wrong with that:

  * It was FALSE. A reader using the manifest to answer "is this artefact
    native, and which object is inside it" got the opposite answer.
  * It was UNFIXABLE by inspection. The compiled modules never touch disk --
    the build holds them base64-encoded and XOR-packs them straight into the
    loader -- so there was no path for `native_blob_path` to hash, and no
    caller ever set it. A control that can only ever report "absent" is worse
    than no control: it trains a reader to ignore the field.

These tests pin the replacement contract: the record is built from the
in-memory mapping, covers every embedded platform, states which form the hash
covers, and stays honestly empty for a bytecode-only artefact.
"""
import base64
import hashlib
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.build_manifest import (  # noqa: E402
    MANIFEST_SUFFIX, build_manifest, sign_manifest, verify_manifest,
    write_manifest,
)


def _artefact(tmp_path, body="print('x')\n"):
    p = tmp_path / "art.py"
    p.write_text(body, encoding="utf-8")
    return str(p)


def _record(tmp_path, **kwargs):
    art = _artefact(tmp_path)
    path = write_manifest(art, **kwargs)
    return json.loads(open(path, encoding="utf-8").read())["native_blob"]


def test_native_blob_record_is_written_from_the_in_memory_mapping(tmp_path):
    """The exact defect: a real blob must not be recorded as bytes: 0."""
    elf = b"\x7fELF" + bytes(range(256)) * 4
    rec = _record(tmp_path, native_blobs={
        "linux": base64.b64encode(elf).decode("ascii")})
    assert rec["bytes"] == len(elf), rec
    assert rec["sha256"] == hashlib.sha256(elf).hexdigest(), rec
    assert rec["platforms"]["linux"]["bytes"] == len(elf), rec


def test_the_record_states_which_form_the_hash_covers(tmp_path):
    """Packed bytes and plaintext bytes hash differently; say which is which.

    The artefact carries the object image XOR-packed against the loader's
    derived key. Anyone hashing the embedded base64 literal gets a different
    digest than this record and would reasonably conclude the artefact had
    been tampered with. Naming the form is what stops that false positive.
    """
    elf = b"\x7fELF" + b"\x02" * 128
    rec = _record(tmp_path, native_blobs={
        "linux": base64.b64encode(elf).decode("ascii")})
    assert rec["hashed_form"] == "plaintext-object-image", rec
    packed = bytes(b ^ 0x5A for b in elf)
    assert hashlib.sha256(packed).hexdigest() != rec["sha256"], \
        "the test's packing must differ from the plaintext to be meaningful"


def test_record_covers_every_embedded_platform(tmp_path):
    """One-platform and three-platform builds must not look the same."""
    win = b"MZ" + b"\x00" * 400
    lin = b"\x7fELF" + b"\x01" * 300
    rec = _record(tmp_path, native_blobs={
        "windows": base64.b64encode(win).decode("ascii"),
        "linux": base64.b64encode(lin).decode("ascii"),
        "darwin": "",
    })
    assert set(rec["platforms"]) == {"windows", "linux"}, rec
    # The top-level pair describes the largest blob, so a reader that only
    # knows the single-blob schema still sees a real size and its digest.
    assert rec["bytes"] == len(win), rec
    assert rec["sha256"] == rec["platforms"]["windows"]["sha256"], rec


def test_empty_platforms_are_not_recorded_as_blobs(tmp_path):
    """`{'linux': '', 'windows': ''}` is a bytecode build, not a native one."""
    rec = _record(tmp_path, native_blobs={"linux": "", "windows": "", "darwin": ""})
    assert rec["bytes"] == 0, rec
    assert rec["platforms"] == {}, rec


def test_python_only_build_records_no_native_blob(tmp_path):
    """The fix must not invent a blob for a bytecode-only artefact."""
    rec = _record(tmp_path)
    assert rec["bytes"] == 0, rec
    assert rec["sha256"] == "", rec
    assert rec["platforms"] == {}, rec


def test_native_blob_path_still_works_for_callers_that_have_a_file(tmp_path):
    """The pre-existing file-based input must keep its meaning."""
    blob = tmp_path / "payload.so"
    blob.write_bytes(b"\x7fELF" + b"\x03" * 64)
    rec = _record(tmp_path, native_blob_path=str(blob))
    assert rec["bytes"] == 68, rec
    assert rec["sha256"] == hashlib.sha256(blob.read_bytes()).hexdigest(), rec


# ── manifest trust anchor (review register, third pass, item 2) ───────────
#
# The RC acceptance found that the provenance key and the manifest key are
# two INDEPENDENT signing inputs, and the anchor question applies to both: a
# manifest that authenticates itself through its own embedded key would
# recreate the exact fail-open the provenance fix just closed. The anchor is
# the NIXON_BUILD_MANIFEST_PUBKEY out-of-band pin; under the release policy a
# signed manifest with NO trusted anchor is a failed verdict.


def test_manifest_re_signed_by_untrusted_key_rejected_under_publisher_pin(
        tmp_path, monkeypatch):
    """The publisher's pin refuses a manifest re-signed by another key.

    An attacker re-signs the manifest with their own Ed25519 key: the hash
    still matches, the 'signed' flag is still true, and the signature is
    valid FOR THE ATTACKER KEY. Only the out-of-band publisher pin rejects
    it.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey)
    art = _artefact(tmp_path)
    attacker = Ed25519PrivateKey.generate()
    mpath = write_manifest(art, private_key=attacker)
    assert mpath
    publisher = Ed25519PrivateKey.generate()
    monkeypatch.setenv("NIXON_BUILD_MANIFEST_PUBKEY",
                       publisher.public_key().public_bytes_raw().hex())
    res = verify_manifest(art)
    assert res["ok"] is False, (
        "a manifest re-signed by an untrusted key was accepted under the "
        "publisher's pin")
    assert "signature invalid" in res["reason"], res["reason"]


def test_manifest_with_the_correct_pin_verifies(tmp_path, monkeypatch):
    """The publisher's own pin verifies the publisher's manifest."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey)
    art = _artefact(tmp_path)
    publisher = Ed25519PrivateKey.generate()
    write_manifest(art, private_key=publisher)
    monkeypatch.setenv("NIXON_BUILD_MANIFEST_PUBKEY",
                       publisher.public_key().public_bytes_raw().hex())
    res = verify_manifest(art)
    assert res["ok"] is True, res["reason"]
    assert res["signed"] is True


def test_release_policy_refuses_a_signed_manifest_with_no_anchor(
        tmp_path, monkeypatch):
    """No anchor + release policy = failed verdict, never hash-only trust.

    With NIXON_REQUIRE_PROVENANCE=1 a signed manifest whose signature cannot
    be checked against a trusted anchor FAILS instead of trusting the hash.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey)
    art = _artefact(tmp_path)
    write_manifest(art, private_key=Ed25519PrivateKey.generate())
    monkeypatch.delenv("NIXON_BUILD_MANIFEST_PUBKEY", raising=False)
    monkeypatch.setenv("NIXON_REQUIRE_PROVENANCE", "1")
    res = verify_manifest(art)
    assert res["ok"] is False, (
        "a signed manifest passed WITHOUT any trusted anchor under the "
        "release policy")
    assert "trusted anchor" in res["reason"]


def test_unsigned_manifest_reports_unsigned_without_policy(tmp_path,
                                                           monkeypatch):
    """Without the release policy the old contract holds: no anchor and no
    signature means 'unsigned', which is reported rather than fatal."""
    art = _artefact(tmp_path)
    write_manifest(art)
    monkeypatch.delenv("NIXON_BUILD_MANIFEST_PUBKEY", raising=False)
    monkeypatch.delenv("NIXON_REQUIRE_PROVENANCE", raising=False)
    res = verify_manifest(art)
    assert res["ok"] is True and res["signed"] is False


def test_the_manifest_pin_env_var_matches_the_documented_name():
    """The policy doc names the SAME env var the implementation reads."""
    from obfuscator.build_manifest import MANIFEST_PIN_ENV
    doc = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "docs", "MAXIMUM_SECURITY.md"),
               encoding="utf-8").read()
    assert "NIXON_BUILD_MANIFEST_PUBKEY" in doc
    assert MANIFEST_PIN_ENV == "NIXON_BUILD_MANIFEST_PUBKEY"
