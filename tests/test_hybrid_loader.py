"""Extract + exercise the emitted hybrid-loader fragment from pipeline.py.

The loader template contains {placeholders}; for testing we substitute a
dummy key and exec everything up to _exec_fallback (which needs the real
blob wiring), then test _ct_unmarshal / _nyser_loads directly.
"""
import re

import pytest

from obfuscator.nyser import dumps


def _load_fragment():
    src = open("obfuscator/core/pipeline.py").read()
    m = re.search(r"loader_template = r'''(.*?)'''", src, re.DOTALL)
    assert m, "loader_template not found"
    tpl = m.group(1)
    # Batch-3: BLOB_KEY now reconstructs from XOR shares + build-id salt.
    # Substitute dummy shares of the zero key (salted by a fixed test id).
    import base64 as _b64
    import hashlib as _hl
    from obfuscator.key_emit import split_key, split_seed_for_build
    _bid = "testfrag-build-id"
    _s0, _s1 = split_key(b"\x00" * 32, split_seed_for_build(_bid))
    tpl = tpl.replace('"{build_id}"', '"%s"' % _bid)
    tpl = tpl.replace('"{share0}"', '"%s"' % _s0)
    tpl = tpl.replace('"{share1}"', '"%s"' % _s1)
    assert "{share0}" not in tpl and "{share1}" not in tpl
    # Module header (sys/platform/base64/... imports) must be exec'd: the
    # key-reconstruct path uses base64 at module scope. Start from the top
    # (as the real loader does), not from the ctypes import.
    frag = tpl[:tpl.find("def _exec_fallback")]
    ns = {"__name__": "testfrag"}
    exec(compile(frag, "<frag>", "exec"), ns)
    return ns


@pytest.fixture(scope="module")
def frag():
    return _load_fragment()


def test_fragment_compiles():
    _load_fragment()  # raises on syntax error


def test_ct_unmarshal_normal(frag):
    import marshal
    raw = marshal.dumps(compile("q = 6 * 7\n", "<t>", "exec"))
    ns = {}
    exec(frag["_ct_unmarshal"](raw), ns)
    assert ns["q"] == 42


def test_ct_unmarshal_under_hook(frag):
    """Hooking marshal.loads must not break the C-API path.

    Rationale: ctypes is imported at loader top BEFORE any hook can
    install (the import system itself needs marshal for .pyc, so a
    lazy import under a hook is a lost cause — top-level wins).
    """
    import marshal
    raw = marshal.dumps(compile("q = 6 * 7\n", "<t>", "exec"))
    orig = marshal.loads
    marshal.loads = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("hooked"))
    try:
        co2 = frag["_ct_unmarshal"](raw)
    finally:
        marshal.loads = orig
    ns = {}
    exec(co2, ns)
    assert ns["q"] == 42


def test_nyser_embedded_path(frag):
    blob = dumps(compile("w = 100 + 23\n", "<t2>", "exec"))
    ns = {}
    exec(frag["_ct_unmarshal"](blob), ns)
    assert ns["w"] == 123


def test_nyser_embedded_path_under_hook(frag):
    import marshal
    blob = dumps(compile("w = 100 + 23\n", "<t2>", "exec"))
    orig = marshal.loads
    marshal.loads = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("hooked"))
    try:
        co3 = frag["_ct_unmarshal"](blob)
    finally:
        marshal.loads = orig
    ns = {}
    exec(co3, ns)
    assert ns["w"] == 123


def test_nyser_embedded_rejects_tamper(frag):
    blob = bytearray(dumps(compile("x = 1\n", "<t>", "exec")))
    blob[-5] ^= 0xFF
    with pytest.raises(ValueError):
        frag["_ct_unmarshal"](bytes(blob))
