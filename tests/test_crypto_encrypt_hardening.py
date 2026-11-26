"""Regression tests for NIX v3 and ELF encryption hardening."""

import hashlib
import hmac
import os
import shutil
import stat
import struct
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from encrypt import aes, container
from encrypt.elf import ELFParser
from encrypt.encrypt import _write_key_file, encrypt_binary


KEY = bytes(range(32))
NONCE = bytes(range(16))
PLAINTEXT = b"NIX v3 authenticated payload\x00\xff" * 4


def _hkdf_sha256(ikm, salt, info, length):
    """Independent RFC 5869 HKDF-SHA256 reference."""
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    output = b""
    block = b""
    counter = 1
    while len(output) < length:
        block = hmac.new(
            prk, block + info + bytes([counter]), hashlib.sha256
        ).digest()
        output += block
        counter += 1
    return output[:length]


def test_v3_known_answer_uses_hkdf_separated_keys_and_canonical_header(monkeypatch):
    monkeypatch.setattr(container.os, "urandom", lambda size: NONCE)

    packed = container.pack_bytes(PLAINTEXT, KEY)

    header = struct.pack("<IIII", container.NIX_MAGIC, 3, len(PLAINTEXT), len(PLAINTEXT))
    enc_key = _hkdf_sha256(KEY, NONCE, b"NIX-v3-encryption", 32)
    mac_key = _hkdf_sha256(KEY, NONCE, b"NIX-v3-authentication", 32)
    iv = _hkdf_sha256(KEY, NONCE, b"NIX-v3-iv", 16)
    ciphertext = aes.aes256_ctr_encrypt(PLAINTEXT, enc_key, iv[:8])
    tag = hmac.new(mac_key, header + NONCE + ciphertext, hashlib.sha256).digest()

    assert packed == header + NONCE + tag + ciphertext
    assert container.unpack_bytes(packed, KEY) == PLAINTEXT


@pytest.mark.parametrize("offset", [0, 4, 8, 12, 16, 32, len(PLAINTEXT) + 63])
def test_v3_rejects_header_nonce_tag_and_ciphertext_tampering(offset):
    packed = bytearray(container.pack_bytes(PLAINTEXT, KEY))
    packed[offset] ^= 1
    with pytest.raises(ValueError):
        container.unpack_bytes(bytes(packed), KEY)


@pytest.mark.parametrize("version", [0, 1, 2, 4, 0xFFFFFFFF])
def test_v3_version_whitelist_fails_closed(version):
    packed = bytearray(container.pack_bytes(PLAINTEXT, KEY))
    struct.pack_into("<I", packed, 4, version)
    with pytest.raises(ValueError, match="version|legacy"):
        container.unpack_bytes(bytes(packed), KEY)


def _legacy_v2_container():
    encrypted = aes.aes256_ctr_encrypt(PLAINTEXT, KEY, NONCE[:8])
    header = struct.pack("<IIII", container.NIX_MAGIC, 2, len(PLAINTEXT), len(encrypted))
    tag = hmac.new(KEY, NONCE[:8] + encrypted, hashlib.sha256).digest()
    return header + NONCE[:8] + tag + encrypted


def test_legacy_v2_is_rejected_with_migration_message():
    with pytest.raises(ValueError, match="legacy.*v2.*re-encrypt"):
        container.unpack_bytes(_legacy_v2_container(), KEY)


@pytest.mark.parametrize("trim", [1, 8, 16, 32, 64])
def test_v3_rejects_every_truncation_boundary(trim):
    packed = container.pack_bytes(PLAINTEXT, KEY)
    with pytest.raises(ValueError):
        container.unpack_bytes(packed[:-trim], KEY)


def test_v3_rejects_trailing_bytes():
    packed = container.pack_bytes(PLAINTEXT, KEY)
    with pytest.raises(ValueError, match="length|size|trailing"):
        container.unpack_bytes(packed + b"trailing", KEY)


@pytest.mark.parametrize("field_offset", [8, 12])
def test_v3_rejects_inconsistent_sizes(field_offset):
    packed = bytearray(container.pack_bytes(PLAINTEXT, KEY))
    struct.pack_into("<I", packed, field_offset, len(PLAINTEXT) + 1)
    with pytest.raises(ValueError, match="size|length"):
        container.unpack_bytes(bytes(packed), KEY)


def test_v3_uses_a_fresh_128_bit_nonce():
    first = container.pack_bytes(PLAINTEXT, KEY)
    second = container.pack_bytes(PLAINTEXT, KEY)
    assert first[16:32] != second[16:32]
    assert container.container_info(first)["version"] == 3


def test_key_file_creation_is_private_and_exact(tmp_path):
    path = tmp_path / "artifact.key"
    _write_key_file(str(path), KEY)
    assert path.read_bytes() == KEY
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_key_file_refuses_to_follow_a_symlink(tmp_path):
    target = tmp_path / "victim"
    target.write_bytes(b"do not overwrite")
    target.chmod(0o644)
    link = tmp_path / "artifact.key"
    link.symlink_to(target)

    with pytest.raises(OSError):
        _write_key_file(str(link), KEY)

    assert target.read_bytes() == b"do not overwrite"
    assert stat.S_IMODE(target.stat().st_mode) == 0o644
    assert link.is_symlink()


def test_key_file_refuses_existing_0644_file_without_changing_it(tmp_path):
    path = tmp_path / "artifact.key"
    path.write_bytes(b"existing")
    path.chmod(0o644)

    with pytest.raises(FileExistsError):
        _write_key_file(str(path), KEY)

    assert path.read_bytes() == b"existing"
    assert stat.S_IMODE(path.stat().st_mode) == 0o644


@pytest.mark.skipif(shutil.which("gcc") is None, reason="gcc not available")
def test_same_reproducibility_seed_and_key_do_not_reuse_artifact_keystream(
    tmp_path, monkeypatch
):
    source = tmp_path / "hello.c"
    source.write_text('int main(void) { return 7; }\n')
    binary = tmp_path / "hello"
    subprocess.run(["gcc", "-O0", "-o", str(binary), str(source)], check=True)
    monkeypatch.setenv("NIXON_ENC_RUNTIME_KEY", KEY.hex())
    seed = b"s" * 32

    first_path = tmp_path / "first.enc"
    second_path = tmp_path / "second.enc"
    first = encrypt_binary(str(binary), str(first_path), seed=seed, block_size=64)
    second = encrypt_binary(str(binary), str(second_path), seed=seed, block_size=64)

    first_text = ELFParser(first_path.read_bytes()).section_data(
        ELFParser(first_path.read_bytes()).get_text_section()[1]
    )
    second_text = ELFParser(second_path.read_bytes()).section_data(
        ELFParser(second_path.read_bytes()).get_text_section()[1]
    )
    assert first_text != second_text
    assert first["seed"] == second["seed"] == seed.hex()
