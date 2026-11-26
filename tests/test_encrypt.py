import os
import platform
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from encrypt.aes import (
    aes256_ctr_encrypt, aes256_ctr_decrypt, generate_encryption_seed,
    derive_block_key, expand_key_to_keystream,
)
from encrypt.elf import ELFParser
from encrypt.stub import make_stub_xor_decrypt, make_stub_with_keystream, stub_size
from encrypt.container import container_info, pack_bytes, unpack_bytes
from encrypt.encrypt import encrypt_binary, encrypt_binary_per_block, _split_blocks


class TestAES:
    """
    TestAES
    
    Positive test cases for aes.
    """
    def test_roundtrip(self):
        key = generate_encryption_seed()
        nonce = key[:8]
        plaintext = b"Hello Nixon AES!" * 20
        ct = aes256_ctr_encrypt(plaintext, key, nonce)
        pt2 = aes256_ctr_decrypt(ct, key, nonce)
        assert plaintext == pt2

    def test_different_keys_different_ciphertext(self):
        pt = b"A" * 64
        key1 = generate_encryption_seed()
        key2 = generate_encryption_seed()
        nonce = b"\x00" * 8
        ct1 = aes256_ctr_encrypt(pt, key1, nonce)
        ct2 = aes256_ctr_encrypt(pt, key2, nonce)
        assert ct1 != ct2

    def test_block_key_derivation(self):
        seed = generate_encryption_seed()
        k0 = derive_block_key(seed, 0, 64)
        k1 = derive_block_key(seed, 1, 64)
        assert len(k0) == 32
        assert len(k1) == 32
        assert k0 != k1

    def test_keystream_expansion(self):
        key = generate_encryption_seed()
        ks = expand_key_to_keystream(key, 128)
        assert len(ks) == 128


class TestELF:
    """
    TestELF
    
    Positive test cases for elf.
    """
    @pytest.fixture
    def sample_elf(self):
        path = os.path.join(os.path.dirname(__file__), "..", "build", "orbital-relay")
        if not os.path.isfile(path):
            pytest.skip("orbital-relay binary not found")
        with open(path, "rb") as f:
            return f.read()

    def test_parse_header(self, sample_elf):
        elf = ELFParser(sample_elf)
        assert elf.is_64
        assert elf.e_type == 3

    def test_find_text_section(self, sample_elf):
        elf = ELFParser(sample_elf)
        idx, sec = elf.get_text_section()
        assert sec["size"] > 0
        assert sec["flags"] & 0x4

    def test_section_data(self, sample_elf):
        elf = ELFParser(sample_elf)
        idx, sec = elf.get_text_section()
        data = elf.section_data(sec)
        assert len(data) == sec["size"]
        assert len(data) > 100

    def test_entry_offset(self, sample_elf):
        elf = ELFParser(sample_elf)
        off = elf.get_entry_offset_in_text()
        assert off >= 0

    def test_split_blocks(self):
        data = b"X" * 200
        blocks = _split_blocks(data, 64)
        assert len(blocks) == 4
        assert len(blocks[0]) == 64
        assert len(blocks[1]) == 64
        assert len(blocks[2]) == 64
        assert len(blocks[3]) == 8

    def test_replace_text(self, sample_elf):
        elf = ELFParser(sample_elf)
        idx, sec = elf.get_text_section()
        old_size = sec["size"]
        elf.section_data(sec)

        new_data = b"\x90" * old_size
        elf.replace_text(new_data, add_stub_size=0)
        assert elf.section_data(sec) == new_data


class TestStub:
    """
    TestStub
    
    Positive test cases for stub.
    """
    def test_stub_generation(self):
        stub = make_stub_xor_decrypt(text_size=64, original_entry=0,
                                     keystream=b"\x00" * 64)
        assert len(stub) == stub_size(64)

    def test_stub_requires_keystream(self):
        with pytest.raises(ValueError, match="keystream"):
            make_stub_xor_decrypt(text_size=64, original_entry=0)

    def test_stub_with_keystream(self):
        ks = b"\xAB" * 128
        stub = make_stub_with_keystream(text_size=128, original_entry=16, keystream=ks)
        assert len(stub) == stub_size(128)

    def test_stub_size_calculation(self):
        assert stub_size(64) == stub_size(64)
        assert stub_size(128) - stub_size(64) == 64


