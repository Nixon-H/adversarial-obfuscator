"""compress_contest.py — best-of-N compression contest for fallback blobs.

Tries zlib / bz2 / lzma (+ pyzstd only if importable) and returns the
smallest blob.  The fallback envelope prefixes a single backend-ID byte so
the loader can decompress correctly while staying backward compatible with
legacy prefix-less zlib blobs.

Backend IDs (chosen to never collide with legacy zlib streams, which start
with 0x78):
    zlib -> 0x00, bz2 -> 0x01, lzma -> 0x02, zstd -> 0x03
"""

from __future__ import annotations

import bz2
import lzma
import zlib

BACKEND_IDS: dict[str, int] = {
    "zlib": 0x00,
    "bz2": 0x01,
    "lzma": 0x02,
    "zstd": 0x03,
}

ID_TO_BACKEND: dict[int, str] = {v: k for k, v in BACKEND_IDS.items()}


def _candidates(data: bytes) -> list[tuple[str, bytes]]:
    out: list[tuple[str, bytes]] = []
    try:
        out.append(("zlib", zlib.compress(data, 9)))
    except Exception:
        pass
    try:
        out.append(("bz2", bz2.compress(data, 9)))
    except Exception:
        pass
    try:
        out.append(("lzma", lzma.compress(data)))
    except Exception:
        pass
    try:
        import pyzstd  # type: ignore

        out.append(("zstd", pyzstd.compress(data)))
    except Exception:
        pass  # pyzstd not installed — skip silently
    return out


def best_compress(data: bytes) -> tuple[str, bytes]:
    """Return (backend_name, blob) for the smallest successful compression."""
    cands = _candidates(bytes(data))
    if not cands:
        raise RuntimeError("no compression backend available")
    return min(cands, key=lambda kv: len(kv[1]))


def decompress_auto(name: str, blob: bytes) -> bytes:
    """Inverse of a single backend compression."""
    if name == "zlib":
        return zlib.decompress(blob)
    if name == "bz2":
        return bz2.decompress(blob)
    if name == "lzma":
        return lzma.decompress(blob)
    if name == "zstd":
        try:
            import pyzstd  # type: ignore
        except ImportError as e:
            raise ValueError("zstd blob but pyzstd not installed") from e
        return pyzstd.decompress(blob)
    raise ValueError(f"unknown compression backend: {name!r}")


def pack(name: str, blob: bytes) -> bytes:
    """Prefix a compressed blob with its backend-ID byte."""
    try:
        bid = BACKEND_IDS[name]
    except KeyError as e:
        raise ValueError(f"unknown compression backend: {name!r}") from e
    return bytes([bid]) + bytes(blob)


def unpack_and_decompress(data: bytes) -> bytes:
    """Decompress a packed envelope; legacy prefix-less blobs decode as zlib."""
    raw = bytes(data)
    if raw and raw[0] in ID_TO_BACKEND:
        return decompress_auto(ID_TO_BACKEND[raw[0]], raw[1:])
    # Legacy blob without prefix — always zlib.
    return zlib.decompress(raw)
