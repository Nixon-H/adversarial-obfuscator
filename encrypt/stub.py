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

import functools
import struct

# Header layout (20 bytes): text_base_delta (8), original_entry (8),
# text_size (4), followed by the keystream.
STUB_HEADER_SIZE = 20
# Keyed header adds 4 bytes of padding before the keystream; the key-path
# delta is patched into the code's disp32.
STUB_HEADER_SIZE_KEYED = 24
# The .rodata variant appends rodata_base_delta (8), rodata_size (4) and
# 4 bytes of padding after the keyed header.
STUB_HEADER_SIZE_KEYED_RO = 40

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


def _build_code_keyed(with_rodata: bool = False):
    """Assemble the runtime-key variant of the decryptor.

    The embedded keystream is XOR-masked with a 32-byte key read from a
    file at runtime (path embedded in the stub header).  Without that file
    the stub exits(1); ciphertext XOR the embedded bytes is no longer the
    plaintext.  Register use adds r14 = key buffer, r15 = fd.

    With ``with_rodata`` the stub also decrypts a second region (``.rodata``)
    using the same masked-keystream scheme, bracketed by mprotect calls so
    the section is read-only again before the original entry runs.  The
    default path is byte-identical to the pre-existing stub.
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

    # ---- optional second region: .rodata ----
    # Same masked-keystream scheme, bracketed by mprotect so the section is
    # read-only again before the original entry runs.  r13 holds the region
    # base; rdx is reloaded with the .text size afterwards because the
    # epilogue's mprotect RX still needs it.
    ro_offsets = {}
    if with_rodata:
        code += b'\x4c\x8b\xab\x00\x00\x00\x00'    # mov r13, [rbx+ro_delta]
        ro_offsets['ro_delta'] = len(code) - 4
        code += b'\x49\x01\xdd'                    # add r13, rbx

        # mprotect(ro_base, ro_size, RW)
        code += b'\x4c\x89\xef'                    # mov rdi, r13
        code += b'\x4c\x89\xee'                    # mov rsi, r13
        off_ro_size1 = len(code)
        code += b'\x8b\x93\x00\x00\x00\x00'        # mov edx, [rbx+ro_size]
        code += b'\x48\x01\xd6'                    # add rsi, rdx
        code += b'\x48\x81\xc6\xff\x0f\x00\x00'    # add rsi, 0xfff
        code += b'\x48\x81\xe6\x00\xf0\xff\xff'    # and rsi, -4096
        code += b'\x48\x81\xe7\x00\xf0\xff\xff'    # and rdi, -4096
        code += b'\x48\x29\xfe'                    # sub rsi, rdi
        code += b'\xba\x07\x00\x00\x00'            # mov edx, 7
        code += b'\xb8\x0a\x00\x00\x00'            # mov eax, 10
        code += b'\x0f\x05'                        # syscall

        # decrypt: embedded_ks ^ runtime_key
        code += b'\x4c\x89\xe8'                    # mov rax, r13
        off_ro_size2 = len(code)
        code += b'\x8b\x93\x00\x00\x00\x00'        # mov edx, [rbx+ro_size]
        off_ro_ks = len(code)
        code += b'\x4c\x8d\x83\x00\x00\x00\x00'    # lea r8, [rbx+ro_ks]
        code += b'\x45\x31\xc9'                    # xor r9d, r9d
        ro_loop = len(code)
        code += b'\x47\x8a\x14\x08'                # mov r10b, [r8+r9]
        code += b'\x4d\x89\xcb'                    # mov r11, r9
        code += b'\x41\x83\xe3\x1f'                # and r11d, 31
        code += b'\x47\x32\x14\x1e'                # xor r10b, [r14+r11]
        code += b'\x46\x30\x14\x08'                # xor [rax+r9], r10b
        code += b'\x41\xff\xc1'                    # inc r9d
        code += b'\x41\x39\xd1'                    # cmp r9d, edx
        code += b'\x72' + bytes([(ro_loop - (len(code) + 2)) & 0xFF])

        # mprotect(ro_base, ro_size, R)
        code += b'\x4c\x89\xef'                    # mov rdi, r13
        code += b'\x4c\x89\xee'                    # mov rsi, r13
        off_ro_size3 = len(code)
        code += b'\x8b\x93\x00\x00\x00\x00'        # mov edx, [rbx+ro_size]
        code += b'\x48\x01\xd6'                    # add rsi, rdx
        code += b'\x48\x81\xc6\xff\x0f\x00\x00'    # add rsi, 0xfff
        code += b'\x48\x81\xe6\x00\xf0\xff\xff'    # and rsi, -4096
        code += b'\x48\x81\xe7\x00\xf0\xff\xff'    # and rdi, -4096
        code += b'\x48\x29\xfe'                    # sub rsi, rdi
        code += b'\xba\x05\x00\x00\x00'            # mov edx, 5
        code += b'\xb8\x0a\x00\x00\x00'            # mov eax, 10
        code += b'\x0f\x05'                        # syscall

        # The epilogue's mprotect RX reads rdx as the .text size.
        off_ro_restore = len(code)
        code += b'\x8b\x93\x00\x00\x00\x00'        # mov edx, [rbx+size1]

        ro_offsets.update({
            'ro_size1': off_ro_size1 + 2,
            'ro_size2': off_ro_size2 + 2,
            'ro_size3': off_ro_size3 + 2,
            'ro_keystream': off_ro_ks + 3,
            'ro_restore': off_ro_restore + 2,
        })

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

    offsets = {
        'delta': off_delta + 3,
        'size1': off_size1 + 2,
        'entry': off_entry + 3,
        'size2': off_size2 + 2,
        'keystream': off_ks + 3,
        'key_path': off_path + 3,
    }
    offsets.update(ro_offsets)
    return code, offsets


_CODE_KEYED, _OFFSETS_KEYED = _build_code_keyed()
STUB_CODE_SIZE_KEYED = len(_CODE_KEYED)

_CODE_KEYED_RO, _OFFSETS_KEYED_RO = _build_code_keyed(with_rodata=True)
STUB_CODE_SIZE_KEYED_RO = len(_CODE_KEYED_RO)


def _make_stub(text_size, original_entry, keystream, text_base_delta,
               key_path: str | None = None,
               rodata_size: int = 0,
               rodata_base_delta: int = 0,
               rodata_keystream: bytes = b""):
    if text_size <= 0:
        raise ValueError("text_size must be positive")
    if original_entry < 0:
        raise ValueError("original_entry must be non-negative")
    if len(keystream) != text_size:
        raise ValueError(
            f"keystream length {len(keystream)} != text_size {text_size}")
    if rodata_size < 0:
        raise ValueError("rodata_size must be non-negative")
    if rodata_size and len(rodata_keystream) != rodata_size:
        raise ValueError(
            f"rodata keystream length {len(rodata_keystream)} != "
            f"rodata_size {rodata_size}")
    if rodata_size and key_path is None:
        raise ValueError(
            "rodata encryption requires key_path: an unmasked keystream "
            "would make the section trivially recoverable")

    if key_path is None:
        code = bytearray(_CODE)
        offsets = _OFFSETS
        header_size = STUB_HEADER_SIZE
        key_bytes = b""
    elif rodata_size:
        code = bytearray(_CODE_KEYED_RO)
        offsets = _OFFSETS_KEYED_RO
        header_size = STUB_HEADER_SIZE_KEYED_RO
        key_bytes = key_path.encode("utf-8") + b"\x00"
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
                         data_off + header_size + text_size + rodata_size)

    header = (struct.pack('<q', text_base_delta)
              + struct.pack('<q', original_entry)
              + struct.pack('<I', text_size))
    if key_path is not None:
        # Padding to the 24-byte keyed header; the path delta lives in
        # the code's disp32, not in this field.
        header += struct.pack('<i', 0)

    if rodata_size:
        # The .rodata fields sit after the keyed header, so the .text
        # keystream offset above is unchanged.
        header += (struct.pack('<q', rodata_base_delta)
                   + struct.pack('<I', rodata_size)
                   + struct.pack('<i', 0))
        ro_ks_off = data_off + header_size + text_size
        struct.pack_into('<i', code, offsets['ro_delta'], data_off + 24)
        for key in ('ro_size1', 'ro_size2', 'ro_size3'):
            struct.pack_into('<i', code, offsets[key], data_off + 32)
        # The epilogue's mprotect RX reloads the .text size.
        struct.pack_into('<i', code, offsets['ro_restore'], data_off + 16)
        struct.pack_into('<i', code, offsets['ro_keystream'], ro_ks_off)

    return (bytes(code) + header + bytes(keystream)
            + bytes(rodata_keystream) + key_bytes)


def make_stub_with_keystream(text_size: int, original_entry: int,
                             keystream: bytes,
                             text_base_delta: int | None = None,
                             key_path: str | None = None,
                             rodata_size: int = 0,
                             rodata_base_delta: int = 0,
                             rodata_keystream: bytes = b"") -> bytes:
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
        rodata_size: When non-zero, the stub also decrypts this many bytes
            at the .rodata base, bracketed by mprotect calls.
        rodata_base_delta: Signed offset from the anchor to the .rodata base.
        rodata_keystream: Exactly ``rodata_size`` bytes of masked keystream.
    """
    if text_base_delta is None:
        text_base_delta = -(text_size + _ANCHOR)
    return _make_stub(text_size, original_entry, keystream, text_base_delta,
                      key_path=key_path,
                      rodata_size=rodata_size,
                      rodata_base_delta=rodata_base_delta,
                      rodata_keystream=rodata_keystream)


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


