"""Operator-held shards must be part of the hybrid loader's blob key.

The stream-envelope format stopped trivial known-plaintext recovery, but the
key itself was still fully reconstructable from artefact literals.  When an
operator exports ``NX_SEAL_SHARD``/``NX_TABLE_SHARD`` at build time, the same
shard(s) must be present at run time; neither value is embedded in the
artefact.  With no shards exported the legacy unbound derivation is unchanged.
"""
import base64
import hashlib
import marshal
import os
import sys
import zlib

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import generate_hybrid_loader_script
from obfuscator.core.utils import fast_xor_bytes, stream_xor_open
from obfuscator.key_emit import (
    apply_operator_key_mask,
    derive_effective_key,
)

_BLANKS = {"windows": "", "linux": "", "darwin": ""}
_RAW_KEY = bytes(range(32))
_BUILD_ID = "operator-key-01"
_SEAL = "17" * 32
_TABLE = "42" * 32
_PAYLOAD_SRC = "OP_BLOB_RAN = 4242\n"


def _sealed_fallback():
    marshalled = marshal.dumps(compile(_PAYLOAD_SRC, "<op_blob>", "exec"))
    return fast_xor_bytes(zlib.compress(marshalled), _RAW_KEY)


def _loader(**kwargs):
    kwargs.setdefault("build_id", _BUILD_ID)
    return generate_hybrid_loader_script(
        dict(_BLANKS), _sealed_fallback(), _RAW_KEY.hex(), **kwargs)


def _exec(src, name="op_blob_loader"):
    ns = {"__name__": name}
    exec(compile(src, "<%s>" % name, "exec"), ns)
    return ns


def _run_fallback_through_loader_chain(ns):
    ns["_nx_cfi_mark"]("enter")
    ns["_exec_fallback"]()


def _expected(build_id=_BUILD_ID, seal=None, table=None):
    return apply_operator_key_mask(
        derive_effective_key(_RAW_KEY, build_id), seal, table)


def test_operator_mask_is_identity_without_shards(monkeypatch):
    monkeypatch.delenv("NX_SEAL_SHARD", raising=False)
    monkeypatch.delenv("NX_TABLE_SHARD", raising=False)
    assert apply_operator_key_mask(_RAW_KEY) == _RAW_KEY


def test_operator_mask_uses_both_shards_and_length_prefixes():
    both = apply_operator_key_mask(_RAW_KEY, _SEAL, _TABLE)
    seal_only = apply_operator_key_mask(_RAW_KEY, _SEAL, "")
    table_only = apply_operator_key_mask(_RAW_KEY, "", _TABLE)
    concatenation_collision = apply_operator_key_mask(_RAW_KEY, _SEAL + "x", _TABLE[:-1])
    assert len({both, seal_only, table_only, concatenation_collision, _RAW_KEY}) == 5


def test_bound_build_runs_with_the_same_operator_shards(monkeypatch):
    monkeypatch.setenv("NX_SEAL_SHARD", _SEAL)
    monkeypatch.setenv("NX_TABLE_SHARD", _TABLE)
    src, _, _ = _loader()
    assert _SEAL not in src and _TABLE not in src
    ns = _exec(src)
    assert ns["BLOB_KEY"] == _expected()
    _run_fallback_through_loader_chain(ns)
    assert ns.get("OP_BLOB_RAN") == 4242


def test_missing_runtime_shard_cannot_decrypt_the_fallback(monkeypatch):
    monkeypatch.setenv("NX_SEAL_SHARD", _SEAL)
    monkeypatch.setenv("NX_TABLE_SHARD", _TABLE)
    src, _, _ = _loader()
    monkeypatch.delenv("NX_SEAL_SHARD", raising=False)
    monkeypatch.delenv("NX_TABLE_SHARD", raising=False)
    ns = _exec(src, name="op_blob_missing_shard")
    bound = _expected(seal=_SEAL, table=_TABLE)
    assert ns["BLOB_KEY"] != bound
    ciphertext = base64.b85decode(ns["FALLBACK_BLOB"])
    wrong_plain = ns["_xor_decrypt"](ciphertext, ns["BLOB_KEY"])
    with pytest.raises(Exception):
        zlib.decompress(wrong_plain)


