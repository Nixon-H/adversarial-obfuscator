"""runtime_config.py

Purpose:
    Produce the runtime's start-up configuration from a built binary.

Architectural Role:
    ``runtime/src/integrity.rs`` verifies the process's own executable
    text, but ``RuntimeConfig::default()`` leaves
    ``integrity_expected_crc`` at ``None`` — so ``verify_text_section``
    was never called and the check was a no-op. The relay now reads this
    file at start-up; this module is what writes it, at build time,
    from the binary that was just built.

    The value is the CRC32 of the executable segment **exactly as the
    kernel maps it**: the PT_LOAD with PF_X, page-aligned at both ends,
    read from the file and zero-padded if the segment is shorter than
    its memory image. ``verify_text_section`` hashes that same range
    from ``/proc/self/maps``, so the two agree by construction.

Security Relevance:
    An integrity check with no expected value is decoration. This is
    the value.
"""

from __future__ import annotations

import json
import os
import struct
import sys

CONFIG_NAME = "runtime_config.json"
PAGE = 0x1000


def _crc32_table():
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            crc = (0xEDB88320 ^ (crc >> 1)) if (crc & 1) else (crc >> 1)
        table.append(crc & 0xFFFFFFFF)
    return table


_CRC_TABLE = _crc32_table()


def crc32(data: bytes) -> int:
    """The same CRC-32 as runtime/src/integrity.rs (IEEE, reflected)."""
    crc = 0xFFFFFFFF
    for b in data:
        crc = _CRC_TABLE[(crc ^ b) & 0xFF] ^ (crc >> 8)
    return crc ^ 0xFFFFFFFF


def executable_segment(path: str) -> bytes:
    """The bytes the kernel maps for the executable PT_LOAD segment."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"\x7fELF":
        raise ValueError(f"{path} is not an ELF binary")
    is64 = data[4] == 2
    if is64:
        e_phoff = struct.unpack_from("<Q", data, 0x20)[0]
    else:
        e_phoff = struct.unpack_from("<I", data, 0x20)[0]
    e_phentsize, e_phnum = struct.unpack_from("<HH", data, 0x36)

    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        if is64:
            p_type, p_flags = struct.unpack_from("<II", data, off)
            p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, _align = struct.unpack_from(
                "<QQQQQQ", data, off + 8
            )
        else:
            (p_type, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz,
             p_flags, _align) = struct.unpack_from("<IIIIIIII", data, off)
        if p_type != 1:          # PT_LOAD
            continue
        if not (p_flags & 1):    # PF_X
            continue
        start = p_vaddr & ~(PAGE - 1)
        end = (p_vaddr + p_memsz + PAGE - 1) & ~(PAGE - 1)
        file_off = p_offset & ~(PAGE - 1)
        length = end - start
        seg = data[file_off:file_off + length]
        if len(seg) < length:
            seg = seg + b"\x00" * (length - len(seg))
        return seg
    raise ValueError(f"{path} has no executable PT_LOAD segment")


def expected_crc(path: str) -> int:
    return crc32(executable_segment(path))


def write_config(binary_path: str, out_dir: str | None = None) -> str:
    """Write runtime_config.json next to the binary; returns its path."""
    out_dir = out_dir or os.path.dirname(os.path.abspath(binary_path))
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, CONFIG_NAME)
    payload = {
        "integrity_expected_crc": expected_crc(binary_path),
        "binary": os.path.basename(binary_path),
    }
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, path)
    return path


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("usage: python3 -m scripts.runtime_config <binary>", file=sys.stderr)
        return 2
    path = write_config(argv[0])
    with open(path) as f:
        data = json.load(f)
    print(f"  RTCFG   {path} (crc32=0x{data['integrity_expected_crc']:08x})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
