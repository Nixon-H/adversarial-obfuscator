"""§4 sensitive-memory handling: lock key and plaintext pages against swap.

The review's row: *"Swap | Sensitive-memory handling"*. The gap it names is
real — `PR_SET_DUMPABLE=0` and `RLIMIT_CORE=0` stop a core dump and an external
`/proc/<pid>/mem` read, but neither prevents the kernel from writing a secret
page to swap, where it outlives the process on disk.

`mlock(2)` is the answer for the pages this code owns. Verified on this machine
before building on it:

    VmLck before          0 kB
    mlock 64 KB buffer    68 kB   (67 kB span, page-rounded)
    munlock               0 kB

so the call genuinely pins the pages rather than silently no-oping.

Scope, and why it is deliberately narrow:

  * only the buffers the loader allocates are locked — the derived key and the
    decrypted section/plaintext buffers;
  * the CPython heap is NOT locked and cannot be: `RLIMIT_MEMLOCK` is 8 MB here
    and the interpreter's heap is far larger, so a whole-process mlock would
    fail and take the artefact with it;
  * `mlock` pins PHYSICAL pages, so every copy of the secret made by the
    interpreter (a `bytes` slice, an interned string, a temporary) is a fresh
    page that is not covered. This is the CPython-erasure limit the review
    states explicitly, and locking does not change it.

Fail-soft by design: a kernel or container that refuses `mlock` (a low
`RLIMIT_MEMLOCK`, a seccomp filter, a restricted container) must not stop the
artefact from running. The result is reported, not swallowed silently, so an
operator can see whether the control is actually in force.
"""
from __future__ import annotations

PAGE = 4096


def emit_snippet() -> str:
    """Return the runtime snippet: `_nx_mlock` / `_nx_munlock` / `_nx_mlock_report`."""
    return r'''
_NX_MLOCKED = []
_NX_MLOCK_STATE = {"supported": None, "locked": 0, "failed": 0}


def _nx_mlock(buf):
    """Pin the pages backing a mutable buffer; return True when locked.

    The range must be page-aligned (mlock rejects an unaligned start), so the
    span is widened to whole pages. That can cover bytes adjacent to the
    buffer in the same page -- unavoidable with page granularity, and stated
    rather than hidden: locking a page protects its neighbours too.
    """
    try:
        import ctypes as _ml_ct
        import ctypes.util as _ml_ctu
        if not isinstance(buf, (bytearray, memoryview)):
            # Counted as a failure, not skipped: the report is what an operator
            # reads to decide whether the control is in force, so a refused
            # buffer must show up rather than silently vanish from the totals.
            _NX_MLOCK_STATE["failed"] += 1
            return False
        if not len(buf):
            _NX_MLOCK_STATE["failed"] += 1
            return False
        _ml_libc = _ml_ct.CDLL(_ml_ctu.find_library("c") or "libc.so.6",
                              use_errno=True)
        _addr = _ml_ct.addressof(_ml_ct.c_char.from_buffer(buf))
        _start = _addr - (_addr % 4096)
        _length = _addr + len(buf) - _start
        _rc = _ml_libc.mlock(_ml_ct.c_void_p(_start), _ml_ct.c_size_t(_length))
        if _rc == 0:
            _NX_MLOCKED.append((_start, _length))
            _NX_MLOCK_STATE["supported"] = True
            _NX_MLOCK_STATE["locked"] += 1
            return True
        _NX_MLOCK_STATE["supported"] = False
        _NX_MLOCK_STATE["failed"] += 1
        return False
    except Exception:
        _NX_MLOCK_STATE["supported"] = False
        _NX_MLOCK_STATE["failed"] += 1
        return False


def _nx_munlock_all():
    """Release every locked span. Called after the plaintext is wiped."""
    try:
        import ctypes as _mu_ct
        import ctypes.util as _mu_ctu
        _mu_libc = _mu_ct.CDLL(_mu_ctu.find_library("c") or "libc.so.6",
                              use_errno=True)
        while _NX_MLOCKED:
            _start, _length = _NX_MLOCKED.pop()
            _mu_libc.munlock(_mu_ct.c_void_p(_start), _mu_ct.c_size_t(_length))
    except Exception:
        pass


def _nx_mlock_report():
    """What actually happened, for the memory probe and for NIXON_MEM_REPORT."""
    return dict(_NX_MLOCK_STATE)


try:
    _NX_MLOCK_RESULT = _nx_mlock_report()
except Exception:
    _NX_MLOCK_RESULT = {}
'''
