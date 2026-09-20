"""Shared AES-256-CTR test vectors for all implementations."""
import pytest

# NIST AES-256 Known Answer Test vectors
KEY_256 = bytes.fromhex("603deb1015ca71be2b73aef0857d77811f352c073b6108d72d9810a30914dff4")
PLAINTEXT_256 = bytes.fromhex("6bc1bee22e409f96e93d7e117393172a")
CIPHERTEXT_256 = bytes.fromhex("f3eed1bdb5d2a03c064b5a7e3db181f8")
NONCE = bytes.fromhex("0000000000000000")


def test_python_aes_kat():
    from encrypt.aes import aes256_encrypt_block
    result = aes256_encrypt_block(PLAINTEXT_256, KEY_256)
    assert result == CIPHERTEXT_256, f"Python AES KAT mismatch"


def test_python_aes_ctr_roundtrip():
    from encrypt.aes import aes256_ctr_keystream
    pt = b"Hello, World! This is a test of AES-256-CTR."
    key = KEY_256
    ks = aes256_ctr_keystream(key, NONCE, len(pt))
    ct = bytes(p ^ k for p, k in zip(pt, ks))
    ks2 = aes256_ctr_keystream(key, NONCE, len(pt))
    pt2 = bytes(c ^ k for c, k in zip(ct, ks2))
    assert pt == pt2, "AES-256-CTR round-trip failed"


def test_python_derive_block_key():
    from encrypt.aes import derive_block_key
    k = derive_block_key(KEY_256, 0, 16)
    assert len(k) == 32
    assert k != b"\x00" * 32


def test_aes_deterministic():
    from encrypt.aes import aes256_encrypt_block
    r1 = aes256_encrypt_block(PLAINTEXT_256, KEY_256)
    r2 = aes256_encrypt_block(PLAINTEXT_256, KEY_256)
    assert r1 == r2, "AES must be deterministic with same key/plaintext"