class TestContainer:
    """
    TestContainer
    
    Positive test cases for container.
    """
    def test_roundtrip(self):
        key = generate_encryption_seed()
        plaintext = b"Test container payload data " * 50
        container = pack_bytes(plaintext, key)
        result = unpack_bytes(container, key)
        assert plaintext == result

    def test_integrity_check(self):
        key = generate_encryption_seed()
        plaintext = b"Integrity test data"
        container = bytearray(pack_bytes(plaintext, key))
        container[-1] ^= 0xFF
        with pytest.raises(ValueError, match="Integrity"):
            unpack_bytes(bytes(container), key)

    def test_container_info(self):
        key = generate_encryption_seed()
        container = pack_bytes(b"Hello", key)
        info = container_info(container)
        assert info["magic"] == "0x4e4958"
        assert info["version"] == 3  # v3: random nonce + keyed HMAC, legacy refused
        assert info["original_size"] == 5

    def test_same_plaintext_same_key_gives_different_ciphertext(self):
        """v3 regression: the nonce is random, not derived from the plaintext,
        so encrypting the same plaintext twice must not yield equal containers."""
        key = generate_encryption_seed()
        plaintext = b"repeatable secret" * 10
        c1 = pack_bytes(plaintext, key)
        c2 = pack_bytes(plaintext, key)
        assert c1 != c2
        assert unpack_bytes(c1, key) == plaintext
        assert unpack_bytes(c2, key) == plaintext

    def test_legacy_v1_container_is_rejected(self):
        """v1 containers have no keyed integrity check and must not be read."""
        import hashlib as _hl
        import struct as _st
        from encrypt import aes as _aes
        key = generate_encryption_seed()
        plaintext = b"legacy payload"
        sha = _hl.sha256(plaintext).digest()
        nonce = sha[:8]
        enc = _aes.aes256_ctr_encrypt(plaintext, key, nonce)
        v1 = _st.pack('<IIII', 0x4E4958, 1, len(plaintext), len(enc)) + sha + enc
        with pytest.raises(ValueError, match="legacy NIX v1"):
            unpack_bytes(v1, key)

    def test_tampered_ciphertext_fails_hmac_before_decrypt(self):
        key = generate_encryption_seed()
        plaintext = b"mac me"
        container = bytearray(pack_bytes(plaintext, key))
        container[-1] ^= 0xFF
        with pytest.raises(ValueError, match="HMAC"):
            unpack_bytes(bytes(container), key)

    def test_bad_magic(self):
        key = generate_encryption_seed()
        container = bytearray(pack_bytes(b"test", key))
        container[0:4] = b"\x00\x00\x00\x00"
        with pytest.raises(ValueError, match="magic"):
            unpack_bytes(bytes(container), key)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@pytest.mark.skipif(
    not os.path.isfile(os.path.join(BASE_DIR, "build", "orbital-relay")),
    reason="orbital-relay binary not found",
)
class TestEncryptBinary:
    """
    TestEncryptBinary
    
    Positive test cases for encryptbinary.
    """
    @staticmethod
    def _clean(output):
        # The writer refuses to replace an existing key sidecar (security
        # property), so tests must remove both artefacts from earlier runs.
        for path in (output, output + ".key"):
            if os.path.exists(path):
                os.unlink(path)

    def test_encrypt_bulk_mode(self, tmp_path):
        output = str(tmp_path / "test_enc_bulk")
        self._clean(output)
        try:
            result = encrypt_binary(
                os.path.join(BASE_DIR, "build", "orbital-relay"),
                output,
                block_size=64,
                text_size=4096,
            )
            assert result["num_blocks"] > 0
            assert result["block_size"] == 64
            assert os.path.getsize(output) > 0
        finally:
            self._clean(output)

    def test_encrypt_with_seed(self, tmp_path):
        output = str(tmp_path / "test_enc_seeded")
        self._clean(output)
        try:
            seed = bytes.fromhex("ab" * 32)
            result = encrypt_binary(
                os.path.join(BASE_DIR, "build", "orbital-relay"),
                output,
                seed=seed,
                text_size=4096,
            )
            assert result["seed"] == "ab" * 32
        finally:
            self._clean(output)

    def test_encrypt_per_block(self, tmp_path):
        output = str(tmp_path / "test_enc_pb")
        self._clean(output)
        try:
            result = encrypt_binary_per_block(
                os.path.join(BASE_DIR, "build", "orbital-relay"),
                output,
                block_size=128,
                text_size=4096,
            )
            assert result["num_blocks"] > 0
        finally:
            self._clean(output)


def test_binary_encrypt_decrypt_roundtrip():
    """Encrypt a binary blob and decrypt it back via container, verifying integrity."""
    from encrypt.container import pack_bytes, unpack_bytes

    payload = b"\x01\x02\x03\x04" * 256  # 1KB test payload
    key = b"K" * 32

    container = pack_bytes(payload, key)
    assert len(container) > 0, "Container not created"

    result = unpack_bytes(container, key)
    assert result == payload, "Binary round-trip mismatch"


