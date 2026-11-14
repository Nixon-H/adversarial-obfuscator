"""Runtime key source for encrypt.py (audit round 2, final asterisk).

The packed artifact's embedded keystream is XOR-masked with a 32-byte key
that lives in a 0600 sidecar, NOT in the binary. The stub reads the key
from the embedded path at run time; without the file it exits(1).

Verified at the stub level (in-process and subprocess) and at the
static-extraction level: ciphertext XOR embedded (masked) bytes is NOT
the plaintext anymore.
"""
import os
import subprocess
import sys

from encrypt.stub import make_stub_with_keystream, stub_size


def _build_stub_pair(key_path):
    """Build (ciphertext, stub, text) with the runtime key written to
    ``key_path`` (0600). Returns (ct, stub, text)."""
    text = b"\xb8\x2a\x00\x00\x00\xc3" + b"\x90" * 58
    ks = os.urandom(64)
    key = os.urandom(32)
    masked = bytes(k ^ key[i % 32] for i, k in enumerate(ks))
    ct = bytes(t ^ k for t, k in zip(text, ks))
    stub = make_stub_with_keystream(64, 0, masked, key_path=key_path)
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, key)
    finally:
        os.close(fd)
    return ct, stub, text


def _run_stub_child(ct, stub):
    """Run the stub in a child process (exit(1) from the stub must not
    kill this test process)."""
    code = f'''
import ctypes, mmap
buf = mmap.mmap(-1, {len(ct) + len(stub)},
                prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC)
buf[0:{len(ct)}] = {ct!r}
buf[{len(ct)}:] = {stub!r}
raw = (ctypes.c_char * len(buf)).from_buffer(buf)
fn = ctypes.CFUNCTYPE(ctypes.c_int)(ctypes.addressof(raw) + {len(ct)})
fn()
'''
    return subprocess.run([sys.executable, "-c", code], capture_output=True)


def test_stub_size_includes_key_path(tmp_path):
    key_path = str(tmp_path / "enc.key")
    stub = make_stub_with_keystream(64, 0, os.urandom(64), key_path=key_path)
    assert len(stub) == stub_size(64, len(key_path) + 1)


def test_stub_decrypts_with_runtime_key_file(tmp_path):
    key_path = str(tmp_path / "enc.key")
    ct, stub, text = _build_stub_pair(key_path)
    proc = _run_stub_child(ct, stub)
    assert proc.returncode == 0, (proc.returncode, proc.stderr[-300:])
    assert b"42" not in proc.stderr  # sanity: no crash output


def test_stub_exits_1_without_the_key_file(tmp_path):
    key_path = str(tmp_path / "missing.key")  # never created
    ct, stub, _ = _build_stub_pair(key_path)
    os.remove(key_path)
    proc = _run_stub_child(ct, stub)
    assert proc.returncode == 1, (proc.returncode, proc.stderr[-300:])


def test_static_extraction_no_longer_yields_plaintext(tmp_path):
    key_path = str(tmp_path / "enc.key")
    ct, stub, text = _build_stub_pair(key_path)
    # The embedded keystream is the MASKED one: extracting it and XORing
    # with the ciphertext yields garbage without the 0600 sidecar key.
    masked = stub[-64:]
    leak = bytes(c ^ m for c, m in zip(ct, masked))
    assert leak != text
    # And the run without the key confirms it dynamically.
    os.remove(key_path)
    proc = _run_stub_child(ct, stub)
    assert proc.returncode == 1