def test_native_blob_is_stream_packed_with_the_operator_key(monkeypatch):
    """Native blobs must decrypt with exactly the loader's effective key."""
    monkeypatch.setenv("NX_SEAL_SHARD", _SEAL)
    monkeypatch.setenv("NX_TABLE_SHARD", _TABLE)
    blob = b"\x7fELF" + bytes(range(1, 200))
    blobs = {"windows": "", "linux": base64.b64encode(blob).decode("ascii"), "darwin": ""}
    src, real_blobs, _ = generate_hybrid_loader_script(
        blobs, b"", _RAW_KEY.hex(), build_id=_BUILD_ID)
    assert _SEAL not in src and _TABLE not in src
    packed = base64.b64decode(real_blobs["linux"])
    assert packed[:4] == b"NXS1"
    bound_key = _expected(seal=_SEAL, table=_TABLE)
    assert stream_xor_open(packed, bound_key) == blob
    unbound_key = derive_effective_key(_RAW_KEY, _BUILD_ID)
    assert stream_xor_open(packed, unbound_key) != blob


def test_unicode_and_delimiter_shards_use_byte_length_transcripts(monkeypatch):
    """Non-ASCII/delimiter shards must have one unambiguous transcript."""
    seal = "é|"
    table = "x:1"
    seal_bytes = seal.encode("utf-8")
    table_bytes = table.encode("utf-8")
    material = (
        b"nx-operator-blob:"
        + str(len(seal_bytes)).encode("ascii") + b":" + seal_bytes
        + b"|"
        + str(len(table_bytes)).encode("ascii") + b":" + table_bytes
    )
    mask = hashlib.sha256(material).digest()
    expected = bytes(
        b ^ mask[i % len(mask)] for i, b in enumerate(
            derive_effective_key(_RAW_KEY, _BUILD_ID)))
    monkeypatch.setenv("NX_SEAL_SHARD", seal)
    monkeypatch.setenv("NX_TABLE_SHARD", table)
    src, _, _ = _loader()
    assert seal not in src and table not in src
    ns = _exec(src, name="op_blob_unicode_shards")
    assert ns["BLOB_KEY"] == expected
    _run_fallback_through_loader_chain(ns)
    assert ns.get("OP_BLOB_RAN") == 4242


def test_unbound_build_keeps_the_legacy_key(monkeypatch):
    monkeypatch.delenv("NX_SEAL_SHARD", raising=False)
    monkeypatch.delenv("NX_TABLE_SHARD", raising=False)
    src, _, _ = _loader()
    ns = _exec(src, name="op_blob_unbound")
    assert ns["BLOB_KEY"] == derive_effective_key(_RAW_KEY, _BUILD_ID)
    _run_fallback_through_loader_chain(ns)
    assert ns.get("OP_BLOB_RAN") == 4242


def test_unbound_build_ignores_runtime_operator_shards(monkeypatch):
    """Shards exported for another artefact must not break an unbound one."""
    monkeypatch.delenv("NX_SEAL_SHARD", raising=False)
    monkeypatch.delenv("NX_TABLE_SHARD", raising=False)
    src, _, _ = _loader()
    monkeypatch.setenv("NX_SEAL_SHARD", _SEAL)
    monkeypatch.setenv("NX_TABLE_SHARD", _TABLE)
    ns = _exec(src, name="op_blob_unbound_ambient")
    assert ns["BLOB_KEY"] == derive_effective_key(_RAW_KEY, _BUILD_ID)
    _run_fallback_through_loader_chain(ns)
    assert ns.get("OP_BLOB_RAN") == 4242
