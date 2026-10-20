"""Cryptographic fallback-semantics tests (additive, stdlib + pytest only).

Scope: ``obfuscator/core/pipeline.py`` selection + encryption paths
(``_check_aes_ctr`` / ``Nixon_Enc_AES_CTR`` / ``Nixon_Enc_blob`` /
``encrypt_payload``) versus what the emitted artifact LOADER can decrypt
(``CIPHER_SOURCE.decrypt`` in ``obfuscator/core/sources.py`` — a SHA-256
keystream XOR, i.e. the inverse of ``Nixon_Enc_blob`` — and the hybrid
loader ``_xor_decrypt`` repeating-key XOR, ``pipeline.py:1543``).

Python 3.10 compatible (no match statements, no PEP 604 annotations).

Documented FINDINGS (see also the final report):
  F1 (critical, fixed): with ``cryptography`` installed (it is pinned in
      ``requirements.txt``), ``encrypt_payload`` defaulted to real AES-CTR,
      but NO emitted loader template implements AES-CTR decryption
      (``sources.py`` contains zero ``cryptography``/``Crypto.Cipher``
      references). The loader's ``NixonCipher.decrypt`` only inverts the
      XOR-stream ``Nixon_Enc_blob`` construction, so an AES-CTR core blob
      is NOT loader-readable (lands in ``S_PAD`` "Magic Mismatch",
      ``sources.py:6269``). The XOR "fallback" is the only
      loader-compatible construction.
  F1 (fixed): ``encrypt_payload`` defaulted to real AES-CTR when
      ``cryptography`` was installed, but NO emitted loader template
      implements AES-CTR decryption — an AES-CTR core blob was NOT
      loader-readable (``S_PAD`` "Magic Mismatch"). The legacy
      ``build_project`` call site now forces ``use_aes_ctr=False`` with
      rationale comment (``pipeline.py``), since the loader must stay
      stdlib-only. AES-CTR remains available for non-artifact uses.
  F2 (fixed): ``CIPHER_SOURCE`` (the XOR-stream decryptor) was canonically
      labeled ``"AES_GCM"`` in ``_VARS_MAP["CIPHER_CLS"]``
      (``sources.py:830``); renamed to ``"XOR_STREAM"``. Emitted class
      names were already randomized so artifacts never carried the
      literal string.
  F3: the ``Nixon_Enc_*`` blob layer has NO integrity tag (CTR malleability
      proven below). Blob integrity exists only (a) at build time for the
      whole artifact file (``pipeline.py:2850`` HMAC seal), (b) for string
      tables (8-byte HMAC, ``pipeline.py:249`` verified at
      ``sources.py:5556``), and (c) as a plaintext MAGIC-prefix format
      check (``sources.py:6269-6273``) — none of which is a MAC over the
      ``encrypt_payload`` ciphertext. (The ChaCha20 string subsystem
      ``obfuscator/chacha20.py`` *is* AEAD; it is a separate path.)
  F4: ``Nixon_Enc_AES_CTR``/``Nixon_Enc_blob`` perform NO key/nonce
      validation: key/nonce are hashed (``sha256(key+nonce)``), so short
      keys and long nonces are silently absorbed (entropy reduction, no
      error), and empty plaintext yields ``b""``. Non-bytes inputs raise a
      bare ``TypeError`` from ``bytes()/hashlib``, not a ``ValueError``.
"""

import hashlib
import inspect
import os
import sys

import pytest

from obfuscator.core import pipeline as P
from obfuscator.core.sources import CIPHER_SOURCE, _VARS_MAP
from obfuscator.core.utils import fast_xor_bytes


def _need_crypto():
    """Skip unless the ``cryptography`` package is importable.

    Module level stays importable without it so the fallback-semantics
    tests still run in a crypto-less environment (the suite is executed
    both with and without ``cryptography`` visible).
    """
    return pytest.importorskip("cryptography.hazmat.primitives.ciphers",
                               reason="AES-CTR KAT needs cryptography")

