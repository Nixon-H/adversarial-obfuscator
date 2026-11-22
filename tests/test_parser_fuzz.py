"""Malformed-input suite for the security-sensitive parsers (review
register, sixth pass, item 5).

The goal is NOT zero crashes — it is proving that malformed input cannot
produce an UNINTENDED ACCEPTANCE. Every parser here must either reject the
input or return a structured refusal; a parser that ACCEPTS malformed
framing (truncated records, oversized lengths, duplicate indices, wrong
magic, allocation-exhaustion lengths) is a bypass in the making.

All file writes go through pytest's ``tmp_path`` Path handles.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from obfuscator.section_split import split_sealed, stream_join  # noqa: E402
from obfuscator.build_manifest import (  # noqa: E402
    verify_manifest, write_manifest, MANIFEST_SUFFIX,
)

KEY = b"\xa5" * 32
PAYLOAD = b"fuzz-target-payload" * 40


def _valid_pack():
    return split_sealed(PAYLOAD, sections=4, key=KEY)


MALFORMED_PACKS = {
    "count larger than sections": lambda p: p.__setitem__("count", 9),
    "count zero": lambda p: p.__setitem__("count", 0),
    "total negative": lambda p: p.__setitem__("total", -1),
    "total huge": lambda p: p.__setitem__("total", 2 ** 31),
    "sections not a list": lambda p: p.__setitem__("sections", {"a": 1}),
    "section missing data": lambda p: p["sections"][0].pop("data"),
    "section missing nonce": lambda p: p["sections"][0].pop("nonce"),
    "nonce wrong length": lambda p: p["sections"][0].__setitem__("nonce", "ab"),
    "nonce not hex": lambda p: p["sections"][0].__setitem__("nonce", "zz"),
    "data not hex": lambda p: p["sections"][0].__setitem__("data", "zz"),
    "index negative": lambda p: p["sections"][0].__setitem__("i", -1),
    "index not int": lambda p: p["sections"][0].__setitem__("i", "0"),
    "key_hint wrong": lambda p: p.__setitem__("key_hint", "0" * 16),
    "state wrong": lambda p: p.__setitem__("state", "0" * 64),
    "v as string": lambda p: p.__setitem__("v", "2"),
    "v negative": lambda p: p.__setitem__("v", -2),
}


@pytest.mark.parametrize("name", sorted(MALFORMED_PACKS))
def test_malformed_pack_field_is_rejected(name):
    """Every malformed framing field must be refused, never accepted."""
    pack = _valid_pack()
    MALFORMED_PACKS[name](pack)
    with pytest.raises((ValueError, KeyError, TypeError)):
        stream_join(pack, KEY)


def test_malformed_manifest_json_is_refused(tmp_path, monkeypatch):
    """Non-JSON and truncated manifests refuse with ok: False."""
    monkeypatch.delenv("NIXON_BUILD_MANIFEST_PUBKEY", raising=False)
    monkeypatch.delenv("NIXON_REQUIRE_PROVENANCE", raising=False)
    art = tmp_path / "mf.py"
    art.write_text("print('mf')\n", encoding="utf-8")
    write_manifest(str(art))
    mpath = art.with_name(art.name + MANIFEST_SUFFIX)
    for bad in ('', '{', '{"schema": "nx-build-manifest/v1"', "null", "[]"):
        mpath.write_text(bad, encoding="utf-8")
        res = verify_manifest(str(art))
        assert res["ok"] is False, (
            "a malformed manifest (%r) was accepted" % bad)


def test_manifest_with_wrong_schema_is_refused(tmp_path, monkeypatch):
    monkeypatch.delenv("NIXON_BUILD_MANIFEST_PUBKEY", raising=False)
    monkeypatch.delenv("NIXON_REQUIRE_PROVENANCE", raising=False)
    art = tmp_path / "mf2.py"
    art.write_text("print('mf2')\n", encoding="utf-8")
    write_manifest(str(art))
    mpath = art.with_name(art.name + MANIFEST_SUFFIX)
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    manifest["schema"] = "something-else/v9"
    mpath.write_text(json.dumps(manifest, indent=2, sort_keys=True),
                     encoding="utf-8")
    res = verify_manifest(str(art))
    assert res["ok"] is False
    assert "schema" in res["reason"]


def test_manifest_with_oversized_fields_is_refused(tmp_path, monkeypatch):
    """Allocation-exhaustion lengths must not produce an acceptance."""
    monkeypatch.delenv("NIXON_BUILD_MANIFEST_PUBKEY", raising=False)
    monkeypatch.delenv("NIXON_REQUIRE_PROVENANCE", raising=False)
    art = tmp_path / "mf3.py"
    art.write_text("print('mf3')\n", encoding="utf-8")
    write_manifest(str(art))
    mpath = art.with_name(art.name + MANIFEST_SUFFIX)
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    manifest["artefact"]["sha256"] = "f" * 100000
    mpath.write_text(json.dumps(manifest, indent=2, sort_keys=True),
                     encoding="utf-8")
    res = verify_manifest(str(art))
    assert res["ok"] is False, "an oversized declared hash was accepted"


def test_binary_parsers_survive_hostile_input():
    """Truncated/absurd binary headers read as invalid, never crash the
    parser into an acceptance."""
    from obfuscator import native_harden as nh
    assert nh.verify_pe_bytes(b"")["valid"] is False
    assert nh.verify_pe_bytes(b"\x7fELF")["valid"] is False
    assert nh.verify_pe_bytes(b"MZ" + b"\x00" * 4)["valid"] is False
    assert nh.verify_macho_bytes(b"")["valid"] is False
    assert nh.verify_macho_bytes(b"\xcf\xfa\xed\xfe")["valid"] is False
    assert nh.verify_macho_bytes(
        b"\xcf\xfa\xed\xfe" + b"\x00" * 16)["valid"] is False


def test_pack_v2_join_survives_binary_garbage():
    """The join must refuse binary garbage, never accept it as a pack."""
    import base64
    from obfuscator.section_split import stream_join
    for garbage in (b"", b"\x00" * 64, b"\xff" * 64, KEY, KEY * 2):
        pack = {"sections": [{"i": 0,
                              "nonce": base64.b85encode(
                                  b"\x00" * 16).decode("ascii"),
                              "data": base64.b85encode(garbage).decode(
                                  "ascii")}],
                "count": 1, "total": len(garbage), "per_section": True,
                "v": 2, "key_hint": "0" * 16, "state": "0" * 64}
        raised = None
        try:
            stream_join(pack, KEY)
        except (ValueError, KeyError, TypeError) as exc:
            raised = exc
        assert raised is not None, (
            "binary garbage of length %d was ACCEPTED as a section"
            % len(garbage))


def test_malformed_inputs_produce_never_accept_never_crash():
    """The suite-level invariant: malformed framing is either refused with a
    structured error or reported invalid — never an acceptance. The row
    tests above are the measurements; this test states the goal so a future
    parser change keeps it true."""
    assert len(MALFORMED_PACKS) >= 16, (
        "the malformed-input matrix must stay populated")
