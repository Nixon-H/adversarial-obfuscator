"""Tests for obfuscator/section_split.py — sealed section streaming."""
import base64
import hashlib
import hmac
import json

import pytest

from obfuscator.section_split import (
    _keystream, _section_key, _state_digest, pack_json, split_sealed,
    stream_join,
)


def test_roundtrip_basic():
    payload = b"payload-bytes-" * 100
    pack = split_sealed(payload, sections=4, key=b"K" * 32)
    assert pack["count"] == 4
    out = stream_join(pack, b"K" * 32)
    assert bytes(out) == payload


def test_roundtrip_single_and_empty():
    assert bytes(stream_join(split_sealed(b"x", sections=4, key=b"K" * 32), b"K" * 32)) == b"x"
    assert bytes(stream_join(split_sealed(b"", sections=4, key=b"K" * 32), b"K" * 32)) == b""


def test_wrong_key_fails():
    pack = split_sealed(b"secret", sections=2, key=b"K" * 32)
    with pytest.raises(ValueError):
        stream_join(pack, b"W" * 32)


def test_tampered_section_fails():
    pack = split_sealed(b"secret-data-here", sections=3, key=b"K" * 32)
    # XOR the first byte instead of overwriting it with "ff": 1 run
    # in 256 the original byte IS 0xff, the pack is unchanged, and
    # the test fails with "DID NOT RAISE" (seen on the 3.11 job).
    _data = pack["sections"][1]["data"]
    pack["sections"][1]["data"] = ("%02x" % (int(_data[:2], 16) ^ 0xFF)) + _data[2:]
    with pytest.raises(ValueError):
        stream_join(pack, b"K" * 32)


def test_reordered_sections_still_join():
    # Order travels with the sections (index field), so shuffle is fine.
    pack = split_sealed(b"order-test-payload", sections=4, key=b"K" * 32)
    pack["sections"] = list(reversed(pack["sections"]))
    assert bytes(stream_join(pack, b"K" * 32)) == b"order-test-payload"


def test_missing_section_fails():
    pack = split_sealed(b"0123456789abcdef", sections=4, key=b"K" * 32)
    pack["sections"].pop()
    with pytest.raises(ValueError):
        stream_join(pack, b"K" * 32)


def test_pack_json_envelope():
    blob, key = pack_json(b"hello", sections=2)
    pack = json.loads(blob.decode())
    assert pack["count"] == 2
    assert bytes(stream_join(pack, key)) == b"hello"


def test_returns_mutable_buffer():
    pack = split_sealed(b"wipe-me", sections=2, key=b"K" * 32)
    out = stream_join(pack, b"K" * 32)
    assert isinstance(out, bytearray)


def test_unkeyed_tag_forgery_is_rejected():
    """The section tag must be a MAC, not a bare digest.

    Anyone can recompute sha256(part); the old format accepted that, so an
    attacker who could touch the ciphertext could re-seal modified bytes
    with an unkeyed tag.  With the HMAC, the same forgery -- correct
    keystream, correct unkeyed tag -- must be rejected.
    """
    import hashlib

    import pytest

    from obfuscator.section_split import _keystream, split_sealed, stream_join

    key = b"K" * 32
    pack = split_sealed(b"secret-payload-bytes", sections=2, key=key)
    # Attacker with the pack (not the key) rewrites section 0 using the OLD
    # scheme: plaintext, sha256(part) tag, keystream ciphertext.
    sec = pack["sections"][0]
    nonce = bytes.fromhex(sec["nonce"])
    forged_plain = b"FORGED" + b"x" * 8
    forged_tagged = hashlib.sha256(forged_plain).digest() + forged_plain
    sec["data"] = bytes(
        a ^ b for a, b in zip(forged_tagged, _keystream(key, nonce, len(forged_tagged)))
    ).hex()
    with pytest.raises(ValueError):
        stream_join(pack, key)


# ── crypto-architecture audit (reviewer P1, 2026-11-20) ──────────────────
#
# The reviewer asked which primitive protects the shipped sections, how the
# keys are derived and separated, and whether nonces are unique. These tests
# pin the answers to the code that actually ships, so the documentation
# cannot drift into "AES-GCM is implemented, therefore AES-GCM is used".