STUB_HEADER_SIZE_AEAD = 64
STUB_MAGIC = b"NXAEAD1\0"
STUB_VERSION = 1
_AEAD_HEADER = struct.Struct("<8sIIIIqqIqIII")


def make_aead_header(text_size: int, original_entry: int, nonce: bytes,
                     text_base_delta: int, rodata_size: int = 0,
                     rodata_base_delta: int = 0, block_index: int = 0) -> bytes:
    """Canonical 64-byte authenticated header for the compiled ELF stub."""
    if len(nonce) != 12:
        raise ValueError("AEAD nonce must be 12 bytes")
    return _AEAD_HEADER.pack(
        STUB_MAGIC, STUB_VERSION, STUB_HEADER_SIZE_AEAD, text_size, 0,
        text_base_delta, original_entry, rodata_size, rodata_base_delta,
        block_index, 0, 0,
    )


def _c_array(data: bytes) -> str:
    return ",".join(str(value) for value in data)


@functools.lru_cache(maxsize=128)
def _compile_aead_template(text_size: int, path_len: int,
                           rodata_size: int) -> tuple[bytes, int]:
    """Compile one invariant stub layout and return its header offset.

    Header/nonce/tag/path bytes are data only. Compiling a canonical layout
    once per structural shape avoids invoking GCC for every encrypted block.
    """
    import os
    from pathlib import Path
    import subprocess
    import tempfile

    if text_size <= 0 or path_len <= 1 or rodata_size < 0:
        raise ValueError("invalid AEAD stub layout")
    nonce = b"\0" * 12
    tag = b"\0" * 16
    path = b"A" * (path_len - 1) + b"\0"
    header = make_aead_header(
        text_size, 0, nonce, -(text_size + 6), rodata_size, 0, 0,
    )
    template = Path(__file__).with_name("stub_aead_template.c").read_text()
    source = template.replace("@HEADER@", _c_array(header))
    source = source.replace("@NONCE@", _c_array(nonce))
    source = source.replace("@TAG@", _c_array(tag))
    source = source.replace("@PATHLEN@", str(path_len))
    source = source.replace("@KEYPATH@", _c_array(path))
    scratch = Path(tempfile.mkdtemp(prefix="nix-aead-", dir=os.environ.get("TMPDIR")))
    try:
        c_path = scratch / "stub.c"
        elf_path = scratch / "stub.elf"
        bin_path = scratch / "stub.bin"
        script_path = scratch / "stub.ld"
        c_path.write_text(source, encoding="ascii")
        script_path.write_text(
            "ENTRY(stub_main)\n"
            "SECTIONS {\n"
            "  . = 0; .text.stub_main : { *(.text.stub_main) }\n"
            "  .text : { *(.text*) }\n"
            "  .rodata : { *(.rodata.aead.0) *(.rodata.aead.1) "
            "*(.rodata.aead.2) *(.rodata.aead.3) *(.rodata*) }\n"
            "  /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) "
            "*(.got*) *(.plt*) *(.dynamic) *(.dyn*) }\n"
            "}\n",
            encoding="ascii",
        )
        subprocess.run([
            "gcc", "-Os", "-fPIE", "-pie", "-nostdlib", "-static",
            "-fno-stack-protector", "-fno-builtin", "-Wl,--build-id=none",
            "-Wl,-z,noseparate-code", "-Wl,-T", str(script_path),
            "-o", str(elf_path), str(c_path),
        ], check=True, capture_output=True, timeout=60)
        subprocess.run([
            "objcopy", "-O", "binary", "--only-section=.text.stub_main",
            "--only-section=.text", "--only-section=.rodata",
            str(elf_path), str(bin_path),
        ], check=True, capture_output=True, timeout=30)
        blob = bin_path.read_bytes()
        rodata_path = scratch / "rodata.bin"
        subprocess.run([
            "objcopy", "--dump-section", f".rodata={rodata_path}", str(elf_path),
        ], check=True, capture_output=True, timeout=30)
        if not blob or not rodata_path.exists():
            raise RuntimeError("compiled AEAD stub is empty")
        rodata = rodata_path.read_bytes()
        header_in_rodata = rodata.find(header)
        metadata = header + nonce + tag + path
        if header_in_rodata < 0 or rodata[
                header_in_rodata:header_in_rodata + len(metadata)] != metadata:
            raise RuntimeError("compiled AEAD stub metadata layout is not contiguous")
        header_offset = len(blob) - len(rodata) + header_in_rodata
        return blob, header_offset
    finally:
        import shutil
        shutil.rmtree(scratch, ignore_errors=True)


