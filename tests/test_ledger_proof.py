import os
import struct
import tempfile
import hashlib

from scripts.ledger_proof import (
    read_elf_text_section,
    compute_merkle_root,
    compute_memory_layout_fingerprint,
    generate_proof_payload,
    generate_ledger_proof,
)


def _make_elf64_with_text(text_data: bytes) -> str:
    """Build a minimal ELF64 binary with a .text section containing text_data."""
    elf_hdr_size = 64
    phdr_size = 56
    shdr_size = 64
    num_phdr = 1
    num_shdr = 3

    text_offset = elf_hdr_size + phdr_size * num_phdr + shdr_size * num_shdr
    shstrtab_data = b"\x00.shstrtab\x00.text\x00"
    shstrtab_offset = text_offset + len(text_data)

    e_ident = b"\x7fELF" + b"\x02\x01\x01\x00" + b"\x00" * 8
    e_type = 0x0002
    e_machine = 0x003E
    e_version = 0x00000001
    e_entry = 0x0000000000400000
    e_phoff = elf_hdr_size
    e_shoff = elf_hdr_size + phdr_size
    e_flags = 0
    e_ehsize = elf_hdr_size
    e_phentsize = phdr_size
    e_phnum = num_phdr
    e_shentsize = shdr_size
    e_shnum = num_shdr
    e_shstrndx = 2

    header = struct.pack(
        "<16sHHIQQQIHHHHHH",
        e_ident, e_type, e_machine, e_version, e_entry, e_phoff,
        e_shoff, e_flags, e_ehsize, e_phentsize, e_phnum,
        e_shentsize, e_shnum, e_shstrndx,
    )

    ph_type = 1
    ph_flags = 5
    ph_offset = text_offset
    ph_vaddr = 0x0000000000400000
    ph_paddr = 0x0000000000400000
    ph_filesz = len(text_data)
    ph_memsz = len(text_data)
    ph_align = 0x1000

    prog_header = struct.pack(
        "<IIQQQQQQ",
        ph_type, ph_flags, ph_offset, ph_vaddr, ph_paddr,
        ph_filesz, ph_memsz, ph_align,
    )

    sh_null = struct.pack("<IIQQQQIIQQ", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    sh_name_text = 11
    sh_text = struct.pack(
        "<IIQQQQIIQQ",
        sh_name_text, 1, 6, 0x0000000000400000,
        text_offset, len(text_data), 0, 0, 1, 0,
    )

    sh_name_strtab = 1
    sh_strtab = struct.pack(
        "<IIQQQQIIQQ",
        sh_name_strtab, 3, 0, 0,
        shstrtab_offset, len(shstrtab_data), 0, 0, 1, 0,
    )

    fd, path = tempfile.mkstemp(suffix=".elf", prefix="test_ledger_")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(header)
        f.write(prog_header)
        f.write(sh_null)
        f.write(sh_text)
        f.write(sh_strtab)
        f.write(text_data)
        f.write(shstrtab_data)
    return path


def test_elf_header_parsing():
    text_content = b"\x48\x31\xc0\x48\xff\xc0\xc3"
    path = _make_elf64_with_text(text_content)
    try:
        text_data, segments = read_elf_text_section(path)
        assert text_data == text_content, f"Expected {text_content!r}, got {text_data!r}"
        assert len(segments) == 1
        assert segments[0]["type"] == 1
        assert segments[0]["vaddr"] == 0x0000000000400000
        assert segments[0]["filesz"] == len(text_content)
        assert segments[0]["memsz"] == len(text_content)
    finally:
        os.unlink(path)


def test_sha256_hashing():
    data = b"hello world"
    expected = hashlib.sha256(data).digest()
    result = compute_merkle_root(data, block_size=64)
    assert result == expected, "Single-block merkle root should equal SHA256 of data"


def test_merkle_root_multi_block():
    data = b"A" * 128
    root = compute_merkle_root(data, block_size=64)
    block1 = hashlib.sha256(b"A" * 64).digest()
    block2 = hashlib.sha256(b"A" * 64).digest()
    expected = hashlib.sha256(block1 + block2).digest()
    assert root == expected, f"Expected {expected!r}, got {root!r}"


def test_merkle_root_empty():
    result = compute_merkle_root(b"", block_size=64)
    assert result == hashlib.sha256(b"").digest()


def test_memory_layout_fingerprint():
    segments = [
        {"type": 1, "vaddr": 0x400000, "memsz": 100, "flags": 5},
        {"type": 1, "vaddr": 0x500000, "memsz": 200, "flags": 7},
        {"type": 2, "vaddr": 0, "memsz": 0, "flags": 0},  # non-PT_LOAD, ignored
    ]
    fp = compute_memory_layout_fingerprint(segments)
    expected = hashlib.sha256(
        struct.pack('<QQI', 0x400000, 100, 5)
        + struct.pack('<QQI', 0x500000, 200, 7)
    ).digest()
    assert fp == expected


def test_proof_payload_serialization_roundtrip():
    proof = {
        "text_hash": b"\x01" * 32,
        "merkle_root": b"\x02" * 32,
        "memory_layout_hash": b"\x03" * 32,
        "timestamp": 1234567890,
        "nonce": b"\x04" * 16,
        "text_section": b"test",
    }
    build_seed = b"\x05" * 32
    payload = generate_proof_payload(proof, build_seed)

    assert len(payload) >= 8
    magic, version = struct.unpack_from("<II", payload, 0)
    assert magic == 0x4C454447
    assert version == 1

    text_hash = payload[8:40]
    merkle_root = payload[40:72]
    mem_layout_hash = payload[72:104]
    timestamp = struct.unpack_from("<Q", payload, 104)[0]
    nonce = payload[112:128]
    binding = payload[128:144]

    assert text_hash == proof["text_hash"]
    assert merkle_root == proof["merkle_root"]
    assert mem_layout_hash == proof["memory_layout_hash"]
    assert timestamp == proof["timestamp"]
    assert nonce == proof["nonce"]
    expected_binding = hashlib.sha256(
        proof["text_hash"] + proof["merkle_root"] + build_seed
    ).digest()[:16]
    assert binding == expected_binding


def test_generate_ledger_proof_writes_file():
    text_content = b"\x48\x31\xc0\xc3"
    path = _make_elf64_with_text(text_content)
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = generate_ledger_proof(path, tmpdir)
            proof_file = os.path.join(tmpdir, "ledger_proof.bin")
            assert os.path.exists(proof_file)
            with open(proof_file, "rb") as f:
                written = f.read()
            assert written == payload
            magic, version = struct.unpack_from("<II", payload, 0)
            assert magic == 0x4C454447
            assert version == 1
    finally:
        os.unlink(path)
