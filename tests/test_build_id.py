"""Batch-3 build-id salt: per-build BLOB_KEY derivation in the hybrid loader.

Identical payload+key pairs must emit different blobs/loaders per build
(salted effective key ``xor(key, sha256(build_id))``); both decrypt
correctly; a tampered build id fails; a fixed build id is deterministic.
"""
import base64
import marshal
import os
import re
import sys
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import generate_hybrid_loader_script
from obfuscator.core.utils import fast_xor_bytes
from obfuscator.key_emit import derive_effective_key

_BLANKS = {"windows": "", "linux": "", "darwin": ""}
_RAW_KEY = bytes(range(32))
_PAYLOAD_SRC = "BUILD_ID_E2E = 100 + 23\n"


def _enc_blob():
    marshalled = marshal.dumps(compile(_PAYLOAD_SRC, "<build_id_e2e>", "exec"))
    return fast_xor_bytes(zlib.compress(marshalled), _RAW_KEY)


def _run_loader(src):
    ns = {"__name__": "build_id_loader"}
    exec(compile(src, "<build_id_loader>", "exec"), ns)
    ns["_exec_fallback"]()
    return ns


def test_same_payload_twice_different_blobs():
    enc = _enc_blob()
    _, _, fb1 = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(), build_id="bid-aaa")
    _, _, fb2 = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(), build_id="bid-bbb")
    assert fb1 and fb2 and fb1 != fb2


def test_both_decrypt_correctly():
    enc = _enc_blob()
    for bid in ("bid-aaa", "bid-bbb"):
        src, _, _ = generate_hybrid_loader_script(
            dict(_BLANKS), bytes(enc), _RAW_KEY.hex(), build_id=bid)
        compile(src, "<build_id_loader>", "exec")
        ns = _run_loader(src)
        assert ns.get("BUILD_ID_E2E") == 123, bid
        assert ns.get("BLOB_KEY") == derive_effective_key(_RAW_KEY, bid)


def test_tampered_build_id_fails():
    enc = _enc_blob()
    src, _, _ = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(), build_id="bid-good")
    bid = re.search(r'_NX_BUILD_ID = "([^"]+)"', src).group(1)
    tampered = src.replace('"%s"' % bid, '"%s-tampered"' % bid, 1)
    ns = {"__name__": "build_id_tampered"}
    exec(compile(tampered, "<build_id_tampered>", "exec"), ns)
    assert ns.get("BLOB_KEY") != derive_effective_key(_RAW_KEY, "bid-good")
    try:
        ns["_exec_fallback"]()
    except BaseException:
        return  # SystemExit from the loader's except path counts as failure
    raise AssertionError("tampered build_id should fail decrypt")


def test_deterministic_with_fixed_build_id():
    enc = _enc_blob()
    kw = dict(build_id="bid-fixed")
    _, _, fb1 = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(), **kw)
    _, _, fb2 = generate_hybrid_loader_script(
        dict(_BLANKS), bytes(enc), _RAW_KEY.hex(), **kw)
    assert fb1 == fb2


def test_random_build_id_by_default():
    enc = _enc_blob()
    _, _, fb1 = generate_hybrid_loader_script(dict(_BLANKS), bytes(enc), _RAW_KEY.hex())
    _, _, fb2 = generate_hybrid_loader_script(dict(_BLANKS), bytes(enc), _RAW_KEY.hex())
    assert fb1 != fb2  # fresh os.urandom(8) salt per call (overwhelmingly)