def _compile_aead_stub(header: bytes, nonce: bytes, tag: bytes,
                       key_path: str) -> bytes:
    """Patch an invariant compiled stub with authenticated artifact metadata."""
    import os

    if len(header) != 64 or len(nonce) != 12 or len(tag) != 16:
        raise ValueError("invalid AEAD stub metadata lengths")
    fields = _AEAD_HEADER.unpack(header)
    if fields[0] != STUB_MAGIC or fields[1] != STUB_VERSION \
            or fields[2] != STUB_HEADER_SIZE_AEAD:
        raise ValueError("invalid AEAD stub header")
    path_bytes = os.fsencode(key_path) + b"\0"
    if not path_bytes or b"\0" in path_bytes[:-1]:
        raise ValueError("key path must be a non-empty NUL-free path")
    template, offset = _compile_aead_template(
        fields[3], len(path_bytes), fields[7],
    )
    built = bytearray(template)
    built[offset:offset + 64] = header
    built[offset + 64:offset + 76] = nonce
    built[offset + 76:offset + 92] = tag
    built[offset + 92:offset + 92 + len(path_bytes)] = path_bytes
    return bytes(built)


def make_stub_aead(text_size: int, original_entry: int, key_path: str,
                   nonce: bytes, tag: bytes, text_base_delta: int,
                   rodata_size: int = 0, rodata_base_delta: int = 0,
                   block_index: int = 0) -> bytes:
    """Build a standalone authenticated ELF stub with no embedded key."""
    if text_size <= 0 or original_entry < 0 or rodata_size < 0:
        raise ValueError("invalid AEAD stub sizes")
    header = make_aead_header(
        text_size, original_entry, nonce, text_base_delta,
        rodata_size, rodata_base_delta, block_index,
    )
    return _compile_aead_stub(header, nonce, tag, key_path)


