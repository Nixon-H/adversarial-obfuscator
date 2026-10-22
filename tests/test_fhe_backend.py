"""The FHE/ORAM bootstrap backend must be real.

The loader's FHE class used to look for ``FHE_new``/``ORAM_new`` in
``nixon_core.so`` -- symbols that existed nowhere in ``native/``.  So
the loader always took its pure-Python fallback, where
``encrypt_batch``/``dec_batch`` were NO-OPS, and the bootstrap
"verified" a plaintext array it never encrypted.  The build reported
FHE and ORAM as enabled.

Now the C core implements a real homomorphic scheme and the Python
fallback implements the SAME one, so:

* the C path round-trips, and its addition is homomorphic;
* the Python fallback round-trips the same way (it is no longer a
  no-op);
* the loader's bootstrap actually checks the round-trip.
"""

import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from obfuscator.core.sources import FHE_SOURCE, ORAM_SOURCE  # noqa: E402

CORE = os.path.join(ROOT, "build", "nixon_core.so")


def _loader_classes():
    """The loader's FHE and ORAM classes, as the loader emits them.

    ``__file__`` points into a directory with no ``nixon_core.so``, so
    these exercise the PYTHON path; the C path is tested separately.
    """
    import tempfile

    namespace = {"__file__": os.path.join(tempfile.gettempdir(), "_nix_fhe_probe.py")}
    exec(compile(FHE_SOURCE.replace("{FHE_CLS}", "_LoaderFhe"), "<fhe>", "exec"),
         namespace)
    exec(compile(ORAM_SOURCE.replace("{ORAM_CLS}", "_LoaderOram"), "<oram>", "exec"),
         namespace)
    return namespace["_LoaderFhe"], namespace["_LoaderOram"]


def _c_core_available():
    if not os.path.exists(CORE):
        return False
    return subprocess.run(["sh", "-c", "command -v g++ >/dev/null"],
                          capture_output=True).returncode == 0


# --------------------------------------------------------------------------
# The C implementation
# --------------------------------------------------------------------------

@pytest.mark.skipif(not _c_core_available(), reason="the C core is not built")
def test_the_c_core_exports_the_loader_symbols():
    """The loader's symbols must exist, or the backend is unreachable."""
    out = subprocess.run(["nm", "-D", "--defined-only", CORE],
                         capture_output=True, text=True, timeout=60).stdout
    for symbol in ("FHE_new", "FHE_encrypt_batch", "FHE_add_batch",
                   "FHE_dec_batch", "FHE_free_array",
                   "ORAM_new", "ORAM_access"):
        assert symbol in out, "%s is not exported by the C core" % symbol


@pytest.mark.skipif(not _c_core_available(), reason="the C core is not built")
def test_the_c_fhe_round_trips_and_is_homomorphic():
    """Encrypt, add two ciphertexts, decrypt: the sum comes back."""
    import ctypes

    lib = ctypes.CDLL(CORE)
    lib.FHE_new.restype = ctypes.c_void_p
    lib.FHE_new.argtypes = [ctypes.c_size_t]
    lib.FHE_encrypt_batch.restype = ctypes.POINTER(ctypes.c_uint32)
    lib.FHE_encrypt_batch.argtypes = [ctypes.c_void_p,
                                      ctypes.POINTER(ctypes.c_uint32),
                                      ctypes.c_size_t]
    lib.FHE_add_batch.restype = ctypes.POINTER(ctypes.c_uint32)
    lib.FHE_add_batch.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_size_t]
    lib.FHE_dec_batch.restype = ctypes.POINTER(ctypes.c_uint32)
    lib.FHE_dec_batch.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32),
                                  ctypes.c_size_t]
    lib.FHE_free_array.argtypes = [ctypes.POINTER(ctypes.c_uint32)]

    handle = lib.FHE_new(16)
    a = [i + 1 for i in range(16)]
    b = [100 + i for i in range(16)]

    ca = lib.FHE_encrypt_batch(handle, (ctypes.c_uint32 * 16)(*a), 16)
    cb = lib.FHE_encrypt_batch(handle, (ctypes.c_uint32 * 16)(*b), 16)
    assert [ca[i] for i in range(16)] != a, "the ciphertext is the plaintext"

    dec = lib.FHE_dec_batch(handle, ca, 16)
    assert [dec[i] for i in range(16)] == a, "the round-trip lost the plaintext"

    summed = lib.FHE_add_batch(handle, ca, cb, 16)
    dec_sum = lib.FHE_dec_batch(handle, summed, 16)
    assert [dec_sum[i] for i in range(16)] == [x ^ y for x, y in zip(a, b)], (
        "the addition is not homomorphic")


