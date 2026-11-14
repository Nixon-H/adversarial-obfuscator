"""x86_64 decryption stub generator.

Generates position-independent shellcode that makes the .text pages writable,
XOR-decrypts the .text section in place using an embedded keystream, restores
the pages to read+execute, then jumps to the original entry point.

Keyed mode (the default for `encrypt_binary`): the embedded keystream is
XOR-masked with a 32-byte runtime key read from a sidecar file whose path is
embedded in the stub.  Without that file the stub exits(1); the artifact
alone does not decrypt.  The legacy no-key mode embeds the keystream
verbatim and is retained for tests/backwards compatibility.

Public API:
    - make_stub_with_keystream(text_size, original_entry, keystream,
                               text_base_delta=None, key_path=None) -> bytes
    - make_stub_xor_decrypt(text_size, original_entry, text_base_delta=0,
                            keystream=None, key_path=None) -> bytes
    - stub_size(text_size, key_path_len=0) -> int
    - STUB_CODE_SIZE, STUB_CODE_SIZE_KEYED, STUB_HEADER_SIZE: size constants

Dependencies:
    - None (standard library only: struct)
"""

import struct

# Header layout (20 bytes): text_base_delta (8), original_entry (8),
# text_size (4), followed by the keystream.
STUB_HEADER_SIZE = 20
# Keyed header adds 4 bytes of padding before the keystream; the key-path
# delta is patched into the code's disp32.
STUB_HEADER_SIZE_KEYED = 24

# rbx points at the `pop rbx` instruction: 1 byte (push rdx) + 5 (call).
_ANCHOR = 6


def _build_code():
    """Assemble the position-independent decryptor.

    Returns (code, offsets) where offsets maps header field names to the
    position of their disp32 operand inside ``code``.

    Register use: rbx = anchor (address of ``pop rbx``), rax = .text base,
    rcx = original entry offset, rdx = text size, r8 = keystream, r9 = index,
    r10b = keystream byte, r12 = saved .text base across syscalls.
    """
    code = bytearray()

    # The ELF entry protocol passes rtld_fini in rdx; preserve it.
    code += b'\x52'                            # push rdx
    # call +0; pop rbx  -> rbx = address of the pop (stub_base + 6)
    code += b'\xe8\x00\x00\x00\x00'
    code += b'\x5b'

    # mov rax, [rbx + text_base_delta]
    off_delta = len(code)
    code += b'\x48\x8b\x83\x00\x00\x00\x00'
    # add rax, rbx  -> rax = .text base
    code += b'\x48\x01\xd8'
    # mov r12, rax  (survive syscalls)
    code += b'\x49\x89\xc4'

    # mov edx, [rbx + text_size]
    off_size1 = len(code)
    code += b'\x8b\x93\x00\x00\x00\x00'

    # mprotect(page_start, page_end - page_start, PROT_READ|WRITE|EXEC)
    #   rsi = (text_base + size + 0xfff) & ~0xfff
    #   rdi = text_base & ~0xfff
    code += b'\x48\x89\xc6'                    # mov rsi, rax
    code += b'\x48\x01\xd6'                    # add rsi, rdx
    code += b'\x48\x81\xc6\xff\x0f\x00\x00'    # add rsi, 0xfff
    code += b'\x48\x81\xe6\x00\xf0\xff\xff'    # and rsi, -4096
    code += b'\x48\x89\xc7'                    # mov rdi, rax
    code += b'\x48\x81\xe7\x00\xf0\xff\xff'    # and rdi, -4096
    code += b'\x48\x29\xfe'                    # sub rsi, rdi
    code += b'\xba\x07\x00\x00\x00'            # mov edx, 7
    code += b'\xb8\x0a\x00\x00\x00'            # mov eax, 10 (SYS_mprotect)
    code += b'\x0f\x05'                        # syscall
    code += b'\x4c\x89\xe0'                    # mov rax, r12

    # mov edx, [rbx + text_size]
    off_size2 = len(code)
    code += b'\x8b\x93\x00\x00\x00\x00'
    # lea r8, [rbx + keystream]
    off_ks = len(code)
    code += b'\x4c\x8d\x83\x00\x00\x00\x00'

    # xor r9d, r9d
    code += b'\x45\x31\xc9'
    loop = len(code)
    code += b'\x47\x8a\x14\x08'                # mov r10b, [r8 + r9]
    code += b'\x46\x30\x14\x08'                # xor [rax + r9], r10b
    code += b'\x41\xff\xc1'                    # inc r9d
    code += b'\x41\x39\xd1'                    # cmp r9d, edx
    code += b'\x72' + bytes([(loop - (len(code) + 2)) & 0xff])  # jb loop

    # mprotect(page_start, len, PROT_READ|EXEC)
    code += b'\x49\x89\xc4'                    # mov r12, rax
    code += b'\x48\x89\xc6'                    # mov rsi, rax
    code += b'\x48\x01\xd6'                    # add rsi, rdx
    code += b'\x48\x81\xc6\xff\x0f\x00\x00'    # add rsi, 0xfff
    code += b'\x48\x81\xe6\x00\xf0\xff\xff'    # and rsi, -4096
    code += b'\x48\x89\xc7'                    # mov rdi, rax
    code += b'\x48\x81\xe7\x00\xf0\xff\xff'    # and rdi, -4096
    code += b'\x48\x29\xfe'                    # sub rsi, rdi
    code += b'\xba\x05\x00\x00\x00'            # mov edx, 5
    code += b'\xb8\x0a\x00\x00\x00'            # mov eax, 10
    code += b'\x0f\x05'                        # syscall
    code += b'\x4c\x89\xe0'                    # mov rax, r12
    # syscall clobbers rcx, so load the entry offset only now.
    off_entry = len(code)
    code += b'\x48\x8b\x8b\x00\x00\x00\x00'  # mov rcx, [rbx+entry]
    # Self-modifying code: serialize the instruction pipeline before
    # executing the freshly decrypted bytes (Intel SDM self-modifying-code
    # rule).  cpuid clobbers rax/rbx/rcx/rdx, so save what we need.
    code += b'\x49\x89\xcd'                    # mov r13, rcx
    code += b'\x31\xc0'                        # xor eax, eax
    code += b'\x0f\xa2'                        # cpuid
    code += b'\x4c\x89\xe0'                    # mov rax, r12
    code += b'\x4c\x89\xe9'                    # mov rcx, r13
    code += b'\x5a'                            # pop rdx (restore rtld_fini)
    code += b'\x48\x01\xc8'                    # add rax, rcx
    code += b'\x48\xff\xe0'                    # jmp rax

    return code, {
        'delta': off_delta + 3,
        'size1': off_size1 + 2,
        'entry': off_entry + 3,
        'size2': off_size2 + 2,
        'keystream': off_ks + 3,
    }


