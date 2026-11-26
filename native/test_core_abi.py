#!/usr/bin/env python3
"""ctypes regressions for the native white-box C ABI.

Run against a freshly built library, for example:

    NIXON_CORE_SO=/tmp/opencode/wb.so python3 native/test_core_abi.py

The SIZE_MAX probes run in child processes so a regression that lets a C++
exception cross the C ABI fails the test instead of terminating the runner.
"""

import ctypes
import os
import subprocess
import sys
import unittest


SIZE_MAX = ctypes.c_size_t(-1).value
DEFAULT_SO = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "build", "wb.so")
)
SO_PATH = os.path.abspath(os.environ.get("NIXON_CORE_SO", DEFAULT_SO))

WBC_OK = 0
WBC_ERR_INVALID_ARGUMENT = -1
WBC_ERR_OVERFLOW = -2
WBC_ERR_INTERNAL = -3


def _configure(lib):
    byte_p = ctypes.POINTER(ctypes.c_uint8)
    lib.WBC_new.argtypes = [byte_p, ctypes.c_size_t]
    lib.WBC_new.restype = ctypes.c_void_p
    lib.WBC_del.argtypes = [ctypes.c_void_p]
    lib.WBC_del.restype = None
    lib.WBC_encrypt.argtypes = [ctypes.c_void_p, byte_p, ctypes.c_size_t]
    lib.WBC_encrypt.restype = byte_p
    lib.WBC_decrypt.argtypes = [ctypes.c_void_p, byte_p, ctypes.c_size_t]
    lib.WBC_decrypt.restype = byte_p
    lib.WBC_free_array.argtypes = [byte_p]
    lib.WBC_free_array.restype = None
    lib.WBC_encrypted_size.argtypes = [ctypes.c_size_t]
    lib.WBC_encrypted_size.restype = ctypes.c_size_t
    lib.WBC_decrypted_size.argtypes = [ctypes.c_void_p, byte_p, ctypes.c_size_t]
    lib.WBC_decrypted_size.restype = ctypes.c_size_t

    lib.WBE_new.argtypes = [ctypes.c_int, byte_p, byte_p, byte_p]
    lib.WBE_new.restype = ctypes.c_void_p
    lib.WBE_del.argtypes = [ctypes.c_void_p]
    lib.WBE_del.restype = None
    lib.WBE_encrypt.argtypes = [ctypes.c_void_p, byte_p, ctypes.c_size_t]
    lib.WBE_encrypt.restype = byte_p
    lib.WBE_decrypt.argtypes = [ctypes.c_void_p, byte_p, ctypes.c_size_t]
    lib.WBE_decrypt.restype = byte_p


def _new_wbc(lib):
    key = (ctypes.c_uint8 * 16).from_buffer_copy(bytes(range(16)))
    handle = lib.WBC_new(key, len(key))
    if not handle:
        raise AssertionError("WBC_new returned NULL for a valid 16-byte key")
    return handle


def _bytes(lib, pointer, length):
    if length == 0:
        return b""
    return bytes(ctypes.cast(pointer, ctypes.POINTER(ctypes.c_uint8 * length)).contents)


def _encrypt(lib, handle, plaintext):
    buf = (ctypes.c_uint8 * max(1, len(plaintext)))()
    if plaintext:
        ctypes.memmove(buf, plaintext, len(plaintext))
    encrypted = lib.WBC_encrypt(handle, buf, len(plaintext))
    if not encrypted:
        raise AssertionError("WBC_encrypt returned NULL")
    length = lib.WBC_encrypted_size(len(plaintext))
    try:
        return encrypted, _bytes(lib, encrypted, length)
    except Exception:
        lib.WBC_free_array(encrypted)
        raise


def _overflow_child(lib):
    handle = _new_wbc(lib)
    try:
        if lib.WBC_encrypted_size(SIZE_MAX) != 0:
            raise AssertionError("SIZE_MAX did not use the overflow sentinel")
        one_byte = (ctypes.c_uint8 * 1)(0x41)
        if lib.WBC_encrypt(handle, one_byte, SIZE_MAX):
            raise AssertionError("WBC_encrypt accepted SIZE_MAX")

        if hasattr(lib, "WBC_encrypt_ex"):
            byte_pp = ctypes.POINTER(ctypes.POINTER(ctypes.c_uint8))
            lib.WBC_encrypt_ex.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.c_size_t,
                byte_pp,
                ctypes.POINTER(ctypes.c_size_t),
            ]
            lib.WBC_encrypt_ex.restype = ctypes.c_int
            out = ctypes.POINTER(ctypes.c_uint8)()
            out_len = ctypes.c_size_t(123)
            status = lib.WBC_encrypt_ex(
                handle, one_byte, SIZE_MAX, ctypes.byref(out), ctypes.byref(out_len)
            )
            if status != WBC_ERR_OVERFLOW or out or out_len.value != 0:
                raise AssertionError(
                    f"WBC_encrypt_ex overflow result: status={status}, "
                    f"out={bool(out)}, out_len={out_len.value}"
                )
    finally:
        lib.WBC_del(handle)


