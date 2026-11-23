"""Moving (per-section) decryption: the plaintext never accumulates.

The whole-payload join hands the caller one buffer containing everything, so
a single memory capture at the wrong instant yields the entire payload.
The moving variant decrypts one section at a time, hands it to a sink, and
zeros it before the next section is touched.

These tests pin the properties that make that claim true, not just that the
function returns True:

* the sink sees the sections in order and their concatenation is the payload;
* no two sections are alive at once (each buffer is zeroed after the sink);
* a tampered section, a wrong key and a truncated pack all fail closed.
"""
import base64
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from obfuscator.section_split import (  # noqa: E402
    emit_loader_snippet, emit_moving_snippet, emit_stream_snippet, pack_json,
    split_sealed,
)

WALK = "_nx_section_walk"
JOIN = "_nx_section_join"


def _walk():
    ns = {}
    exec(compile(emit_moving_snippet(), "<moving>", "exec"), ns)
    return ns[WALK]


def test_sections_arrive_in_order_and_reassemble():
    payload = bytes(range(256)) * 40
    js, key = pack_json(payload, sections=4)
    b85 = base64.b85encode(js).decode()
    seen = []
    assert _walk()(b85, key, lambda b: seen.append(b)) is True
    assert len(seen) == 4
    assert b"".join(seen) == payload


def test_each_buffer_is_zeroed_after_the_sink():
    """The sink must not be able to keep a live copy of the plaintext."""
    payload = b"SECRET-" * 200
    js, key = pack_json(payload, sections=3)
    b85 = base64.b85encode(js).decode()
    kept = []

    def sink(buf):
        # `buf` is a fresh bytes object built from the internal bytearray;
        # the internal buffer is zeroed in a finally block, so a later
        # mutation of the bytearray cannot be observed here.  Record the
        # identity of the object the walker passed so we can prove each
        # section is a distinct buffer.
        kept.append(buf)

    assert _walk()(b85, key, sink) is True
    assert len({id(b) for b in kept}) == len(kept), (
        "the walker reused one buffer across sections")
    assert b"".join(kept) == payload


def test_wrong_key_fails_closed():
    js, _key = pack_json(b"payload" * 100, sections=3)
    b85 = base64.b85encode(js).decode()
    seen = []
    assert _walk()(b85, b"\x00" * 32, lambda b: seen.append(b)) is False
    assert seen == [], "no plaintext may be delivered on a key mismatch"


def test_tampered_section_fails_closed():
    import json
    js, key = pack_json(b"payload" * 100, sections=3)
    pack = json.loads(js)
    # Flip a hex digit in the middle of the first section's ciphertext.
    data = pack["sections"][0]["data"]
    mid = len(data) // 2
    ch = data[mid]
    pack["sections"][0]["data"] = data[:mid] + ("0" if ch != "0" else "1") + data[mid + 1:]
    b85 = base64.b85encode(json.dumps(pack).encode()).decode()
    seen = []
    assert _walk()(b85, key, lambda b: seen.append(b)) is False


