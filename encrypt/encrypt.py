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
                   enable_microjit: bool = False,
                   encrypt_rodata: bool = False) -> dict:
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
        encrypt_rodata: If True, also encrypt .rodata in place and extend the
            stub to decrypt it.  Skipped (with a logged reason) when the
            section is absent or shares a page with .text, because restoring
            the page to read-only would strip execute permission from code.

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

    # ---- optional .rodata encryption -------------------------------------
    # .rodata holds the string literals a native binary would otherwise leak
    # in cleartext.  It is encrypted in place (same length, so every vaddr
    # and relocation stays valid) and the stub decrypts it before the
    # original entry runs.
    rodata_plan = _plan_rodata_encryption(elf, seed, encrypt_rodata,
                                          runtime_key=runtime_key)

    # The stub lives in its own executable PT_LOAD segment appended at EOF.
    # Keeping it out of .text means no existing vaddr moves, so DT_FINI,
    # DT_INIT_ARRAY and relocations stay valid.
    key_path_len = len(runtime_key_path.encode("utf-8")) + 1
    stub_len = stubmod.stub_size(text_size, key_path_len=key_path_len,
                                 rodata_size=rodata_plan['size'])
    plan = elf.plan_load_segment(stub_len)
    stub_vaddr = plan['vaddr'] + plan['table_size']
    stub = stubmod.make_stub_with_keystream(
        text_size=text_size,
        original_entry=entry_offset_in_text,
        keystream=masked_keystream,
        text_base_delta=text_addr - (stub_vaddr + 6),
        key_path=runtime_key_path,
        rodata_size=rodata_plan['size'],
        rodata_base_delta=(rodata_plan['addr'] - (stub_vaddr + 6)
                           if rodata_plan['size'] else 0),
        rodata_keystream=rodata_plan['masked_keystream'],
    )

    elf.replace_text(encrypted_text, add_stub_size=0)
    if rodata_plan['size']:
        elf.replace_rodata_span(rodata_plan['addr'], rodata_plan['ciphertext'])
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
        'rodata_size': rodata_plan['size'],
        'rodata_encrypted': bool(rodata_plan['size']),
    }
    if rodata_plan['skipped_reason']:
        result['rodata_skipped_reason'] = rodata_plan['skipped_reason']
    if degradation_config:
        result['degradation'] = degradation_config
    result['enable_exec_guard'] = enable_exec_guard
    return result


_RODATA_DOMAIN = b"nixon-rodata-v1"


def _rodata_keystream(seed: bytes, size: int) -> bytes:
    """Derive a keystream for .rodata, domain-separated from .text.

    Reusing the .text keystream would let an attacker who recovers one
    region's plaintext XOR the other region's ciphertext against it, so the
    derivation is keyed with a distinct domain tag.
    """
    out = bytearray()
    counter = 0
    while len(out) < size:
        blk_key = hashlib.sha256(
            seed + _RODATA_DOMAIN + counter.to_bytes(8, "little")).digest()
        nonce = hashlib.sha256(blk_key + b"ro").digest()[:8]
        take = min(4096, size - len(out))
        out += aes.aes256_ctr_keystream(blk_key, nonce, take)
        counter += 1
    return bytes(out[:size])


def _plan_rodata_encryption(elf, seed: bytes, enabled: bool,
                            runtime_key: bytes = b"") -> dict:
    """Decide whether .rodata can be encrypted, and prepare the ciphertext.

    Returns a dict with ``size`` (0 when nothing will be encrypted),
    ``addr``, ``ciphertext``, ``masked_keystream`` and ``skipped_reason``.

    Every ``.rodata*`` section is covered, not just the bare ``.rodata``:
    toolchains split string literals across ``.rodata.str1.1``,
    ``.rodata.cst8`` and friends, and encrypting only the bare name would
    leave most literals in cleartext.  The sections are treated as one
    contiguous span, which is only accepted when nothing else lives inside
    it -- otherwise the stub would decrypt data it does not own.

    The guards exist because encrypting .rodata is only safe when the span
    is self-contained: the stub mprotects it read-only again before the
    original entry runs, and if it shared a page with .text that would strip
    execute permission from live code.
    """
    plan = {'size': 0, 'addr': 0, 'ciphertext': b'',
            'masked_keystream': b'', 'skipped_reason': ''}
    if not enabled:
        plan['skipped_reason'] = 'disabled'
        return plan

    sections = elf.get_rodata_sections()
    if not sections:
        plan['skipped_reason'] = 'no .rodata section'
        return plan

    sections = [(i, sec) for i, sec in sections
                if sec['type'] != elfmod.SHT_NOBITS]
    if not sections:
        plan['skipped_reason'] = '.rodata has no file backing (SHT_NOBITS)'
        return plan

    span_start = min(sec['addr'] for _, sec in sections)
    span_end = max(sec['addr'] + sec['size'] for _, sec in sections)
    span_size = span_end - span_start
    if span_size <= 0:
        plan['skipped_reason'] = '.rodata is empty'
        return plan

    # Nothing but .rodata* may live inside the span, or the stub would
    # decrypt (and mprotect) data that belongs to another section.
    ro_ids = {id(sec) for _, sec in sections}
    for sec in elf.sections:
        if id(sec) in ro_ids or sec['size'] == 0:
            continue
        if not (sec['flags'] & 0x2):  # SHF_ALLOC only
            continue
        if sec['addr'] < span_end and span_start < sec['addr'] + sec['size']:
            plan['skipped_reason'] = (
                f'{elf.section_name(sec).decode("latin-1") or "<unnamed>"} '
                'overlaps the .rodata span')
            return plan

    ro_page_start = span_start & ~0xFFF
    ro_page_end = (span_end + 0xFFF) & ~0xFFF
    _, text_sec = elf.get_text_section()
    tx_start, tx_end = elf.page_range(text_sec)
    if ro_page_start < tx_end and tx_start < ro_page_end:
        plan['skipped_reason'] = (
            '.rodata shares a page with .text; restoring it read-only would '
            'strip execute permission from code')
        return plan

    # Read the span straight out of the file: sections inside it are
    # contiguous in vaddr, and the padding between them is part of the span.
    base_idx, base_sec = next(
        (i, sec) for i, sec in sections if sec['addr'] == span_start)
    file_off = base_sec['offset']
    if file_off + span_size > len(elf.data):
        plan['skipped_reason'] = '.rodata span extends beyond the file'
        return plan
    data = elf.data[file_off:file_off + span_size]

    ks = _rodata_keystream(seed, span_size)
    # The stub XORs the embedded keystream with the runtime key before use,
    # so what ships must be the masked form -- exactly as for .text.
    if len(runtime_key) != 32:
        plan['skipped_reason'] = 'runtime key unavailable'
        return plan
    masked = bytes(k ^ runtime_key[i % 32] for i, k in enumerate(ks))
    plan.update({
        'size': span_size,
        'addr': span_start,
        'ciphertext': bytes(p ^ k for p, k in zip(data, ks)),
        'masked_keystream': masked,
    })
    return plan


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
