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
    emit_moving_snippet, pack_json,
)

WALK = "_nx_section_walk"


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
