"""Regression tests for the precision audit shard A5.

Each test names a concrete failure mode found by reading the five loader-security
modules linearly. They are intentionally isolated and fast.
"""

import base64
import ctypes
import random
import re
import struct
import sys
import types

import pytest

from obfuscator import driver_blocklist as db
from obfuscator import native_harden as nh
from obfuscator import section_split as ss
from obfuscator.anti_rea import canary_tokens
from obfuscator.vm_dispatch import virtualize_source


# ── section_split ────────────────────────────────────────────────────────


def test_stream_join_sealed_allocation_failure_still_returns_payload(monkeypatch):
    """A hardening allocation failure must not turn a valid payload into b""."""
    payload = b"section-plaintext-that-must-survive" * 8
    key = b"K" * 32
    pack = ss.split_sealed(payload, sections=3, key=key)

    def fail_seal(_buf, protect=None):
        raise MemoryError("simulated mapping allocation failure")

    monkeypatch.setattr(ss, "seal_joined", fail_seal)
    sealed = ss.stream_join_sealed(pack, key)
    try:
        assert len(sealed) == len(payload)
        assert bytes(sealed.view) == payload
    finally:
        sealed.close()


def test_stream_join_sealed_wipes_its_intermediate_join(monkeypatch):
    """The copied join is internal scratch, not a second plaintext kept in heap."""
    payload = b"wipe-me" * 20
    scratch = bytearray(payload)
    monkeypatch.setattr(ss, "stream_join", lambda _pack, _key: scratch)

    def copy_seal(buf, protect=None):
        return types.SimpleNamespace(copied=bytes(buf))

    monkeypatch.setattr(ss, "seal_joined", copy_seal)
    result = ss.stream_join_sealed(object(), b"key")
    assert result.copied == payload
    assert scratch == b"\x00" * len(payload)


def test_stream_snippet_dispatches_zstd_envelopes(monkeypatch):
    """0x03 is zstd in the compression envelope, never legacy zlib."""

    class FakeZstdDecompressor:
        def __init__(self):
            self.eof = False

        def decompress(self, data):
            # Toy stream format for dispatch testing: byte 0x04 terminates
            # the frame, every prior byte passes through unchanged.
            out = bytearray()
            for byte in data:
                if byte == 4:
                    self.eof = True
                elif not self.eof:
                    out.append(byte)
            return bytes(out)

    fake = types.SimpleNamespace(ZstdDecompressor=FakeZstdDecompressor)
    monkeypatch.setitem(sys.modules, "pyzstd", fake)

    payload = b"zstd backend dispatch payload" * 5
    assert b"\x04" not in payload
    stream = b"\x03" + payload + b"\x04"
    js, key = ss.pack_json(stream, sections=4, key=b"Z" * 32)
    ns = {}
    exec(compile(ss.emit_stream_snippet(), "<stream>", "exec"), ns)
    out = ns["_nx_section_stream"](base64.b85encode(js).decode("ascii"), key)
    assert out is not None
    assert bytes(out) == payload


# ── anti_rea ─────────────────────────────────────────────────────────────


def test_aws_canary_tokens_have_the_real_20_character_shape():
    """AKIA canaries must match the scanner-recognised access-key shape."""
    tokens = canary_tokens(random.Random(1), 3)[:3]
    assert all(len(tok) == 20 for tok in tokens)
    assert all(re.fullmatch(r"AKIA[0-9A-Z]{16}", tok) for tok in tokens)
    assert all(tok.endswith("EXAMPLE") for tok in tokens)


# ── native_harden ────────────────────────────────────────────────────────


def _pe32_with_load_config(guard_flags):
    """Minimal PE32 image with GuardFlags at the authoritative 32-bit offset."""
    e_lfanew = 0x80
    head = bytearray(e_lfanew)
    head[:2] = b"MZ"
    struct.pack_into("<I", head, 0x3C, e_lfanew)
    coff = bytearray(20)
    struct.pack_into("<H", coff, 0, 0x014C)       # Intel 386
    struct.pack_into("<H", coff, 2, 1)            # one section
    struct.pack_into("<H", coff, 16, 0xE0)        # PE32 optional-header size
    opt = bytearray(0xE0)
    struct.pack_into("<H", opt, 0, 0x10B)         # PE32
    struct.pack_into("<H", opt, 70, nh.PE_GUARD_CF)
    struct.pack_into("<I", opt, 92, 16)           # NumberOfRvaAndSizes
    lc_rva = 0x1000
    struct.pack_into("<II", opt, 96 + 10 * 8, lc_rva, 0x100)
    headers = bytes(head) + b"PE\0\0" + bytes(coff) + bytes(opt)
    raw_ptr = 0x200
    section = bytearray(40)
    section[:5] = b".data"
    struct.pack_into("<IIII", section, 8, 0x100, lc_rva, 0x100, raw_ptr)
    body = bytearray(headers) + bytes(section)
    while len(body) < raw_ptr + 0x100:
        body.append(0)
    struct.pack_into("<I", body, raw_ptr + nh.LOAD_CONFIG_GUARD_FLAGS_OFFSET32,
                     guard_flags)
    return bytes(body)


def test_pe32_guard_flags_are_read_at_the_32_bit_load_config_offset():
    flags = nh.PE_GUARD_CF_INSTRUMENTED | nh.PE_GUARD_CF_FUNCTION_TABLE_PRESENT
    report = nh.verify_pe_bytes(_pe32_with_load_config(flags))
    assert report["valid"] is True
    assert report["cfg_guard_flags"] == flags
    assert report["cfg_instrumented"] is True
    assert report["cfg_function_table"] is True


