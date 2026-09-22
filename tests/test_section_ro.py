"""Tests for GAP #18: RO-after-load wired to the section path.

After sections are loaded/streamed, the section buffers are re-protected
read-only (best-effort, never breaking loads on platforms without
mprotect). Covers:

  * loads work fine with the RO pass on (roundtrip through
    ``stream_join_sealed`` / ``seal_joined`` / ``protect_after_load``);
  * the ``MemoryGuard.protect_region`` helper is honoured when injected
    via the ``protect`` hook (mock/spy);
  * on Linux, the sealed mapping is verifiably non-writable: the buffer
    region parsed from ``/proc/self/maps`` must lack the ``w`` bit, else
    the test falls back to asserting the loader works + the helper was
    invoked.
"""

from __future__ import annotations

import ctypes
import os
import sys

import pytest

from obfuscator import section_split as ss
from obfuscator.section_split import (
    protect_after_load,
    seal_joined,
    split_sealed,
    stream_join,
    stream_join_sealed,
)

KEY = b"K" * 32
PAYLOAD = b"ro-after-load-payload-" * 50


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _maps_perms_for(addr: int):
    """Return the perms field (e.g. ``r--p``) for the mapping of *addr*.

    Returns None when ``/proc/self/maps`` is unavailable or no mapping
    contains the address.
    """
    try:
        with open("/proc/self/maps", "r", encoding="utf-8",
                  errors="replace") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) < 2:
                    continue
                try:
                    lo_s, hi_s = parts[0].split("-", 1)
                    lo, hi = int(lo_s, 16), int(hi_s, 16)
                except ValueError:
                    continue
                if lo <= addr < hi:
                    return parts[1]
    except OSError:
        return None
    return None


def _sealed_addr(sealed) -> int:
    try:
        return ctypes.addressof(ctypes.c_char.from_buffer(sealed._mapping))
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# loads work fine with the RO pass on
# ---------------------------------------------------------------------------

def test_sealed_roundtrip_matches_plain_join():
    pack = split_sealed(PAYLOAD, sections=4, key=KEY)
    sealed = stream_join_sealed(pack, KEY)
    try:
        assert bytes(sealed.view) == PAYLOAD
        assert bytes(sealed.view) == bytes(stream_join(pack, KEY))
        assert len(sealed) == len(PAYLOAD)
    finally:
        sealed.close()


def test_seal_joined_roundtrip():
    buf = bytearray(PAYLOAD)
    sealed = seal_joined(buf)
    try:
        assert bytes(sealed.view) == PAYLOAD
    finally:
        sealed.close()


def test_protect_after_load_never_breaks_load():
    # Best-effort: whatever it returns, the buffer must stay intact and
    # readable — loads never break because of hardening. A heap bytearray
    # must be REFUSED on the safe default path (hardening its shared page
    # would fault unrelated objects), so this asserts False + intact data.
    buf = stream_join(split_sealed(PAYLOAD, sections=3, key=KEY), KEY)
    result = protect_after_load(buf)
    assert result is False
    assert bytes(buf) == PAYLOAD


def test_protect_after_load_mmap_buffer_applies():
    import mmap as _mmap

    if ss._mprotect_fn is None:
        import pytest as _pytest
        _pytest.skip("mprotect unavailable on this platform")
    buf = _mmap.mmap(-1, len(PAYLOAD),
                     prot=_mmap.PROT_READ | _mmap.PROT_WRITE)
    try:
        buf.write(PAYLOAD)
        buf.seek(0)
        assert protect_after_load(buf) is True
        buf.seek(0)
        assert buf.read(len(PAYLOAD)) == PAYLOAD
    finally:
        # Restore RW so munmap-time teardown never trips on PROT_READ.
        try:
            addr = ctypes.addressof(ctypes.c_char.from_buffer(buf))
            page = _mmap.PAGESIZE
            aligned = addr & ~(page - 1)
            size = ((addr + len(PAYLOAD) + page - 1) & ~(page - 1)) - aligned
            ss._mprotect_fn(ctypes.c_void_p(aligned),
                            ctypes.c_size_t(size), 1 | 2)
        except Exception:
            pass
        buf.close()


def test_empty_payload_loads_with_ro_pass():
    pack = split_sealed(b"", sections=4, key=KEY)
    assert bytes(stream_join(pack, KEY)) == b""
    sealed = stream_join_sealed(pack, KEY)
    try:
        assert bytes(sealed.view) == b""
        assert len(sealed) == 0
    finally:
        sealed.close()