_CODE, _OFFSETS = _build_code()
STUB_CODE_SIZE = len(_CODE)


def _build_code_keyed():
    """Assemble the runtime-key variant of the decryptor.

    The embedded keystream is XOR-masked with a 32-byte key read from a
    file at runtime (path embedded in the stub header).  Without that file
    the stub exits(1); ciphertext XOR the embedded bytes is no longer the
    plaintext.  Register use adds r14 = key buffer, r15 = fd.
    """
    code = bytearray()

    code += b'\x52'                            # push rdx (rtld_fini)
    code += b'\xe8\x00\x00\x00\x00'            # call +0
    code += b'\x5b'                            # pop rbx (anchor)

    off_delta = len(code)
    code += b'\x48\x8b\x83\x00\x00\x00\x00'    # mov rax, [rbx+delta]
    code += b'\x48\x01\xd8'                    # add rax, rbx
    code += b'\x49\x89\xc4'                    # mov r12, rax

    # ---- load the runtime key from the embedded path ----
    off_path = len(code)
    code += b'\x48\x8d\xbb\x00\x00\x00\x00'    # lea rdi, [rbx+path]
    code += b'\x31\xf6'                        # xor esi, esi (O_RDONLY)
    code += b'\x31\xd2'                        # xor edx, edx
    code += b'\xb8\x02\x00\x00\x00'            # mov eax, 2 (SYS_open)
    code += b'\x0f\x05'                        # syscall
    code += b'\x48\x85\xc0'                    # test rax, rax
    js_fail = len(code)
    code += b'\x78\x00'                        # js fail (patched)
    code += b'\x49\x89\xc7'                    # mov r15, rax (fd)
    code += b'\x48\x83\xec\x20'                # sub rsp, 32
    code += b'\x48\x89\xe6'                    # mov rsi, rsp
    code += b'\x4c\x89\xff'                    # mov rdi, r15
    code += b'\xba\x20\x00\x00\x00'            # mov edx, 32
    code += b'\x31\xc0'                        # xor eax, eax (SYS_read)
    code += b'\x0f\x05'                        # syscall
    code += b'\x48\x83\xf8\x20'                # cmp rax, 32
    jne_fail = len(code)
    code += b'\x75\x00'                        # jne fail (patched)
    code += b'\x4c\x89\xff'                    # mov rdi, r15
    code += b'\xb8\x03\x00\x00\x00'            # mov eax, 3 (SYS_close)
    code += b'\x0f\x05'                        # syscall
    code += b'\x49\x89\xe6'                    # mov r14, rsp (key buffer)
    jmp_ok = len(code)
    code += b'\xeb\x00'                        # jmp key_ok (patched)
    fail_pos = len(code)
    code += b'\xb8\x3c\x00\x00\x00'            # mov eax, 60 (SYS_exit)
    code += b'\xbf\x01\x00\x00\x00'            # mov edi, 1
    code += b'\x0f\x05'                        # syscall
    code += b'\x0f\x0b'                        # ud2
    key_ok = len(code)
    code[js_fail + 1] = (fail_pos - (js_fail + 2)) & 0xFF
    code[jne_fail + 1] = (fail_pos - (jne_fail + 2)) & 0xFF
    code[jmp_ok + 1] = (key_ok - (jmp_ok + 2)) & 0xFF

    # ---- mprotect RWX ----
    code += b'\x4c\x89\xe0'                    # mov rax, r12
    off_size1 = len(code)
    code += b'\x8b\x93\x00\x00\x00\x00'        # mov edx, [rbx+size]
    code += b'\x48\x89\xc6'                    # mov rsi, rax
    code += b'\x48\x01\xd6'                    # add rsi, rdx
    code += b'\x48\x81\xc6\xff\x0f\x00\x00'    # add rsi, 0xfff
    code += b'\x48\x81\xe6\x00\xf0\xff\xff'    # and rsi, -4096
    code += b'\x48\x89\xc7'                    # mov rdi, rax
    code += b'\x48\x81\xe7\x00\xf0\xff\xff'    # and rdi, -4096
    code += b'\x48\x29\xfe'                    # sub rsi, rdi
    code += b'\xba\x07\x00\x00\x00'            # mov edx, 7
    code += b'\xb8\x0a\x00\x00\x00'            # mov eax, 10 (SYS_mprotect)
    code += b'\x0f\x05'                        # syscall
    code += b'\x4c\x89\xe0'                    # mov rax, r12

    # ---- decrypt: embedded_ks ^ runtime_key ----
    off_size2 = len(code)
    code += b'\x8b\x93\x00\x00\x00\x00'        # mov edx, [rbx+size]
    off_ks = len(code)
    code += b'\x4c\x8d\x83\x00\x00\x00\x00'    # lea r8, [rbx+keystream]
    code += b'\x45\x31\xc9'                    # xor r9d, r9d
    loop = len(code)
    code += b'\x47\x8a\x14\x08'                # mov r10b, [r8+r9]
    code += b'\x4d\x89\xcb'                    # mov r11, r9
    code += b'\x41\x83\xe3\x1f'                # and r11d, 31
    code += b'\x47\x32\x14\x1e'                # xor r10b, [r14+r11]
    code += b'\x46\x30\x14\x08'                # xor [rax+r9], r10b
    code += b'\x41\xff\xc1'                    # inc r9d
    code += b'\x41\x39\xd1'                    # cmp r9d, edx
    code += b'\x72' + bytes([(loop - (len(code) + 2)) & 0xFF])  # jb loop

    # ---- restore stack, mprotect RX, jump to the original entry ----
    code += b'\x48\x83\xc4\x20'                # add rsp, 32
    code += b'\x4c\x89\xe0'                    # mov rax, r12
    code += b'\x48\x89\xc6'                    # mov rsi, rax
    code += b'\x48\x01\xd6'                    # add rsi, rdx
    code += b'\x48\x81\xc6\xff\x0f\x00\x00'    # add rsi, 0xfff
    code += b'\x48\x81\xe6\x00\xf0\xff\xff'    # and rsi, -4096
    code += b'\x48\x89\xc7'                    # mov rdi, rax
    code += b'\x48\x81\xe7\x00\xf0\xff\xff'    # and rdi, -4096
    code += b'\x48\x29\xfe'                    # sub rsi, rdi
    code += b'\xba\x05\x00\x00\x00'            # mov edx, 5
    code += b'\xb8\x0a\x00\x00\x00'            # mov eax, 10
    code += b'\x0f\x05'                        # syscall
    code += b'\x4c\x89\xe0'                    # mov rax, r12
    off_entry = len(code)
    code += b'\x48\x8b\x8b\x00\x00\x00\x00'    # mov rcx, [rbx+entry]
    code += b'\x49\x89\xcd'                    # mov r13, rcx
    code += b'\x31\xc0'                        # xor eax, eax
    code += b'\x0f\xa2'                        # cpuid
    code += b'\x4c\x89\xe0'                    # mov rax, r12
    code += b'\x4c\x89\xe9'                    # mov rcx, r13
    code += b'\x5a'                            # pop rdx
    code += b'\x48\x01\xc8'                    # add rax, rcx
    code += b'\x48\xff\xe0'                    # jmp rax

    return code, {
        'delta': off_delta + 3,
        'size1': off_size1 + 2,
        'entry': off_entry + 3,
        'size2': off_size2 + 2,
        'keystream': off_ks + 3,
        'key_path': off_path + 3,
    }


