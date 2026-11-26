"""RFC 8439 and native-stub regressions for sidecar-keyed ELF encryption."""

import os
import struct
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


KEY = bytes.fromhex(
    "808182838485868788898a8b8c8d8e8f"
    "909192939495969798999a9b9c9d9e9f"
)
NONCE = bytes.fromhex("070000004041424344454647")
AAD = bytes.fromhex("50515253c0c1c2c3c4c5c6c7")
PLAINTEXT = (
    b"Ladies and Gentlemen of the class of '99: If I could offer you "
    b"only one tip for the future, sunscreen would be it."
)
CIPHERTEXT = bytes.fromhex(
    "d31a8d34648e60db7b86afbc53ef7ec2"
    "a4aded51296e08fea9e2b5a736ee62d6"
    "3dbea45e8ca9671282fafb69da92728b"
    "1a71de0a9e060b2905d6a5b67ecd3b36"
    "92ddbd7f2d778b8c9803aee328091b58"
    "fab324e4fad675945585808b4831d7bc"
    "3ff4def08e4b7a9de576d26586cec64b"
    "6116"
)
TAG = bytes.fromhex("1ae10b594f09e26a7e902ecbd0600691")


def test_rfc8439_aead_known_answer():
    from encrypt.chacha20poly1305 import open as aead_open, seal

    ciphertext, tag = seal(KEY, NONCE, PLAINTEXT, AAD)
    assert ciphertext == CIPHERTEXT
    assert tag == TAG
    assert aead_open(KEY, NONCE, ciphertext, tag, AAD) == PLAINTEXT


@pytest.mark.parametrize("length", [0, 1, 15, 16, 17, 63, 64, 65, 4097])
def test_aead_roundtrip_across_block_boundaries(length):
    from encrypt.chacha20poly1305 import open as aead_open, seal

    plaintext = bytes((i * 37) & 0xFF for i in range(length))
    aad = b"context" + length.to_bytes(4, "little")
    ciphertext, tag = seal(KEY, NONCE, plaintext, aad)
    assert aead_open(KEY, NONCE, ciphertext, tag, aad) == plaintext


@pytest.mark.parametrize("part", ["key", "nonce", "ciphertext", "tag", "aad"])
def test_aead_rejects_tampering(part):
    from encrypt.chacha20poly1305 import open as aead_open, seal

    ciphertext, tag = seal(KEY, NONCE, PLAINTEXT, AAD)
    key, nonce, aad = KEY, NONCE, AAD
    if part == "key":
        key = bytes([key[0] ^ 1]) + key[1:]
    elif part == "nonce":
        nonce = bytes([nonce[0] ^ 1]) + nonce[1:]
    elif part == "ciphertext":
        ciphertext = bytes([ciphertext[0] ^ 1]) + ciphertext[1:]
    elif part == "tag":
        tag = bytes([tag[0] ^ 1]) + tag[1:]
    else:
        aad += b"changed"

    with pytest.raises(ValueError, match="authentication"):
        aead_open(key, nonce, ciphertext, tag, aad)


def _stub_material(tmp_path, text, rodata=b"", key=KEY, nonce=NONCE):
    from encrypt import chacha20poly1305
    from encrypt import stub

    key_path = tmp_path / "artifact.key"
    key_path.write_bytes(key)
    key_path.chmod(0o600)
    path_len = len(os.fsencode(key_path)) + 1
    stub_len = stub.stub_size(len(text), path_len, len(rodata), aead=True)
    page = 4096
    stub_offset = (len(text) + page - 1) & ~(page - 1)
    ro_offset = stub_offset + ((stub_len + page - 1) & ~(page - 1))
    text_delta = -stub_offset - 6
    ro_delta = ro_offset - stub_offset - 6 if rodata else 0
    header = stub.make_aead_header(
        len(text), 0, nonce, text_base_delta=text_delta,
        rodata_size=len(rodata), rodata_base_delta=ro_delta, block_index=3,
    )
    ciphertext, tag = chacha20poly1305.seal(
        key, nonce, text + rodata, header
    )
    text_ct = ciphertext[:len(text)]
    ro_ct = ciphertext[len(text):]
    built = stub.make_stub_aead(
        len(text), 0, str(key_path), nonce, tag,
        text_base_delta=text_delta, rodata_size=len(rodata),
        rodata_base_delta=ro_delta, block_index=3,
    )
    header_offset = stub.aead_header_offset(built, path_len)
    assert built[header_offset:header_offset + 64] == header
    return text_ct, built, ro_ct, text, rodata, key_path


