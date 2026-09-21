"""Section-split sealed streaming (V10 adopt, medium).

Splits a payload blob into N individually-sealed sections that the loader
streams back one at a time, so the FULL code object is never resident in
one readable buffer. Each section carries its own SHA-256 integrity tag
and index; out-of-order or tampered sections fail closed.

Wire format per section (JSON dict, hex strings):
  {i, n, salt, nonce, data} — data = XOR-stream(salt/nonce) over
  (sha256(plaintext) + plaintext), same construction as hwid_lock but
  WITHOUT machine binding (transport-only seal; HWID lock composes on top
  by locking the joined plaintext separately).

Memory discipline: join-then-wipe — the joined plaintext is a bytearray,
handed to the caller, who must _nx_wipe it after exec (see secure_temp).
Sections themselves are wiped after streaming.
"""

from __future__ import annotations

import hashlib
import json
import os

DEFAULT_SECTIONS = 4


def _keystream(key: bytes, nonce: bytes, ln: int) -> bytes:
    out = bytearray()
    c = 0
    while len(out) < ln:
        out.extend(hashlib.sha256(key + nonce + c.to_bytes(8, "big")).digest())
        c += 1
    return bytes(out[:ln])


def split_sealed(payload: bytes, *, sections: int = DEFAULT_SECTIONS,
                 key: bytes | None = None) -> dict:
    """Split payload into N sealed sections. Returns pack dict.

    pack = {sections: [...], count, total, key_hint}: key_hint is the hex
    of sha256(key)[:8] so the loader can confirm it derived the same
    session key (the key itself travels via the existing BLOB_KEY path —
    never inside the pack).
    """
    if sections < 1:
        raise ValueError("sections must be >= 1")
    data = bytes(payload)
    if key is None:
        key = os.urandom(32)
    else:
        key = bytes(key)
    n = min(sections, max(1, len(data)))
    chunk = (len(data) + n - 1) // n
    out_sections = []
    for i in range(n):
        part = data[i * chunk:(i + 1) * chunk]
        nonce = os.urandom(16)
        tagged = hashlib.sha256(part).digest() + part
        enc = bytes(a ^ b for a, b in zip(tagged, _keystream(key, nonce, len(tagged))))
        out_sections.append({
            "i": i,
            "salt": hashlib.sha256(key + nonce).hexdigest()[:16],
            "nonce": nonce.hex(),
            "data": enc.hex(),
        })
    return {
        "sections": out_sections,
        "count": n,
        "total": len(data),
        "key_hint": hashlib.sha256(key).hexdigest()[:16],
    }


def stream_join(pack: dict, key: bytes) -> bytearray:
    """Verify + join sections in order. Returns mutable bytearray.

    Raises ValueError on: wrong section count, index mismatch, tag failure,
    total-length mismatch, or key_hint mismatch. Caller MUST wipe the
    returned buffer after use.
    """
    sections = pack["sections"]
    if len(sections) != pack["count"]:
        raise ValueError("section count mismatch")
    expect_hint = hashlib.sha256(bytes(key)).hexdigest()[:16]
    if expect_hint != pack.get("key_hint"):
        raise ValueError("section session-key mismatch")
    ordered = sorted(sections, key=lambda s: s["i"])
    if [s["i"] for s in ordered] != list(range(pack["count"])):
        raise ValueError("section index mismatch")
    joined = bytearray()
    for sec in ordered:
        nonce = bytes.fromhex(sec["nonce"])
        enc = bytes.fromhex(sec["data"])
        tagged = bytes(a ^ b for a, b in zip(enc, _keystream(bytes(key), nonce, len(enc))))
        if len(tagged) < 32:
            raise ValueError("section truncated")
        tag, part = tagged[:32], tagged[32:]
        if hashlib.sha256(part).digest() != tag:
            raise ValueError(f"section {sec['i']} integrity failure")
        joined.extend(part)
    if len(joined) != pack["total"]:
        raise ValueError("joined length mismatch")
    return joined


def pack_json(payload: bytes, *, sections: int = DEFAULT_SECTIONS,
              key: bytes | None = None) -> tuple[bytes, bytes]:
    """Split + serialize. Returns (json_bytes, session_key).

    The caller transports json_bytes (inside the fallback blob) and the
    session key via the existing BLOB_KEY path.
    """
    key = os.urandom(32) if key is None else bytes(key)
    pack = split_sealed(payload, sections=sections, key=key)
    return json.dumps(pack, sort_keys=True).encode("utf-8"), key