_CODE_KEYED, _OFFSETS_KEYED = _build_code_keyed()
STUB_CODE_SIZE_KEYED = len(_CODE_KEYED)


def _make_stub(text_size, original_entry, keystream, text_base_delta,
               key_path: str | None = None):
    if text_size <= 0:
        raise ValueError("text_size must be positive")
    if original_entry < 0:
        raise ValueError("original_entry must be non-negative")
    if len(keystream) != text_size:
        raise ValueError(
            f"keystream length {len(keystream)} != text_size {text_size}")

    if key_path is None:
        code = bytearray(_CODE)
        offsets = _OFFSETS
        header_size = STUB_HEADER_SIZE
        key_bytes = b""
    else:
        code = bytearray(_CODE_KEYED)
        offsets = _OFFSETS_KEYED
        header_size = STUB_HEADER_SIZE_KEYED
        key_bytes = key_path.encode("utf-8") + b"\x00"

    header_start = len(code)
    data_off = header_start - _ANCHOR

    struct.pack_into('<i', code, offsets['delta'], data_off)
    struct.pack_into('<i', code, offsets['size1'], data_off + 16)
    struct.pack_into('<i', code, offsets['entry'], data_off + 8)
    struct.pack_into('<i', code, offsets['size2'], data_off + 16)
    struct.pack_into('<i', code, offsets['keystream'],
                     data_off + header_size)
    if key_path is not None:
        struct.pack_into('<i', code, offsets['key_path'],
                         data_off + header_size + text_size)

    header = (struct.pack('<q', text_base_delta)
              + struct.pack('<q', original_entry)
              + struct.pack('<I', text_size))
    if key_path is not None:
        # Padding to the 24-byte keyed header; the path delta lives in
        # the code's disp32, not in this field.
        header += struct.pack('<i', 0)

    return bytes(code) + header + bytes(keystream) + key_bytes