def _run_stub(text_ct, built, ro_ct=b"", ro_expected=b""):
    page_size = 4096
    stub_offset = (len(text_ct) + page_size - 1) & ~(page_size - 1)
    blob = text_ct + b"\0" * (stub_offset - len(text_ct)) + built
    ro_offset = 0
    if ro_ct:
        ro_offset = stub_offset + ((len(built) + page_size - 1) & ~(page_size - 1))
        blob += b"\0" * (ro_offset - stub_offset - len(built)) + ro_ct
    mapped_size = (len(blob) + page_size - 1) & ~(page_size - 1)
    program = f'''
import ctypes
import mmap
blob = {blob!r}
mm = mmap.mmap(-1, {mapped_size}, prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC)
mm.write(blob)
raw = (ctypes.c_char * len(mm)).from_buffer(mm)
fn = ctypes.CFUNCTYPE(ctypes.c_int)(ctypes.addressof(raw) + {stub_offset})
result = fn()
assert result == 42, result
assert bytes(mm[{ro_offset}:{ro_offset + len(ro_expected)}]) == {ro_expected!r}
del fn, raw
mm.close()
'''
    return subprocess.run(
        [sys.executable, "-c", program], capture_output=True, timeout=10
    )


def _text():
    return b"\xb8\x2a\x00\x00\x00\xc3" + b"\x90" * 59


@pytest.mark.skipif(
    not sys.platform.startswith("linux") or os.uname().machine != "x86_64",
    reason="native stub is Linux x86-64",
)
def test_native_stub_authenticates_and_decrypts_text(tmp_path):
    text = _text()
    text_ct, built, _, _, _, _ = _stub_material(tmp_path, text)
    run = _run_stub(text_ct, built)
    assert run.returncode == 0, run.stderr[-500:]


@pytest.mark.skipif(
    not sys.platform.startswith("linux") or os.uname().machine != "x86_64",
    reason="native stub is Linux x86-64",
)
def test_native_stub_authenticates_and_decrypts_rodata(tmp_path):
    text = _text()
    rodata = b"secret rodata crosses a ChaCha block boundary"
    text_ct, built, ro_ct, _, _, _ = _stub_material(tmp_path, text, rodata)
    run = _run_stub(text_ct, built, ro_ct, rodata)
    assert run.returncode == 0, run.stderr[-500:]


def test_authenticated_stub_embeds_no_key_or_keystream(tmp_path):
    from encrypt import stub

    text = _text()
    _, built, _, _, _, key_path = _stub_material(tmp_path, text)
    assert len(built) == stub.stub_size(
        len(text), len(os.fsencode(key_path)) + 1, aead=True)
    assert text not in built
    assert KEY not in built
    assert NONCE in built
    assert "i % 32" not in open(stub.__file__, encoding="utf-8").read()


@pytest.mark.skipif(
    not sys.platform.startswith("linux") or os.uname().machine != "x86_64",
    reason="native stub is Linux x86-64",
)
@pytest.mark.parametrize("part", ["nonce", "tag", "ciphertext", "header", "key"])
def test_native_stub_fails_closed_on_tampering(tmp_path, part):
    from encrypt import stub

    text = _text()
    text_ct, built, _, _, _, key_path = _stub_material(tmp_path, text)
    header_offset = stub.aead_header_offset(built, len(os.fsencode(key_path)) + 1)
    if part == "nonce":
        built = bytearray(built)
        built[header_offset + 64] ^= 1
        built = bytes(built)
    elif part == "tag":
        built = bytearray(built)
        built[header_offset + 64 + 12] ^= 1
        built = bytes(built)
    elif part == "ciphertext":
        text_ct = bytes([text_ct[0] ^ 1]) + text_ct[1:]
    elif part == "header":
        built = bytearray(built)
        built[header_offset] ^= 1
        built = bytes(built)
    else:
        key_path.write_bytes(b"x" * 32)

    run = _run_stub(text_ct, built)
    assert run.returncode not in (0, 42), (run.returncode, run.stderr[-500:])


@pytest.mark.skipif(
    not sys.platform.startswith("linux") or os.uname().machine != "x86_64",
    reason="native stub is Linux x86-64",
)
def test_native_stub_requires_the_separate_key_file(tmp_path):
    text = _text()
    text_ct, built, _, _, _, key_path = _stub_material(tmp_path, text)
    key_path.unlink()
    run = _run_stub(text_ct, built)
    assert run.returncode not in (0, 42)


def test_aead_compilation_is_cached_per_structural_layout():
    from encrypt import stub

    stub._compile_aead_template.cache_clear()
    path = "/tmp/artifact.key"
    stub.make_stub_aead(64, 0, path, b"\x01" * 12, b"\x02" * 16, -70)
    stub.make_stub_aead(
        64, 0, path, b"\x03" * 12, b"\x04" * 16, -70, block_index=9,
    )
    info = stub._compile_aead_template.cache_info()
    assert info.misses == 1
    assert info.hits == 1


def test_authenticated_header_has_fixed_canonical_layout():
    from encrypt import stub

    header = stub.make_aead_header(
        64, 16, NONCE, text_base_delta=-70, rodata_size=19,
        rodata_base_delta=1234, block_index=7,
    )
    assert len(header) == stub.STUB_HEADER_SIZE_AEAD == 64
    magic, version, size, text_size, flags, delta, entry, ro_size, ro_delta, index, _, _ = (
        struct.unpack("<8sIIIIqqIqIII", header)
    )
    assert (magic, version, size, text_size, flags) == (
        stub.STUB_MAGIC, stub.STUB_VERSION, 64, 64, 0
    )
    assert (delta, entry, ro_size, ro_delta, index) == (-70, 16, 19, 1234, 7)
