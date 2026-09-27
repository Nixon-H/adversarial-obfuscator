"""XOR-split key emission for the hybrid loader (batch 3).

The fallback ``BLOB_KEY`` must never appear as a contiguous hex literal in
emitted artifacts (trivially greppable).  Instead we emit two
base64-encoded XOR shares that reconstruct the key at runtime::

    key == b64decode(share0) XOR b64decode(share1)

plus a per-build ``_NX_BUILD_ID`` salt: the effective key is
``xor(raw_key, sha256(build_id))`` (cycled), so identical payload+key
pairs still produce different blobs/loaders on every build.

Build-time API: :func:`split_key`, :func:`derive_effective_key`,
:func:`split_seed_for_build`, :func:`emit_key_loader`.
Runtime (emitted) counterpart: the snippet from :func:`emit_key_loader`
recomputes the same derivation from the embedded ``_NX_BUILD_ID``.
"""

from __future__ import annotations

import base64
import hashlib


def _keystream(seed: bytes, length: int) -> bytes:
    """Deterministic SHA-256-CTR stream (stdlib only)."""
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hashlib.sha256(seed + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(out[:length])


def split_key(key: bytes, seed: bytes) -> tuple[str, str]:
    """Split ``key`` into two base64 XOR shares, deterministically from ``seed``.

    Returns ``(share0_b64, share1_b64)`` with
    ``b64decode(share0) XOR b64decode(share1) == key``.
    """
    if not isinstance(key, (bytes, bytearray)) or len(key) == 0:
        raise ValueError("key must be non-empty bytes")
    if not isinstance(seed, (bytes, bytearray)) or len(seed) == 0:
        raise ValueError("seed must be non-empty bytes")
    key = bytes(key)
    s0 = _keystream(bytes(seed), len(key))
    s1 = bytes(a ^ b for a, b in zip(key, s0))
    return (base64.b64encode(s0).decode("ascii"),
            base64.b64encode(s1).decode("ascii"))


def combine_shares(share0_b64: str, share1_b64: str) -> bytes:
    """Recombine two base64 shares (documents the runtime invariant)."""
    s0 = base64.b64decode(share0_b64)
    s1 = base64.b64decode(share1_b64)
    if len(s0) != len(s1):
        raise ValueError("share length mismatch")
    return bytes(a ^ b for a, b in zip(s0, s1))


def derive_effective_key(key: bytes, build_id: str) -> bytes:
    """Per-build effective key: ``xor(key, sha256(build_id))`` (mask cycled).

    For keys <= 32 bytes this equals ``xor(key, sha256(build_id)[:len(key)])``.
    """
    if not isinstance(key, (bytes, bytearray)) or len(key) == 0:
        raise ValueError("key must be non-empty bytes")
    mask = hashlib.sha256(str(build_id).encode()).digest()
    return bytes(b ^ mask[i % len(mask)] for i, b in enumerate(bytes(key)))


def split_seed_for_build(build_id: str) -> bytes:
    """Deterministic split seed bound to ``build_id`` (domain-separated)."""
    return hashlib.sha256(("nx-key-split:" + str(build_id)).encode()).digest()


def emit_key_loader(share0_b64: str, share1_b64: str, build_id: str,
                    varname: str = "BLOB_KEY") -> str:
    """Return the runtime key-reconstruction snippet for the loader template.

    Emits base64 share literals plus the ``_NX_BUILD_ID`` salt; the loader
    recomputes ``xor(raw, sha256(build_id))`` so a tampered build id yields
    a wrong key (decrypt fails).  Share buffers are bytearrays so the
    emitted ``_nx_wipe`` can zero them after derivation.

    NOTE: this helper documents the contract exercised by
    ``generate_hybrid_loader_script``; the canonical emitted form now lives
    inline in the loader template (``_BLOB_S0``/``_BLOB_S1``/``_NX_BUILD_ID``
    + ``_nx_key_reconstruct()``) so the key path and the ``_nx_wipe``/
    build-id-salt paths share one code path. The snippet here is kept in
    sync with that form (same share literals, same derivation) for
    standalone tests and auditing.
    """
    if not isinstance(varname, str) or not varname.isidentifier():
        raise ValueError("varname must be a valid identifier")
    if not isinstance(share0_b64, str) or not share0_b64:
        raise ValueError("share0_b64 must be a non-empty string")
    if not isinstance(share1_b64, str) or not share1_b64:
        raise ValueError("share1_b64 must be a non-empty string")
    if not isinstance(build_id, str) or not build_id:
        raise ValueError("build_id must be a non-empty string")
    # b64 alphabet has no quotes/backslashes: safe inside "..." literals.
    # Newlines/CRs are rejected too: b64decode() silently ignores them,
    # but they would break the emitted "..." literal (source injection).
    for chunk in (share0_b64, share1_b64):
        base64.b64decode(chunk)  # fail fast on malformed shares
        if '"' in chunk or "\\" in chunk or "\n" in chunk or "\r" in chunk:
            raise ValueError("share contains unsafe characters")
    if '"' in build_id or "\\" in build_id or "\n" in build_id or "\r" in build_id:
        raise ValueError("build_id contains unsafe characters")
    return (
        "_NX_BUILD_ID = \"%s\"\n" % (build_id,)
        + "_BLOB_S0 = bytearray(base64.b64decode(\"%s\"))\n" % (share0_b64,)
        + "_BLOB_S1 = bytearray(base64.b64decode(\"%s\"))\n" % (share1_b64,)
        + "_BLOB_RAW = bytearray(_a ^ _b for _a, _b in zip(_BLOB_S0, _BLOB_S1))\n"
        + "import hashlib as _nx_hk\n"
        + "_BLOB_MASK = _nx_hk.sha256(_NX_BUILD_ID.encode()).digest()\n"
        + "%s = bytes(_b ^ _BLOB_MASK[_i %% len(_BLOB_MASK)] for _i, _b in enumerate(_BLOB_RAW))\n" % (varname,)
        + "_nx_wipe(_BLOB_S0)\n"
        + "_nx_wipe(_BLOB_S1)\n"
        + "_nx_wipe(_BLOB_RAW)\n"
    )
