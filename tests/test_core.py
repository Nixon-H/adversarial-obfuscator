import os
import ctypes
import marshal
import pytest

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "build")
PY_COMPILE_SO = os.path.join(BUILD_DIR, "py_compile.so")
CORE_SO = os.path.join(BUILD_DIR, "nixon_core.so")
WB_SO = os.path.join(BUILD_DIR, "wb.so")

_HAS_PY_COMPILE = os.path.isfile(PY_COMPILE_SO)
_HAS_CORE = os.path.isfile(CORE_SO)
_HAS_WB = os.path.isfile(WB_SO)


@pytest.mark.skipif(not _HAS_PY_COMPILE, reason="py_compile.so not found in build/")
def test_compile_to_marshal():
    lib = ctypes.CDLL(PY_COMPILE_SO)

    lib.CompileToMarshal.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    lib.CompileToMarshal.restype = ctypes.POINTER(ctypes.c_uint8)
    lib.FreeMarshalBuffer.argtypes = [ctypes.POINTER(ctypes.c_uint8)]

    source = b"x = 1\ny = 2\nprint(x + y)\n"
    out_size = ctypes.c_size_t(0)

    buf = lib.CompileToMarshal(source, b"<test>", ctypes.byref(out_size))
    assert out_size.value > 0, "CompileToMarshal returned zero-length output"
    assert buf is not None

    raw = bytes(ctypes.cast(buf, ctypes.POINTER(ctypes.c_uint8 * out_size.value)).contents)
    code_obj = marshal.loads(raw)
    assert hasattr(code_obj, "co_code"), "Marshal output is not a code object"

    lib.FreeMarshalBuffer(buf)


@pytest.mark.skipif(not _HAS_WB and not _HAS_CORE, reason="neither wb.so nor nixon_core.so found in build/")
def test_whitebox_encrypt_modifies_data():
    """Verify that WBC_encrypt actually transforms data (any available .so).

    NOTE (2026-09-20): WBC is now a padded 8-round Feistel white-box, so
    ciphertext is ((len/16)+1)*16 bytes. Size helpers expose the lengths.
    """
    so = WB_SO if _HAS_WB else CORE_SO
    lib = ctypes.CDLL(so)

    lib.WBC_new.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
    lib.WBC_new.restype = ctypes.c_void_p
    lib.WBC_del.argtypes = [ctypes.c_void_p]
    lib.WBC_encrypt.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
    lib.WBC_encrypt.restype = ctypes.POINTER(ctypes.c_uint8)
    lib.WBC_free_array.argtypes = [ctypes.POINTER(ctypes.c_uint8)]
    lib.WBC_encrypted_size.argtypes = [ctypes.c_size_t]
    lib.WBC_encrypted_size.restype = ctypes.c_size_t

    key = bytes(range(16))
    plaintext = b"Hello Nixon Crypto!"

    key_arr = (ctypes.c_uint8 * len(key)).from_buffer_copy(key)
    wbc = lib.WBC_new(key_arr, len(key))
    assert wbc is not None

    pt_arr = (ctypes.c_uint8 * len(plaintext)).from_buffer_copy(plaintext)
    encrypted = lib.WBC_encrypt(wbc, pt_arr, len(plaintext))
    assert encrypted is not None
    enc_len = lib.WBC_encrypted_size(len(plaintext))
    assert enc_len == ((len(plaintext) // 16) + 1) * 16
    enc_bytes = bytes(ctypes.cast(encrypted, ctypes.POINTER(ctypes.c_uint8 * enc_len)).contents)

    assert enc_bytes != plaintext + b"\x00" * (enc_len - len(plaintext)), "Encryption produced identical output"
    assert len(enc_bytes) == enc_len, "Encryption wrong length"

    lib.WBC_free_array(encrypted)
    lib.WBC_del(wbc)

    _libc = ctypes.CDLL(None)
    _libc.memset.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t]
    _libc.memset(key_arr, 0, ctypes.sizeof(key_arr))


@pytest.mark.skipif(not _HAS_WB and not _HAS_CORE, reason="no whitebox .so found")
def test_whitebox_decrypt_runs():
    """Verify WBC_decrypt round-trips (padded Feistel must be exact inverse)."""
    so = WB_SO if _HAS_WB else CORE_SO
    lib = ctypes.CDLL(so)

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

    key = bytes(range(16))

    for plaintext in (b"Hello Nixon Crypto!", b"A", bytes(range(255)), b"y" * 16, b"z" * 32):
        key_arr = (ctypes.c_uint8 * len(key)).from_buffer_copy(key)
        wbc = lib.WBC_new(key_arr, len(key))
        assert wbc is not None

        pt_arr = (ctypes.c_uint8 * len(plaintext)).from_buffer_copy(plaintext)
        encrypted = lib.WBC_encrypt(wbc, pt_arr, len(plaintext))
        assert encrypted is not None
        enc_len = lib.WBC_encrypted_size(len(plaintext))
        enc_arr = (ctypes.c_uint8 * enc_len).from_buffer_copy(
            bytes(ctypes.cast(encrypted, ctypes.POINTER(ctypes.c_uint8 * enc_len)).contents))

        dec_len = lib.WBC_decrypted_size(wbc, enc_arr, enc_len)
        assert dec_len == len(plaintext), f"decrypted size {dec_len} != {len(plaintext)}"
        decrypted = lib.WBC_decrypt(wbc, enc_arr, enc_len)
        assert decrypted is not None
        dec_bytes = bytes(ctypes.cast(decrypted, ctypes.POINTER(ctypes.c_uint8 * dec_len)).contents)
        assert dec_bytes == plaintext, f"round-trip failed for len {len(plaintext)}"

        lib.WBC_free_array(encrypted)
        lib.WBC_free_array(decrypted)
        lib.WBC_del(wbc)

        _libc = ctypes.CDLL(None)
        _libc.memset.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t]
        _libc.memset(key_arr, 0, ctypes.sizeof(key_arr))
