"""Pins finding MIMOSA-INTAKE-001 and its v3 resolution.

Found by the maintainer on 2026-11-23 while attacking a weakness listed in
`CRYPTO_REVIEW_BUNDLE_STANDALONE.md` §8: two packs built with the same session
key and the same total length were interchangeable section-by-section, because
the authenticated context bound (v, i, total, nonce) but no pack identity.

RESOLVED in pack format v3 (decision authorised by the repository owner):
a 16-byte per-pack identity, derived from the session key and a random
per-build pack nonce carried in the header, is appended to every section's MAC
context. A spliced section now fails its tag.

This module was written BEFORE the fix, deliberately, so that closing the
finding could not happen silently: the original assertions failed the moment
the splice started being refused, forcing this rewrite. Both halves are kept —
the attack is still exercised, and the refusal is now what is asserted. A test
that only checks the happy path would not notice if v3 were reverted.
"""
import copy
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from obfuscator import section_split as ss  # noqa: E402
from obfuscator.pack_state import state_digest  # noqa: E402

KEY = b"\x11" * 32
FILED = os.path.join(REPO, "docs", "security", "REVIEW_FINDINGS_FILED.md")
RUNBOOK = os.path.join(REPO, "docs", "security", "CRYPTO_REVIEW_PACKAGE.md")


def _packs():
    """Two v3 packs: same key, same section count, same total, other content."""
    a = ss.split_sealed(b"A" * 32, sections=4, key=KEY, nonce_seed=b"aaa")
    b = ss.split_sealed(b"B" * 32, sections=4, key=KEY, nonce_seed=b"bbb")
    return a, b


def _splice(host, donor, indices):
    """Replace `indices` in host with donor's, recomputing the unkeyed digest."""
    forged = copy.deepcopy(host)
    for i in indices:
        forged["sections"][i] = copy.deepcopy(donor["sections"][i])
    forged["state"] = state_digest(forged["sections"], forged["count"],
                                   forged["total"])
    return forged


# ── the fix: the splice is refused ────────────────────────────────────

def test_the_cross_pack_substitution_is_refused():
    """MIMOSA-INTAKE-001's attack, now failing at the MAC.

    Preconditions are asserted so the test cannot pass vacuously: the packs
    really do share a key and a total, so the ONLY thing distinguishing them
    is the pack identity.
    """
    a, b = _packs()
    assert a["total"] == b["total"], "precondition: equal totals"
    assert a["key_hint"] == b["key_hint"], "precondition: same session key"
    assert a["pack_nonce"] != b["pack_nonce"], (
        "precondition: distinct pack nonces, so distinct identities")

    forged = _splice(a, b, [0, 1])
    with pytest.raises(ValueError, match="integrity failure"):
        ss.stream_join(forged, KEY)


def test_the_pack_identity_is_bound_into_every_section():
    """Each section's tag commits to the pack id; changing it breaks them all."""
    pack = ss.split_sealed(b"identity" * 40, sections=4, key=KEY,
                           nonce_seed=b"id")
    assert pack["v"] == 3
    pack_id = ss._pack_id(KEY, bytes.fromhex(pack["pack_nonce"]))
    assert len(pack_id) == ss.PACK_ID_BYTES == 16

    # A different pack id changes every context...
    other_id = ss._pack_id(KEY, b"\x00" * 16)
    assert other_id != pack_id
    # ...and the context is what the tag covers, so a pack rebuild with a
    # different nonce is not interchangeable with this one.
    other = ss.split_sealed(b"identity" * 40, sections=4, key=KEY,
                            nonce_seed=b"different")
    assert other["pack_nonce"] != pack["pack_nonce"]
    forged = _splice(pack, other, [0])
    with pytest.raises(ValueError, match="integrity failure"):
        ss.stream_join(forged, KEY)


def test_a_v3_pack_without_its_nonce_is_refused_not_downgraded():
    """Falling back to the v2 context would restore the splice.

    A v3 pack missing `pack_nonce` must be a refusal. Silently treating it as
    v2 is precisely the downgrade the identity exists to prevent.
    """
    pack = ss.split_sealed(b"downgrade-me" * 20, sections=4, key=KEY,
                           nonce_seed=b"dg")
    stripped = copy.deepcopy(pack)
    stripped.pop("pack_nonce", None)
    with pytest.raises(ValueError, match="pack nonce|integrity failure"):
        ss.stream_join(stripped, KEY)

    short = copy.deepcopy(pack)
    short["pack_nonce"] = "00" * 8   # wrong length
    with pytest.raises(ValueError):
        ss.stream_join(short, KEY)

    not_hex = copy.deepcopy(pack)
    not_hex["pack_nonce"] = "zz" * 16
    with pytest.raises(ValueError):
        ss.stream_join(not_hex, KEY)