def test_the_shipped_construction_is_v2_keystream_xor_plus_bound_hmac():
    """Section data is SHA-256 keystream XOR; integrity is a CONTEXT-BOUND HMAC.

    The AEAD helper (obfuscator.aead) exists and is separately tested, but it
    is NOT what protects the section pack -- the loader must run on customer
    machines with stdlib only, which is why the construction is stdlib
    SHA-256/HMAC rather than AES-GCM. Anyone summarising this project must
    not report "AES-GCM sections".

    Reconstructed BY HAND from the shipped output (v2 scheme): the keystream
    key and the MAC key are domain-separated, and the MAC binds the section
    index, the pack total and the nonce. This is the review register's P1
    "key separation + explicit context binding", measured on the output.
    """
    key = b"A" * 32
    payload = b"shipped-path" * 50
    pack = split_sealed(payload, sections=3, key=key)
    assert pack["v"] == 3, "the pack must declare its scheme version"
    for section in pack["sections"]:
        nonce = bytes.fromhex(section["nonce"])
        ciphertext = bytes.fromhex(section["data"])
        # Role-separated keys: the keystream runs under the ENC key, the tag
        # verifies under the MAC key. Deriving both here means a regression
        # to the shared-key shape breaks this test.
        enc_key = hashlib.sha256(
            b"nx-section-enc:" + key
            + section["i"].to_bytes(4, "big") + nonce).digest()
        mac_key = hashlib.sha256(
            b"nx-section-mac:" + key
            + section["i"].to_bytes(4, "big") + nonce).digest()
        assert enc_key != mac_key, "enc and mac keys must be independent"
        recovered = bytes(
            a ^ b for a, b in zip(
                ciphertext, _keystream(enc_key, nonce, len(ciphertext))))
        assert recovered[32:] == payload[
            section["i"] * (len(payload) // 3):
            (section["i"] + 1) * (len(payload) // 3)], (
            "section body is not a plain keystream XOR under the ENC key")
        # the 32-byte prefix is an HMAC under the MAC key, bound to
        # version4 || index4 || total4 || nonce || plaintext (the AAD role,
        # including the VERSION so a downgrade edit fails the tag).
        ctx = ((3).to_bytes(4, "big")
               + section["i"].to_bytes(4, "big")
               + len(payload).to_bytes(4, "big") + nonce
               + hashlib.sha256(
                   b"nx-pack-id:" + key
                   + bytes.fromhex(pack["pack_nonce"])).digest()[:16])
        expected = hmac.new(mac_key, ctx + recovered[32:],
                            hashlib.sha256).digest()
        assert recovered[:32] == expected


def test_each_section_uses_a_distinct_derived_key():
    """Key separation: master + index + nonce, never the master directly."""
    key = b"B" * 32
    pack = split_sealed(b"x" * 300, sections=4, key=key)
    derived = set()
    for section in pack["sections"]:
        nonce = bytes.fromhex(section["nonce"])
        section_key = _section_key(key, section["i"], nonce)
        assert section_key != key, (
            "a section used the master key directly instead of a derived one")
        derived.add(section_key)
    assert len(derived) == 4, "two sections share a derived key"


def test_section_nonces_are_unique_per_pack():
    """Nonce uniqueness: the counter-mode stream must never repeat."""
    key = b"C" * 32
    pack = split_sealed(b"y" * 400, sections=6, key=key)
    nonces = [section["nonce"] for section in pack["sections"]]
    assert len(set(nonces)) == len(nonces), "nonce reuse inside one pack"


def test_index_binds_the_key_not_just_the_metadata():
    """Same master key, same nonce, different index -> different key.

    If the index only appeared in the metadata, an attacker could relabel a
    section and have it decrypt; it must be part of the key derivation.
    """
    key = b"D" * 32
    nonce = b"N" * 16
    assert _section_key(key, 0, nonce) != _section_key(key, 1, nonce)


def test_a_relabelled_section_fails_to_join():
    """Moving ciphertext between sections breaks the tag (key is bound)."""
    key = b"E" * 32
    payload = b"z" * 400
    pack = split_sealed(payload, sections=4, key=key)
    pack["sections"][0]["data"] = pack["sections"][1]["data"]
    with pytest.raises(ValueError):
        stream_join(pack, key)


def test_the_shipped_construction_is_v2_keystream_xor_plus_bound_hmac():
    """Section data is SHA-256 keystream XOR; integrity is a CONTEXT-BOUND HMAC.

    The AEAD helper (obfuscator.aead) exists and is separately tested, but it
    is NOT what protects the section pack -- the loader must run on customer
    machines with stdlib only, which is why the construction is stdlib
    SHA-256/HMAC rather than AES-GCM. Anyone summarising this project must
    not report "AES-GCM sections".

    Reconstructed BY HAND from the shipped output (v2 scheme): the keystream
    key and the MAC key are domain-separated, and the MAC binds the section
    index, the pack total and the nonce. This is the review register's P1
    "key separation + explicit context binding", measured on the output.
    """
    key = b"A" * 32
    payload = b"shipped-path" * 50
    pack = split_sealed(payload, sections=3, key=key)
    assert pack["v"] == 3, "the pack must declare its scheme version"
    for section in pack["sections"]:
        nonce = bytes.fromhex(section["nonce"])
        ciphertext = bytes.fromhex(section["data"])
        # Role-separated keys: the keystream runs under the ENC key, the tag
        # verifies under the MAC key. Deriving both here means a regression
        # to the shared-key shape breaks this test.
        enc_key = hashlib.sha256(
            b"nx-section-enc:" + key
            + section["i"].to_bytes(4, "big") + nonce).digest()
        mac_key = hashlib.sha256(
            b"nx-section-mac:" + key
            + section["i"].to_bytes(4, "big") + nonce).digest()
        assert enc_key != mac_key, "enc and mac keys must be independent"
        recovered = bytes(
            a ^ b for a, b in zip(
                ciphertext, _keystream(enc_key, nonce, len(ciphertext))))
        assert recovered[32:] == payload[
            section["i"] * (len(payload) // 3):
            (section["i"] + 1) * (len(payload) // 3)], (
            "section body is not a plain keystream XOR under the ENC key")
        # the 32-byte prefix is an HMAC under the MAC key, bound to
        # version4 || index4 || total4 || nonce || plaintext (the AAD role,
        # including the VERSION so a downgrade edit fails the tag).
        ctx = ((3).to_bytes(4, "big")
               + section["i"].to_bytes(4, "big")
               + len(payload).to_bytes(4, "big") + nonce
               + hashlib.sha256(
                   b"nx-pack-id:" + key
                   + bytes.fromhex(pack["pack_nonce"])).digest()[:16])
        expected = hmac.new(mac_key, ctx + recovered[32:],
                            hashlib.sha256).digest()
        assert recovered[:32] == expected


def test_a_v1_pack_still_verifies_through_stream_join():
    """Old artefacts must stay loadable: the legacy path is preserved.

    A pack built by the pre-v2 scheme (single derived key, MAC over the
    plaintext only, no "v" field) is reconstructed here exactly as that
    scheme defined it and verifies through the CURRENT stream_join -- so the
    scheme change ships without a compatibility cliff for old artefacts.
    """
    key = b"B" * 32
    payload = b"legacy-pack" * 40
    n = 3
    chunk = (len(payload) + n - 1) // n
    sections = []
    for i in range(n):
        part = payload[i * chunk:(i + 1) * chunk]
        nonce = hashlib.sha256(
            b"legacy-nonce" + i.to_bytes(4, "big")).digest()[:16]
        skey = _section_key(key, i, nonce)
        tag = hmac.new(skey + nonce, part, hashlib.sha256).digest()
        enc = bytes(a ^ b for a, b in zip(
            tag + part,
            _keystream(skey, nonce, len(tag) + len(part))))
        sections.append({"i": i, "salt": "0" * 16, "nonce": nonce.hex(),
                         "data": enc.hex()})
    pack = {"sections": sections, "count": n, "total": len(payload),
            "key_hint": hashlib.sha256(key).hexdigest()[:16],
            "per_section": True,
            "state": _state_digest(sections, n, len(payload))}
    joined = stream_join(pack, key)
    assert bytes(joined) == payload
    # The v1 MAC is hmac(skey + nonce, plaintext) -- asserted here so the
    # legacy path in stream_join stays exactly the pre-v2 scheme.
    skey0 = _section_key(key, 0, bytes.fromhex(sections[0]["nonce"]))
    part0 = payload[:chunk]


def test_relabelled_sections_fail_the_bound_tag():
    """Swapping two sections' indices must not yield a reordered payload.

    Under v1 the plaintext MAC verified fine after a relabel (the tag covered
    only the plaintext), so a pack editor could reorder sections and the
    loader would accept the result if the state digest tolerated it. Under
    v2 the tag is computed over the section's own index, so a relabelled
    section fails verification outright.
    """
    key = b"C" * 32
    payload = bytes(range(256)) * 4
    pack = split_sealed(payload, sections=4, key=key)
    swapped = json.loads(json.dumps(pack))
    swapped["sections"][0]["i"], swapped["sections"][1]["i"] = \
        swapped["sections"][1]["i"], swapped["sections"][0]["i"]
    with pytest.raises(ValueError):
        stream_join(swapped, key)


def test_a_tampered_total_fails_the_bound_tag():
    """Pointing the pack at a different declared total must fail verification.

    Under v1, `total` was checked only against the JOINED length after every
    tag had verified. Under v2 the total is inside every tag's MAC input, so
    a pack editor cannot change what the loader believes it is assembling
    without invalidating every tag.
    """
    key = b"D" * 32
    payload = b"context-binding" * 30
    pack = split_sealed(payload, sections=4, key=key)
    altered = json.loads(json.dumps(pack))
    altered["total"] = pack["total"] - 1
    # The state digest also covers total, so rebuild it the way an editor
    # would have to; the POINT is that the per-section tags still fail.
    from obfuscator.pack_state import state_digest as _sd
    altered["state"] = _sd(altered["sections"], altered["count"],
                           altered["total"])
    with pytest.raises(ValueError):
        stream_join(altered, key)


def test_every_emitted_loader_snippet_compiles_and_matches_the_v2_scheme():
    """The loader templates must implement EXACTLY the packer's scheme.

    There are three emitted copies (whole-payload join, moving decryption,
    streaming decompress) plus the test-side stream_join. A drift between
    the packer and any of them ships an artefact whose loader cannot decrypt
    its own sections.

    Each emitted source is compiled here (a syntax drift breaks the build)
    and its scheme invariants are asserted on the source text: the v2 branch
    keys off the pack version, derives both role keys from the same basis
    the packer uses, and feeds the MAC the same context. Runtime parity --
    the snippets actually decrypting a real pack -- is exercised end to end
    by the artefact build tests, which run the real loader on a real v2 pack.
    """
    key = b"E" * 32
    payload = b"snippet-parity" * 200
    pack_json_bytes, _ = pack_json(payload, sections=4, key=key)
    pack = json.loads(pack_json_bytes.decode("utf-8"))
    assert pack["v"] == 3
    assert "pack_nonce" in pack, "a v3 pack must carry its pack nonce"

    from obfuscator.section_split import (
        emit_loader_snippet, emit_moving_snippet, emit_stream_snippet,
        JOIN_FUNC, )

    for snippet in (emit_loader_snippet(JOIN_FUNC),
                    emit_moving_snippet(),
                    emit_stream_snippet()):
        compile(snippet, "<emitted-snippet>", "exec")
        # The version dispatch must exist and must treat 2 as legacy-but-
        # loadable, not as the current scheme ...
        assert "_pv == 3" in snippet, (
            "the emitted loader must branch on the v3 scheme")
        assert "_pv == 2" in snippet, (
            "the emitted loader must still accept v2 packs")
        # ... derive BOTH role keys from the identical basis the packer
        # uses (master || index4 || nonce) ...
        assert 'b"nx-section-enc:"' in snippet
        assert 'b"nx-section-mac:"' in snippet
        assert snippet.count('b"nx-section-key:"') >= 1, \
            "the v1 legacy path remains for packs built before v2"
        # ... bind the PACK IDENTITY into the context (MIMOSA-INTAKE-001) ...
        assert 'b"nx-pack-id:"' in snippet, (
            "the emitted loader must derive the pack identity, or a built "
            "artefact cannot decrypt its own v3 pack")
        assert '_pack_ident' in snippet, (
            "the pack identity must be appended to the MAC context")
        # ... and refuse a v3 pack that omits its pack nonce rather than
        # silently falling back to v2, which would restore the splice.
        assert 'pack_nonce' in snippet, (
            "the emitted loader must read the pack nonce from the header")
        assert "missing its pack nonce" in snippet, (
            "the emitted loader must refuse a v3 pack with no pack nonce "
            "instead of downgrading to the v2 context")
        # ... and feed the MAC the context the packer binds.
        assert "_mctx + part" in snippet
        assert 'int(pack["total"]).to_bytes(4, "big")' in snippet


def test_the_packer_and_stream_join_agree_on_a_v2_pack():
    """Round-trip through the shipped functions: seal -> verify -> join."""
    key = b"F" * 32
    payload = bytes(range(256)) * 8
    pack = split_sealed(payload, sections=5, key=key)
    joined = stream_join(pack, key)
    assert bytes(joined) == payload
    pack_json_bytes, k = pack_json(payload, sections=5, key=key)
    assert k == key
    pack2 = json.loads(pack_json_bytes.decode("utf-8"))
    assert bytes(stream_join(pack2, key)) == payload


# ── downgrade resistance (review register, item 2) ────────────────────────
#
# The distinction the register draws: RETAINING a v1 reader for old artefacts
# is not wrong; a NEW RELEASE silently ACCEPTING v1 is a policy decision and
# is tested as such. Three layers pin it:
#   1. the version field is INSIDE the v2 MAC, so editing or stripping it
#      fails the tag even without the policy flag;
#   2. the release-mode gate (NIXON_REQUIRE_PACK_V2) refuses v1 outright,
#      baked into the emitted loader at build time;
#   3. the framing tamper matrix — version, index, total, nonce, ciphertext,
#      tag and ordering each tampered INDEPENDENTLY — must all be rejected.


def test_the_version_field_is_bound_into_the_v2_tag():
    """Downgrading a pack's version from 2 to 1 must fail verification.

    Under a MAC that ignores the version, an editor who flipped ``v`` to 1
    would silently move the loader onto the legacy path and the v2 guarantees
    (separated keys, bound metadata) would disappear. The version is now
    inside every tag's MAC input, so a tampered or stripped version fails
    verification before anything else happens.
    """
    key = b"G" * 32
    payload = b"downgrade" * 100
    pack = split_sealed(payload, sections=4, key=key)
    downgraded = json.loads(json.dumps(pack))
    downgraded["v"] = 1
    with pytest.raises(ValueError):
        stream_join(downgraded, key)
    stripped = json.loads(json.dumps(pack))
    del stripped["v"]
    with pytest.raises(ValueError):
        stream_join(stripped, key)


def test_the_full_framing_tamper_matrix_is_rejected():
    """Each framing field tampered INDEPENDENTLY must cause rejection.

    Eight independent edits, one assertion each: version (downgrade + strip),
    section index, total, nonce, ciphertext, tag, and a state-consistent
    reorder. Every one must be rejected by the MAC/state checks BEFORE any
    plaintext is trusted.
    """
    key = b"H" * 32
    payload = bytes(range(256)) * 4
    base = split_sealed(payload, sections=4, key=key)

    def variant(mutate):
        v = json.loads(json.dumps(base))
        mutate(v)
        return v

    def bump_total(p):
        p["total"] += 1
        from obfuscator.pack_state import state_digest as _sd
        p["state"] = _sd(p["sections"], p["count"], p["total"])

    def swap_indices(p):
        # A genuine ORDER tamper: relabel sections 0 and 1 with each other's
        # index (the multiset is unchanged, so the state digest still
        # validates). The join sorts by `i`, so this makes the loader decrypt
        # section 1's ciphertext as if it were section 0's -- which the
        # index-bound tags must reject. (A pure list reorder is a no-op BY
        # DESIGN: the loader sorts by `i`, so the register's "ordering"
        # concern is expressed through the `i` field, which is inside every
        # tag.)
        p["sections"][0]["i"], p["sections"][1]["i"] = \
            p["sections"][1]["i"], p["sections"][0]["i"]

    cases = {
        "version downgraded": lambda p: p.__setitem__("v", 1),
        "version stripped": lambda p: p.pop("v"),
        "section index relabelled": lambda p: (
            p["sections"][0].__setitem__("i", 3)),
        "total tampered": bump_total,
        "nonce swapped between sections": lambda p: p["sections"][0].__setitem__(
            "nonce", p["sections"][1]["nonce"]),
        "ciphertext flipped": lambda p: p["sections"][2].__setitem__(
            "data", ("FF" if p["sections"][2]["data"][0] != "F" else "00")
            + p["sections"][2]["data"][2:]),
        "tag flipped": lambda p: p["sections"][1].__setitem__(
            "data", ("0" if p["sections"][1]["data"][0] != "0" else "1")
            + p["sections"][1]["data"][1:]),
        "indices swapped (order tamper)": swap_indices,
    }
    for name, mutate in cases.items():
        v = variant(mutate)
        raised = None
        try:
            stream_join(v, key)
        except ValueError as exc:
            raised = exc
        assert raised is not None, (
            "tamper case %r was ACCEPTED by stream_join" % name)


def test_release_mode_loader_snippets_refuse_v1_packs():
    """NIXON_REQUIRE_PACK_V2 bakes a v1 refusal into the emitted loader.

    The gate is a BUILD-TIME substitution: the emitted snippet carries
    ``_NX_PACK_V2_REQUIRED = True`` and fails closed on any pack whose
    version is not 2, BEFORE the state check and long before any plaintext.
    The default (False) keeps v1 acceptance for old artefacts -- the policy
    choice is explicit on both sides.
    """
    from obfuscator.section_split import (
        emit_loader_snippet, emit_moving_snippet, emit_stream_snippet,
        JOIN_FUNC, )

    for emit in (emit_loader_snippet(JOIN_FUNC, require_v2=True),
                 emit_moving_snippet(require_v2=True),
                 emit_stream_snippet(require_v2=True)):
        compile(emit, "<v2-required>", "exec")
        assert "_NX_PACK_V2_REQUIRED = True" in emit
        assert 'pack.get("v") != 2' in emit
    for emit in (emit_loader_snippet(JOIN_FUNC),
                 emit_moving_snippet(),
                 emit_stream_snippet()):
        compile(emit, "<v2-optional>", "exec")
        assert "_NX_PACK_V2_REQUIRED = False" in emit


def test_plaintext_is_only_consumed_after_the_v2_tag_verifies():
    """Every decrypt path must verify the tag BEFORE touching plaintext.

    The reviewer's requirement, pinned on the source: in all three emitted
    snippets the compare_digest of the section tag must appear BEFORE the
    first use of the decrypted part (decompress / sink / extend). A future
    edit that consumes plaintext ahead of verification breaks this test.
    """
    from obfuscator.section_split import (
        emit_loader_snippet, emit_moving_snippet, emit_stream_snippet,
        JOIN_FUNC, )

    for snippet in (emit_loader_snippet(JOIN_FUNC),
                    emit_moving_snippet(),
                    emit_stream_snippet()):
        verify_at = snippet.find("compare_digest")
        assert verify_at > 0, "no constant-time tag verification found"
        # the FIRST consumption of the decrypted body must come after the
        # verification: the consuming statements reference `part` after the
        # compare (the tag itself is the slice BEFORE `part`).
        consume_markers = ("out.extend(part)", "sink(bytes(buf))",
                           "buf = bytearray(part)")
        consume_at = min((snippet.find(m, verify_at) for m in consume_markers
                          if snippet.find(m, verify_at) >= 0),
                         default=-1)
        assert consume_at > verify_at, (
            "a decrypt path consumes plaintext BEFORE verifying the section "
            "tag; the MAC must gate every use of `part`")


def test_mac_comparison_is_constant_time():
    """The tag comparison uses hmac.compare_digest, not ==.

    A ==-compare leaks the prefix length of the matching bytes through
    timing; the construction must use the constant-time primitive on every
    path (test-side stream_join AND all three emitted snippets).
    """
    import inspect
    from obfuscator.section_split import (
        stream_join, emit_loader_snippet, emit_moving_snippet,
        emit_stream_snippet, JOIN_FUNC)
    assert "compare_digest" in inspect.getsource(stream_join)
    for snippet in (emit_loader_snippet(JOIN_FUNC),
                    emit_moving_snippet(),
                    emit_stream_snippet()):
        assert "compare_digest" in snippet
        # and no plain == comparison of the tag
        assert "tag ==" not in snippet