# ---------------------------------------------------------------------------
# NIST SP 800-38A, section F.5 (CTR mode). Embedded, never fetched.
# F.5.1 CTR-AES128, F.5.2 CTR-AES192, F.5.3 CTR-AES256 share the same
# initial counter block f0f1...fdfeff and plaintext blocks; only
# key/ciphertext differ. Cross-checked against the SP800 vectors shipped
# in the local pycryptodome self-test suite
# (Crypto/SelfTest/Cipher/test_CTR.py::SP800TestVectors).
# ---------------------------------------------------------------------------
_F51_KEY = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
_F52_KEY = bytes.fromhex(
    "8e73b0f7da0e6452c810f32b809079e562f8ead2522c6b7b")
_F53_KEY = bytes.fromhex(
    "603deb1015ca71be2b73aef0857d77811f352c073b6108d72d9810a30914dff4")
_F5_CTR0 = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff")
_F5_PT = [
    bytes.fromhex("6bc1bee22e409f96e93d7e117393172a"),
    bytes.fromhex("ae2d8a571e03ac9c9eb76fac45af8e51"),
    bytes.fromhex("30c81c46a35ce411e5fbc1191a0a52ef"),
    bytes.fromhex("f69f2445df4f9b17ad2b417be66c3710"),
]
_F51_CT = [
    bytes.fromhex("874d6191b620e3261bef6864990db6ce"),
    bytes.fromhex("9806f66b7970fdff8617187bb9fffdff"),
    bytes.fromhex("5ae4df3edbd5d35e5b4f09020db03eab"),
    bytes.fromhex("1e031dda2fbe03d1792170a0f3009cee"),
]
_F52_CT1 = bytes.fromhex("1abc932417521ca24f2b0459fe7e6e0b")
_F53_CT = [
    bytes.fromhex("601ec313775789a5b7a7f504bbf3d228"),
    bytes.fromhex("f443e3ca4d62b59aca84e990cacaf5c5"),
    bytes.fromhex("2b0930daa23de94ce87017ba2d84988d"),
    bytes.fromhex("dfc9c58db67aada613c2dd08457941a6"),
]


def _raw_aes_ctr(key, iv, data):
    """Independent reference: raw AES-CTR via the ``cryptography`` package."""
    from cryptography.hazmat.primitives.ciphers import (
        Cipher, algorithms, modes)
    enc = Cipher(algorithms.AES(bytes(key)), modes.CTR(bytes(iv))).encryptor()
    return enc.update(bytes(data)) + enc.finalize()


def _reference_nixon_aes_ctr(data, key, nonce):
    """Reference for the wrapper's *documented* construction.

    ``Nixon_Enc_AES_CTR`` derives ``aes_key = sha256(key+nonce)[:32]`` and
    ``iv = sha256(nonce+key)[:16]`` and applies raw AES-CTR. This rebuilds
    that construction from the KAT-validated primitive above, so the test
    ties the wrapper to the standard without reimplementing AES.
    """
    aes_key = hashlib.sha256(bytes(key) + bytes(nonce)).digest()[:32]
    iv = hashlib.sha256(bytes(nonce) + bytes(key)).digest()[:16]
    return _raw_aes_ctr(aes_key, iv, data)


def _loader_cipher_decrypt(data, key, nonce):
    """The REAL emitted loader decrypt path (``CIPHER_SOURCE`` template).

    The template carries a ``{CIPHER_CLS}`` placeholder and reads the
    ``_nixon_...`` hashlib alias plus the ``_NX_POISON`` offset global;
    both are provided here exactly as the loader does (offset 0 default).
    """
    import re
    g = {"hashlib": hashlib}
    # Bind every _nixon_* module-global alias the template reads (the exact
    # non-ASCII identifier is extracted programmatically — never retyped).
    for alias in set(re.findall(r"_nixon_\w+", CIPHER_SOURCE)):
        g.setdefault(alias, hashlib)
    ns = {}
    exec(CIPHER_SOURCE.replace("{CIPHER_CLS}", "NixonCipher"), g, ns)  # noqa: S102
    return ns["NixonCipher"](bytes(key)).decrypt(bytes(data), bytes(nonce))


