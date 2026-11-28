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
import os


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


def derive_effective_key(key: bytes, build_id: str,
                         customer_salt: str = "") -> bytes:
    """Per-build effective key: ``xor(key, sha256(build_id))`` (mask cycled).

    For keys <= 32 bytes this equals ``xor(key, sha256(build_id)[:len(key)])``.

    ``customer_salt`` adds a second, domain-separated mask
    (``sha256(b"nx-customer:" + salt)``).  It is empty by default, so the
    derivation is byte-identical to the pre-salt one unless a build is
    explicitly bound to a customer.  With a salt, two builds of the same
    payload for two customers do not share a payload key: transferring an
    artefact from one to the other does not decrypt.
    """
    if not isinstance(key, (bytes, bytearray)) or len(key) == 0:
        raise ValueError("key must be non-empty bytes")
    mask = hashlib.sha256(str(build_id).encode()).digest()
    derived = bytes(b ^ mask[i % len(mask)] for i, b in enumerate(bytes(key)))
    salt = str(customer_salt or "")
    if salt:
        if '"' in salt or "\\" in salt or "\n" in salt or "\r" in salt:
            raise ValueError("customer_salt contains unsafe characters")
        cmask = hashlib.sha256(b"nx-customer:" + salt.encode()).digest()
        derived = bytes(b ^ cmask[i % len(cmask)]
                        for i, b in enumerate(derived))
    return derived


def apply_operator_key_mask(key: bytes, seal_shard: str | None = None,
                            table_shard: str | None = None) -> bytes:
    """Bind a payload/blob key to operator-held runtime shards.

    ``NX_SEAL_SHARD`` and ``NX_TABLE_SHARD`` are deliberately not embedded in
    the artefact.  When either is present at build time the packed payload is
    sealed with this additional domain-separated mask; the emitted loader
    records that public binding fact and derives the same mask only when the
    operator exports the same shard(s) at run time.  Lengths are encoded in
    the transcript so concatenated shards cannot collide.  With neither shard
    set at build time this is the identity, preserving legacy unsigned/unbound
    builds; shard variables that happen to exist only at run time are ignored
    for those unbound artefacts.
    """
    if not isinstance(key, (bytes, bytearray)) or len(key) == 0:
        raise ValueError("key must be non-empty bytes")
    seal = str(os.environ.get("NX_SEAL_SHARD", "") if seal_shard is None else seal_shard or "")
    table = str(os.environ.get("NX_TABLE_SHARD", "") if table_shard is None else table_shard or "")
    if not seal and not table:
        return bytes(key)
    seal_bytes = seal.encode("utf-8")
    table_bytes = table.encode("utf-8")
    material = (
        b"nx-operator-blob:"
        + str(len(seal_bytes)).encode("ascii") + b":" + seal_bytes
        + b"|"
        + str(len(table_bytes)).encode("ascii") + b":" + table_bytes
    )
    mask = hashlib.sha256(material).digest()
    return bytes(b ^ mask[i % len(mask)] for i, b in enumerate(bytes(key)))


def split_seed_for_build(build_id: str) -> bytes:
    """Deterministic split seed bound to ``build_id`` (domain-separated)."""
    return hashlib.sha256(("nx-key-split:" + str(build_id)).encode()).digest()


def emit_key_loader(share0_b64: str, share1_b64: str, build_id: str,
                    varname: str = "BLOB_KEY", customer_salt: str = "") -> str:
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
    decoded = []
    for chunk in (share0_b64, share1_b64):
        decoded.append(base64.b64decode(chunk, validate=True))  # fail fast on malformed shares
        if '"' in chunk or "\\" in chunk or "\n" in chunk or "\r" in chunk:
            raise ValueError("share contains unsafe characters")
    if len(decoded[0]) != len(decoded[1]):
        raise ValueError("share length mismatch")
    if '"' in build_id or "\\" in build_id or "\n" in build_id or "\r" in build_id:
        raise ValueError("build_id contains unsafe characters")
    salt = str(customer_salt or "")
    operator_bound = bool(
        os.environ.get("NX_SEAL_SHARD") or os.environ.get("NX_TABLE_SHARD"))
    out = (
        "_NX_BUILD_ID = \"%s\"\n" % (build_id,)
        + "_NX_CUSTOMER_SALT = \"%s\"\n" % (salt,)
        + "_NX_OPERATOR_BOUND = %s\n" % (operator_bound,)
        + "_BLOB_S0 = bytearray(base64.b64decode(\"%s\"))\n" % (share0_b64,)
        + "_BLOB_S1 = bytearray(base64.b64decode(\"%s\"))\n" % (share1_b64,)
        + "_BLOB_RAW = bytearray(_a ^ _b for _a, _b in zip(_BLOB_S0, _BLOB_S1))\n"
        + "import hashlib as _nx_hk\n"
        + "_BLOB_MASK = _nx_hk.sha256(_NX_BUILD_ID.encode()).digest()\n"
        + "%s = bytes(_b ^ _BLOB_MASK[_i %% len(_BLOB_MASK)] for _i, _b in enumerate(_BLOB_RAW))\n" % (varname,)
    )
    if salt:
        out += (
            "_BLOB_CMASK = _nx_hk.sha256(b\"nx-customer:\" + _NX_CUSTOMER_SALT.encode()).digest()\n"
            "%s = bytes(_b ^ _BLOB_CMASK[_i %% len(_BLOB_CMASK)] for _i, _b in enumerate(%s))\n"
            % (varname, varname)
        )
    out += (
        "import os as _nx_os\n"
        "_nx_seal_shard = str(_nx_os.environ.get(\"NX_SEAL_SHARD\", \"\") or \"\")\n"
        "_nx_table_shard = str(_nx_os.environ.get(\"NX_TABLE_SHARD\", \"\") or \"\")\n"
        "if _NX_OPERATOR_BOUND and (_nx_seal_shard or _nx_table_shard):\n"
        "    _nx_seal_bytes = _nx_seal_shard.encode(\"utf-8\")\n"
        "    _nx_table_bytes = _nx_table_shard.encode(\"utf-8\")\n"
        "    _nx_op_material = (\n"
        "        b\"nx-operator-blob:\"\n"
        "        + str(len(_nx_seal_bytes)).encode(\"ascii\") + b\":\" + _nx_seal_bytes\n"
        "        + b\"|\"\n"
        "        + str(len(_nx_table_bytes)).encode(\"ascii\") + b\":\" + _nx_table_bytes\n"
        "    )\n"
        "    _BLOB_OMASK = _nx_hk.sha256(_nx_op_material).digest()\n"
        "    %s = bytes(_b ^ _BLOB_OMASK[_i %% len(_BLOB_OMASK)] for _i, _b in enumerate(%s))\n"
        % (varname, varname)
    )
    out += (
        "_nx_wipe(_BLOB_S0)\n"
        "_nx_wipe(_BLOB_S1)\n"
        "_nx_wipe(_BLOB_RAW)\n"
    )
    return out
