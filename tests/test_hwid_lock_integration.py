"""HWID-lock integration: build-time lock_payload <-> loader inline-unlock roundtrip.

The loader template (obfuscator/core/pipeline.py::generate_hybrid_loader_script)
embeds a stdlib-only ``_nx_hwid_unlock`` (PBKDF2-HMAC-SHA256 + SHA-256-CTR
stream, mirroring obfuscator/hwid_lock.py). The runtime HWID is
``format(uuid.getnode(), "x")``; --hwid must equal that string. Wrong host or
tampered data raises ValueError.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.core.pipeline import generate_hybrid_loader_script
from obfuscator.hwid_lock import lock_payload


def _extract_unlock(loader_src):
    """Exec the tail of the loader far enough to get _nx_hwid_unlock."""
    marker = "def _nx_hwid_unlock(blob_bytes):"
    assert marker in loader_src, "inline unlock missing from loader"
    start = loader_src.find("_NX_HWID_LOCK =")
    assert start != -1
    tail = loader_src[start:]
    ns = {"__name__": "hwid_unlock_test"}
    exec(compile(tail, "<hwid_unlock>", "exec"), ns)
    assert callable(ns["_nx_hwid_unlock"])
    return ns["_nx_hwid_unlock"]


def _hwid():
    """What the emitted loader derives: the sysfs MAC, not uuid.getnode().

    uuid.getnode() can shell out to ip/ifconfig/arp (and blocks for
    minutes inside the threaded loader), and returns a random per-process
    value when every method fails -- so the loader reads
    /sys/class/net/*/address instead.
    """
    from obfuscator.hwid import machine_fingerprint_part
    return machine_fingerprint_part()


def test_inline_unlock_roundtrip_same_host():
    hwid = _hwid()
    payload = b"marshal-payload-bytes\x00\x01\x02"
    pack = lock_payload(payload, hwid)
    blob = json.dumps(pack, sort_keys=True).encode("utf-8")

    loader_src, _, _ = generate_hybrid_loader_script(
        {"windows": "", "linux": "", "darwin": ""}, b"", "00" * 32,
        hwid_lock=True,
    )
    assert "_NX_HWID_LOCK = 'ENABLED'" in loader_src
    unlock = _extract_unlock(loader_src)
    assert unlock(blob) == payload


def test_inline_unlock_disabled_is_passthrough():
    loader_src, _, _ = generate_hybrid_loader_script(
        {"windows": "", "linux": "", "darwin": ""}, b"", "00" * 32,
    )
    assert "_NX_HWID_LOCK = 'DISABLED'" in loader_src
    unlock = _extract_unlock(loader_src)
    assert unlock(b"raw-bytes") == b"raw-bytes"


def test_inline_unlock_wrong_hwid_raises():

    real_pack = lock_payload(b"secret", "some-other-host")
    blob = json.dumps(real_pack, sort_keys=True).encode("utf-8")
    loader_src, _, _ = generate_hybrid_loader_script(
        {"windows": "", "linux": "", "darwin": ""}, b"", "00" * 32,
        hwid_lock=True,
    )
    unlock = _extract_unlock(loader_src)
    # Locked for a different HWID: tag check must fail on this host
    # (unless this host's derived HWID happens to equal that string).
    if _hwid() == "some-other-host":
        return
    try:
        unlock(blob)
    except ValueError:
        return
    raise AssertionError("expected ValueError for wrong hwid")


def test_inline_unlock_tampered_raises():
    hwid = _hwid()
    pack = lock_payload(b"secret-data", hwid)
    pack["data"] = ("00" if pack["data"][:2] != "00" else "ff") + pack["data"][2:]
    blob = json.dumps(pack, sort_keys=True).encode("utf-8")
    loader_src, _, _ = generate_hybrid_loader_script(
        {"windows": "", "linux": "", "darwin": ""}, b"", "00" * 32,
        hwid_lock=True,
    )
    unlock = _extract_unlock(loader_src)
    try:
        unlock(blob)
    except ValueError:
        return
    raise AssertionError("expected ValueError for tampered data")


def test_inline_unlock_matches_reference_unlock():
    """Cross-check inline unlock against hwid_lock.unlock_payload."""
    from obfuscator.hwid_lock import unlock_payload

    hwid = _hwid()
    payload = b"\x00\xff binary \x01 payload"
    pack = lock_payload(payload, hwid)
    blob = json.dumps(pack, sort_keys=True).encode("utf-8")
    loader_src, _, _ = generate_hybrid_loader_script(
        {"windows": "", "linux": "", "darwin": ""}, b"", "00" * 32,
        hwid_lock=True,
    )
    unlock = _extract_unlock(loader_src)
    assert unlock(blob) == unlock_payload(pack, hwid) == payload
