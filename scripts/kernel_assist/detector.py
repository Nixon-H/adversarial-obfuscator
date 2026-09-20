from __future__ import annotations

import ctypes
import ctypes.util
import os
import struct

try:
    import ctypes  # noqa: F811

    _libc = ctypes.util.find_library("c")
    LIBC = ctypes.CDLL(_libc, use_errno=True) if _libc else None
except Exception:
    LIBC = None


class KernelCapabilities:
    """Runtime-detected kernel capabilities with fallback state."""

    __slots__ = ("userfaultfd", "seccomp", "ebpf", "memfd", "mlock")

    def __init__(
        self,
        userfaultfd: bool = False,
        seccomp: bool = False,
        ebpf: bool = False,
        memfd: bool = False,
        mlock: bool = False,
    ) -> None:
        self.userfaultfd = userfaultfd
        self.seccomp = seccomp
        self.ebpf = ebpf
        self.memfd = memfd
        self.mlock = mlock

    def to_dict(self) -> dict[str, bool]:
        return {
            "userfaultfd": self.userfaultfd,
            "seccomp": self.seccomp,
            "ebpf": self.ebpf,
            "memfd": self.memfd,
            "mlock": self.mlock,
        }

    def __repr__(self) -> str:
        active = [k for k, v in self.to_dict().items() if v]
        return f"KernelCapabilities(available={active or ['none']})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, KernelCapabilities):
            return NotImplemented
        return all(
            getattr(self, s) == getattr(other, s) for s in self.__slots__
        )


def _check_userfaultfd() -> bool:
    """Check if userfaultfd is available at runtime."""
    uffd_path = "/proc/sys/vm/unprivileged_userfaultfd"
    try:
        if os.path.exists(uffd_path):
            with open(uffd_path) as f:
                val = f.read().strip()
            if val == "1":
                return True
        if not LIBC:
            return False
        SYS_userfaultfd = 323
        _syscall = None
        for name in ("syscall", "__syscall", "syscall_no_errno"):
            fn = getattr(LIBC, name, None)
            if fn is not None:
                _syscall = fn
                break
        if _syscall is None:
            return False
        _syscall.restype = ctypes.c_long
        _syscall.argtypes = (ctypes.c_long,)
        ret = _syscall(SYS_userfaultfd)
        if ret >= 0:
            os.close(ret)
            return True
        return False
    except Exception:
        return False


def _check_seccomp() -> bool:
    """Check if seccomp is available at runtime via prctl."""
    if not LIBC:
        return False
    try:
        PR_GET_SECCOMP = 21
        prctl = LIBC.prctl
        prctl.restype = ctypes.c_long
        prctl.argtypes = (ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong)
        ret = prctl(PR_GET_SECCOMP, 0, 0, 0, 0)
        return ret >= 0
    except Exception:
        return False


def _check_ebpf() -> bool:
    """Check if eBPF is available at runtime."""
    bpf_fs = "/sys/fs/bpf"
    try:
        if os.path.isdir(bpf_fs):
            return True
    except Exception:
        pass
    if not LIBC:
        return False
    try:
        NR_bpf = 321
        _syscall = getattr(LIBC, "syscall", None)
        if _syscall is None:
            return False
        _syscall.restype = ctypes.c_long
        _syscall.argtypes = (ctypes.c_long, ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong)
        BPF_PROG_LOAD = 5
        ret = _syscall(NR_bpf, BPF_PROG_LOAD, None, 0)
        return ret >= 0 or (ret < 0 and ctypes.get_errno() not in (22, 38, 95))
    except Exception:
        return False


def _check_memfd() -> bool:
    """Check if memfd_create is available."""
    if not LIBC:
        return False
    try:
        fn = getattr(LIBC, "memfd_create", None)
        if fn is not None:
            return True
    except Exception:
        pass
    try:
        os.memfd_create
        return True
    except AttributeError:
        pass
    return False


def _check_mlock() -> bool:
    """Check if mlockall is available."""
    if not LIBC:
        return False
    try:
        fn = LIBC.mlockall
        return True
    except AttributeError:
        return False


def detect_kernel_capabilities() -> KernelCapabilities:
    """Detect available kernel features at runtime.

    Returns:
        KernelCapabilities with all features detected via try/except.
        Never raises an exception.
    """
    return KernelCapabilities(
        userfaultfd=_check_userfaultfd(),
        seccomp=_check_seccomp(),
        ebpf=_check_ebpf(),
        memfd=_check_memfd(),
        mlock=_check_mlock(),
    )
