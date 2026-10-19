"""Section-split sealed streaming (V10 adopt, medium).

.. warning::

   **NOT WIRED INTO THE BUILD.**  This module is implemented and unit
   tested (``tests/test_section_split.py``, ``tests/test_section_ro.py``)
   but no build, pipeline or loader path calls it: a repo-wide search
   finds references only in those two test files.  Do not read the
   presence of this file (or of its tests) as "the artifact is protected
   by section splitting" — it is not.  Wiring it in needs a loader-side
   streaming path and a ``--no-section-split`` escape hatch; until that
   exists, treat this as library/experimental code.

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

RO-after-load (audit GAP #18): after sections are loaded/streamed, the
section buffers can be re-protected read-only via ``protect_after_load``
(best-effort in-place mprotect, never breaks loads) or — preferably — via
``seal_joined`` / ``stream_join_sealed``, which copy the plaintext into a
dedicated anonymous mmap and mprotect THAT mapping PROT_READ. The dedicated
mapping owns its pages, so it cannot wedge unrelated heap objects.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import json
import mmap
import os
from typing import Any, Optional

DEFAULT_SECTIONS = 4


def _keystream(key: bytes, nonce: bytes, ln: int) -> bytes:
    out = bytearray()
    c = 0
    while len(out) < ln:
        out.extend(hashlib.sha256(key + nonce + c.to_bytes(8, "big")).digest())
        c += 1
    return bytes(out[:ln])


def split_sealed(payload: bytes, *, sections: int = DEFAULT_SECTIONS,
                 key: Optional[bytes] = None) -> dict:
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
              key: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """Split + serialize. Returns (json_bytes, session_key).

    The caller transports json_bytes (inside the fallback blob) and the
    session key via the existing BLOB_KEY path.
    """
    key = os.urandom(32) if key is None else bytes(key)
    pack = split_sealed(payload, sections=sections, key=key)
    return json.dumps(pack, sort_keys=True).encode("utf-8"), key


# ---------------------------------------------------------------------------
# RO-after-load (audit GAP #18).
#
# Wiring note: the native ``runtime/src/memguard.rs::protect_region`` /
# ``platform.rs::protect_pages`` (mprotect / VirtualProtect) exists but the
# Rust runtime is NOT linked into this Python loader path (``runtime`` is a
# plain rlib with no cdylib/pyo3 binding; see ``runtime/Cargo.toml`` which
# has no ``crate-type``). So no Rust-side work is needed here: the Python
# side below is the correct and sufficient link. The default path is a
# direct ctypes ``mprotect`` (PROT_READ, no EXEC bit — least privilege for
# data buffers, unlike ``MemoryGuard.protect_region`` which applies RX).
# Where the existing ``scripts/kernel_assist/memory_guard.py::MemoryGuard``
# helper is already in use, it covers raw addresses via ``protect_region``
# and can be routed through the optional ``protect`` callable hook that
# ``protect_after_load`` / ``seal_joined`` / ``stream_join_sealed`` all
# accept (tests spy on it). All hardening is best-effort with graceful
# fallback on platforms without mprotect.
#
# Safety note: CPython ``bytearray`` buffers live on the shared heap and a
# page is usually larger than the buffer — mprotect works on whole pages, so
# hardening a live ``bytearray`` in place risks write-protecting UNRELATED
# heap objects that share the page. Therefore the preferred API is
# ``seal_joined`` / ``stream_join_sealed``, which copy the plaintext into a
# dedicated anonymous mmap region and mprotect THAT mapping: the mapping
# owns its pages, exactly like the Rust ``alloc_pages`` side.
# ---------------------------------------------------------------------------

_PROT_READ = 1

_libc: Any = None
try:
    _libc_path = ctypes.util.find_library("c")
    if _libc_path:
        _libc = ctypes.CDLL(_libc_path, use_errno=True)
except Exception:
    _libc = None

_mprotect_fn: Any = None
try:
    if _libc is not None:
        _mprotect_fn = _libc.mprotect
        _mprotect_fn.restype = ctypes.c_int
        _mprotect_fn.argtypes = (
            ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int)
except Exception:
    _mprotect_fn = None


def mprotect_available() -> bool:
    """Return True when a raw ``mprotect`` entry point was resolved."""
    return _mprotect_fn is not None


def _raw_mprotect_readonly(addr: int, size: int) -> bool:
    """Best-effort page-aligned ``mprotect(addr, size, PROT_READ)``.

    Returns True when the kernel accepted the protection, False otherwise
    (no libc, bad args, non-zero return, missing syscall). Never raises.
    """
    if _mprotect_fn is None:
        return False
    try:
        if not addr or size <= 0:
            return False
        page_size = mmap.PAGESIZE
        aligned_addr = addr & ~(page_size - 1)
        aligned_size = (
            (addr + size + page_size - 1) & ~(page_size - 1)) - aligned_addr
        if aligned_size <= 0:
            return False
        ret = _mprotect_fn(
            ctypes.c_void_p(aligned_addr),
            ctypes.c_size_t(aligned_size),
            _PROT_READ,
        )
        return ret == 0
    except Exception:
        return False


def _buffer_address(buf: Any) -> int:
    """Best-effort address of a writable buffer's first byte (0 if unknown)."""
    try:
        return ctypes.addressof(ctypes.c_char.from_buffer(buf))
    except Exception:
        return 0


