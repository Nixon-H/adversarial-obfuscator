"""Section-split sealed streaming (V10 adopt, medium).

.. note::

   **Wired into the hybrid loader** (``obfuscator/core/pipeline.py``)
   as the opt-in ``--section-split`` / ``--section-count`` flags.  The
   payload then travels as N independently sealed sections instead of one
   blob, so the whole encrypted payload is never resident in a single
   buffer and a partial dump yields no complete code object.  The
   sections are sealed with the same effective key the loader already
   derives at runtime, so no second key is introduced.  A tampered,
   truncated or mis-keyed pack fails closed through the kill ladder
   (silent, exit 137).

   The loader-side half is :func:`emit_loader_snippet`; the build-side
   half is :func:`pack_json`.  Without the flag the loader is unchanged.

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

from obfuscator.pack_state import state_digest as _state_digest

import ctypes
import ctypes.util
import hashlib
import hmac
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


def _section_key(master: bytes, index: int, nonce: bytes) -> bytes:
    """Per-position section key.

    Tier 1.1 asks for a key derived from the section's POSITION (and, at the
    call site, the licence material and hardware, which are already mixed
    into ``master``).  Using one key for every section meant that recovering
    the key of any single section unlocked all of them -- the opposite of
    what moving decryption is for.  Deriving per position plus the section
    nonce makes each section's key independent.
    """
    return hashlib.sha256(
        b"nx-section-key:" + bytes(master) + index.to_bytes(4, "big") + nonce
    ).digest()


def split_sealed(payload: bytes, *, sections: int = DEFAULT_SECTIONS,
                 key: Optional[bytes] = None,
                 nonce_seed: Optional[bytes] = None) -> dict:
    """Split payload into N sealed sections. Returns pack dict.

    pack = {sections: [...], count, total, key_hint, per_section}: key_hint
    is the hex of sha256(key)[:8] so the loader can confirm it derived the
    same session key (the key itself travels via the existing BLOB_KEY path
    -- never inside the pack).  ``per_section`` marks a pack whose sections
    each use their own derived key.
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
        # nonce_seed: derive the per-section nonces from caller material
        # instead of os.urandom -- the honey/decoy pack must be
        # DETERMINISTIC per build (same seed -> same pack), or two builds
        # with identical inputs diverge byte-wise and reproducible-build
        # checks (test_loader_flag_off_byte_identical_apart_from_markers)
        # fail.  The real payload path keeps urandom.
        if nonce_seed is None:
            nonce = os.urandom(16)
        else:
            nonce = hashlib.sha256(b"nx-nonce:" + bytes(nonce_seed) +
                                   i.to_bytes(4, "big")).digest()[:16]
        # Each section is sealed under its OWN key, derived from the master
        # key, the section index and the section nonce.
        skey = _section_key(key, i, nonce)
        # Keyed tag, not a bare sha256: an unkeyed digest detects corruption
        # but is not a MAC, so anyone able to touch the ciphertext could
        # recompute it.  HMAC with the section key needs no new crypto and
        # keeps the same 32-byte-prefix layout.
        _tag = hmac.new(skey + nonce, part, hashlib.sha256).digest()
        tagged = _tag + part
        enc = bytes(a ^ b for a, b in zip(tagged, _keystream(skey, nonce, len(tagged))))
        out_sections.append({
            "i": i,
            "salt": hashlib.sha256(skey + nonce).hexdigest()[:16],
            "nonce": nonce.hex(),
            "data": enc.hex(),
        })
    return {
        "sections": out_sections,
        "count": n,
        "total": len(data),
        "key_hint": hashlib.sha256(key).hexdigest()[:16],
        "per_section": True,
        # Runtime state validation (§1): a digest over the pack's DECLARED
        # structure, so a hand-edited pack that changes count/total/index
        # ordering fails on internal inconsistency instead of only on the
        # per-section tags. The tags already cover the ciphertext; this binds
        # the metadata those tags are interpreted under, which is the part an
        # attacker would edit to make the loader mis-slice a pack.
        "state": _state_digest(out_sections, n, len(data)),
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
    per_section = bool(pack.get("per_section"))
    for sec in ordered:
        nonce = bytes.fromhex(sec["nonce"])
        enc = bytes.fromhex(sec["data"])
        # Per-position key when the pack says so; the legacy single-key path
        # stays for packs built before the change.
        skey = _section_key(bytes(key), int(sec["i"]), nonce) if per_section else bytes(key)
        tagged = bytes(a ^ b for a, b in zip(enc, _keystream(skey, nonce, len(enc))))
        if len(tagged) < 32:
            raise ValueError("section truncated")
        tag, part = tagged[:32], tagged[32:]
        if not hmac.compare_digest(
                hmac.new(skey + nonce, part, hashlib.sha256).digest(), tag):
            raise ValueError(f"section {sec['i']} integrity failure")
        joined.extend(part)
    if len(joined) != pack["total"]:
        raise ValueError("joined length mismatch")
    return joined


def pack_json(payload: bytes, *, sections: int = DEFAULT_SECTIONS,
              key: Optional[bytes] = None,
              nonce_seed: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """Split + serialize. Returns (json_bytes, session_key).

    The caller transports json_bytes (inside the fallback blob) and the
    session key via the existing BLOB_KEY path.  ``nonce_seed`` makes the
    pack deterministic (see split_sealed).
    """
    key = os.urandom(32) if key is None else bytes(key)
    pack = split_sealed(payload, sections=sections, key=key,
                        nonce_seed=nonce_seed)
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
    # CDLL(None) resolves libc from the already-loaded process image. find_library
    # can shell out to the toolchain on macOS, and a subprocess launched from a
    # threaded build has been observed to block for minutes.
    _libc = ctypes.CDLL(None, use_errno=True)
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


# ---------------------------------------------------------------------------
# Loader-side snippet
# ---------------------------------------------------------------------------

#: Name of the join function emitted into the loader.
JOIN_FUNC = "_nx_section_join"

#: The loader-side join, as source.  Stdlib only (json, hashlib, base64);
#: it mirrors :func:`stream_join` exactly, including the failure cases:
#: wrong count, index mismatch, a tampered section, a length mismatch or a
#: key that does not match the pack's key hint.  It returns ``None`` on any
#: failure so the caller can fail closed.
LOADER_JOIN_SOURCE = '''def {FUNC}(pack_b85, key):
    """Join the sealed sections of a payload pack.

    The pack travels base85-encoded (one string, no quoting hazards) and
    the key is the one the loader already derives at runtime, so the
    section seal never needs a second key in the artifact.
    """
    import base64 as _nx_sb64
    import hashlib as _nx_sh
    import hmac as _nx_hm
    import json as _nx_sj
    try:
        pack = _nx_sj.loads(_nx_sb64.b85decode(pack_b85).decode("utf-8"))
        sections = pack["sections"]
        # §1 runtime state validation: the declared structure must match the
        # content it describes. Fails closed on a pack without `state`.
        if not _nx_pack_state_ok(pack):
            raise ValueError("section pack state invalid")
        # §1 runtime state validation (shared check; see pack_state.py).
        if not _nx_pack_state_ok(pack):
            raise ValueError("section pack state invalid")
        if len(sections) != pack["count"]:
            raise ValueError("section count mismatch")
        if _nx_sh.sha256(bytes(key)).hexdigest()[:16] != pack.get("key_hint"):
            raise ValueError("section key mismatch")
        ordered = sorted(sections, key=lambda s: s["i"])
        if [s["i"] for s in ordered] != list(range(pack["count"])):
            raise ValueError("section index mismatch")
        out = bytearray()
        _per_section = bool(pack.get("per_section"))
        for sec in ordered:
            nonce = bytes.fromhex(sec["nonce"])
            enc = bytes.fromhex(sec["data"])
            # Per-position key: sha256("nx-section-key:" + master + index +
            # nonce).  Must match split_sealed exactly.
            if _per_section:
                skey = _nx_sh.sha256(
                    b"nx-section-key:" + bytes(key)
                    + int(sec["i"]).to_bytes(4, "big") + nonce).digest()
            else:
                skey = bytes(key)
            ks = bytearray()
            c = 0
            while len(ks) < len(enc):
                ks.extend(_nx_sh.sha256(skey + nonce + c.to_bytes(8, "big")).digest())
                c += 1
            tagged = bytes(a ^ b for a, b in zip(enc, bytes(ks[:len(enc)])))
            if len(tagged) < 32:
                raise ValueError("section truncated")
            tag, part = tagged[:32], tagged[32:]
            if not _nx_hm.compare_digest(
                    _nx_hm.new(skey + nonce, part, _nx_sh.sha256).digest(), tag):
                raise ValueError("section integrity failure")
            out.extend(part)
        if len(out) != pack["total"]:
            raise ValueError("joined length mismatch")
        return out
    except Exception:
        return None
'''


def emit_loader_snippet(func_name: str = None) -> str:
    """Return the loader-side join source, ready to embed.

    The emitted function is self-contained (stdlib imports only) and
    returns ``None`` on any verification failure, so the caller can fail
    closed instead of running a partially joined payload.
    """
    name = func_name or JOIN_FUNC
    from obfuscator.pack_state import emit_state_check_snippet as _esc
    return _esc() + "\n" + LOADER_JOIN_SOURCE.replace("{FUNC}", name)


#: Loader-side MOVING decryption.  Each section is decrypted on demand,
#: handed to the sink, then wiped, so the process never holds the whole
#: plaintext at once.  A memory dump therefore captures one section, not the
#: payload.
LOADER_MOVING_SOURCE = '''def {FUNC}(pack_b85, key, sink):
    """Decrypt one section at a time and hand it to ``sink``.

    ``sink(bytes)`` is called once per section, in order, with that
    section's plaintext only.  The buffer is zeroed before the next section
    is decrypted, so at no instant does the process hold more than one
    section of plaintext.  Returns True on success, False on any
    verification failure (the caller must fail closed).

    This is the moving-decryption counterpart of the whole-payload join:
    the same per-section seal and HMAC, but the plaintext never accumulates.
    """
    import base64 as _nx_mb64
    import hashlib as _nx_mh
    import hmac as _nx_mhm
    import json as _nx_mj
    try:
        pack = _nx_mj.loads(_nx_mb64.b85decode(pack_b85).decode("utf-8"))
        sections = pack["sections"]
        # §1 runtime state validation (shared check; see pack_state.py).
        if not _nx_pack_state_ok(pack):
            return False
        if len(sections) != pack["count"]:
            return False
        # Same key_hint check as the whole-payload join.
        if _nx_mh.sha256(bytes(key)).hexdigest()[:16] != pack.get("key_hint"):
            return False
        ordered = sorted(sections, key=lambda s: s["i"])
        if [s["i"] for s in ordered] != list(range(pack["count"])):
            return False
        total = 0
        _per_section = bool(pack.get("per_section"))
        for entry in ordered:
            nonce = bytes.fromhex(entry["nonce"])
            enc = bytes.fromhex(entry["data"])
            if _per_section:
                skey = _nx_mh.sha256(
                    b"nx-section-key:" + bytes(key)
                    + int(entry["i"]).to_bytes(4, "big") + nonce).digest()
            else:
                skey = bytes(key)
            ks = bytearray()
            c = 0
            while len(ks) < len(enc):
                ks.extend(_nx_mh.sha256(skey + nonce + c.to_bytes(8, "big")).digest())
                c += 1
            tagged = bytearray(a ^ b for a, b in zip(enc, bytes(ks[:len(enc)])))
            for i in range(len(ks)):
                ks[i] = 0
            if len(tagged) < 32:
                return False
            tag, part = bytes(tagged[:32]), bytes(tagged[32:])
            if not _nx_mhm.compare_digest(
                    _nx_mhm.new(skey + nonce, part, _nx_mh.sha256).digest(), tag):
                return False
            buf = bytearray(part)
            try:
                sink(bytes(buf))
            finally:
                for i in range(len(buf)):
                    buf[i] = 0
            total += len(part)
        if total != pack["total"]:
            return False
        return True
    except Exception:
        return False
'''


def emit_moving_snippet(func_name: str = "_nx_section_walk") -> str:
    """Return the loader-side MOVING-decryption source, ready to embed."""
    from obfuscator.pack_state import emit_state_check_snippet as _esc
    return _esc() + "\n" + LOADER_MOVING_SOURCE.replace("{FUNC}", func_name)


#: Loader-side STREAMING decompression.  This is the piece that makes moving
#: decryption real: instead of joining every section into one ciphertext
#: buffer and decompressing that, each section is decrypted, fed straight
#: into an incremental decompressor, and wiped.  Neither the full ciphertext
#: nor the full compressed stream is ever resident.
LOADER_STREAM_SOURCE = '''def {FUNC}(pack_b85, key):
    """Decrypt + decompress section by section; return the raw payload.

    Returns a ``bytearray`` (mutable, so the caller can wipe it) or None on
    any verification failure.  At no point does the process hold the whole
    ciphertext or the whole compressed stream: each section is decrypted
    into a small buffer, pushed through the incremental decompressor, and
    zeroed before the next section is touched.
    """
    import base64 as _nx_sb64
    import bz2 as _nx_sbz2
    import hashlib as _nx_sh
    import hmac as _nx_shm
    import json as _nx_sj
    import lzma as _nx_slz
    import zlib as _nx_szl
    try:
        pack = _nx_sj.loads(_nx_sb64.b85decode(pack_b85).decode("utf-8"))
        sections = pack["sections"]
        # §1 runtime state validation (shared check; see pack_state.py).
        if not _nx_pack_state_ok(pack):
            return None
        if len(sections) != pack["count"]:
            return None
        if _nx_sh.sha256(bytes(key)).hexdigest()[:16] != pack.get("key_hint"):
            return None
        ordered = sorted(sections, key=lambda s: s["i"])
        if [s["i"] for s in ordered] != list(range(pack["count"])):
            return None
        # The compression backend is chosen by the first plaintext byte, so
        # it can only be selected once the first section is decrypted.
        dec = None
        out = bytearray()
        total = 0
        _per_section = bool(pack.get("per_section"))
        for idx, entry in enumerate(ordered):
            nonce = bytes.fromhex(entry["nonce"])
            enc = bytes.fromhex(entry["data"])
            if _per_section:
                skey = _nx_sh.sha256(
                    b"nx-section-key:" + bytes(key)
                    + int(entry["i"]).to_bytes(4, "big") + nonce).digest()
            else:
                skey = bytes(key)
            ks = bytearray()
            c = 0
            while len(ks) < len(enc):
                ks.extend(_nx_sh.sha256(skey + nonce + c.to_bytes(8, "big")).digest())
                c += 1
            tagged = bytearray(a ^ b for a, b in zip(enc, bytes(ks[:len(enc)])))
            for i in range(len(ks)):
                ks[i] = 0
            if len(tagged) < 32:
                return None
            tag, part = bytes(tagged[:32]), bytes(tagged[32:])
            if not _nx_shm.compare_digest(
                    _nx_shm.new(skey + nonce, part, _nx_sh.sha256).digest(), tag):
                return None
            buf = bytearray(part)
            try:
                if dec is None:
                    # First section: pick the backend from its first byte and
                    # strip that byte from the stream.
                    first = buf[0] if buf else -1
                    body = bytes(buf[1:]) if buf else b""
                    if first == 0x01:
                        dec = _nx_sbz2.BZ2Decompressor()
                    elif first == 0x02:
                        dec = _nx_slz.LZMADecompressor()
                    elif first == 0x00:
                        dec = _nx_szl.decompressobj()
                    else:
                        # Legacy prefix-less zlib.
                        dec = _nx_szl.decompressobj()
                        body = bytes(buf)
                    out.extend(dec.decompress(body))
                else:
                    out.extend(dec.decompress(bytes(buf)))
            finally:
                for i in range(len(buf)):
                    buf[i] = 0
            total += len(part)
        if total != pack["total"]:
            return None
        # Flush whatever the incremental decompressor is still holding.
        try:
            out.extend(dec.flush())
        except Exception:
            pass
        return out
    except Exception:
        return None
'''


def emit_stream_snippet(func_name: str = "_nx_section_stream") -> str:
    """Return the loader-side STREAMING decrypt+decompress source."""
    from obfuscator.pack_state import emit_state_check_snippet as _esc
    return _esc() + "\n" + LOADER_STREAM_SOURCE.replace("{FUNC}", func_name)