def test_macho_filetype_names_use_the_real_numeric_mapping():
    def macho(filetype):
        data = bytearray(32)
        struct.pack_into("<I", data, 0, 0xFEEDFACF)
        struct.pack_into("<I", data, 12, filetype)
        return bytes(data)

    assert nh.verify_macho_bytes(macho(9))["filetype_name"] == "dylib_stub"
    assert nh.verify_macho_bytes(macho(10))["filetype_name"] == "dsym"
    assert nh.verify_macho_bytes(macho(11))["filetype_name"] == "kext_bundle"


# ── driver_blocklist ─────────────────────────────────────────────────────


def test_windows_file_version_reads_the_fixedfileinfo_version_dwords(monkeypatch):
    """dwSignature/dwStrucVersion are not dwFileVersionMS/LS."""
    ms = (2 << 16) | 3
    ls = (0 << 16) | 0
    image = struct.pack("<4I", 0xFEEF04BD, 0x00010000, ms, ls) + b"\0" * 64

    class FakeVersionDLL:
        def GetFileVersionInfoSizeW(self, _path, _reserved):
            return len(image)

        def GetFileVersionInfoW(self, _path, _zero, size, buf):
            ctypes.memmove(buf, image, min(size, len(image)))
            return 1

        def VerQueryValueW(self, buf, key, ptr_ref, len_ref):
            assert key == "\\"
            ctypes.cast(ptr_ref, ctypes.POINTER(ctypes.c_void_p)).contents.value = (
                ctypes.addressof(buf))
            ctypes.cast(len_ref, ctypes.POINTER(ctypes.c_uint)).contents.value = len(image)
            return 1

    fake = FakeVersionDLL()
    monkeypatch.setattr(db.platform, "system", lambda: "Windows")
    monkeypatch.setattr(ctypes, "WinDLL", lambda name: fake, raising=False)
    assert db.get_file_version(r"C:\drivers\dbutildrv2.sys") == "2.3.0.0"


# ── vm_dispatch ──────────────────────────────────────────────────────────


def _vm_result(source, args, family):
    code, stats = virtualize_source(source, seed=11, family=family)
    ns = {}
    exec(compile(code, "<vm>", "exec"), ns)
    fn = ns["f"]
    try:
        return ("ok", fn(*args)), stats, code
    except Exception as exc:
        return ("exc", type(exc).__name__, str(exc)), stats, code


def _native_result(source, args):
    ns = {}
    exec(compile(source, "<native>", "exec"), ns)
    try:
        return ("ok", ns["f"](*args))
    except Exception as exc:
        return ("exc", type(exc).__name__, str(exc))


@pytest.mark.parametrize("family", ("a", "b"))
def test_vm_boolean_ops_short_circuit_instead_of_evaluating_both_sides(family):
    for source in (
        "def f():\n    return False and (1 / 0)\n",
        "def f():\n    return True or (1 / 0)\n",
    ):
        result, stats, _code = _vm_result(source, (), family)
        assert stats["virtualized"] == 1
        assert result == _native_result(source, ())


@pytest.mark.parametrize("family", ("a", "b"))
def test_vm_boolean_ops_preserve_operand_results(family):
    source = "def f(a, b):\n    return (a and b, a or b)\n"
    for args in ((0, 5), (3, 0), ("", None), ([1], [2])):
        result, stats, _code = _vm_result(source, args, family)
        assert stats["virtualized"] == 1
        assert result == _native_result(source, args)


@pytest.mark.parametrize("family", ("a", "b"))
def test_vm_positional_only_defaults_are_emitted_in_the_right_place(family):
    source = "def f(a, b=10, /, c=20):\n    return a + b + c\n"
    result, stats, code = _vm_result(source, (1,), family)
    assert stats["virtualized"] == 1, "pos-only defaults were silently skipped"
    assert result == ("ok", 31)
    ns = {}
    exec(compile(code, "<vm>", "exec"), ns)
    import inspect
    assert str(inspect.signature(ns["f"])) == "(a, b=10, /, c=20)"


@pytest.mark.parametrize("family", ("a", "b"))
def test_vm_augassign_uses_real_in_place_semantics(family):
    source = "def f():\n    x = []\n    y = x\n    x += [1]\n    return (x, y)\n"
    result, stats, _code = _vm_result(source, (), family)
    assert stats["virtualized"] == 1
    assert result == _native_result(source, ())
    assert result == ("ok", ([1], [1]))


@pytest.mark.parametrize("family", ("a", "b"))
def test_vm_unassigned_locals_raise_unboundlocalerror_not_none(family):
    source = "def f(cond):\n    if cond:\n        x = 1\n    return x\n"
    result, stats, _code = _vm_result(source, (False,), family)
    assert stats["virtualized"] == 1
    assert result == _native_result(source, (False,))
    assert result[0] == "exc" and result[1] == "UnboundLocalError"


@pytest.mark.parametrize("family", ("a", "b"))
def test_vm_rejects_a_body_local_named_range_instead_of_miscompiling(family):
    source = ("def f():\n    range = 1\n    total = 0\n"
              "    for i in range(3):\n        total = total + i\n    return total\n")
    result, stats, _code = _vm_result(source, (), family)
    assert stats["virtualized"] == 0, "a local range shadow must stay unvirtualized"
    assert result == _native_result(source, ())
    assert result[0] == "exc" and result[1] == "TypeError"