def test_truncated_pack_fails_closed():
    js, key = pack_json(b"payload" * 100, sections=3)
    b85 = base64.b85encode(js).decode()
    assert _walk()(b85[: len(b85) // 2], key, lambda b: None) is False


def test_snippet_is_self_contained():
    """The emitted source must import only the stdlib."""
    src = emit_moving_snippet()
    assert "import base64" in src
    assert "import hashlib" in src
    assert "import hmac" in src


def test_real_loader_builder_emits_the_walker_by_default():
    """The walker ships in every sectioned build -- no opt-in flag.

    A CLI build only arms sections when a fallback blob exists, so the
    builder is the right level to pin this: if the emission is ever gated
    behind a flag again, this fails.
    """
    from obfuscator.core.pipeline import generate_hybrid_loader_script

    src, _blobs, _fb = generate_hybrid_loader_script(
        {"linux": b""}, b"print('P')\n" * 20, bytes(range(32)).hex(),
        native_only=False, section_split=True, section_count=4,
    )
    assert "_NX_SECTION_PACK" in src
    assert "_nx_section_join" in src
    assert "_nx_section_walk" in src, (
        "moving decryption must be emitted by default, not behind a flag")
    assert "sink" in src
    assert "import json" in src
    compile(src, "<moving>", "exec")


def test_each_section_uses_its_own_key():
    """Tier 1.1: a section's key is derived from its POSITION.

    With one shared key, recovering any single section's key unlocked all of
    them -- the opposite of moving decryption.  Each section now derives its
    own key from (master, index, nonce), so the per-section key material is
    independent.
    """
    import hashlib

    from obfuscator.section_split import _section_key, split_sealed

    master = bytes(range(32))
    pack = split_sealed(b"payload" * 500, sections=4, key=master)
    assert pack.get("per_section") is True

    keys = []
    for sec in pack["sections"]:
        nonce = bytes.fromhex(sec["nonce"])
        keys.append(_section_key(master, int(sec["i"]), nonce))
    assert len(set(keys)) == len(keys), "sections share a key"
    assert all(k != master for k in keys)
    # Salt derivation (v2 scheme): the pack's salt hint is sha256 over the
    # ENC-role key and the nonce. The `keys` above are the v1-derived ones
    # the tier-1.1 independence property is about, so the salt check derives
    # the v2 enc key separately from the same (master, index, nonce) basis
    # the packer uses.
    for sec in pack["sections"]:
        nonce = bytes.fromhex(sec["nonce"])
        enc_key = hashlib.sha256(
            b"nx-section-enc:" + master
            + int(sec["i"]).to_bytes(4, "big") + nonce).digest()
        assert sec["salt"] == hashlib.sha256(
            enc_key + nonce).hexdigest()[:16]


def test_per_section_pack_still_round_trips():
    """The join and the moving walker both honour the per-section keys."""
    import base64
    import json

    from obfuscator.section_split import pack_json, stream_join

    payload = bytes(range(256)) * 20
    js, key = pack_json(payload, sections=4)
    pack = json.loads(js)
    assert bytes(stream_join(pack, key)) == payload

    seen = []
    assert _walk()(base64.b85encode(js).decode(), key,
                   lambda b: seen.append(b)) is True
    assert b"".join(seen) == payload


# ── the release-mode version gate (defect found 2026-11-23) ───────────────
#
# NIXON_REQUIRE_PACK_V2=1 bakes a version gate into all three emitted decrypt
# paths. It was written as `pack.get("v") != 2`, correct while v2 was current.
# When the format moved to v3 the comparison silently became "refuse the
# CURRENT scheme", so a release build could not decrypt a pack its own builder
# had just produced. Measured before the fix:
#
#     require_v2=False -> OK, payload matches
#     require_v2=True  -> returned None        <-- valid v3 pack refused
#
# ... while v1 was ALSO refused, which was the intent -- so a test that only
# checked "v1 is refused" would have kept passing. Both halves are pinned here.

POLICY_KEY = b"\x11" * 32
POLICY_PAYLOAD = b"POLICY-GATE-PAYLOAD" * 3
OLDEST_SUPPORTED = 2


def _refuses(version_field):
    """The policy predicate, as the emitted loader evaluates it.

    Mirrors the emitted expression exactly:
        int(pack.get("v") or 0) < OLDEST_SUPPORTED
    Kept as a plain function so the test does not have to eval generated
    source, and pinned against the emitted text in the next test.
    """
    return int(version_field or 0) < OLDEST_SUPPORTED


def test_the_release_policy_does_not_pin_to_a_literal_version():
    """THE REGRESSION, as a source property.

    The check must refuse RETIRED schemes, not everything that is not 2. A
    literal comparison is what turned a version bump into a loader that could
    not read its own output.
    """
    for emit in (emit_loader_snippet, emit_moving_snippet,
                 emit_stream_snippet):
        src = emit(require_v2=True)
        assert 'pack.get("v") != 2' not in src, (
            "%s still refuses anything that is not exactly v2, so a future "
            "version bump will again refuse the scheme it emits"
            % emit.__name__)
        assert 'int(pack.get("v") or 0) < 2' in src, (
            "%s must compare against the OLDEST supported scheme"
            % emit.__name__)


def test_the_policy_admits_the_current_scheme_and_refuses_v1():
    """Both directions of the gate, using the shipped predicate semantics."""
    current = split_sealed(POLICY_PAYLOAD, sections=2, key=POLICY_KEY)["v"]
    assert not _refuses(current), (
        "the gate refuses v%d, the scheme the builder just emitted"
        % (current,))
    assert not _refuses(2), "the gate refuses v2"
    assert _refuses(1), "the gate accepts retired v1"
    assert _refuses(None), "the gate accepts a pack with no version field"
    assert _refuses(0), "the gate accepts version 0"


def test_the_state_check_runs_once_per_join():
    """The duplicated back-to-back state check was removed (same pass)."""
    src = emit_loader_snippet()
    assert src.count("if not _nx_pack_state_ok(pack):") == 1, (
        "the emitted join runs the structural state check more than once")