@pytest.fixture
def aes_cache_reset(monkeypatch):
    """Reset the cached ``_check_aes_ctr`` result around selection tests."""
    P._AES_CTR_AVAILABLE = None
    yield
    P._AES_CTR_AVAILABLE = None


def _block_imports(monkeypatch, *names):
    """Simulate missing optional deps (seam used by ``_check_aes_ctr``).

    ``sys.modules[name] = None`` makes ``from name import ...`` raise
    ``ImportError`` (via ``ModuleNotFoundError``, a subclass), which is
    what the ``except ImportError`` clauses in ``pipeline.py`` catch.
    """
    for name in names:
        monkeypatch.setitem(sys.modules, name, None)


# ===========================================================================
# 1. AES-CTR known-answer + malleability documentation.
# ===========================================================================
class TestAesCtrKnownAnswer:
    def test_nist_f51_aes128_first_block(self):
        _need_crypto()
        ct = _raw_aes_ctr(_F51_KEY, _F5_CTR0, _F5_PT[0])
        assert ct == _F51_CT[0]

    def test_nist_f51_aes128_all_four_blocks(self):
        _need_crypto()
        pt = b"".join(_F5_PT)
        ct = _raw_aes_ctr(_F51_KEY, _F5_CTR0, pt)
        assert ct == b"".join(_F51_CT)

    def test_nist_f52_aes192_first_block(self):
        _need_crypto()
        ct = _raw_aes_ctr(_F52_KEY, _F5_CTR0, _F5_PT[0])
        assert ct == _F52_CT1

    def test_nist_f53_aes256_all_four_blocks(self):
        _need_crypto()
        pt = b"".join(_F5_PT)
        ct = _raw_aes_ctr(_F53_KEY, _F5_CTR0, pt)
        assert ct == b"".join(_F53_CT)

    def test_wrapper_matches_reference_construction(self):
        _need_crypto()
        key, nonce = b"K" * 32, b"N" * 16
        data = b"wrapper-construction probe payload " * 4
        assert (P.Nixon_Enc_AES_CTR(data, key, nonce)
                == _reference_nixon_aes_ctr(data, key, nonce))

    def test_wrapper_roundtrip_and_determinism(self):
        key, nonce = b"K" * 32, b"N" * 16
        data = b"roundtrip payload \x00\xff binary ok " * 8
        ct = P.Nixon_Enc_AES_CTR(data, key, nonce)
        assert ct != data  # non-degenerate
        assert P.Nixon_Enc_AES_CTR(ct, key, nonce) == data  # CTR is XOR
        assert P.Nixon_Enc_AES_CTR(data, key, nonce) == ct  # deterministic

    def test_tampered_ciphertext_still_decrypts_malleable(self):
        # CTR has NO integrity: flipping a ciphertext bit flips the same
        # plaintext bit and decryption "succeeds". Documented here as
        # understood; integrity for blobs comes from OUTER layers only —
        # and FINDING F3: no HMAC exists around the Nixon_Enc_* blob layer
        # (build-time file seal pipeline.py:2850, string-table HMAC
        # pipeline.py:249/sources.py:5556, MAGIC-prefix format check
        # sources.py:6269-6273 — none is a MAC over this ciphertext).
        key, nonce = b"K" * 32, b"N" * 16
        data = b"malleability probe payload 0123456789"
        ct = bytearray(P.Nixon_Enc_AES_CTR(data, key, nonce))
        ct[5] ^= 0x01  # single-bit tamper
        tampered_plain = P.Nixon_Enc_AES_CTR(bytes(ct), key, nonce)
        assert tampered_plain != data  # wrong plaintext, silently accepted
        assert tampered_plain[5] == (data[5] ^ 0x01)  # same-bit flip (CTR)
        assert tampered_plain[:5] == data[:5]
        assert tampered_plain[6:] == data[6:]


