"""AUDIT GAP #33: static HWID fingerprint format.

Canonical static fingerprint: ``HWID:<64 hex chars>`` (case-insensitive,
canonicalized to lowercase) documented in :mod:`obfuscator.hwid_lock`.

- static fp accepted: binds/unbinds via lock_payload/unlock_payload
  (PBKDF2 path unchanged downstream) and the emitted loader embeds it as
  ``_NX_HWID_STATIC`` so inline unlock uses it verbatim.
- wrong static fp refuses (ValueError on unlock / inline unlock).
- dynamic path untouched: opaque ``--hwid`` strings pass through with
  byte-identical PBKDF2 keys; loader with empty/non-static hwid embeds
  ``_NX_HWID_STATIC = ''`` and keeps ``uuid.getnode()`` collection.
"""
import ast
import json
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import generate_hybrid_loader_script
from obfuscator.hwid_lock import (
    derive_hwid_key,
    is_static_hwid,
    lock_payload,
    normalize_static_hwid,
    unlock_payload,
)

_FP = "HWID:" + "ab12" * 16
_FP_UPPER = "HWID:" + "AB12" * 16
_FP_OTHER = "HWID:" + "cd34" * 16

_SALT = bytes.fromhex("00" * 16)


def _extract_unlock(loader_src):
    marker = "def _nx_hwid_unlock(blob_bytes):"
    assert marker in loader_src, "inline unlock missing from loader"
    start = loader_src.find("_NX_HWID_LOCK =")
    assert start != -1
    tail = loader_src[start:]
    ns = {"__name__": "hwid_static_test"}
    exec(compile(tail, "<hwid_static_unlock>", "exec"), ns)
    assert callable(ns["_nx_hwid_unlock"])
    return ns["_nx_hwid_unlock"]


def test_static_format_predicate_and_canonicalization():
    assert is_static_hwid(_FP)
    assert is_static_hwid(_FP_UPPER)
    assert not is_static_hwid("")
    assert not is_static_hwid("HWID-1")
    assert not is_static_hwid(format(uuid.getnode(), "x"))
    assert not is_static_hwid("HWID:xyz")
    assert normalize_static_hwid(_FP_UPPER) == _FP
    assert normalize_static_hwid(_FP) == _FP
    # Non-static strings pass through untouched (dynamic path identical).
    assert normalize_static_hwid("HWID-1") == "HWID-1"
    assert normalize_static_hwid("") == ""


def test_malformed_static_prefix_fails_closed():
    for bad in ("HWID:", "HWID:xyz", "HWID:" + "ab" * 16, "HWID:" + "zz" * 32):
        with pytest.raises(ValueError):
            normalize_static_hwid(bad)


def test_static_fp_binds_and_unbinds():
    pack = lock_payload(b"static-secret", _FP)
    assert set(pack) == {"salt", "nonce", "data"}
    assert unlock_payload(pack, _FP) == b"static-secret"
    # Uppercase form canonicalizes to the same key/material.
    assert unlock_payload(pack, _FP_UPPER) == b"static-secret"
    assert derive_hwid_key(_FP, _SALT) == derive_hwid_key(_FP_UPPER, _SALT)


def test_wrong_static_fp_refuses():
    pack = lock_payload(b"static-secret", _FP)
    with pytest.raises(ValueError):
        unlock_payload(pack, _FP_OTHER)


def test_dynamic_path_untouched():
    k1 = derive_hwid_key("HWID-1", _SALT)
    k2 = derive_hwid_key("HWID-1", _SALT)
    assert k1 == k2
    pack = lock_payload(b"hello world", "HWID-1")
    assert unlock_payload(pack, "HWID-1") == b"hello world"
    with pytest.raises(ValueError):
        unlock_payload(pack, "HWID-2")
    # A static fp never collides with the dynamic namespace.
    assert derive_hwid_key(_FP, _SALT) != derive_hwid_key("HWID-1", _SALT)


def test_loader_embeds_static_and_unlocks_verbatim():
    payload = b"static-loader-payload\x00\x01"
    pack = lock_payload(payload, _FP)
    blob = json.dumps(pack, sort_keys=True).encode("utf-8")
    src, _, _ = generate_hybrid_loader_script(
        {"windows": "", "linux": "", "darwin": ""}, b"", "00" * 32,
        hwid=_FP, hwid_lock=True,
    )
    assert "_NX_HWID_LOCK = 'ENABLED'" in src
    assert "_NX_HWID_STATIC = '%s'" % (_FP,) in src
    compile(src, "<hwid_static_loader>", "exec")
    ast.parse(src, feature_version=(3, 10))
    unlock = _extract_unlock(src)
    assert unlock(blob) == payload


def test_loader_static_wrong_fp_refuses():
    pack = lock_payload(b"secret", _FP_OTHER)
    blob = json.dumps(pack, sort_keys=True).encode("utf-8")
    src, _, _ = generate_hybrid_loader_script(
        {"windows": "", "linux": "", "darwin": ""}, b"", "00" * 32,
        hwid=_FP, hwid_lock=True,
    )
    unlock = _extract_unlock(src)
    with pytest.raises(ValueError):
        unlock(blob)


def test_loader_dynamic_keeps_getnode_and_empty_static():
    src, _, _ = generate_hybrid_loader_script(
        {"windows": "", "linux": "", "darwin": ""}, b"", "00" * 32,
        hwid_lock=True,
    )
    assert "_NX_HWID_STATIC = ''" in src
    assert 'format(_hl_uuid.getnode(), "x")' in src
    compile(src, "<hwid_dynamic_loader>", "exec")
    ast.parse(src, feature_version=(3, 10))


def test_loader_malformed_static_fails_closed():
    with pytest.raises(ValueError):
        generate_hybrid_loader_script(
            {"windows": "", "linux": "", "darwin": ""}, b"", "00" * 32,
            hwid="HWID:xyz", hwid_lock=True,
        )
