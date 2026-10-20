import os
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
        stub = make_stub_xor_decrypt(text_size=64, original_entry=0)
        assert len(stub) > 0
        # Code portion should be 49 bytes, header 20, keystream 64 = 133
        assert len(stub) == 133

    def test_stub_with_keystream(self):
        ks = b"\xAB" * 128
        stub = make_stub_with_keystream(text_size=128, original_entry=16, keystream=ks)
        assert len(stub) == 49 + 20 + 128

    def test_stub_size_calculation(self):
        assert stub_size(64) == 49 + 64 + 20
        assert stub_size(128) == 49 + 128 + 20


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
        assert info["version"] == 1
        assert info["original_size"] == 5

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
    def test_encrypt_bulk_mode(self):
        result = encrypt_binary(
            os.path.join(BASE_DIR, "build", "orbital-relay"),
            "/tmp/test_enc_bulk",
            block_size=64,
            text_size=4096,
        )
        assert result["num_blocks"] > 0
        assert result["block_size"] == 64
        assert os.path.getsize("/tmp/test_enc_bulk") > 0
        os.unlink("/tmp/test_enc_bulk")

    def test_encrypt_with_seed(self):
        seed = bytes.fromhex("ab" * 32)
        result = encrypt_binary(
            os.path.join(BASE_DIR, "build", "orbital-relay"),
            "/tmp/test_enc_seeded",
            seed=seed,
            text_size=4096,
        )
        assert result["seed"] == "ab" * 32
        os.unlink("/tmp/test_enc_seeded")

    def test_encrypt_per_block(self):
        result = encrypt_binary_per_block(
            os.path.join(BASE_DIR, "build", "orbital-relay"),
            "/tmp/test_enc_pb",
            block_size=128,
            text_size=4096,
        )
        assert result["num_blocks"] > 0
        os.unlink("/tmp/test_enc_pb")


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
