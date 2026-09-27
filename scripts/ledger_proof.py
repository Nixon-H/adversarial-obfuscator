#!/usr/bin/env python3
"""Ledger Integrity Proof Generator for Shadow Compiler."""
# TWIN: runtime/src/ledger.rs (in-artifact append-only event ledger) — that
# ledger records runtime events inside the protected binary; this script
# generates offline integrity proofs over built artifacts. Do not merge.

import os
import struct
import hashlib
import time
import secrets


def read_elf_text_section(binary_path: str):
    """Read .text section data and program headers from an ELF binary."""
    with open(binary_path, 'rb') as f:
        data = f.read()
    if data[:4] != b'\x7fELF':
        raise ValueError("Not an ELF file")
    is_64 = data[4] == 2
    if is_64:
        e_phoff = struct.unpack_from('<Q', data, 32)[0]
        e_phentsize = struct.unpack_from('<H', data, 54)[0]
        e_phnum = struct.unpack_from('<H', data, 56)[0]
        e_shoff = struct.unpack_from('<Q', data, 40)[0]
        e_shentsize = struct.unpack_from('<H', data, 58)[0]
        e_shnum = struct.unpack_from('<H', data, 60)[0]
        e_shstrndx = struct.unpack_from('<H', data, 62)[0]
    else:
        e_phoff = struct.unpack_from('<I', data, 28)[0]
        e_phentsize = struct.unpack_from('<H', data, 42)[0]
        e_phnum = struct.unpack_from('<H', data, 44)[0]
        e_shoff = struct.unpack_from('<I', data, 32)[0]
        e_shentsize = struct.unpack_from('<H', data, 46)[0]
        e_shnum = struct.unpack_from('<H', data, 48)[0]
        e_shstrndx = struct.unpack_from('<H', data, 50)[0]

    segments = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        if is_64:
            p_type = struct.unpack_from('<I', data, off)[0]
            p_flags = struct.unpack_from('<I', data, off + 4)[0]
            p_offset = struct.unpack_from('<Q', data, off + 8)[0]
            p_vaddr = struct.unpack_from('<Q', data, off + 16)[0]
            p_filesz = struct.unpack_from('<Q', data, off + 32)[0]
            p_memsz = struct.unpack_from('<Q', data, off + 40)[0]
        else:
            p_type = struct.unpack_from('<I', data, off)[0]
            p_offset = struct.unpack_from('<I', data, off + 4)[0]
            p_vaddr = struct.unpack_from('<I', data, off + 8)[0]
            p_filesz = struct.unpack_from('<I', data, off + 16)[0]
            p_memsz = struct.unpack_from('<I', data, off + 20)[0]
            p_flags = struct.unpack_from('<I', data, off + 24)[0]
        segments.append({
            'type': p_type, 'flags': p_flags,
            'vaddr': p_vaddr, 'memsz': p_memsz, 'filesz': p_filesz,
        })

    strtab_off = e_shoff + e_shstrndx * e_shentsize
    if is_64:
        strtab_sh_off = struct.unpack_from('<Q', data, strtab_off + 24)[0]
        strtab_size = struct.unpack_from('<Q', data, strtab_off + 32)[0]
    else:
        strtab_sh_off = struct.unpack_from('<I', data, strtab_off + 16)[0]
        strtab_size = struct.unpack_from('<I', data, strtab_off + 20)[0]
    strtab = data[strtab_sh_off:strtab_sh_off + strtab_size]

    text_data = None
    for i in range(e_shnum):
        sh_off = e_shoff + i * e_shentsize
        sh_name = struct.unpack_from('<I', data, sh_off)[0]
        if is_64:
            sh_offset = struct.unpack_from('<Q', data, sh_off + 24)[0]
            sh_size = struct.unpack_from('<Q', data, sh_off + 32)[0]
        else:
            sh_offset = struct.unpack_from('<I', data, sh_off + 16)[0]
            sh_size = struct.unpack_from('<I', data, sh_off + 20)[0]
        name_end = strtab.index(b'\x00', sh_name)
        name = strtab[sh_name:name_end].decode('ascii', errors='replace')
        if name == '.text':
            text_data = data[sh_offset:sh_offset + sh_size]
            break

    if text_data is None:
        raise ValueError("Could not find .text section")
    return text_data, segments


def compute_merkle_root(data: bytes, block_size: int = 64) -> bytes:
    """Compute Merkle tree root over blocks of data."""
    if not data:
        return hashlib.sha256(b'').digest()
    blocks = [data[i:i + block_size] for i in range(0, len(data), block_size)]
    hashes = [hashlib.sha256(block).digest() for block in blocks]
    while len(hashes) > 1:
        next_level = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + (hashes[i + 1] if i + 1 < len(hashes) else hashes[i])
            next_level.append(hashlib.sha256(combined).digest())
        hashes = next_level
    return hashes[0]


def compute_memory_layout_fingerprint(segments: list) -> bytes:
    """Compute SHA256 of PT_LOAD segment layout (vaddr, memsz, flags)."""
    layout = b''
    for seg in segments:
        if seg['type'] == 1:
            layout += struct.pack('<QQI', seg['vaddr'], seg['memsz'], seg['flags'])
    return hashlib.sha256(layout).digest()


def compute_text_proof(binary_path: str) -> dict:
    """Compute a full integrity proof for the binary's .text section."""
    text_data, segments = read_elf_text_section(binary_path)
    return {
        'text_hash': hashlib.sha256(text_data).digest(),
        'merkle_root': compute_merkle_root(text_data),
        'memory_layout_hash': compute_memory_layout_fingerprint(segments),
        'timestamp': int(time.time()),
        'nonce': secrets.token_bytes(16),
        'text_section': text_data,
    }


def generate_proof_payload(proof: dict, build_seed: bytes) -> bytes:
    """Serialize the proof into a compact binary payload for embedding."""
    payload = b''
    payload += struct.pack('<II', 0x4C454447, 1)
    payload += proof['text_hash']
    payload += proof['merkle_root']
    payload += proof['memory_layout_hash']
    payload += struct.pack('<Q', proof['timestamp'])
    payload += proof['nonce']
    binding = hashlib.sha256(proof['text_hash'] + proof['merkle_root'] + build_seed).digest()
    payload += binding[:16]
    return payload


def generate_ledger_proof(binary_path: str, output_dir: str, build_seed: bytes | None = None) -> bytes:
    """Generate a ledger integrity proof from an ELF binary and write it to output_dir."""
    proof = compute_text_proof(binary_path)
    if build_seed is None:
        build_seed = secrets.token_bytes(32)
    payload = generate_proof_payload(proof, build_seed)
    os.makedirs(output_dir, exist_ok=True)
    proof_path = os.path.join(output_dir, "ledger_proof.bin")
    with open(proof_path, "wb") as f:
        f.write(payload)
    return payload
