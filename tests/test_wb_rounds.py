"""Tests for white-box round range 8-12 (V10 parity).

Two instances (distinct per-object salts) must usually differ structurally
(different ciphertext for same plaintext+key) while BOTH round-trip.
"""
import ctypes
import os

import pytest

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "build")
WB_SO = os.path.join(BUILD_DIR, "wb.so")

_HAS_WB = os.path.isfile(WB_SO)


def _lib():
    lib = ctypes.CDLL(WB_SO)
    lib.WBC_new.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
    lib.WBC_new.restype = ctypes.c_void_p
    lib.WBC_del.argtypes = [ctypes.c_void_p]
    lib.WBC_encrypt.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
    lib.WBC_encrypt.restype = ctypes.POINTER(ctypes.c_uint8)
    lib.WBC_decrypt.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
    lib.WBC_decrypt.restype = ctypes.POINTER(ctypes.c_uint8)
    lib.WBC_free_array.argtypes = [ctypes.POINTER(ctypes.c_uint8)]
    lib.WBC_encrypted_size.argtypes = [ctypes.c_size_t]
    lib.WBC_encrypted_size.restype = ctypes.c_size_t
    lib.WBC_decrypted_size.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
    lib.WBC_decrypted_size.restype = ctypes.c_size_t
    return lib


def _roundtrip(lib, key, pt):
    ka = (ctypes.c_uint8 * 16).from_buffer_copy(key)
    wbc = lib.WBC_new(ka, 16)
    assert wbc is not None
    try:
        elen = lib.WBC_encrypted_size(len(pt))
        pa = (ctypes.c_uint8 * max(len(pt), 1)).from_buffer_copy(pt if pt else b"\x00")
        enc = lib.WBC_encrypt(wbc, pa, len(pt))
        assert enc is not None
        enc_b = bytes(ctypes.cast(enc, ctypes.POINTER(ctypes.c_uint8 * elen)).contents)
        ea = (ctypes.c_uint8 * elen).from_buffer_copy(enc_b)
        dlen = lib.WBC_decrypted_size(wbc, ea, elen)
        dec = lib.WBC_decrypt(wbc, ea, elen)
        dec_b = bytes(ctypes.cast(dec, ctypes.POINTER(ctypes.c_uint8 * dlen)).contents) if dlen else b""
        lib.WBC_free_array(enc)
        lib.WBC_free_array(dec)
        return enc_b, dec_b
    finally:
        lib.WBC_del(wbc)


@pytest.mark.skipif(not _HAS_WB, reason="wb.so not found in build/")
def test_round_range_diversity():
    """Two instances (random salts -> usually different round counts AND
    tables) must produce different ciphertext for the same input."""
    lib = _lib()
    key = bytes(range(16))
    pt = b"round-range diversity probe payload!!"
    seen = set()
    for _ in range(6):
        enc, dec = _roundtrip(lib, key, pt)
        assert dec == pt
        seen.add(enc)
    # 6 random salts: P(all identical) negligible unless diversity broke.
    assert len(seen) > 1, "all instances produced identical ciphertext"


@pytest.mark.skipif(not _HAS_WB, reason="wb.so not found in build/")
def test_roundtrip_various_lengths():
    lib = _lib()
    key = bytes(range(16))
    for pt in (b"A", b"B" * 16, b"C" * 31, b"D" * 64, bytes(range(200))):
        _, dec = _roundtrip(lib, key, pt)
        assert dec == pt, f"round-trip failed for len {len(pt)}"