def _wbe_overflow_child(lib):
    # One round of identity tables is enough to reach the oversized vector
    # construction in WBE_encrypt.
    tables = (ctypes.c_uint8 * 256)(*range(256))
    mix_keys = (ctypes.c_uint8 * 16)()
    handle = lib.WBE_new(1, tables, tables, mix_keys)
    if not handle:
        raise AssertionError("WBE_new returned NULL for valid identity tables")
    try:
        one_byte = (ctypes.c_uint8 * 1)(0x41)
        if lib.WBE_encrypt(handle, one_byte, SIZE_MAX):
            raise AssertionError("WBE_encrypt accepted SIZE_MAX")
        if lib.WBE_decrypt(handle, one_byte, SIZE_MAX):
            raise AssertionError("WBE_decrypt accepted SIZE_MAX")
    finally:
        lib.WBE_del(handle)


class WhiteboxAbiRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(SO_PATH):
            raise unittest.SkipTest(f"native library not found: {SO_PATH}")
        cls.lib = ctypes.CDLL(SO_PATH)
        _configure(cls.lib)
        cls.handle = _new_wbc(cls.lib)

    @classmethod
    def tearDownClass(cls):
        cls.lib.WBC_del(cls.handle)

    def test_encrypted_size_boundaries(self):
        self.assertEqual(self.lib.WBC_encrypted_size(0), 16)
        self.assertEqual(self.lib.WBC_encrypted_size(15), 16)
        self.assertEqual(self.lib.WBC_encrypted_size(16), 32)
        self.assertEqual(self.lib.WBC_encrypted_size(SIZE_MAX - 16), SIZE_MAX - 15)
        self.assertEqual(self.lib.WBC_encrypted_size(SIZE_MAX - 15), 0)
        self.assertEqual(self.lib.WBC_encrypted_size(SIZE_MAX), 0)

    def test_size_max_does_not_cross_c_abi(self):
        result = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--overflow-child", SO_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"SIZE_MAX child failed ({result.returncode}):\n{result.stderr}",
        )

    def test_wbe_size_max_does_not_cross_c_abi(self):
        result = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--wbe-overflow-child", SO_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"WBE SIZE_MAX child failed ({result.returncode}):\n{result.stderr}",
        )

    def test_empty_plaintext_roundtrip_legacy(self):
        encrypted, ciphertext = _encrypt(self.lib, self.handle, b"")
        try:
            self.assertEqual(len(ciphertext), 16)
            self.assertEqual(
                self.lib.WBC_decrypted_size(self.handle, encrypted, len(ciphertext)), 0
            )
            decrypted = self.lib.WBC_decrypt(self.handle, encrypted, len(ciphertext))
            self.assertTrue(
                decrypted,
                "valid empty plaintext must return a non-NULL success sentinel",
            )
            self.lib.WBC_free_array(decrypted)
        finally:
            self.lib.WBC_free_array(encrypted)

    def test_empty_plaintext_roundtrip_ex(self):
        self.assertTrue(hasattr(self.lib, "WBC_encrypt_ex"), "WBC_encrypt_ex is missing")
        self.assertTrue(hasattr(self.lib, "WBC_decrypt_ex"), "WBC_decrypt_ex is missing")
        byte_p = ctypes.POINTER(ctypes.c_uint8)
        byte_pp = ctypes.POINTER(byte_p)
        self.lib.WBC_encrypt_ex.argtypes = [
            ctypes.c_void_p,
            byte_p,
            ctypes.c_size_t,
            byte_pp,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        self.lib.WBC_encrypt_ex.restype = ctypes.c_int
        self.lib.WBC_decrypt_ex.argtypes = list(self.lib.WBC_encrypt_ex.argtypes)
        self.lib.WBC_decrypt_ex.restype = ctypes.c_int

        encrypted = ctypes.POINTER(ctypes.c_uint8)()
        encrypted_len = ctypes.c_size_t(123)
        status = self.lib.WBC_encrypt_ex(
            self.handle,
            None,
            0,
            ctypes.byref(encrypted),
            ctypes.byref(encrypted_len),
        )
        self.assertEqual(status, WBC_OK)
        self.assertTrue(encrypted)
        self.assertEqual(encrypted_len.value, 16)
        try:
            decrypted = ctypes.POINTER(ctypes.c_uint8)()
            decrypted_len = ctypes.c_size_t(123)
            status = self.lib.WBC_decrypt_ex(
                self.handle,
                encrypted,
                encrypted_len,
                ctypes.byref(decrypted),
                ctypes.byref(decrypted_len),
            )
            self.assertEqual(status, WBC_OK)
            self.assertTrue(
                decrypted,
                "WBC_decrypt_ex must return a freeable non-NULL pointer for empty output",
            )
            self.assertEqual(decrypted_len.value, 0)
            self.lib.WBC_free_array(decrypted)
        finally:
            self.lib.WBC_free_array(encrypted)

    def test_malformed_padding_is_rejected(self):
        zero_enc, zero_ciphertext = _encrypt(self.lib, self.handle, b"\x00" * 16)
        high_enc, high_ciphertext = _encrypt(self.lib, self.handle, b"\x11" * 16)
        mixed_enc, mixed_ciphertext = _encrypt(
            self.lib, self.handle, b"\x10" * 15 + b"\x0f"
        )
        try:
            # Duplicating E(0x00*16) yields an all-zero padded block (pad=0).
            # Duplicating E(0x11*16) yields pad=17, and the mixed second block
            # has a final pad byte of 15 preceded by 16 (inconsistent PKCS#7).
            malformed = (
                zero_ciphertext[:16] + zero_ciphertext[:16],
                high_ciphertext[:16] + high_ciphertext[:16],
                zero_ciphertext[:16] + mixed_ciphertext[:16],
                zero_ciphertext[:15],
                zero_ciphertext + b"\x00",
            )
            for index, ciphertext in enumerate(malformed):
                with self.subTest(case=index):
                    buf = (ctypes.c_uint8 * len(ciphertext)).from_buffer_copy(ciphertext)
                    self.assertFalse(
                        self.lib.WBC_decrypt(self.handle, buf, len(ciphertext))
                    )
                    self.assertEqual(
                        self.lib.WBC_decrypted_size(self.handle, buf, len(ciphertext)),
                        0,
                    )
                    if hasattr(self.lib, "WBC_decrypt_ex"):
                        out = ctypes.POINTER(ctypes.c_uint8)()
                        out_len = ctypes.c_size_t(123)
                        status = self.lib.WBC_decrypt_ex(
                            self.handle,
                            buf,
                            len(ciphertext),
                            ctypes.byref(out),
                            ctypes.byref(out_len),
                        )
                        self.assertNotEqual(status, WBC_OK)
                        self.assertFalse(out)
                        self.assertEqual(out_len.value, 0)
        finally:
            self.lib.WBC_free_array(zero_enc)
            self.lib.WBC_free_array(high_enc)
            self.lib.WBC_free_array(mixed_enc)

    def test_invalid_arguments_initialize_ex_outputs(self):
        self.assertTrue(hasattr(self.lib, "WBC_decrypt_ex"), "WBC_decrypt_ex is missing")
        byte_p = ctypes.POINTER(ctypes.c_uint8)
        self.lib.WBC_decrypt_ex.argtypes = [
            ctypes.c_void_p,
            byte_p,
            ctypes.c_size_t,
            ctypes.POINTER(byte_p),
            ctypes.POINTER(ctypes.c_size_t),
        ]
        self.lib.WBC_decrypt_ex.restype = ctypes.c_int
        out = ctypes.POINTER(ctypes.c_uint8)()
        out_len = ctypes.c_size_t(123)
        status = self.lib.WBC_decrypt_ex(
            self.handle, None, 1, ctypes.byref(out), ctypes.byref(out_len)
        )
        self.assertEqual(status, WBC_ERR_INVALID_ARGUMENT)
        self.assertFalse(out)
        self.assertEqual(out_len.value, 0)


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--overflow-child":
        lib = ctypes.CDLL(os.path.abspath(sys.argv[2]))
        _configure(lib)
        _overflow_child(lib)
        return 0
    if len(sys.argv) >= 3 and sys.argv[1] == "--wbe-overflow-child":
        lib = ctypes.CDLL(os.path.abspath(sys.argv[2]))
        _configure(lib)
        _wbe_overflow_child(lib)
        return 0
    unittest.main(verbosity=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
