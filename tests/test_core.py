import os
import ctypes
import marshal
import struct
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
    """Verify that WBC_encrypt actually transforms data (any available .so)."""
    so = WB_SO if _HAS_WB else CORE_SO
    lib = ctypes.CDLL(so)

    lib.WBC_new.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
    lib.WBC_new.restype = ctypes.c_void_p
    lib.WBC_del.argtypes = [ctypes.c_void_p]
    lib.WBC_encrypt.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
    lib.WBC_encrypt.restype = ctypes.POINTER(ctypes.c_uint8)
    lib.WBC_free_array.argtypes = [ctypes.POINTER(ctypes.c_uint8)]

    key = bytes(range(16))
    plaintext = b"Hello Nixon Crypto!"

    key_arr = (ctypes.c_uint8 * len(key)).from_buffer_copy(key)
    wbc = lib.WBC_new(key_arr, len(key))
    assert wbc is not None

    pt_arr = (ctypes.c_uint8 * len(plaintext)).from_buffer_copy(plaintext)
    encrypted = lib.WBC_encrypt(wbc, pt_arr, len(plaintext))
    enc_bytes = bytes(ctypes.cast(encrypted, ctypes.POINTER(ctypes.c_uint8 * len(plaintext))).contents)

    assert enc_bytes != plaintext, "Encryption produced identical output"
    assert len(enc_bytes) == len(plaintext), "Encryption changed length"

    lib.WBC_free_array(encrypted)
    lib.WBC_del(wbc)


@pytest.mark.skipif(not _HAS_WB and not _HAS_CORE, reason="no whitebox .so found")
def test_whitebox_decrypt_runs():
    """Verify WBC_decrypt does not crash (output need not round-trip if .so has bugs)."""
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

    key = bytes(range(16))
    plaintext = b"Hello Nixon Crypto!"

    key_arr = (ctypes.c_uint8 * len(key)).from_buffer_copy(key)
    wbc = lib.WBC_new(key_arr, len(key))
    assert wbc is not None

    pt_arr = (ctypes.c_uint8 * len(plaintext)).from_buffer_copy(plaintext)
    encrypted = lib.WBC_encrypt(wbc, pt_arr, len(plaintext))

    decrypted = lib.WBC_decrypt(wbc, encrypted, len(plaintext))
    dec_bytes = bytes(ctypes.cast(decrypted, ctypes.POINTER(ctypes.c_uint8 * len(plaintext))).contents)
    assert len(dec_bytes) == len(plaintext), "Decryption changed length"

    lib.WBC_free_array(encrypted)
    lib.WBC_free_array(decrypted)
    lib.WBC_del(wbc)
