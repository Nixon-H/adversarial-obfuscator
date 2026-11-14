"""Binary encryption pipeline — Stage 4.

Obfuscates compiled ELF binaries block-by-block using AES-256-CTR. Supports
two modes: bulk (single stub, safe for linked executables) and per-block
(individual stubs, for relocatable objects). Embeds decryption metadata
in a `.shadorenc` ELF section.

Confidentiality note: the keystream embedded in the stub is XOR-masked with
a 32-byte runtime key written to a 0600 sidecar (`<output>.key`).  The stub
reads that file at startup and exits(1) if it is missing, so the artifact
alone does not decrypt.  The sidecar must be distributed with the artifact.

Public API:
    - encrypt_binary(input_path, output_path, seed, block_size, ...) -> dict
    - encrypt_binary_per_block(input_path, output_path, seed, block_size, ...) -> dict

Dependencies:
    - encrypt.aes, encrypt.elf, encrypt.stub
"""

import os
import struct
import hashlib

from . import aes
from . import elf as elfmod
from . import stub as stubmod


def encrypt_binary(input_path: str, output_path: str,
                   seed: bytes | None = None,
                   block_size: int = 64,
                   bulk_mode: bool = True,
                   text_size: int | None = None,
                   degradation_config: dict | None = None,
                   enable_exec_guard: bool = False,
                   enable_microjit: bool = False) -> dict:
    """
    Encrypt blocks in the compiled binary.

    In bulk mode (default), the entire .text section is split into blocks,
    each block encrypted with AES-256-CTR (per-block key derived from seed + index),
    and a single decryptor stub is appended to .text.
    The ELF entry point is redirected to the stub.

    Args:
        input_path: Path to the compiled ELF binary.
        output_path: Path to write the encrypted binary.
        seed: 32-byte seed for key derivation. Auto-generated if None.
        block_size: Block size in bytes (default 64).
        bulk_mode: If True, use single-stub bulk decrypt (safe for linked binaries).
        text_size: If set, only encrypt the first text_size bytes of .text.
        degradation_config: Optional dict specifying degradation trigger parameters.
        enable_microjit: If True, embed JIT seed in metadata for polymorphic reassembly.

    Returns:
        dict: {num_blocks, block_size, seed (hex), entry_point_info}
    """
    if seed is None:
        seed = aes.generate_encryption_seed()
    if len(seed) != 32:
        raise ValueError("Seed must be 32 bytes (256 bits)")

    with open(input_path, 'rb') as f:
        data = f.read()

    elf = elfmod.ELFParser(data)
    idx, text_sec = elf.get_text_section()
    text_data = elf.section_data(text_sec)
    if text_size is not None:
        text_data = text_data[:text_size]
        text_sec['size'] = len(text_data)
        elf._set_shdr_field(idx, 'size', len(text_data))
    text_addr = text_sec['addr']
    text_size = len(text_data)

    entry_offset_in_text = elf.get_entry_offset_in_text()

    blocks = _split_blocks(text_data, block_size)
    num_blocks = len(blocks)

    encrypted_blocks = []
    all_keystream = b''
    for i, blk in enumerate(blocks):
        blk_key = aes.derive_block_key(seed, i, len(blk))
        nonce = hashlib.sha256(blk_key).digest()[:8]
        keystream = aes.aes256_ctr_keystream(blk_key, nonce, len(blk))
        encrypted = bytes(p ^ k for p, k in zip(blk, keystream))
        encrypted_blocks.append(encrypted)
        all_keystream += keystream

    encrypted_text = b''.join(encrypted_blocks)

    # Runtime key source: the embedded keystream is XOR-masked with a key
    # that lives in a sidecar file, not in the binary.  Without the file the
    # stub exits(1); ciphertext XOR the embedded bytes is not the plaintext.
    runtime_key_path = os.path.abspath(output_path) + ".key"
    env_key = os.environ.get("NIXON_ENC_RUNTIME_KEY", "").strip()
    if env_key:
        try:
            runtime_key = bytes.fromhex(env_key)
        except ValueError as exc:
            raise ValueError("NIXON_ENC_RUNTIME_KEY must be hex") from exc
        if len(runtime_key) != 32:
            raise ValueError("NIXON_ENC_RUNTIME_KEY must be 32 bytes")
    else:
        runtime_key = os.urandom(32)
    masked_keystream = bytes(
        k ^ runtime_key[i % 32] for i, k in enumerate(all_keystream))

    # The stub lives in its own executable PT_LOAD segment appended at EOF.
    # Keeping it out of .text means no existing vaddr moves, so DT_FINI,
    # DT_INIT_ARRAY and relocations stay valid.
    key_path_len = len(runtime_key_path.encode("utf-8")) + 1
    stub_len = stubmod.stub_size(text_size, key_path_len=key_path_len)
    plan = elf.plan_load_segment(stub_len)
    stub_vaddr = plan['vaddr'] + plan['table_size']
    stub = stubmod.make_stub_with_keystream(
        text_size=text_size,
        original_entry=entry_offset_in_text,
        keystream=masked_keystream,
        text_base_delta=text_addr - (stub_vaddr + 6),
        key_path=runtime_key_path,
    )

    elf.replace_text(encrypted_text, add_stub_size=0)
    new_entry = elf.add_load_segment(stub, plan)
    elf.set_entry_point(new_entry)

    _write_key_file(runtime_key_path, runtime_key)

    if enable_microjit:
        microjit_seed = int.from_bytes(os.urandom(4), 'little')
        if degradation_config:
            degradation_config['microjit_seed'] = microjit_seed
        else:
            degradation_config = {'microjit_seed': microjit_seed}

    metadata = _build_shadorenc_metadata(block_size, num_blocks,
                                         text_size, entry_offset_in_text,
                                         len(stub), degradation_config,
                                         enable_exec_guard)
    elf.add_shadorenc_section(metadata)
    elf.save(output_path, mode=_source_mode(input_path))

    result = {
        'num_blocks': num_blocks,
        'block_size': block_size,
        'seed': seed.hex(),
        'entry_point': hex(new_entry),
        'original_entry': hex(text_addr + entry_offset_in_text),
        'text_size': text_size,
        'stub_size': len(stub),
        'enable_microjit': enable_microjit,
        'key_file': runtime_key_path,
        'confidentiality': 'runtime key file; keystream masked in the stub',
    }
    if degradation_config:
        result['degradation'] = degradation_config
    result['enable_exec_guard'] = enable_exec_guard
    return result


