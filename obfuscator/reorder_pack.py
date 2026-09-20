"""reorder_pack.py — deterministic chunk-reorder + substitution container.

Splits blobs into chunks, shuffles chunk order via a SHA-256-seeded
Fisher-Yates shuffle, then applies a seeded 256-byte substitution table.
No ``random`` module is used so builds are reproducible for a given seed.
"""

from __future__ import annotations

import hashlib


class _SeededRng:
    """Counter-based PRNG: entropy = sha256(seed + counter).digest()."""

    def __init__(self, seed: bytes) -> None:
        if not isinstance(seed, (bytes, bytearray)):
            raise TypeError("seed must be bytes")
        self._seed = bytes(seed)
        self._counter = 0
        self._buf = b""

    def _refill(self) -> None:
        counter = self._counter.to_bytes(8, "big")
        self._buf += hashlib.sha256(self._seed + counter).digest()
        self._counter += 1

    def randbelow(self, n: int) -> int:
        """Return a uniform-ish int in range(n) using rejection sampling."""
        if n <= 0:
            raise ValueError("randbelow requires n > 0")
        # Rejection sampling for unbiased results.
        limit = 256 - (256 % n)
        while True:
            if not self._buf:
                self._refill()
            b = self._buf[0]
            self._buf = self._buf[1:]
            if b < limit:
                return b % n

    def shuffle(self, xs: list) -> None:
        """In-place Fisher-Yates shuffle using this PRNG."""
        for i in range(len(xs) - 1, 0, -1):
            j = self.randbelow(i + 1)
            xs[i], xs[j] = xs[j], xs[i]


def _shuffled_table(seed: bytes) -> bytes:
    rng = _SeededRng(seed + b"|table|")
    table = list(range(256))
    rng.shuffle(table)
    return bytes(table)


def _shuffled_order(n: int, seed: bytes) -> list[int]:
    rng = _SeededRng(seed + b"|order|")
    order = list(range(n))
    rng.shuffle(order)
    return order


def pack_container(
    blobs: list[bytes], seed: bytes, chunk_size: int = 4096
) -> dict:
    """Pack *blobs* into a shuffled, substituted container dict.

    Returns a dict with (at minimum) keys ``order`` (list[int]),
    ``table`` (256 bytes) and ``data`` (bytes), plus the metadata needed
    to invert the transform. Round-trips through :func:`unpack_container`.
    """
    if chunk_size is None or int(chunk_size) <= 0:
        raise ValueError("chunk_size must be a positive int")
    chunk_size = int(chunk_size)
    blobs = [bytes(b) for b in blobs]

    table = _shuffled_table(bytes(seed))

    # Split each blob into chunk_size pieces (original order).
    chunks: list[bytes] = []
    for blob in blobs:
        if len(blob) == 0:
            continue
        for off in range(0, len(blob), chunk_size):
            chunks.append(blob[off : off + chunk_size])

    n = len(chunks)
    order = _shuffled_order(n, bytes(seed))
    clens_orig = [len(c) for c in chunks]
    shuffled = [chunks[order[i]] for i in range(n)] if n else []
    chunk_lens = [clens_orig[order[i]] for i in range(n)] if n else []
    joined = b"".join(shuffled)
    data = bytes(table[b] for b in joined)

    return {
        "order": list(order),
        "table": bytes(table),
        "data": bytes(data),
        "sizes": [len(b) for b in blobs],
        "chunk_lens": list(chunk_lens),
        "chunk_size": chunk_size,
        "count": len(blobs),
    }


def unpack_container(pack: dict) -> list[bytes]:
    """Invert :func:`pack_container`. Handles empty containers."""
    order = list(pack["order"])
    table = bytes(pack["table"])
    data = bytes(pack["data"])
    sizes = list(pack.get("sizes", []))
    chunk_lens = list(pack.get("chunk_lens", []))

    if len(table) != 256:
        raise ValueError("table must be exactly 256 bytes")
    if sorted(table) != list(range(256)):
        raise ValueError("table must be a permutation of range(256)")

    n = len(order)
    if sorted(order) != list(range(n)):
        raise ValueError("order must be a permutation of range(n_chunks)")
    if len(chunk_lens) != n:
        raise ValueError("chunk_lens length must match order length")

    # Invert substitution.
    inv = bytearray(256)
    for i, v in enumerate(table):
        inv[v] = i
    raw = bytes(inv[b] for b in data)

    if sum(chunk_lens) != len(raw):
        raise ValueError("chunk_lens do not match data length")

    # Split back into shuffled chunks, then invert the permutation.
    shuffled: list[bytes] = []
    off = 0
    for ln in chunk_lens:
        shuffled.append(raw[off : off + ln])
        off += ln
    orig: list[bytes] = [b""] * n
    for i, o in enumerate(order):
        orig[o] = shuffled[i]
    big = b"".join(orig)

    if sum(sizes) != len(big):
        raise ValueError("blob sizes do not match payload length")
    blobs: list[bytes] = []
    pos = 0
    for ln in sizes:
        blobs.append(big[pos : pos + ln])
        pos += ln
    return blobs
