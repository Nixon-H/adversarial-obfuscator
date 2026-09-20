"""x86_64 decryption stub generator.

Generates position-independent shellcode that XOR-decrypts the .text section
in-place using an embedded AES-256-CTR keystream, then jumps to the original
entry point. Used as the runtime decryptor for encrypted binaries.

Public API:
    - make_stub_xor_decrypt(text_size, original_entry, text_base_delta) -> bytes
    - make_stub_with_keystream(text_size, original_entry, keystream) -> bytes
    - stub_size(text_size) -> int
    - STUB_CODE_SIZE, STUB_HEADER_SIZE: size constants

Dependencies:
    - encrypt.aes (aes256_ctr_keystream)
"""

import hashlib
import struct

from .aes import aes256_ctr_keystream


def make_stub_xor_decrypt(text_size: int, original_entry: int,
                          text_base_delta: int = 0) -> bytes:
    """
    Generate position-independent x86_64 shellcode that XOR-decrypts
    the .text section in-place using an embedded keystream, then jumps
    to the original entry point.

    Args:
        text_size: Total number of bytes to decrypt (original .text size).
        original_entry: Offset from .text base to the original entry point.
        text_base_delta: Signed offset from the stub's anchor point
                         back to the .text base address.
                         Computed as: .text_base - (stub_start_in_text + 6)

    Returns:
        Raw bytes of the stub (code + header + keystream).
    """
    if text_size <= 0:
        raise ValueError("text_size must be positive")
    if original_entry < 0:
        raise ValueError("original_entry must be non-negative")

    # The stub uses call/pop to get its own address (anchor at pop rbx).
    # text_base = rbx + text_base_delta
    # The entry jump target = text_base + original_entry

    rbx_anchor = 6

    # Compute text_base_delta if not provided
    if text_base_delta == 0:
        text_base_delta = -(text_size + rbx_anchor)

    code = bytearray()

    # call +0 (5 bytes) - pushes return address, falls through to pop
    code += b'\xe8\x00\x00\x00\x00'
    # .anchor: pop rbx (1 byte) - rbx = address of this instruction
    code += b'\x5b'

    # mov rax, [rbx + offset_to_text_base_delta]
    # We'll calculate offsets after building the rest
    off_text_base_delta_pos = len(code)
    code += b'\x48\x8b\x43\x00'

    # add rax, rbx  (rax = .text_base)
    code += b'\x48\x01\xd8'

    # mov rcx, [rbx + offset_to_orig_entry]
    off_orig_entry_pos = len(code)
    code += b'\x48\x8b\x4b\x00'

    # mov edx, [rbx + offset_to_key_size]
    off_key_size_pos = len(code)
    code += b'\x8b\x53\x00'

    # lea r8, [rbx + offset_to_keystream]
    off_keystream_pos = len(code)
    code += b'\x4c\x8d\x43\x00'

    # xor r9d, r9d  (index = 0)
    code += b'\x45\x31\xc9'

    # .loop:
    # mov r10b, [r8 + r9]  (load keystream byte)
    loop_start = len(code)
    code += b'\x47\x8a\x14\x0e'
    # xor [rax + r9], r10b (decrypt text byte)
    code += b'\x46\x30\x14\x08'
    # inc r9d
    code += b'\x41\xff\xc1'
    # cmp r9d, edx
    code += b'\x41\x39\xd1'
    # jb .loop
    code += b'\x72\xf0'

    # add rax, rcx  (rax = .text_base + original_entry)
    code += b'\x48\x01\xc8'
    # jmp rax
    code += b'\x48\xff\xe0'

    header_start = len(code)

    data_off = header_start - rbx_anchor

    code[off_text_base_delta_pos + 3] = data_off & 0xff
    code[off_orig_entry_pos + 3] = (data_off + 8) & 0xff
    code[off_key_size_pos + 2] = (data_off + 16) & 0xff
    code[off_keystream_pos + 3] = (data_off + 20) & 0xff

    text_base_delta_bytes = struct.pack('<q', text_base_delta)
    orig_entry_bytes = struct.pack('<q', original_entry)
    key_size_bytes = struct.pack('<I', text_size)

    keystream = _generate_placeholder_keystream(text_size)

    stub = bytes(code) + text_base_delta_bytes + orig_entry_bytes + key_size_bytes + keystream

    return stub


def make_stub_with_keystream(text_size: int, original_entry: int,
                             keystream: bytes) -> bytes:
    rbx_anchor = 6
    text_base_delta = -(text_size + rbx_anchor)

    code = bytearray()
    code += b'\xe8\x00\x00\x00\x00'
    code += b'\x5b'

    off_text_base_delta_pos = len(code)
    code += b'\x48\x8b\x43\x00'
    code += b'\x48\x01\xd8'
    off_orig_entry_pos = len(code)
    code += b'\x48\x8b\x4b\x00'
    off_key_size_pos = len(code)
    code += b'\x8b\x53\x00'
    off_keystream_pos = len(code)
    code += b'\x4c\x8d\x43\x00'
    code += b'\x45\x31\xc9'
    loop_start = len(code)
    code += b'\x47\x8a\x14\x0e'
    code += b'\x46\x30\x14\x08'
    code += b'\x41\xff\xc1'
    code += b'\x41\x39\xd1'
    code += b'\x72\xf0'
    code += b'\x48\x01\xc8'
    code += b'\x48\xff\xe0'

    header_start = len(code)
    data_off = header_start - rbx_anchor

    code[off_text_base_delta_pos + 3] = data_off & 0xff
    code[off_orig_entry_pos + 3] = (data_off + 8) & 0xff
    code[off_key_size_pos + 2] = (data_off + 16) & 0xff
    code[off_keystream_pos + 3] = (data_off + 20) & 0xff

    text_base_delta_bytes = struct.pack('<q', text_base_delta)
    orig_entry_bytes = struct.pack('<q', original_entry)
    key_size_bytes = struct.pack('<I', text_size)

    stub = bytes(code) + text_base_delta_bytes + orig_entry_bytes + key_size_bytes + keystream

    return stub


def _generate_placeholder_keystream(size: int) -> bytes:
    key = hashlib.sha256(b'shadow-compiler-keystream').digest()
    nonce = hashlib.sha256(key).digest()[:8]
    return aes256_ctr_keystream(key, nonce, size)


def stub_size(text_size: int) -> int:
    return 49 + text_size + 20


STUB_CODE_SIZE = 49
STUB_HEADER_SIZE = 20