def test_tampered_sections_still_fail_closed_with_ro():
    pack = split_sealed(b"secret-data-here", sections=3, key=KEY)
    pack["sections"][1]["data"] = "ff" + pack["sections"][1]["data"][2:]
    with pytest.raises(ValueError):
        stream_join_sealed(pack, KEY)


# ---------------------------------------------------------------------------
# helper (MemoryGuard.protect_region) is honoured via the protect hook
# ---------------------------------------------------------------------------

def test_protect_hook_spy_is_invoked():
    # An explicit protect hook is the MemoryGuard path: it is honoured
    # even for heap buffers (caller owns the risk).
    calls = []

    def spy(addr, size):
        calls.append((addr, size))
        return True

    buf = bytearray(PAYLOAD)
    assert protect_after_load(buf, protect=spy) is True
    assert len(calls) == 1
    addr, size = calls[0]
    assert addr != 0
    assert size == len(buf)


def test_seal_uses_memory_guard_helper_when_injected():
    """The existing MemoryGuard helper covers raw buffers (spy double)."""
    try:
        from scripts.kernel_assist.memory_guard import MemoryGuard
    except Exception as exc:
        pytest.skip("MemoryGuard helper unavailable: %s" % (exc,))
    guard = MemoryGuard()
    try:
        calls = []
        orig = guard.protect_region

        def spy(addr, size):
            calls.append((addr, size))
            return orig(addr, size)

        sealed = seal_joined(bytearray(PAYLOAD), protect=spy)
        try:
            assert bytes(sealed.view) == PAYLOAD
            # The helper path was exercised exactly once with the
            # dedicated mapping's address/size.
            assert len(calls) == 1
            assert calls[0][0] == _sealed_addr(sealed)
            assert calls[0][1] == len(PAYLOAD)
        finally:
            sealed.close()
    finally:
        guard.close()


def test_protect_hook_failure_falls_back_gracefully():
    def failing(addr, size):
        raise RuntimeError("no mprotect here")

    buf = bytearray(PAYLOAD)
    assert protect_after_load(buf, protect=failing) is False
    assert bytes(buf) == PAYLOAD

    def false_hook(addr, size):
        return False

    sealed = seal_joined(bytearray(PAYLOAD), protect=false_hook)
    try:
        # Hook declined; direct mprotect may still apply, but the data is
        # usable either way.
        assert bytes(sealed.view) == PAYLOAD
    finally:
        sealed.close()


def test_missing_mprotect_returns_false_without_breaking():
    buf = bytearray(PAYLOAD)
    if ss._mprotect_fn is None:
        assert protect_after_load(buf) is False
        assert bytes(buf) == PAYLOAD
    else:
        pytest.skip("mprotect present on this platform")


# ---------------------------------------------------------------------------
# Linux: verify the sealed region is actually non-writable, else fallback
# ---------------------------------------------------------------------------

def test_sealed_region_nonwritable_or_helper_invoked():
    pack = split_sealed(PAYLOAD, sections=2, key=KEY)
    calls = []

    def spy(addr, size):
        calls.append((addr, size))
        return False  # decline so the direct-mprotect path is exercised

    sealed = stream_join_sealed(pack, KEY, protect=spy)
    try:
        assert bytes(sealed.view) == PAYLOAD
        assert calls, "protect hook must have been invoked"
        addr = _sealed_addr(sealed)
        assert addr != 0
        if sys.platform.startswith("linux") and os.path.exists(
                "/proc/self/maps"):
            perms = _maps_perms_for(addr)
            assert perms is not None, "mapping for sealed region not found"
            if sealed.readonly:
                assert "w" not in perms, (
                    "sealed section mapping is still writable: %s" % perms)
            # readonly=False on this platform means mprotect is
            # unavailable — loader works + helper invoked is the
            # assertion (checked above).
    finally:
        sealed.close()


def test_seal_joined_maps_entry_lacks_write_bit():
    if not (sys.platform.startswith("linux")
            and os.path.exists("/proc/self/maps")):
        pytest.skip("requires Linux /proc/self/maps")
    if ss._mprotect_fn is None:
        pytest.skip("mprotect unavailable on this platform")
    sealed = seal_joined(bytearray(PAYLOAD))
    try:
        assert sealed.readonly, "direct mprotect should have applied"
        addr = _sealed_addr(sealed)
        perms = _maps_perms_for(addr)
        assert perms is not None
        assert "w" not in perms, "sealed mapping still writable: %s" % perms
        assert "r" in perms, "sealed mapping must stay readable: %s" % perms
    finally:
        sealed.close()