def test_seed_reproducibility():
    """Same seed must produce identical deterministic transforms."""
    import random
    r1 = random.Random(12345)
    r2 = random.Random(12345)
    r3 = random.Random(99999)
    seq1 = [r1.random() for _ in range(20)]
    seq2 = [r2.random() for _ in range(20)]
    seq3 = [r3.random() for _ in range(20)]
    assert seq1 == seq2, "Same seed Random produced different sequences"
    assert seq1 != seq3, "Different seed Random produced same sequence"


@pytest.mark.skipif(
    not (sys.platform.startswith("linux") and platform.machine() == "x86_64"),
    reason="stub is x86-64 Linux shellcode",
)
def test_stub_executes_and_decrypts():
    """The stub must decrypt its text and jump to the original entry."""
    import ctypes
    import mmap

    text = b"\xb8\x2a\x00\x00\x00\xc3" + b"\x90" * 58  # mov eax,42; ret
    ks = bytes(range(64))
    ct = bytes(a ^ b for a, b in zip(text, ks))
    stub = make_stub_with_keystream(64, 0, ks)
    blob = ct + stub

    mm = mmap.mmap(-1, 4096,
                   prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC)
    mm.write(blob)
    addr = ctypes.addressof(ctypes.c_char.from_buffer(mm))
    fn = ctypes.CFUNCTYPE(ctypes.c_int)(addr + 64)
    assert fn() == 42
    assert bytes(mm[:64]) == text
    mm.close()


@pytest.mark.skipif(
    not (sys.platform.startswith("linux") and platform.machine() == "x86_64"),
    reason="stub is x86-64 Linux shellcode",
)
def test_keyed_stub_executes_and_decrypts(tmp_path):
    """The keyed stub unmasks the keystream from the runtime key file."""
    import ctypes
    import mmap

    text = b"\xb8\x2a\x00\x00\x00\xc3" + b"\x90" * 58
    ks = os.urandom(64)
    key = os.urandom(32)
    masked = bytes(k ^ key[i % 32] for i, k in enumerate(ks))
    key_path = tmp_path / "enc.key"
    key_path.write_bytes(key)

    stub = make_stub_with_keystream(64, 0, masked, key_path=str(key_path))
    ct = bytes(a ^ b for a, b in zip(text, ks))
    blob = ct + stub

    mm = mmap.mmap(-1, 4096,
                   prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC)
    mm.write(blob)
    addr = ctypes.addressof(ctypes.c_char.from_buffer(mm))
    fn = ctypes.CFUNCTYPE(ctypes.c_int)(addr + 64)
    assert fn() == 42
    assert bytes(mm[:64]) == text
    mm.close()


def test_keyed_stub_does_not_embed_the_raw_keystream(tmp_path):
    """The embedded bytes are keystream XOR runtime key, not the keystream."""
    ks = os.urandom(64)
    key = os.urandom(32)
    masked = bytes(k ^ key[i % 32] for i, k in enumerate(ks))
    key_path = tmp_path / "enc.key"
    key_path.write_bytes(key)
    stub = make_stub_with_keystream(64, 0, masked, key_path=str(key_path))
    assert ks not in stub
    assert masked in stub
    assert key not in stub


@pytest.mark.skipif(shutil.which("gcc") is None, reason="gcc not available")
def test_encrypt_binary_runs(tmp_path):
    """A bulk-encrypted ELF must still run and produce the original output."""
    src = tmp_path / "hello.c"
    src.write_text('#include <stdio.h>\n'
                   'int main(void) { puts("encrypted-ok"); return 7; }\n')
    exe = tmp_path / "hello"
    subprocess.run(["gcc", "-O0", "-o", str(exe), str(src)], check=True)
    out = tmp_path / "hello.enc"
    result = encrypt_binary(str(exe), str(out), block_size=64)
    assert os.path.exists(result["key_file"])
    assert os.path.getsize(result["key_file"]) == 32
    assert (os.stat(result["key_file"]).st_mode & 0o777) == 0o600
    assert "runtime key" in result["confidentiality"]
    run = subprocess.run([str(out)], capture_output=True, text=True)
    assert run.returncode == 7
    assert "encrypted-ok" in run.stdout


@pytest.mark.skipif(shutil.which("gcc") is None, reason="gcc not available")
def test_encrypt_binary_fails_closed_without_the_key_file(tmp_path):
    """The runtime key is required; removing it must not decrypt."""
    src = tmp_path / "hello.c"
    src.write_text('int main(void) { return 7; }\n')
    exe = tmp_path / "hello"
    subprocess.run(["gcc", "-O0", "-o", str(exe), str(src)], check=True)
    out = tmp_path / "hello.enc"
    result = encrypt_binary(str(exe), str(out), block_size=64)
    os.unlink(result["key_file"])
    run = subprocess.run([str(out)], capture_output=True, text=True)
    assert run.returncode != 7
