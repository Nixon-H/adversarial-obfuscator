"""Honeypayload: a plausible decoy payload that costs an analyst real work.

The value of a honeypayload is entirely in these properties, so each one is
pinned here rather than assumed:

* the decoy is a *complete, runnable* program (not a stub);
* it is self-consistent -- running it prints sensible output;
* its key is derived from the build id only, never from the licence, so
  recovering it teaches nothing about the real key chain;
* it is sealed with the same envelope shape as the real payload, so the two
  are indistinguishable by inspection;
* a decoy that fails the plausibility gate is not emitted at all.
"""
import base64
import os
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from obfuscator.honeypayload import (  # noqa: E402
    build_honey_pack, decoy_is_plausible, decoy_key, generate_decoy,
)


def test_decoy_is_a_complete_runnable_program():
    src = generate_decoy(b"seed-a")
    compile(src, "<decoy>", "exec")
    ns = {}
    exec(compile(src, "<decoy>", "exec"), ns)
    assert callable(ns["main"])
    assert ns["main"]([]) == 0


def test_decoy_output_is_self_consistent():
    """Running it must produce plausible output, not a marker that screams fake."""
    import io
    import contextlib

    src = generate_decoy(b"seed-b")
    ns = {}
    exec(compile(src, "<decoy>", "exec"), ns)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ns["main"]([])
    out = buf.getvalue()
    assert "build:" in out and "endpoint:" in out
    assert "https://api." in out
    # No giveaway markers.
    for marker in ("decoy", "honey", "fake", "not the real"):
        assert marker not in out.lower()


def test_decoy_key_is_build_bound_not_licence_bound():
    """The decoy key must not depend on any licence material."""
    a = decoy_key("build-1")
    b = decoy_key("build-1")
    c = decoy_key("build-2")
    assert a == b, "the decoy key must be deterministic per build"
    assert a != c, "different builds must get different decoy keys"
    assert len(a) == 32


def test_decoy_pack_has_the_same_shape_as_the_real_pack():
    pack = build_honey_pack(b"seed-c", "build-x")
    assert set(pack) == {"pack_b85", "key_hint", "source"}
    raw = base64.b85decode(pack["pack_b85"])
    import json
    parsed = json.loads(raw)
    # Same envelope keys the real section pack uses.
    assert set(parsed) >= {"sections", "count", "total", "key_hint"}


def test_decoy_pack_decrypts_to_the_decoy_source():
    """An analyst who breaks it must get the decoy, not garbage."""
    from obfuscator.section_split import stream_join

    pack = build_honey_pack(b"seed-d", "build-y")
    raw = base64.b85decode(pack["pack_b85"])
    import json
    parsed = json.loads(raw)
    joined = stream_join(parsed, decoy_key("build-y"))
    # First byte is the compression envelope id.
    assert joined[0] == 0x00
    source = zlib.decompress(bytes(joined[1:])).decode("utf-8")
    assert source == pack["source"]
    assert decoy_is_plausible(source)


def test_plausibility_gate_rejects_a_stub():
    assert not decoy_is_plausible("print('decoy')")
    assert not decoy_is_plausible("")
    assert decoy_is_plausible(generate_decoy(b"seed-e"))


def test_decoy_is_deterministic_per_seed():
    assert generate_decoy(b"same") == generate_decoy(b"same")
    assert generate_decoy(b"same") != generate_decoy(b"other")
