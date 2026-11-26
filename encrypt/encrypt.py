"""Binary encryption pipeline — Stage 4.

Obfuscates compiled ELF binaries block-by-block using AES-256-CTR. Supports
two modes: bulk (single stub, safe for linked executables) and per-block
(individual stubs, for relocatable objects). Embeds decryption metadata
in a `.shadorenc` ELF section.

Confidentiality note: bulk and per-block modes use ChaCha20-Poly1305 with a
random per-artifact/per-block nonce and a 32-byte runtime key stored only in a
0600 sidecar (`<output>.key`). No key or keystream is embedded. The sidecar
must be distributed separately and the stub fails closed if it is missing.

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
from . import chacha20poly1305 as aead
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

    In bulk mode (default), .text and optional .rodata are encrypted as one
    ChaCha20-Poly1305 message with a random nonce and a standalone decryptor
    stub appended in a new load segment. The ELF entry point is redirected to
    the stub. ``seed`` remains a reproducibility/build identifier, not crypto
    key material.

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

    # Runtime key source: a 32-byte sidecar key. The artifact carries only a
    # random 96-bit nonce, ciphertext, tag, and canonical authenticated header.
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

    # ---- optional .rodata encryption -------------------------------------
    rodata_plan = _plan_rodata_encryption(elf, seed, encrypt_rodata,
                                          runtime_key=runtime_key)
    # The AEAD path below seals this plaintext together with .text; it never
    # embeds a keystream, so there is no masked-keystream/key-reuse surface.
    rodata_plain = rodata_plan['plaintext'] if rodata_plan['size'] else b""

    # The stub lives in its own executable PT_LOAD segment appended at EOF.
    key_path_len = len(runtime_key_path.encode("utf-8")) + 1
    stub_len = stubmod.stub_size(text_size, key_path_len=key_path_len,
                                 rodata_size=rodata_plan['size'], aead=True)
    load_plan = elf.plan_load_segment(stub_len)
    stub_vaddr = load_plan['vaddr'] + load_plan['table_size']
    nonce = os.urandom(12)
    header = stubmod.make_aead_header(
        text_size, entry_offset_in_text, nonce,
        text_base_delta=text_addr - (stub_vaddr + 6),
        rodata_size=rodata_plan['size'],
        rodata_base_delta=(rodata_plan['addr'] - (stub_vaddr + 6)
                           if rodata_plan['size'] else 0),
        block_index=0,
    )
    ciphertext, tag = aead.seal(runtime_key, nonce, text_data + rodata_plain, header)
    encrypted_text = ciphertext[:text_size]
    encrypted_rodata = ciphertext[text_size:]
    stub = stubmod.make_stub_aead(
        text_size=text_size,
        original_entry=entry_offset_in_text,
        key_path=runtime_key_path,
        nonce=nonce,
        tag=tag,
        text_base_delta=text_addr - (stub_vaddr + 6),
        rodata_size=rodata_plan['size'],
        rodata_base_delta=(rodata_plan['addr'] - (stub_vaddr + 6)
                           if rodata_plan['size'] else 0),
        block_index=0,
    )

    elf.replace_text(encrypted_text, add_stub_size=0)
    if rodata_plan['size']:
        elf.replace_rodata_span(rodata_plan['addr'], encrypted_rodata)
    new_entry = elf.add_load_segment(stub, load_plan)
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
        'confidentiality': 'ChaCha20-Poly1305 with separate 0600 runtime key file',
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

    Retained for the legacy keyed-stub API (``make_stub_with_keystream``),
    which embeds an XOR-masked keystream.  The shipped AEAD path does **not**
    use this: it seals .rodata plaintext as part of the authenticated
    ChaCha20-Poly1305 stream, so the runtime key is used exactly once, as the
    AEAD key.  Masking a keystream with that same key (as the legacy stub
    does) would let anyone who knows a stretch of .rodata plaintext recover
    the key and decrypt .text as well.
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
    ``addr``, ``plaintext`` and ``skipped_reason``.

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
    plan = {'size': 0, 'addr': 0, 'plaintext': b'', 'skipped_reason': ''}
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

    # Precondition for the AEAD seal that consumes this plan: a 32-byte key
    # must already exist.  Without one the caller cannot authenticate the
    # artifact, so refusing to plan .rodata keeps the failure closed.
    if len(runtime_key) != 32:
        plan['skipped_reason'] = 'runtime key unavailable'
        return plan
    plan.update({
        'size': span_size,
        'addr': span_start,
        'plaintext': bytes(data),
    })
    return plan


def _write_key_file(path: str, key: bytes) -> None:
    """Create a private key file without following or replacing any path."""
    if len(key) != 32:
        raise ValueError("Runtime key must be 32 bytes")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        view = memoryview(key)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("Short write while creating runtime key file")
            view = view[written:]
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
        stub_len = stubmod.stub_size(len(blk), key_path_len=key_path_len, aead=True)
        nonce = os.urandom(12)
        header = stubmod.make_aead_header(
            len(blk), 0, nonce,
            # The stub precedes its block: block base = stub_base + stub_len.
            text_base_delta=stub_len - 6,
            block_index=i,
        )
        encrypted, tag = aead.seal(runtime_key, nonce, blk, header)
        stub = stubmod.make_stub_aead(
            text_size=len(blk),
            original_entry=0,
            key_path=runtime_key_path,
            nonce=nonce,
            tag=tag,
            text_base_delta=stub_len - 6,
            block_index=i,
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
        'confidentiality': 'ChaCha20-Poly1305 with separate 0600 runtime key file',
    }
    if degradation_config:
        result['degradation'] = degradation_config
    return result
