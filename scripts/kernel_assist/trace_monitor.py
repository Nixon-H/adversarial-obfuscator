from __future__ import annotations

import ctypes
import ctypes.util
import logging
from types import TracebackType
from typing import Optional

from .detector import detect_kernel_capabilities, KernelCapabilities

log = logging.getLogger(__name__)

_libc: Optional[ctypes.CDLL] = None
_libc_path = ctypes.util.find_library("c")
if _libc_path:
    try:
        _libc = ctypes.CDLL(_libc_path, use_errno=True)
    except Exception:
        _libc = None


class TraceMonitor:
    """Process introspection through kernel facilities.

    Reads /proc for memory maps, process status and debugger detection.
    Syscall tracing through ptrace is deliberately not offered in-process:
    PTRACE_TRACEME would make the *caller* the tracee and freeze it on its
    next exec or signal (see :meth:`trace_syscalls`).  All methods have a
    graceful fallback when kernel features are unavailable.  Context-manager
    safe.
    """

    def __init__(self, capabilities: Optional[KernelCapabilities] = None) -> None:
        self._caps = capabilities or detect_kernel_capabilities()
        self._tracing = False
        self._closed = False

    @property
    def features(self) -> KernelCapabilities:
        return self._caps

    def _check_ptrace_available(self) -> bool:
        """Report whether the ptrace entry point exists, without calling it.

        This used to probe with ptrace(PTRACE_TRACEME).  TRACEME names the
        CALLING process as the tracee: on success the caller stops at its
        next exec or signal, and with no tracer waiting to resume it the
        process hangs.  In a test run that froze the interpreter mid-suite
        (CI reported it as exit 145) -- the same footgun already removed
        from obfuscator/core/sources.py.  A symbol check answers the
        question with no side effect.
        """
        return _libc is not None and hasattr(_libc, "ptrace")

    def trace_syscalls(self) -> bool:
        """Report that in-process syscall tracing is unavailable.

        ptrace cannot trace the process that calls it.  PTRACE_TRACEME
        makes the CALLER the tracee and leaves it to stop on its next
        exec or signal; whatever process runs this -- pytest included --
        then hangs at an arbitrary point instead of being traced.  CI
        spent weeks red on exactly that (128 + the stop signal, exit
        145).  Tracing a child needs fork(), TRACEME in the child, then
        exec, which this in-process monitor does not model, so callers
        get the documented graceful no-op.

        Returns:
            Always False: no tracing is activated and no process state
            changes.
        """
        log.info(
            "TraceMonitor: in-process syscall tracing unavailable; "
            "PTRACE_TRACEME would stop the caller, not trace it"
        )
        return False

    def stop_tracing(self) -> bool:
        """Stop ptrace tracing.

        Returns:
            True if stopped or not tracing, False on error.
        """
        if not self._tracing:
            return True
        self._tracing = False
        return True

    def detect_debugger(self) -> bool:
        """Detect if a debugger is attached by reading /proc/self/status TracerPid.

        Returns:
            True if debugger (TracerPid != 0) detected, False otherwise.
            Always safe - never raises.
        """
        try:
            with open("/proc/self/status") as f:
                for line in f:
                    if line.startswith("TracerPid:"):
                        pid_str = line.split(":", 1)[1].strip()
                        pid = int(pid_str) if pid_str.isdigit() else 0
                        return pid != 0
        except Exception:
            pass
        return False

    def read_memory_maps(self) -> list[dict[str, str]]:
        """Read /proc/self/maps for memory mapping introspection.

        Returns:
            List of dicts with addr_start, addr_end, perms, offset, dev,
            inode, pathname. Empty list on failure.
        """
        maps: list[dict[str, str]] = []
        try:
            with open("/proc/self/maps") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(None, 5)
                    if len(parts) < 5:
                        continue
                    addr_range = parts[0]
                    perms = parts[1]
                    offset = parts[2]
                    dev = parts[3]
                    inode = parts[4]
                    pathname = parts[5] if len(parts) > 5 else ""
                    if "-" in addr_range:
                        start, end = addr_range.split("-", 1)
                    else:
                        start, end = addr_range, ""
                    maps.append({
                        "addr_start": start,
                        "addr_end": end,
                        "perms": perms,
                        "offset": offset,
                        "dev": dev,
                        "inode": inode,
                        "pathname": pathname,
                    })
        except Exception:
            pass
        return maps

    def get_process_status(self) -> dict[str, str]:
        """Read /proc/self/status for process state monitoring.

        Returns:
            Dict of key-value pairs from /proc/self/status.
            Empty dict on failure.
        """
        status: dict[str, str] = {}
        try:
            with open("/proc/self/status") as f:
                for line in f:
                    if ":" in line:
                        key, val = line.split(":", 1)
                        status[key.strip()] = val.strip()
        except Exception:
            pass
        return status

    def close(self) -> None:
        """Clean up tracing resources."""
        if self._closed:
            return
        self._closed = True
        self.stop_tracing()

    def __enter__(self) -> TraceMonitor:
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        self.close()
        return None