# ===========================================================================
# 2. Malformed key/nonce handling. FINDING F4: no ValueError contract is
# implemented — lengths are absorbed by sha256 derivation, non-bytes raise
# bare TypeError. These tests pin the ACTUAL defined behavior (no
# traceback-crash beyond a clean exception type, no silent corruption:
# same inputs always roundtrip).
# ===========================================================================
class TestMalformedInputs:
    KEY, NONCE = b"K" * 32, b"N" * 16
    DATA = b"malformed-input probe payload"

    def test_short_key_silently_absorbed_not_rejected(self):
        # FINDING F4: a 1-byte key is accepted (hashed into a full AES key).
        # No ValueError is raised; behavior is deterministic and roundtrips.
        ct = P.Nixon_Enc_AES_CTR(self.DATA, b"K", self.NONCE)
        assert isinstance(ct, bytes) and len(ct) == len(self.DATA)
        assert P.Nixon_Enc_AES_CTR(ct, b"K", self.NONCE) == self.DATA
        assert P.Nixon_Enc_AES_CTR(self.DATA, b"K", self.NONCE) == ct

    def test_long_nonce_silently_absorbed_not_rejected(self):
        # FINDING F4: a 64-byte nonce is accepted (hashed into the 16-byte
        # IV); no ValueError. Distinct nonces still give distinct streams.
        ct = P.Nixon_Enc_AES_CTR(self.DATA, self.KEY, b"N" * 64)
        assert isinstance(ct, bytes) and len(ct) == len(self.DATA)
        assert P.Nixon_Enc_AES_CTR(ct, self.KEY, b"N" * 64) == self.DATA
        assert (P.Nixon_Enc_AES_CTR(self.DATA, self.KEY, b"N" * 64)
                != P.Nixon_Enc_AES_CTR(self.DATA, self.KEY, self.NONCE))

    def test_empty_plaintext_returns_empty(self):
        # Empty input is legitimate for a stream cipher; it yields b"".
        assert P.Nixon_Enc_AES_CTR(b"", self.KEY, self.NONCE) == b""
        assert P.Nixon_Enc_blob(b"", self.KEY, self.NONCE) == b""

    def test_non_bytes_inputs_raise_clean_type_error(self):
        # Not a traceback-crash of the process and not silent: a clean,
        # catchable TypeError (hashlib/bytes require bytes-like). The
        # desired ValueError contract from the task spec is NOT
        # implemented — recorded as FINDING F4.
        with pytest.raises(TypeError):
            P.Nixon_Enc_AES_CTR("str-data", self.KEY, self.NONCE)
        with pytest.raises(TypeError):
            P.Nixon_Enc_AES_CTR(self.DATA, "str-key", self.NONCE)
        with pytest.raises(TypeError):
            P.Nixon_Enc_AES_CTR(self.DATA, self.KEY, None)


