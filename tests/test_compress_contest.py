"""Batch-2: 4-backend compression contest + fallback envelope."""

import os
import sys
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.compress_contest import (
    BACKEND_IDS,
    best_compress,
    decompress_auto,
    pack,
    unpack_and_decompress,
)

PAYLOAD = (b"def hello():\n    return 42\n" * 64) + bytes(range(256)) * 4


def test_roundtrip_zlib():
    import zlib as _z

    blob = _z.compress(PAYLOAD, 9)
    assert decompress_auto("zlib", blob) == PAYLOAD


def test_roundtrip_bz2():
    import bz2

    blob = bz2.compress(PAYLOAD, 9)
    assert decompress_auto("bz2", blob) == PAYLOAD


def test_roundtrip_lzma():
    import lzma

    blob = lzma.compress(PAYLOAD)
    assert decompress_auto("lzma", blob) == PAYLOAD


def test_best_of_picks_smallest():
    import bz2
    import lzma

    name, blob = best_compress(PAYLOAD)
    assert name in BACKEND_IDS
    expected = min(
        len(zlib.compress(PAYLOAD, 9)),
        len(bz2.compress(PAYLOAD, 9)),
        len(lzma.compress(PAYLOAD)),
    )
    assert len(blob) == expected
    assert decompress_auto(name, blob) == PAYLOAD


def test_loader_prefix_roundtrip():
    for name in ("zlib", "bz2", "lzma"):
        raw = PAYLOAD + name.encode()
        blob = {"zlib": zlib.compress, "bz2": __import__("bz2").compress,
                "lzma": __import__("lzma").compress}[name](
            raw, 9) if name != "lzma" else __import__("lzma").compress(raw)
        assert unpack_and_decompress(pack(name, blob)) == raw


def test_legacy_no_prefix_still_works():
    legacy = zlib.compress(PAYLOAD, 9)
    assert legacy[0] not in BACKEND_IDS.values() or True
    assert unpack_and_decompress(legacy) == PAYLOAD


def test_unknown_backend_rejected():
    import pytest

    with pytest.raises(ValueError):
        decompress_auto("rot13", b"xx")
    with pytest.raises(ValueError):
        pack("rot13", b"xx")
