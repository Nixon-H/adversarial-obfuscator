from __future__ import annotations

import ctypes
import ctypes.util
import logging
import os
import struct
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
    """Execution tracing using kernel facilities.

    Uses ptrace for syscall tracing, /proc for memory/process introspection.
    All methods have graceful fallback when kernel features are unavailable.
    Context-manager safe.
    """

    def __init__(self, capabilities: Optional[KernelCapabilities] = None) -> None:
        self._caps = capabilities or detect_kernel_capabilities()
        self._tracing = False
        self._closed = False

    @property
    def features(self) -> KernelCapabilities:
        return self._caps

    def _check_ptrace_available(self) -> bool:
        """Check if ptrace syscall is available."""
        if _libc is None:
            return False
        try:
            ptrace = _libc.ptrace
            ptrace.restype = ctypes.c_long
            ptrace.argtypes = (ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
            PTRACE_TRACEME = 0
            ret = ptrace(PTRACE_TRACEME, 0, None, None)
            if ret == 0:
                return True
            return False
        except Exception:
            return False

    def trace_syscalls(self) -> bool:
        """Begin tracing syscalls via ptrace.

        Only works on Linux with ptrace enabled. If unavailable,
        falls back to no-op.

        Returns:
            True if tracing active, False if unavailable.
        """
        if self._closed:
            return False
        if self._tracing:
            return True
        if _libc is None:
            log.info("TraceMonitor: ptrace not available, tracing disabled")
            return False
        try:
            ptrace = _libc.ptrace
            ptrace.restype = ctypes.c_long
            ptrace.argtypes = (ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
            PTRACE_TRACEME = 0
            ret = ptrace(PTRACE_TRACEME, 0, None, None)
            if ret == 0:
                self._tracing = True
                log.info("TraceMonitor: ptrace tracing active")
                return True
            log.info("TraceMonitor: ptrace not available")
            return False
        except Exception:
            log.info("TraceMonitor: ptrace not available")
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