def _write_key_file(path: str, key: bytes) -> None:
    """Write the 32-byte runtime key with 0600 permissions."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, key)
        os.fsync(fd)
    finally:
        os.close(fd)


def _source_mode(path: str) -> int:
    """Permission bits to carry over to the encrypted output."""
    try:
        return os.stat(path).st_mode & 0o777
    except OSError:
        return 0o755


def _split_blocks(data: bytes, block_size: int) -> list[bytes]:
    blocks = []
    for i in range(0, len(data), block_size):
        blocks.append(data[i:i + block_size])
    return blocks


def _build_shadorenc_metadata(block_size: int,
                               num_blocks: int, text_size: int,
                               original_entry: int,
                               stub_size: int,
                               degradation_config: dict | None = None,
                               enable_exec_guard: bool = False) -> bytes:
    # The seed is deliberately NOT written here. The decryptor stub carries the
    # keystream it needs; storing the seed beside the ciphertext would hand a
    # reader the ability to derive every block key. The detector's finding is
    # correct for the old layout; this is the layout fix.
    data = b''
    data += struct.pack('<I', 0x4E4958)
    data += struct.pack('<I', 2)
    data += struct.pack('<I', block_size)
    data += struct.pack('<I', num_blocks)
    data += struct.pack('<I', text_size)
    data += struct.pack('<I', original_entry)
    data += struct.pack('<I', stub_size)
    if degradation_config:
        deg_flags = degradation_config.get('degradation_flags', 0)
        data += struct.pack('<I', deg_flags)
    data += struct.pack('<I', 1 if enable_exec_guard else 0)
    return data


def encrypt_binary_per_block(input_path: str, output_path: str,
                              seed: bytes | None = None,
                              block_size: int = 64,
                              text_size: int | None = None,
                              degradation_config: dict | None = None) -> dict:
    """
    Per-block encryption with individual stubs before each block.
    WARNING: This mode changes .text layout which can break cross-block
    relative jumps. Use bulk_mode=True (default) for linked executables.

    This mode is best suited for relocatable object files (.o) where the
    linker will resolve all relocations after our transformation.
    """
    if seed is None:
        seed = aes.generate_encryption_seed()
    if len(seed) != 32:
        raise ValueError("Seed must be 32 bytes (256 bits)")

    with open(input_path, 'rb') as f:
        data = f.read()

    elf = elfmod.ELFParser(data)
    idx, text_sec = elf.get_text_section()
    text_data = elf.section_data(text_sec)
    if text_size is not None:
        text_data = text_data[:text_size]
        text_sec['size'] = len(text_data)
        elf._set_shdr_field(idx, 'size', len(text_data))
    text_addr = text_sec['addr']
    entry_offset_in_text = elf.get_entry_offset_in_text()


    blocks = _split_blocks(text_data, block_size)
    num_blocks = len(blocks)

    runtime_key_path = os.path.abspath(output_path) + ".key"
    env_key = os.environ.get("NIXON_ENC_RUNTIME_KEY", "").strip()
    if env_key:
        try:
            runtime_key = bytes.fromhex(env_key)
        except ValueError as exc:
            raise ValueError("NIXON_ENC_RUNTIME_KEY must be hex") from exc
        if len(runtime_key) != 32:
            raise ValueError("NIXON_ENC_RUNTIME_KEY must be 32 bytes")
    else:
        runtime_key = os.urandom(32)
    key_path_len = len(runtime_key_path.encode("utf-8")) + 1

    final_text_parts = []
    for i, blk in enumerate(blocks):
        blk_key = aes.derive_block_key(seed, i, len(blk))
        nonce = hashlib.sha256(blk_key).digest()[:8]
        keystream = aes.aes256_ctr_keystream(blk_key, nonce, len(blk))
        encrypted = bytes(p ^ k for p, k in zip(blk, keystream))
        masked = bytes(k ^ runtime_key[j % 32]
                       for j, k in enumerate(keystream))

        stub_len = stubmod.stub_size(len(encrypted),
                                     key_path_len=key_path_len)
        stub = stubmod.make_stub_with_keystream(
            text_size=len(encrypted),
            original_entry=0,
            keystream=masked,
            # The stub precedes its block: block base = stub_base + stub_len.
            text_base_delta=stub_len - 6,
            key_path=runtime_key_path,
        )
        final_text_parts.append(stub)
        final_text_parts.append(encrypted)

    new_text = b''.join(final_text_parts)
    new_text += b'\x00' * ((len(text_data) - len(new_text)) % 0x1000)
    new_entry = text_addr

    elf.replace_text(new_text, add_stub_size=len(new_text) - len(text_data))
    elf.set_entry_point(new_entry)
    _write_key_file(runtime_key_path, runtime_key)

    metadata = _build_shadorenc_metadata(block_size, num_blocks,
                                         len(text_data), entry_offset_in_text,
                                         len(new_text) - len(text_data),
                                         degradation_config,
                                         enable_exec_guard=False)
    elf.add_shadorenc_section(metadata)
    elf.save(output_path, mode=_source_mode(input_path))

    result = {
        'num_blocks': num_blocks,
        'block_size': block_size,
        'seed': seed.hex(),
        'entry_point': hex(new_entry),
        'original_entry': hex(text_addr + entry_offset_in_text),
        'text_size': len(text_data),
        'stub_total': len(new_text) - len(text_data),
        'key_file': runtime_key_path,
        'confidentiality': 'runtime key file; keystream masked in the stub',
    }
    if degradation_config:
        result['degradation'] = degradation_config
    return result