# ── v2 stays loadable, and v2 still carries the weakness ──────────────

def test_a_v2_pack_is_still_loadable():
    """Backward compatibility: old artefacts must keep working."""
    pack = ss.split_sealed(b"legacy-compat" * 20, sections=4, key=KEY,
                           nonce_seed=b"lc")
    v2 = copy.deepcopy(pack)
    v2["v"] = 2
    v2.pop("pack_nonce", None)
    # Its tags were built under v3, so this WILL fail -- but it must fail as
    # an integrity failure, not as an unsupported-version error, because the
    # v2 code path exists and ran.
    with pytest.raises(ValueError, match="integrity failure"):
        ss.stream_join(v2, KEY)


def test_the_v2_path_still_has_the_splice_weakness():
    """The documented trade: v2 packs remain spliceable, by their format.

    This is asserted rather than described, so nobody later claims the fix
    retroactively protected old artefacts. A v2 pack genuinely does not bind
    a pack identity, and that limitation must stay visible in the record.
    """
    # Two packs built under the V2 context, reconstructed here.
    def v2_pack(payload, seed):
        import hashlib
        import hmac
        n = 4
        chunk = (len(payload) + n - 1) // n
        secs = []
        for i in range(n):
            part = payload[i * chunk:(i + 1) * chunk]
            nonce = hashlib.sha256(b"v2n:" + seed +
                                   i.to_bytes(4, "big")).digest()[:16]
            basis = KEY + i.to_bytes(4, "big") + nonce
            skey = hashlib.sha256(b"nx-section-enc:" + basis).digest()
            mkey = hashlib.sha256(b"nx-section-mac:" + basis).digest()
            ctx = (b"\x00\x00\x00\x02" + i.to_bytes(4, "big")
                   + len(payload).to_bytes(4, "big") + nonce)
            tag = hmac.new(mkey, ctx + part, hashlib.sha256).digest()
            body = tag + part
            ks = b""
            c = 0
            while len(ks) < len(body):
                ks += hashlib.sha256(
                    skey + nonce + c.to_bytes(8, "big")).digest()
                c += 1
            enc = bytes(x ^ y for x, y in zip(body, ks))
            secs.append({"i": i, "salt": "0" * 16, "nonce": nonce.hex(),
                         "data": enc.hex()})
        return {"sections": secs, "count": n, "total": len(payload),
                "key_hint": hashlib.sha256(KEY).hexdigest()[:16],
                "per_section": True, "v": 2,
                "state": state_digest(secs, n, len(payload))}

    a = v2_pack(b"A" * 32, b"one")
    b = v2_pack(b"B" * 32, b"two")
    assert bytes(ss.stream_join(a, KEY)) == b"A" * 32, "v2 pack must load"
    spliced = _splice(a, b, [0])
    # This is the weakness v2 has and v3 closes. Asserting it keeps the
    # register honest about which formats the fix actually protects.
    joined = bytes(ss.stream_join(spliced, KEY))
    assert joined.startswith(b"B" * 8), (
        "v2 is documented as still spliceable; if this now refuses, the "
        "documentation claiming the trade must be updated")


# ── the register row reflects the resolution ─────────────────────────

def test_the_row_records_the_v3_resolution():
    with open(FILED, encoding="utf-8") as fh:
        text = fh.read()
    assert "MIMOSA-INTAKE-001" in text
    assert "v3" in text, "the row must name the format that fixes it"
    assert "self-reported" in text, (
        "the row must still say a maintainer found it; the format's "
        "`reviewer` field exists to prevent that confusion")
    for field in ("package:", "reviewer:", "received:", "severity:", "claim:",
                  "evidence:", "reproducible:", "affects:",
                  "maintainer-response:", "resolution:"):
        assert field in text, "the row is missing the %r field" % (field,)


def test_the_docs_no_longer_describe_the_context_without_a_pack_id():
    """The review package's §4 must match the shipped v3 context."""
    with open(RUNBOOK, encoding="utf-8") as fh:
        text = fh.read()
    assert "pack_id" in text or "pack identity" in text, (
        "the crypto review package still describes the pre-v3 context; a "
        "reviewer would be handed a stale construction")