def make_stub_with_keystream(text_size: int, original_entry: int,
                             keystream: bytes,
                             text_base_delta: int | None = None,
                             key_path: str | None = None) -> bytes:
    """Build a stub that decrypts ``text_size`` bytes at the .text base.

    Args:
        text_size: Number of bytes to decrypt.
        original_entry: Offset from the .text base to the original entry.
        keystream: Exactly ``text_size`` bytes of keystream.
        text_base_delta: Signed offset from the anchor (stub_base + 5) back
            to the .text base.  Defaults to ``-(text_size + 6)``, which is
            correct when the stub is appended directly after the encrypted
            text.  Per-block callers pass ``stub_length - 5`` instead.
        key_path: When set, the stub reads a 32-byte runtime key from this
            file and XORs it into the embedded keystream before decrypting.
            Without the file the stub exits(1).  Without this argument the
            keystream is embedded verbatim (legacy obfuscation-only mode).
    """
    if text_base_delta is None:
        text_base_delta = -(text_size + _ANCHOR)
    return _make_stub(text_size, original_entry, keystream, text_base_delta,
                      key_path=key_path)


def make_stub_xor_decrypt(text_size: int, original_entry: int,
                          text_base_delta: int = 0,
                          keystream: bytes | None = None,
                          key_path: str | None = None) -> bytes:
    """Backwards-compatible wrapper around :func:`make_stub_with_keystream`.

    The old implementation silently used a keystream derived from a public
    constant, which made every artifact built with it trivially decryptable.
    A keystream is now required.
    """
    if keystream is None:
        raise ValueError(
            "make_stub_xor_decrypt requires an explicit keystream; the old "
            "hardcoded placeholder key was publicly computable")
    if text_base_delta == 0:
        text_base_delta = -(text_size + _ANCHOR)
    return _make_stub(text_size, original_entry, keystream, text_base_delta,
                      key_path=key_path)


def stub_size(text_size: int, key_path_len: int = 0) -> int:
    if key_path_len:
        return (STUB_CODE_SIZE_KEYED + STUB_HEADER_SIZE_KEYED
                + text_size + key_path_len)
    return STUB_CODE_SIZE + STUB_HEADER_SIZE + text_size
