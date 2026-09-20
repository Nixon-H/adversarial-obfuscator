from __future__ import annotations

import ctypes
import logging
import mmap
import time
from typing import Any, Callable, Optional

from .detector import detect_kernel_capabilities, KernelCapabilities
from .memory_guard import MemoryGuard
from .trace_monitor import TraceMonitor

log = logging.getLogger(__name__)


class KernelAssistedExecutor:
    """Unified executor with optional kernel-assisted monitoring.

    Runtime capability detection at initialization. Always available,
    but features vary based on detected kernel capabilities.

    Provides:
    - execute_plain(): Fallback execution without kernel features.
    - execute_with_monitoring(): Execution with optional kernel monitoring.
    - supported_features(): List of available feature names.
    - is_available(): Always True.
    """

    def __init__(self, capabilities: Optional[KernelCapabilities] = None) -> None:
        self._caps = capabilities or detect_kernel_capabilities()
        self._memory_guard = MemoryGuard(self._caps)
        self._trace_monitor = TraceMonitor(self._caps)
        self._initialized = True

        active = self.supported_features()
        if active:
            log.info("KernelAssistedExecutor: active features: %s", ", ".join(active))
        else:
            log.info("KernelAssistedExecutor: no kernel features available, using fallback")

    def is_available(self) -> bool:
        """Always returns True. The executor is always usable."""
        return True

    def supported_features(self) -> list[str]:
        """Return list of available kernel feature names."""
        features: list[str] = []
        if self._caps.userfaultfd:
            features.append("userfaultfd")
        if self._caps.seccomp:
            features.append("seccomp")
        if self._caps.ebpf:
            features.append("ebpf")
        if self._caps.memfd:
            features.append("memfd")
        if self._caps.mlock:
            features.append("mlock")
        return features

    def execute_plain(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a function without any kernel-assisted features.

        Always works regardless of kernel capabilities.

        Args:
            func: Callable to execute.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Return value of func.
        """
        return func(*args, **kwargs)

    def execute_with_monitoring(
        self,
        func: Callable[..., Any],
        *args: Any,
        enable_memory_guard: bool = False,
        enable_tracing: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Execute with optional kernel-assisted monitoring.

        Args:
            func: Callable to execute.
            *args: Positional arguments.
            enable_memory_guard: If True, activate MemoryGuard monitoring.
            enable_tracing: If True, activate TraceMonitor tracing.
            **kwargs: Keyword arguments passed to func.

        Returns:
            Return value of func.
        """
        with self._memory_guard as mg:
            if enable_memory_guard:
                mg.lock_memory()
                buf = mmap.mmap(-1, 4096, prot=mmap.PROT_READ | mmap.PROT_WRITE,
                                flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS)
                addr = ctypes.addressof(ctypes.c_char.from_buffer(buf))
                mg.protect_region(addr, 64)
                mg.monitor_execution(lambda ev: None)
            with self._trace_monitor as tm:
                if enable_tracing:
                    tm.trace_syscalls()
                return func(*args, **kwargs)

    def get_kernel_capabilities(self) -> KernelCapabilities:
        """Return detected kernel capabilities."""
        return self._caps

    def __repr__(self) -> str:
        features = self.supported_features()
        return f"KernelAssistedExecutor(features={features or ['fallback']})"