def aead_header_offset(built: bytes, key_path_len: int) -> int:
    """Offset of the canonical header in a compiled AEAD stub."""
    del key_path_len
    start = 0
    while True:
        offset = built.find(STUB_MAGIC, start)
        if offset < 0:
            raise ValueError("compiled AEAD stub has no canonical header")
        if offset + STUB_HEADER_SIZE_AEAD <= len(built):
            fields = _AEAD_HEADER.unpack_from(built, offset)
            if fields[1] == STUB_VERSION and fields[2] == STUB_HEADER_SIZE_AEAD:
                return offset
        start = offset + 1


def stub_size(text_size: int, key_path_len: int = 0,
              rodata_size: int = 0, aead: bool = False) -> int:
    if aead:
        if not key_path_len:
            raise ValueError("AEAD stub requires a sidecar key path")
        template, _ = _compile_aead_template(
            max(text_size, 1), key_path_len, rodata_size,
        )
        return len(template)
    if key_path_len and rodata_size:
        return (STUB_CODE_SIZE_KEYED_RO + STUB_HEADER_SIZE_KEYED_RO
                + text_size + rodata_size + key_path_len)
    if key_path_len:
        return (STUB_CODE_SIZE_KEYED + STUB_HEADER_SIZE_KEYED
                + text_size + key_path_len)
    return STUB_CODE_SIZE + STUB_HEADER_SIZE + text_size
