from __future__ import annotations

import ctypes
import ctypes.util
import logging
import mmap
import os
import struct
import threading
from types import TracebackType
from typing import Callable, Optional

from .detector import detect_kernel_capabilities, KernelCapabilities

log = logging.getLogger(__name__)

_libc: Optional[ctypes.CDLL] = None
_libc_path = ctypes.util.find_library("c")
if _libc_path:
    try:
        _libc = ctypes.CDLL(_libc_path, use_errno=True)
    except Exception:
        _libc = None


def _init_mprotect() -> Optional[Callable]:
    if _libc is None:
        return None
    try:
        fn = _libc.mprotect
        fn.restype = ctypes.c_int
        fn.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int)
        return fn
    except Exception:
        return None


_mprotect_fn = _init_mprotect()
PROT_NONE = 0
PROT_READ = 1
PROT_WRITE = 2
PROT_EXEC = 4


class MemoryGuard:
    """Memory-level execution protection using available kernel facilities.

    Uses userfaultfd (page-level monitoring), mlock (prevent swapping),
    and mprotect (page protection) when available. Falls back to standard
    mmap with no kernel features.

    Context-manager safe: cleanup on exit even with exceptions.
    """

    def __init__(self, capabilities: Optional[KernelCapabilities] = None) -> None:
        self._caps = capabilities or detect_kernel_capabilities()
        self._monitoring_thread: Optional[threading.Thread] = None
        self._monitoring_active = False
        self._uffd_fd: Optional[int] = None
        self._protected_regions: list[dict] = []
        self._locked = False
        self._closed = False

    @property
    def features(self) -> KernelCapabilities:
        return self._caps

    def protect_region(self, addr: int, size: int) -> bool:
        """Protect a memory region (make non-writable).

        Uses mprotect when available, otherwise no-op.

        Args:
            addr: Starting address of region.
            size: Size in bytes.

        Returns:
            True if protection applied, False on fallback.
        """
        if self._closed:
            return False
        page_size = mmap.PAGESIZE
        aligned_addr = addr & ~(page_size - 1)
        aligned_size = ((addr + size + page_size - 1) & ~(page_size - 1)) - aligned_addr
        if _mprotect_fn is not None:
            try:
                ret = _mprotect_fn(
                    ctypes.c_void_p(aligned_addr),
                    ctypes.c_size_t(aligned_size),
                    PROT_READ | PROT_EXEC,
                )
                if ret == 0:
                    self._protected_regions.append({
                        "addr": aligned_addr,
                        "size": aligned_size,
                        "prot": "RX",
                    })
                    return True
            except Exception:
                pass
        self._protected_regions.append({
            "addr": aligned_addr,
            "size": aligned_size,
            "prot": "none (fallback)",
        })
        return False

    def unprotect_region(self, addr: int, size: int) -> bool:
        """Restore read-write access to a previously protected region.

        Args:
            addr: Starting address of region.
            size: Size in bytes.

        Returns:
            True if restored, False on fallback.
        """
        if self._closed:
            return False
        page_size = mmap.PAGESIZE
        aligned_addr = addr & ~(page_size - 1)
        aligned_size = ((addr + size + page_size - 1) & ~(page_size - 1)) - aligned_addr
        if _mprotect_fn is not None:
            try:
                ret = _mprotect_fn(
                    ctypes.c_void_p(aligned_addr),
                    ctypes.c_size_t(aligned_size),
                    PROT_READ | PROT_WRITE | PROT_EXEC,
                )
                if ret == 0:
                    self._protected_regions = [
                        r for r in self._protected_regions
                        if r["addr"] != aligned_addr
                    ]
                    return True
            except Exception:
                pass
        return False

    def _uffd_monitor_loop(self, callback: Callable[[dict], None]) -> None:
        """Background thread for userfaultfd monitoring."""
        import errno
        uffd = self._uffd_fd
        if uffd is None:
            return
        poll_obj = None
        try:
            import select
            poll_obj = select.poll()
            poll_obj.register(uffd, select.POLLIN)
        except Exception:
            pass
        while self._monitoring_active and uffd is not None:
            try:
                if poll_obj is not None:
                    events = poll_obj.poll(500)
                    if not events:
                        continue
                buf = os.read(uffd, 32)
                if len(buf) < 32:
                    continue
                event = struct.unpack("=QQQBBxxxx", buf)
                msg = {
                    "event": event[0],
                    "arg": event[1],
                    "page": event[2],
                    "wake": event[3],
                }
                try:
                    callback(msg)
                except Exception:
                    log.exception("userfaultfd callback error")
            except OSError as e:
                if e.errno == errno.EAGAIN:
                    continue
                if e.errno == errno.EBADF:
                    break
                log.debug("userfaultfd read error: %s", e)
                continue
            except Exception:
                break

    def monitor_execution(self, callback: Callable[[dict], None]) -> bool:
        """Monitor memory execution via userfaultfd.

        Requires CONFIG_USERFAULTFD and userfaultfd syscall.
        Falls back gracefully if unavailable.

        Args:
            callback: Called with event dict on each page fault.

        Returns:
            True if monitoring active, False if not available.
        """
        if not self._caps.userfaultfd:
            log.info("MemoryGuard: userfaultfd not available, monitor disabled")
            return False
        if self._closed:
            return False
        import fcntl
        uffd = None
        try:
            UFFDIO_API = 0xC018AA3F
            uffd = os.open("/dev/userfaultfd", os.O_RDWR | os.O_CLOEXEC)
            api_struct = struct.pack("=QII", 0xAA, 0, 0)
            result = fcntl.ioctl(uffd, UFFDIO_API, bytearray(api_struct))
            self._uffd_fd = uffd
            UFFDIO_REGISTER = 0xC018AA01
            UFFDIO_REGISTER_MODE_MISSING = 1
            for region in self._protected_regions:
                reg_addr = region["addr"]
                if isinstance(reg_addr, ctypes.c_void_p):
                    reg_addr = reg_addr.value or 0
                reg_struct = struct.pack("=QQQ", reg_addr, region["size"], UFFDIO_REGISTER_MODE_MISSING)
                try:
                    fcntl.ioctl(uffd, UFFDIO_REGISTER, bytearray(reg_struct))
                except Exception:
                    log.debug("UFFDIO_REGISTER failed for region at 0x%x", reg_addr)
            self._monitoring_active = True
            self._monitoring_thread = threading.Thread(
                target=self._uffd_monitor_loop,
                args=(callback,),
                daemon=True,
            )
            self._monitoring_thread.start()
            log.info("MemoryGuard: userfaultfd monitoring active")
            return True
        except Exception:
            if uffd is not None:
                try:
                    os.close(uffd)
                except Exception:
                    pass
            log.info("MemoryGuard: userfaultfd not available, monitor disabled")
            return False

    def lock_memory(self) -> bool:
        """Lock memory to prevent swapping via mlockall.

        Returns:
            True if memory locked, False if not available.
        """
        if not self._caps.mlock:
            return False
        if self._locked:
            return True
        if _libc is None:
            return False
        try:
            mlockall = _libc.mlockall
            mlockall.restype = ctypes.c_int
            mlockall.argtypes = (ctypes.c_int,)
            MCL_FUTURE = 2
            ret = mlockall(MCL_FUTURE)
            if ret == 0:
                self._locked = True
                log.info("MemoryGuard: memory locked (mlockall)")
                return True
            return False
        except Exception:
            return False

    def unlock_memory(self) -> bool:
        """Unlock memory via munlockall.

        Returns:
            True if unlocked, False if not available.
        """
        if not self._locked:
            return True
        if _libc is None:
            return False
        try:
            munlockall = _libc.munlockall
            munlockall.restype = ctypes.c_int
            munlockall.argtypes = ()
            ret = munlockall()
            if ret == 0:
                self._locked = False
                return True
            return False
        except Exception:
            return False

    def allocate_guarded_page(self, size: int = mmap.PAGESIZE) -> Optional[memoryview]:
        """Allocate a guarded memory page via mmap.

        Uses anonymous mmap with no kernel features required.
        The page is readable, writable and executable.

        Args:
            size: Size in bytes (defaults to page size).

        Returns:
            A memoryview of the allocated page, or None on failure.
        """
        if self._closed:
            return None
        try:
            buf = mmap.mmap(
                -1, size,
                prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC,
                flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS,
            )
            mv = memoryview(buf)
            addr = ctypes.addressof(ctypes.c_char.from_buffer(buf))
            self._protected_regions.append({
                "addr": addr,
                "size": size,
                "prot": "RWX (mmap)",
                "mmap": buf,
            })
            return mv
        except Exception:
            log.exception("MemoryGuard: mmap allocation failed")
            return None

    def close(self) -> None:
        """Clean up all resources."""
        if self._closed:
            return
        self._closed = True
        self._monitoring_active = False
        if self._uffd_fd is not None:
            try:
                os.close(self._uffd_fd)
            except Exception:
                pass
            self._uffd_fd = None
        if self._monitoring_thread is not None:
            self._monitoring_thread.join(timeout=2.0)
            self._monitoring_thread = None
        self.unlock_memory()
        for region in self._protected_regions:
            mmap_obj = region.get("mmap")
            if mmap_obj is not None:
                try:
                    mmap_obj.close()
                except Exception:
                    pass
        self._protected_regions.clear()

    def __enter__(self) -> MemoryGuard:
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        self.close()
        return None
