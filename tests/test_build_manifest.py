"""§7 supply chain: a build manifest must bind an artefact to its inputs.

The review's point: a compromised build runner can bypass every protection
implemented in the compiler, so the artefact needs evidence of what produced
it. Before this existed, artefacts were signed per-file but nothing recorded
the compiler version, source hash or transform set -- a swapped toolchain or a
silently dropped flag was undetectable.

These tests cover the parts that must not regress: tamper detection, signature
verification with a right and a wrong key, and the fail-closed behaviour when
signing was requested but the manifest could not be produced.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.build_manifest import (  # noqa: E402
    MANIFEST_SUFFIX, SCHEMA, write_manifest, verify_manifest,
)


def _artefact(tmp_path, body="print('x')\n"):
    p = tmp_path / "art.py"
    p.write_text(body, encoding="utf-8")
    return str(p)


def test_manifest_records_toolchain_and_hashes(tmp_path):
    art = _artefact(tmp_path)
    src = tmp_path / "src.py"
    src.write_text("print('x')\n", encoding="utf-8")
    path = write_manifest(art, str(src),
                          transforms=["opaque-predicates(3)"],
                          seed_classes={"reproducible": "sha256(payload)"})
    assert path and os.path.exists(path)
    m = json.load(open(path))
    assert m["schema"] == SCHEMA
    assert m["artefact"]["sha256"], "artefact hash not recorded"
    assert m["source"]["src.py"], "source hash not recorded"
    assert m["toolchain"]["python"], "python version not recorded"
    assert m["transforms"] == ["opaque-predicates(3)"]
    assert m["seeds"]["reproducible"] == "sha256(payload)"


def test_verify_accepts_untampered_artefact(tmp_path):
    art = _artefact(tmp_path)
    write_manifest(art)
    r = verify_manifest(art)
    assert r["ok"] is True, r["reason"]


def test_verify_detects_artefact_tamper(tmp_path):
    art = _artefact(tmp_path)
    write_manifest(art)
    with open(art, "a", encoding="utf-8") as fh:
        fh.write("# injected\n")
    r = verify_manifest(art)
    assert r["ok"] is False
    assert "hash mismatch" in r["reason"], r["reason"]


def test_missing_manifest_is_not_a_pass(tmp_path):
    art = _artefact(tmp_path)
    r = verify_manifest(art)
    assert r["ok"] is False
    assert "missing" in r["reason"]


def test_signature_verifies_and_wrong_key_is_rejected(tmp_path):
    ed = pytest.importorskip(
        "cryptography.hazmat.primitives.asymmetric.ed25519")
    art = _artefact(tmp_path)
    key = ed.Ed25519PrivateKey.generate()
    write_manifest(art, private_key=key)
    m = json.load(open(art + MANIFEST_SUFFIX))
    assert m["signed"] is True
    assert verify_manifest(art, key.public_key())["ok"] is True
    other = ed.Ed25519PrivateKey.generate().public_key()
    r = verify_manifest(art, other)
    assert r["ok"] is False
    assert "signature invalid" in r["reason"], r["reason"]


def test_unsigned_manifest_fails_when_key_is_required(tmp_path):
    """A verifier that pins a key must not accept an unsigned manifest."""
    ed = pytest.importorskip(
        "cryptography.hazmat.primitives.asymmetric.ed25519")
    art = _artefact(tmp_path)
    write_manifest(art)  # no key -> unsigned
    key = ed.Ed25519PrivateKey.generate()
    r = verify_manifest(art, key.public_key())
    assert r["ok"] is False
    assert "unsigned" in r["reason"], r["reason"]


def test_signed_manifest_survives_reserialisation(tmp_path):
    """The signature covers canonical JSON, not the file's byte order."""
    ed = pytest.importorskip(
        "cryptography.hazmat.primitives.asymmetric.ed25519")
    art = _artefact(tmp_path)
    key = ed.Ed25519PrivateKey.generate()
    path = write_manifest(art, private_key=key)
    m = json.load(open(path))
    # rewrite with different formatting / key order
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dict(reversed(list(m.items()))), fh)
    assert verify_manifest(art, key.public_key())["ok"] is True
