"""Runtime memory hardening (§4): anti-dump policy for the protected process.

The measured problem (PyDeObsBench memory probe, 2026-11-18): a running
protected artefact leaves its payload secrets readable in `rw-p [anon]` pages
for 91% of its lifetime. 4/4 secrets were recovered from the `inventory`
target, including a production database password. Section sealing and moving
decryption do not help, because the payload must eventually hold its own
constants as ordinary Python objects to run.

This module cannot fix that -- CPython gives no guaranteed erasure, and the
review says so explicitly. What it CAN do is remove the cheap channels an
attacker uses to reach those objects, and each control below is verified
rather than assumed:

  * ``PR_SET_DUMPABLE=0`` -- measured: it makes ``os.open("/proc/<pid>/mem")``
    fail with EACCES even for the parent process (scripts/verify_dumpable.py).
    This is the channel the memory probe itself uses, so it is the one that
    matters most.
  * core dumps disabled (``RLIMIT_CORE=0``) -- a crash cannot leave a full
    heap image on disk. Verified by reading the limit back.
  * ``MADV_DONTDUMP`` on the interpreter heap is NOT attempted: Python does
    not expose the heap range portably, and a guess would be a false claim.
  * swap: not addressable from userspace without mlock of every object, which
    would also have to be applied by the payload. Documented as a limit, not
    silently skipped.

The snippet is deliberately defensive: every step is wrapped, and a kernel
that refuses a control leaves the process running rather than crashing it.
It also self-reports what actually took effect under
``NIXON_MEM_REPORT=<path>``, so a benchmark can check the control instead of
trusting the build log.
"""
from __future__ import annotations


def emit_snippet(native_enforced: bool = False) -> str:
    """Return the runtime anti-dump snippet (Python source, no placeholders).

    ``native_enforced=True`` (2026-11-19) is for native-only builds, where the
    anti-dump syscalls themselves live in the stripped blob
    (native/enforcement.c, called fail-closed by the loader BEFORE any payload
    code runs). DS 4.1 Flash reconstructed the Python form verbatim from
    artefact text (§5l), so for those builds the snippet keeps only the
    NIXON_MEM_REPORT diagnostic and reads the enforcement bitmask
    (``_NX_NATIVE_ENF``, set by the loader from the native entry's return:
    1 = dumpable off, 2 = core limit zero, 4 = deny-attach) instead of naming
    or calling any syscall. Default False keeps the historical Python form for
    every build that can still reach payload plaintext through Python.
    """
    if not native_enforced:
        return r'''
def _nx_mem_harden():
    """Harden this process against the cheap memory-recovery channels.

    Each control is verified after it is applied and the outcome is recorded,
    because a hardening call that silently no-ops is indistinguishable from
    one that works unless you look.
    """
    _nx_result = {}
    try:
        import ctypes as _nx_ct
        import ctypes.util as _nx_ctu
        # PR_SET_DUMPABLE = 4: clears the suid_dumpable flag, which makes
        # /proc/<pid>/mem unreadable to OTHER processes (including the parent)
        # and disables core dumps for this process. Measured 2026-11-18:
        # os.open("/proc/<pid>/mem") fails EACCES after this call.
        _nx_libc = _nx_ct.CDLL(_nx_ctu.find_library("c") or "libc.so.6",
                              use_errno=True)
        _nx_rc = _nx_libc.prctl(4, 0, 0, 0, 0)
        _nx_result["dumpable"] = ("ok" if _nx_rc == 0
                                  else "failed(errno=%d)" % _nx_ct.get_errno())
    except Exception as _nx_e:
        _nx_result["dumpable"] = "unavailable(%s)" % (type(_nx_e).__name__,)
    try:
        import resource as _nx_res
        _nx_soft, _nx_hard = _nx_res.getrlimit(_nx_res.RLIMIT_CORE)
        _nx_res.setrlimit(_nx_res.RLIMIT_CORE, (0, _nx_hard))
        _nx_now, _ = _nx_res.getrlimit(_nx_res.RLIMIT_CORE)
        _nx_result["core_limit"] = ("0" if _nx_now == 0
                                    else "still %d" % (_nx_now,))
    except Exception as _nx_e:
        _nx_result["core_limit"] = "unavailable(%s)" % (type(_nx_e).__name__,)
    try:
        # A crash dump can also be produced by an explicit SIGQUIT handler;
        # Python's default already kills, so nothing to do beyond the limit.
        _nx_result["core_policy"] = "rlimit_only"
    except Exception:
        pass
    try:
        import os as _nx_os
        _nx_report = _nx_os.environ.get("NIXON_MEM_REPORT")
        if _nx_report:
            with open(_nx_report, "a", encoding="utf-8") as _nx_fh:
                _nx_fh.write("mem_harden " + " ".join(
                    "%s=%s" % (k, v) for k, v in sorted(_nx_result.items())
                ) + "\n")
    except Exception:
        pass
    return _nx_result


try:
    _NX_MEM_HARDENING = _nx_mem_harden()
except Exception:
    _NX_MEM_HARDENING = {}
'''
    return r'''
def _nx_mem_harden():
    """Record what the NATIVE enforcement applied at load time.

    The syscalls live in the stripped blob (native/enforcement.c); the loader
    captured the entry's return bitmask in _NX_NATIVE_ENF. This reports it so
    the NIXON_MEM_REPORT diagnostic stays meaningful without re-deriving any
    syscall constant in artefact text.
    """
    _nx_result = {}
    _nx_mask = globals().get("_NX_NATIVE_ENF", 0)
    _nx_result["dumpable"] = "native(mask=%d)" % (_nx_mask,)
    _nx_result["core_limit"] = "native(mask=%d)" % (_nx_mask,)
    _nx_result["core_policy"] = "native_enforcement"
    try:
        import os as _nx_os
        _nx_report = _nx_os.environ.get("NIXON_MEM_REPORT")
        if _nx_report:
            with open(_nx_report, "a", encoding="utf-8") as _nx_fh:
                _nx_fh.write("mem_harden " + " ".join(
                    "%s=%s" % (k, v) for k, v in sorted(_nx_result.items())
                ) + "\n")
    except Exception:
        pass
    return _nx_result


try:
    _NX_MEM_HARDENING = _nx_mem_harden()
except Exception:
    _NX_MEM_HARDENING = {}
'''
