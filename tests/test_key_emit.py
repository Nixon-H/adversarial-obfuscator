"""Batch-3 key emission: XOR-split shares + build-id salt (obfuscator/key_emit.py).

The loader must never contain the raw key as a contiguous hex literal;
two base64 shares reconstruct it at runtime, salted per build.
"""
import base64
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import generate_hybrid_loader_script
from obfuscator.key_emit import (
    combine_shares,
    derive_effective_key,
    emit_key_loader,
    split_key,
    split_seed_for_build,
)


_KEY = bytes(range(32))
_SEED = b"test-seed-01"


def test_split_roundtrip():
    s0, s1 = split_key(_KEY, _SEED)
    assert combine_shares(s0, s1) == _KEY


def test_shares_differ_from_key():
    s0, s1 = split_key(_KEY, _SEED)
    assert base64.b64decode(s0) != _KEY
    assert base64.b64decode(s1) != _KEY
    # shares are valid base64 of key length
    assert len(base64.b64decode(s0)) == len(_KEY)
    assert len(base64.b64decode(s1)) == len(_KEY)


def test_determinism_with_seed():
    assert split_key(_KEY, _SEED) == split_key(_KEY, _SEED)
    assert split_key(_KEY, b"other-seed") != split_key(_KEY, _SEED)
    assert split_seed_for_build("bid-1") == split_seed_for_build("bid-1")
    assert split_seed_for_build("bid-1") != split_seed_for_build("bid-2")


def test_emit_key_loader_reconstructs_key():
    s0, s1 = split_key(_KEY, _SEED)
    eff = derive_effective_key(_KEY, "bid-emit-01")
    # emit shares of the RAW key (pack-time convention); loader salts them
    r0, r1 = split_key(_KEY, split_seed_for_build("bid-emit-01"))
    snippet = emit_key_loader(r0, r1, "bid-emit-01")
    compile(snippet, "<key_loader>", "exec")
    ns = {"__name__": "key_emit_test", "base64": base64}
    # provide the same _nx_wipe the loader template defines
    import ctypes as _ct

    def _nx_wipe(obj):
        try:
            if isinstance(obj, bytearray) and len(obj):
                _ct.memset(_ct.addressof(_ct.c_char.from_buffer(obj)), 0, len(obj))
        except Exception:
            pass
        return None

    ns["_nx_wipe"] = _nx_wipe
    exec(compile(snippet, "<key_loader>", "exec"), ns)
    assert ns["BLOB_KEY"] == eff
    assert ns["_NX_BUILD_ID"] == "bid-emit-01"


def test_no_hex_literal_of_key_in_loader():
    blanks = {"windows": "", "linux": "", "darwin": ""}
    src, _, _ = generate_hybrid_loader_script(
        blanks, b"", _KEY.hex(), build_id="nohex-01")
    compile(src, "<nohex_loader>", "exec")
    # raw key hex must not appear contiguously...
    assert _KEY.hex() not in src
    # ...nor the effective (salted) key hex
    assert derive_effective_key(_KEY, "nohex-01").hex() not in src
    # shares are present and reconstruct the raw key
    s0 = re.search(r'_BLOB_S0 = "([^"]+)"', src).group(1)
    s1 = re.search(r'_BLOB_S1 = "([^"]+)"', src).group(1)
    assert combine_shares(s0, s1) == _KEY


def test_derive_effective_key_known_vector():
    import hashlib

    eff = derive_effective_key(b"\x00" * 4, "abc")
    mask = hashlib.sha256(b"abc").digest()
    assert eff == mask[:4]
    assert derive_effective_key(_KEY, "x") != derive_effective_key(_KEY, "y")