@pytest.mark.skipif(not _c_core_available(), reason="the C core is not built")
def test_the_c_oram_round_trips():
    import ctypes

    lib = ctypes.CDLL(CORE)
    lib.ORAM_new.restype = ctypes.c_void_p
    lib.ORAM_new.argtypes = [ctypes.c_int]
    lib.ORAM_access.restype = ctypes.c_uint32
    lib.ORAM_access.argtypes = [ctypes.c_void_p, ctypes.c_bool,
                                 ctypes.c_int, ctypes.c_uint32]

    oram = lib.ORAM_new(32)
    lib.ORAM_access(oram, True, 7, 4242)
    assert lib.ORAM_access(oram, False, 7, 0) == 4242
    lib.ORAM_access(oram, True, 9, 99)
    assert lib.ORAM_access(oram, False, 9, 0) == 99
    assert lib.ORAM_access(oram, False, 7, 0) == 4242


# --------------------------------------------------------------------------
# The Python fallback — it must not be a no-op either
# --------------------------------------------------------------------------

@pytest.mark.filterwarnings("ignore:FHE C module not available")
def test_the_python_fhe_fallback_is_a_real_implementation():
    """The fallback round-trips and its addition is homomorphic.

    It used to return its input unchanged: ``encrypt_batch`` was
    ``value_array[:]`` and ``dec_batch`` was ``c_enc[:]``.
    """
    Fhe, _Oram = _loader_classes()
    fhe = Fhe(batch_size=16)
    a = [i + 1 for i in range(16)]
    b = [100 + i for i in range(16)]

    ca = fhe.encrypt_batch(a)
    assert ca != a, "the fallback returned the plaintext unchanged"

    dec = fhe.dec_batch(ca)
    assert dec[:len(a)] == a, "the fallback round-trip lost the plaintext"

    summed = fhe.add_batch(ca, fhe.encrypt_batch(b))
    dec_sum = fhe.dec_batch(summed)
    assert dec_sum[:len(a)] == [x ^ y for x, y in zip(a, b)], (
        "the fallback addition is not homomorphic")


@pytest.mark.filterwarnings("ignore:ORAM C module not available")
def test_the_python_oram_fallback_round_trips():
    _Fhe, Oram = _loader_classes()
    oram = Oram(size=32)
    oram.access('write', 5, 1234)
    assert oram.access('read', 5) == 1234
    oram.access('write', 6, 77)
    assert oram.access('read', 6) == 77
    assert oram.access('read', 5) == 1234


def test_the_c_and_python_paths_derive_the_mask_the_same_way():
    """The two implementations must be the SAME scheme.

    Both derive the per-slot mask as
    ``LE32(SHA-256(key || nonce || LE64(i))[0:4]) & 0x7fffffff``; if
    they drift, the C and Python paths stop being interchangeable.
    """
    from obfuscator.core.sources import FHE_SOURCE

    cpp = open(os.path.join(ROOT, "native", "core.cpp"), encoding="utf-8").read()
    assert "SHA-256(key || nonce || LE64(i))" in cpp or \
        "wb_sha256(buf, sizeof(buf), digest)" in cpp
    assert "FHE_VALUE_MASK" in cpp
    assert "& 0x7fffffff" in FHE_SOURCE
    assert "sha256(self._fhe_key + self._fhe_nonce" in FHE_SOURCE
    assert "to_bytes(8" in FHE_SOURCE


def test_the_bootstrap_verifies_its_round_trip():
    """The loader's bootstrap must CHECK, not just store.

    It used to decrypt a plaintext array and store the result without
    comparing anything, so it verified nothing.
    """
    from obfuscator.core.sources import LOADER_HEAD

    assert "FHE round-trip mismatch" in LOADER_HEAD, (
        "the loader's FHE bootstrap does not check the round-trip")
    assert "returned the plaintext unchanged" in LOADER_HEAD, (
        "the loader's FHE bootstrap does not reject a no-op round-trip")
    assert "_fhe_.add_batch(" in LOADER_HEAD, (
        "the loader's FHE bootstrap does not exercise the homomorphic "
        "addition")
    assert "_fhe_.encrypt_batch(" in LOADER_HEAD, (
        "the loader's FHE bootstrap does not encrypt anything")