# ===========================================================================
# 3. Fallback honesty: selection reporting, loader readability, no AES
# mislabeling of XOR output.
# ===========================================================================
class TestFallbackHonesty:
    def test_selection_reports_boolean(self, aes_cache_reset):
        assert P._check_aes_ctr() in (True, False)
        assert isinstance(P._check_aes_ctr(), bool)

    def test_simulated_no_cryptography_falls_to_pycryptodome(
            self, aes_cache_reset, monkeypatch):
        Crypto = pytest.importorskip("Crypto.Cipher.AES",
                                     reason="needs pycryptodome")
        assert Crypto is not None
        key, nonce = b"K" * 32, b"N" * 16
        data = b"fallback-selection probe " * 6
        expected = P.Nixon_Enc_AES_CTR(data, key, nonce)
        _block_imports(monkeypatch, "cryptography",
                       "cryptography.hazmat",
                       "cryptography.hazmat.primitives",
                       "cryptography.hazmat.primitives.ciphers")
        P._AES_CTR_AVAILABLE = None
        # (a) selection still reports availability (pycryptodome wins) ...
        assert P._check_aes_ctr() is True
        # ... and the same CTR construction is produced (see §4).
        assert P.Nixon_Enc_AES_CTR(data, key, nonce) == expected

    def test_simulated_no_crypto_libs_selects_xor_blob(
            self, aes_cache_reset, monkeypatch):
        _block_imports(monkeypatch, "cryptography",
                       "cryptography.hazmat",
                       "cryptography.hazmat.primitives",
                       "cryptography.hazmat.primitives.ciphers",
                       "Crypto", "Crypto.Cipher", "Crypto.Cipher.AES")
        P._AES_CTR_AVAILABLE = None
        assert P._check_aes_ctr() is False
        key, nonce = b"K" * 32, b"N" * 16
        data = b"pure-xor fallback probe " * 6
        # encrypt_payload routes to Nixon_Enc_blob ...
        assert (P.encrypt_payload(data, key, nonce)
                == P.Nixon_Enc_blob(data, key, nonce))
        # ... and Nixon_Enc_AES_CTR itself degrades to it (no exception).
        assert (P.Nixon_Enc_AES_CTR(data, key, nonce)
                == P.Nixon_Enc_blob(data, key, nonce))

    def test_loader_decrypts_fallback_blob(self):
        # (b) roundtrip through the REAL emitted loader decrypt path
        # (CIPHER_SOURCE template exec'd as the loader executes it).
        key, nonce = b"K" * 32, b"N" * 16
        data = b"loader-compat probe payload \x00\x01\x02" * 16
        blob = P.Nixon_Enc_blob(data, key, nonce)
        assert _loader_cipher_decrypt(blob, key, nonce) == data

    def test_aes_ctr_blob_is_not_loader_readable(self):
        # FINDING F1 (critical, fixed at the call site): AES-CTR ciphertext
        # does NOT decrypt under the loader's NixonCipher (XOR-stream).
        # ``encrypt_payload`` (pipeline.py:415-419) still defaults to AES-CTR
        # for non-artifact uses, so this incompatibility is pinned here —
        # and the legacy ``build_project`` core-blob call site forces
        # ``use_aes_ctr=False`` (see test_legacy_core_blob_forces_xor below).
        key, nonce = b"K" * 32, b"N" * 16
        data = b"aes-loader-mismatch probe payload" * 4
        ct = P.Nixon_Enc_AES_CTR(data, key, nonce)
        assert ct != P.Nixon_Enc_blob(data, key, nonce)  # distinct ciphers
        assert _loader_cipher_decrypt(ct, key, nonce) != data

    def test_legacy_core_blob_forces_xor(self):
        # Regression lock for the F1 fix: the legacy build_project
        # core-blob encryption MUST NOT take the AES branch, because no
        # emitted loader template can invert AES-CTR (loader is stdlib-only).
        import re
        src = open(os.path.join(os.path.dirname(__file__), "..",
                                "obfuscator", "core", "pipeline.py")).read()
        m = re.search(r"core_blob\s*=\s*lzma\.compress\(encrypt_payload\((.*?)\)\)",
                      src)
        assert m, "legacy core_blob call site moved — relocate this lock"
        assert "use_aes_ctr=False" in m.group(1), (
            "legacy core blob must force XOR-stream (loader has no AES inverse)")

    def test_hybrid_xor_loader_path_roundtrips(self):
        # The hybrid FALLBACK_BLOB path uses repeating-key XOR on both
        # sides: build-time fast_xor_bytes (utils.py:276, applied at
        # pipeline.py:1851-1852) and loader _xor_decrypt
        # (pipeline.py:1543-1545, applied at :1669 and :1777).
        key = hashlib.sha256(b"build-id-salt").digest()
        data = b"hybrid xor path probe " * 32
        assert fast_xor_bytes(fast_xor_bytes(data, key), key) == data
        # byte-level equivalence with the loader's 3-line _xor_decrypt:
        loader_xor = bytes([b ^ key[i % len(key)] for i, b in enumerate(
            fast_xor_bytes(data, key))])
        assert loader_xor == data

    def test_emitted_decrypt_templates_make_no_aes_claim(self):
        # (c) no "AES" string inside the actual decrypt code templates.
        assert "AES" not in CIPHER_SOURCE
        assert "aes" not in CIPHER_SOURCE.replace("release", "")
        hybrid_src = inspect.getsource(P.generate_hybrid_loader_script)
        assert "AES" not in hybrid_src

    def test_cipher_cls_source_label_is_honest(self):
        # FINDING F2 (fixed): the XOR-stream cipher class was canonically
        # labeled "AES_GCM" (_VARS_MAP, sources.py:830), presenting XOR-stream
        # output as AES-GCM to auditors. Renamed to "XOR_STREAM".
        # Emitted identifiers are randomized (utils.py:281
        # get_random_var_name), so built artifacts never carried the literal
        # string either way — but the source-level name is now honest.
        assert _VARS_MAP["CIPHER_CLS"] == "XOR_STREAM"
        assert "AES" not in CIPHER_SOURCE  # ...while the code itself is XOR