def _owns_pages(buf: Any) -> bool:
    """Return True when *buf* owns whole pages (safe for raw mprotect).

    Only ``mmap``-backed buffers (or views over one) own their pages. A
    CPython ``bytearray``/``bytes`` lives on the shared heap, so hardening
    its page(s) in place would write-protect UNRELATED live objects — the
    very next heap write could fault and kill the process. The default
    (hook-less) path therefore only attempts raw mprotect for page-owning
    buffers; anything else must go through ``seal_joined`` (which copies
    into a dedicated mapping) or an explicit ``protect`` hook.
    """
    seen = 0
    obj = buf
    while obj is not None and seen < 8:
        if isinstance(obj, mmap.mmap):
            return True
        nxt = getattr(obj, "obj", None)
        if nxt is None or nxt is obj:
            return False
        obj = nxt
        seen += 1
    return False


def _alloc_private(size: int) -> Any:
    """Allocate a private anonymous mapping (portable, may raise)."""
    prot = mmap.PROT_READ | mmap.PROT_WRITE
    try:
        flags = mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS  # type: ignore[attr-defined]
    except AttributeError:
        # Platforms without MAP_ANONYMOUS (e.g. Windows): anonymous
        # mappings need no flag argument.
        return mmap.mmap(-1, size, prot=prot)
    return mmap.mmap(-1, size, prot=prot, flags=flags)


def protect_after_load(buf: Any, protect: Any = None,
                       unsafe_allow_heap: bool = False) -> bool:
    """Best-effort in-place re-protection of a loaded section buffer.

    Read-only hardening for a ``bytearray``/``mmap``/``memoryview`` that has
    just been filled by the streaming loader. Preferred order:

      1. ``protect(addr, size)`` callable when supplied — this is the hook
         for the existing ``MemoryGuard.protect_region`` helper.
      2. Direct ctypes ``mprotect`` (PROT_READ) otherwise, but ONLY for
         page-owning (``mmap``-backed) buffers unless ``unsafe_allow_heap``
         is True.

    Always best-effort: any failure or refusal returns False and the buffer
    keeps its contents (loads never break on platforms without mprotect).
    Callers that need a *verifiable* read-only region should use
    ``seal_joined``, whose dedicated mapping owns its pages.

    WARNING: in-place protection of a CPython ``bytearray`` hardens the
    whole underlying page(s), which are shared with unrelated heap
    objects: hardening them would make the next heap write fault and kill
    the process. The hook-less path therefore REFUSES non-page-owning
    buffers; pass an explicit ``protect`` hook (you own the risk) or
    ``unsafe_allow_heap=True`` only when you can prove the page is
    exclusively owned.
    """
    try:
        size = len(buf)  # type: ignore[arg-type]
    except Exception:
        return False
    if size <= 0:
        return False
    addr = _buffer_address(buf)
    if not addr:
        return False
    if protect is not None:
        try:
            return bool(protect(addr, size))
        except Exception:
            return False
    if not unsafe_allow_heap and not _owns_pages(buf):
        return False
    return _raw_mprotect_readonly(addr, size)


