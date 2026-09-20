"""Binary encryption pipeline — Stage 4.

Encrypts compiled ELF binaries block-by-block using AES-256-CTR. Supports
two modes: bulk (single stub, safe for linked executables) and per-block
(individual stubs, for relocatable objects). Embeds decryption metadata
in a `.shadorenc` ELF section.

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
    text_start = text_sec['offset']
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

    stub = stubmod.make_stub_with_keystream(
        text_size=text_size,
        original_entry=entry_offset_in_text,
        keystream=all_keystream,
    )

    new_text = encrypted_text + stub
    stub_start_in_text = text_size

    new_entry = text_addr + stub_start_in_text

    elf.replace_text(new_text, add_stub_size=len(stub))
    elf.set_entry_point(new_entry)

    if enable_microjit:
        import os
        microjit_seed = int.from_bytes(os.urandom(4), 'little')
        if degradation_config:
            degradation_config['microjit_seed'] = microjit_seed
        else:
            degradation_config = {'microjit_seed': microjit_seed}

    metadata = _build_shadorenc_metadata(seed, block_size, num_blocks,
                                         text_size, entry_offset_in_text,
                                         len(stub), degradation_config,
                                         enable_exec_guard)
    elf.add_shadorenc_section(metadata)
    elf.save(output_path)

    result = {
        'num_blocks': num_blocks,
        'block_size': block_size,
        'seed': seed.hex(),
        'entry_point': hex(new_entry),
        'original_entry': hex(text_addr + entry_offset_in_text),
        'text_size': text_size,
        'stub_size': len(stub),
        'enable_microjit': enable_microjit,
    }
    if degradation_config:
        result['degradation'] = degradation_config
    result['enable_exec_guard'] = enable_exec_guard
    return result


def _split_blocks(data: bytes, block_size: int) -> list[bytes]:
    blocks = []
    for i in range(0, len(data), block_size):
        blocks.append(data[i:i + block_size])
    return blocks


def _build_shadorenc_metadata(seed: bytes, block_size: int,
                               num_blocks: int, text_size: int,
                               original_entry: int,
                               stub_size: int,
                               degradation_config: dict | None = None,
                               enable_exec_guard: bool = False) -> bytes:
    data = b''
    data += struct.pack('<I', 0x4E4958)
    data += struct.pack('<I', 1)
    data += struct.pack('<I', block_size)
    data += struct.pack('<I', num_blocks)
    data += struct.pack('<I', text_size)
    data += struct.pack('<I', original_entry)
    data += struct.pack('<I', stub_size)
    data += seed
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

    STUB_OVERHEAD = stubmod.STUB_CODE_SIZE + stubmod.STUB_HEADER_SIZE

    blocks = _split_blocks(text_data, block_size)
    num_blocks = len(blocks)

    final_text_parts = []
    for i, blk in enumerate(blocks):
        blk_key = aes.derive_block_key(seed, i, len(blk))
        nonce = hashlib.sha256(blk_key).digest()[:8]
        keystream = aes.aes256_ctr_keystream(blk_key, nonce, len(blk))
        encrypted = bytes(p ^ k for p, k in zip(blk, keystream))

        stub = stubmod.make_stub_with_keystream(
            text_size=len(encrypted),
            original_entry=0,
            keystream=keystream,
        )
        final_text_parts.append(stub)
        final_text_parts.append(encrypted)

    new_text = b''.join(final_text_parts)
    new_entry = text_addr

    elf.replace_text(new_text, add_stub_size=len(new_text) - len(text_data))
    elf.set_entry_point(new_entry)

    metadata = _build_shadorenc_metadata(seed, block_size, num_blocks,
                                         len(text_data), entry_offset_in_text,
                                         len(new_text) - len(text_data),
                                         degradation_config,
                                         enable_exec_guard=False)
    elf.add_shadorenc_section(metadata)
    elf.save(output_path)

    result = {
        'num_blocks': num_blocks,
        'block_size': block_size,
        'seed': seed.hex(),
        'entry_point': hex(new_entry),
        'original_entry': hex(text_addr + entry_offset_in_text),
        'text_size': len(text_data),
        'stub_total': len(new_text) - len(text_data),
    }
    if degradation_config:
        result['degradation'] = degradation_config
    return result