# ===========================================================================
# 4. Cross-implementation: cryptography vs pycryptodome.
# ===========================================================================
class TestCrossImplementation:
    VECTORS = [
        (b"K" * 32, b"N" * 16, b"short"),
        (b"K" * 32, b"N" * 16, b"x" * 16),      # exactly one block
        (b"K" * 32, b"N" * 16, b"y" * 100),     # multi-block + partial
        (b"\x00" * 32, b"\xff" * 16, b"zeros-key probe" * 10),
        (b"K" * 32, b"N" * 16, b""),
    ]

    def _without_cryptography(self, monkeypatch):
        _block_imports(monkeypatch, "cryptography",
                       "cryptography.hazmat",
                       "cryptography.hazmat.primitives",
                       "cryptography.hazmat.primitives.ciphers")
        P._AES_CTR_AVAILABLE = None

    def test_pycryptodome_matches_cryptography(self, monkeypatch):
        pytest.importorskip("Crypto.Cipher.AES")
        for key, nonce, data in self.VECTORS:
            P._AES_CTR_AVAILABLE = None
            expected = P.Nixon_Enc_AES_CTR(data, key, nonce)
            self._without_cryptography(monkeypatch)
            assert P._check_aes_ctr() is True  # pycryptodome still wins
            got = P.Nixon_Enc_AES_CTR(data, key, nonce)
            assert got == expected, (key, nonce, data)
            P._AES_CTR_AVAILABLE = None  # avoid leaking blocked state

    def test_each_backend_self_roundtrips(self, monkeypatch):
        pytest.importorskip("Crypto.Cipher.AES")
        key, nonce, data = b"K" * 32, b"N" * 16, b"self-roundtrip " * 9
        P._AES_CTR_AVAILABLE = None
        ct = P.Nixon_Enc_AES_CTR(data, key, nonce)
        assert P.Nixon_Enc_AES_CTR(ct, key, nonce) == data
        self._without_cryptography(monkeypatch)
        ct2 = P.Nixon_Enc_AES_CTR(data, key, nonce)
        assert P.Nixon_Enc_AES_CTR(ct2, key, nonce) == data
        P._AES_CTR_AVAILABLE = None


# ===========================================================================
# 5. Version pinning: installed ``cryptography`` meets the declared floor
# and exposes the APIs the wrapper relies on.
# ===========================================================================
class TestVersionPinning:
    def test_installed_cryptography_meets_declared_floor(self):
        crypto = pytest.importorskip("cryptography",
                                     reason="needs cryptography")
        import re
        from pathlib import Path
        req = (Path(P.__file__).resolve().parent.parent.parent
               / "requirements.txt").read_text()
        m = re.search(r"^cryptography([=<>!~]+)([\d.]+)", req, re.M)
        assert m, "cryptography pin missing from requirements.txt"
        floor = tuple(int(x) for x in m.group(2).split("."))
        installed = tuple(int(x) for x in
                          crypto.__version__.split(".")[:len(floor)])
        assert installed >= floor, (crypto.__version__, m.group(0))

    def test_required_cipher_apis_importable(self):
        pytest.importorskip("cryptography", reason="needs cryptography")
        from cryptography.hazmat.primitives.ciphers import (  # noqa: F401
            Cipher, algorithms, modes)
        assert hasattr(algorithms, "AES") and hasattr(modes, "CTR")

    def test_pycryptodome_api_present_if_installed(self):
        mod = pytest.importorskip("Crypto.Cipher.AES",
                                  reason="pycryptodome optional")
        assert hasattr(mod, "new") and hasattr(mod, "MODE_CTR")