class SealedSection:
    """Read-only view of joined section plaintext in a dedicated mapping.

    Holds the anonymous ``mmap`` alive; ``bytes(view)`` returns the
    plaintext. ``close()`` wipes (best effort) and releases the mapping.
    ``unprotect()`` restores RW (best effort) for teardown paths.
    """

    def __init__(self, mapping: Any, view: Any, size: int) -> None:
        self._mapping = mapping
        self._view = view
        self.size = size
        self.readonly = False
        self.closed = False

    def __len__(self) -> int:
        return self.size

    def __bytes__(self) -> bytes:
        return bytes(self._view)

    @property
    def view(self) -> Any:
        """Read-only ``memoryview`` over the sealed mapping."""
        return self._view

    def unprotect(self) -> bool:
        """Best-effort restore of read-write access. Never raises."""
        if self.closed:
            return False
        if _mprotect_fn is None:
            return False
        try:
            import ctypes as _ct
            addr = _ct.addressof(_ct.c_char.from_buffer(self._mapping))
            page_size = mmap.PAGESIZE
            aligned = addr & ~(page_size - 1)
            size = ((addr + self.size + page_size - 1)
                    & ~(page_size - 1)) - aligned
            ret = _mprotect_fn(
                _ct.c_void_p(aligned), _ct.c_size_t(size),
                _PROT_READ | 2)
            return ret == 0
        except Exception:
            return False

    def close(self) -> None:
        """Best-effort RW-restore, wipe, and release of the mapping.

        The wipe only runs when the mapping is actually writable: writing
        to a still-read-only mapping would fault, so when ``unprotect``
        fails the wipe is skipped and the mapping is simply released
        (munmap works regardless of prot). Never raises.
        """
        if self.closed:
            return
        # Release the exported view FIRST: mmap.close() with a live
        # exported view raises BufferError (previously swallowed, leaking
        # the mapping). Guarded — release() on an already-released view
        # raises ValueError.
        try:
            rel = getattr(self._view, "release", None)
            if callable(rel):
                rel()
        except Exception:
            pass
        writable = not self.readonly
        if self.readonly:
            try:
                if self.unprotect():
                    writable = True
            except Exception:
                writable = False
        if writable and self.size > 0:
            try:
                mv = memoryview(self._mapping)
                try:
                    mv[:] = b"\x00" * self.size
                except Exception:
                    pass
                finally:
                    try:
                        mv.release()
                    except Exception:
                        pass
            except Exception:
                pass
        try:
            self._mapping.close()
        except Exception:
            pass
        finally:
            self.closed = True
            self.readonly = False


def seal_joined(buf: Any, protect: Any = None) -> SealedSection:
    """Copy *buf* into a dedicated mapping and harden it read-only.

    The sealed mapping owns its pages, so ``mprotect`` cannot wedge
    unrelated heap objects (unlike in-place hardening of a ``bytearray``).

    ``protect`` is an optional ``(addr, size) -> bool`` hook for the
    existing ``MemoryGuard.protect_region`` helper; when omitted (or when
    the hook reports failure) a direct ctypes ``mprotect`` is attempted.
    On platforms without mprotect the mapping is still returned with
    ``readonly`` False — the data stays usable either way.

    Raises ``ValueError`` on empty input. Never raises for protection
    failures.
    """
    data = bytes(buf)
    if not data:
        raise ValueError("seal_joined: empty buffer")
    size = len(data)
    mapping = _alloc_private(size)
    mapping.write(data)
    mapping.seek(0)
    addr = _buffer_address(mapping)
    applied = False
    if protect is not None:
        try:
            applied = bool(protect(addr, size))
        except Exception:
            applied = False
    if not applied:
        applied = _raw_mprotect_readonly(addr, size)
    view = memoryview(mapping).toreadonly()
    sealed = SealedSection(mapping, view, size)
    sealed.readonly = applied
    return sealed


def stream_join_sealed(pack: dict, key: bytes,
                       protect: Any = None) -> SealedSection:
    """``stream_join`` + ``seal_joined``: join, copy, and re-protect RO.

    Verification failures still raise ``ValueError`` exactly like
    ``stream_join``; protection itself stays best-effort and is reported on
    the returned ``SealedSection.readonly`` flag. When sealing cannot
    allocate (e.g. zero-length payloads have no mmap-able region) the plain
    ``bytearray`` path is used and ``protect_after_load`` is attempted on
    it instead — loads never break because of hardening.
    """
    joined = stream_join(pack, key)
    if len(joined):
        try:
            return seal_joined(joined, protect=protect)
        except Exception:
            pass
        protect_after_load(joined, protect=protect)
    # Empty (or unsealable) payload: no mmap-able region exists, so return
    # a zero-length sealed view over a placeholder mapping. Loads never
    # break because of hardening.
    mapping = _alloc_private(1)
    view = memoryview(mapping)[:0].toreadonly()
    sealed = SealedSection(mapping, view, 0)
    sealed.readonly = False
    return sealed
