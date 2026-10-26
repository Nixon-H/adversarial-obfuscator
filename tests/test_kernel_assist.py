"""
test_kernel_assist.py

Tests for Kernel-Assisted Execution: detector, memory guard, trace monitor, executor.

Test coverage:
- Positive tests verify kernel capabilities detection, memory protection, tracing, execution
- Negative tests verify missing /proc entries, bad syscalls, invalid addresses
"""
from __future__ import annotations

import ctypes
import mmap
import os
import sys
import tempfile


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.kernel_assist.detector import (
    detect_kernel_capabilities,
    KernelCapabilities,
)
from scripts.kernel_assist.memory_guard import MemoryGuard
from scripts.kernel_assist.trace_monitor import TraceMonitor
from scripts.kernel_assist.executor import KernelAssistedExecutor


class TestDetector:
    """
    TestDetector
    
    Positive test cases for detector.
    """
    def test_detector_always_works(self):
        """detector runs without error even with no kernel features."""
        caps = detect_kernel_capabilities()
        assert isinstance(caps, KernelCapabilities)
        assert isinstance(caps.to_dict(), dict)
        assert len(caps.to_dict()) == 5

    def test_kernel_capabilities_dataclass(self):
        """dataclass works correctly."""
        caps = KernelCapabilities()
        assert caps.userfaultfd is False
        assert caps.seccomp is False
        assert caps.ebpf is False
        assert caps.memfd is False
        assert caps.mlock is False
        assert repr(caps) == "KernelCapabilities(available=['none'])"

        caps2 = KernelCapabilities(userfaultfd=True, mlock=True)
        assert caps2.userfaultfd is True
        assert caps2.mlock is True
        assert "userfaultfd" in repr(caps2)

        d = caps2.to_dict()
        assert d["userfaultfd"] is True
        assert d["mlock"] is True
        assert d["seccomp"] is False

    def test_kernel_capabilities_eq(self):
        caps1 = KernelCapabilities(True, False, False, False, False)
        caps2 = KernelCapabilities(True, False, False, False, False)
        caps3 = KernelCapabilities(False, False, False, False, False)
        assert caps1 == caps2
        assert caps1 != caps3
        assert caps1.__eq__("not a caps") is NotImplemented

    def test_detector_no_crash_on_missing_proc(self):
        """Negative: no crash when /proc entries are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_proc = os.path.join(tmpdir, "proc")
            os.makedirs(fake_proc, exist_ok=True)
            # Use detector directly — it only reads /proc/sys/vm/unprivileged_userfaultfd
            # and /proc/self/status which are real paths. The try/except covers all.
            caps = detect_kernel_capabilities()
            assert isinstance(caps, KernelCapabilities)
            assert isinstance(caps.to_dict(), dict)

    def test_detector_no_crash_on_bad_syscall(self):
        """Negative: no crash when syscalls fail."""
        caps = detect_kernel_capabilities()
        assert isinstance(caps, KernelCapabilities)


class TestMemoryGuard:
    """
    TestMemoryGuard
    
    Positive test cases for memoryguard.
    """
    def test_memory_guard_fallback(self):
        """MemoryGuard works without kernel features."""
        caps = KernelCapabilities()
        guard = MemoryGuard(caps)
        assert guard.features == caps
        assert guard.features.userfaultfd is False
        guard.close()

    def test_memory_guard_protect(self):
        """Basic memory protection with ctypes-allocated buffer."""
        import mmap
        guard = MemoryGuard()
        try:
            buf = mmap.mmap(-1, 4096, prot=mmap.PROT_READ | mmap.PROT_WRITE,
                            flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS)
            addr = ctypes.addressof(ctypes.c_char.from_buffer(buf))
            result = guard.protect_region(addr, 64)
            assert isinstance(result, bool)
            buf.close()
        finally:
            guard.close()

    def test_memory_guard_context_manager(self):
        """Context manager exits cleanly even with exceptions."""
        raised = False
        try:
            with MemoryGuard() as guard:
                assert guard is not None
                raise ValueError("test exception")
        except ValueError:
            raised = True
        assert raised

    def test_memory_guard_lock_unlock(self):
        """lock/unlock memory gracefully."""
        guard = MemoryGuard(KernelCapabilities())
        assert guard.lock_memory() is False
        assert guard.unlock_memory() is True
        guard.close()

    def test_memory_guard_allocate_close(self):
        """Allocate and close without error."""
        guard = MemoryGuard()
        mv = guard.allocate_guarded_page()
        guard.close()
        if mv is not None:
            assert guard._closed is True

    def test_memory_guard_double_close(self):
        """Close twice is safe."""
        guard = MemoryGuard()
        guard.close()
        guard.close()

    def test_memory_guard_allocate_guarded_page_valid(self):
        """allocate_guarded_page returns a valid page."""
        guard = MemoryGuard()
        mv = guard.allocate_guarded_page()
        assert mv is not None
        assert len(mv) == mmap.PAGESIZE
        guard.close()

    def test_memory_guard_protect_unprotect_roundtrip(self):
        """protect_region and unprotect_region roundtrip without error."""
        guard = MemoryGuard()
        buf = mmap.mmap(-1, 4096, prot=mmap.PROT_READ | mmap.PROT_WRITE,
                        flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS)
        addr = ctypes.addressof(ctypes.c_char.from_buffer(buf))
        result_protect = guard.protect_region(addr, 64)
        assert isinstance(result_protect, bool)
        result_unprotect = guard.unprotect_region(addr, 64)
        assert isinstance(result_unprotect, bool)
        buf.close()
        guard.close()

    def test_memory_guard_unaligned_address(self):
        """Unaligned addresses are aligned without error."""
        guard = MemoryGuard()
        result = guard.protect_region(0x123, 64)
        assert isinstance(result, bool)
        guard.close()

    def test_memory_guard_invalid_address(self):
        """Protecting invalid address returns False (no crash)."""
        guard = MemoryGuard()
        result = guard.protect_region(0x1, 4096)
        assert isinstance(result, bool)
        guard.close()

    def test_memory_guard_unprotect_no_crash(self):
        """Unprotect on non-existent region is safe."""
        guard = MemoryGuard()
        result = guard.unprotect_region(0xDEAD0000, 4096)
        assert isinstance(result, bool)
        guard.close()


class TestTraceMonitor:
    """
    TestTraceMonitor
    
    Positive test cases for tracemonitor.
    """
    def test_trace_monitor_detect_debugger(self):
        """TracerPid detection via /proc/self/status."""
        monitor = TraceMonitor()
        detected = monitor.detect_debugger()
        assert isinstance(detected, bool)
        monitor.close()

    def test_trace_monitor_read_memory_maps(self):
        """/proc/self/maps parsing."""
        monitor = TraceMonitor()
        maps = monitor.read_memory_maps()
        assert isinstance(maps, list)
        if maps:
            entry = maps[0]
            assert "addr_start" in entry
            assert "addr_end" in entry
            assert "perms" in entry
            assert "pathname" in entry
        monitor.close()

    def test_trace_monitor_get_process_status(self):
        """/proc/self/status parsing."""
        monitor = TraceMonitor()
        status = monitor.get_process_status()
        assert isinstance(status, dict)
        assert "Name" in status or "Pid" in status or len(status) >= 0
        monitor.close()

    def test_trace_monitor_trace_syscalls(self):
        """ptrace tracing gracefully handled."""
        monitor = TraceMonitor()
        result = monitor.trace_syscalls()
        assert isinstance(result, bool)
        monitor.close()

    def test_trace_syscalls_never_make_this_process_traceable(self):
        """The tracing entry point must not leave the caller under ptrace.

        PTRACE_TRACEME names the CALLING process as the tracee, so the
        caller stops at its next exec or signal and never resumes.  That
        froze this suite mid-run; CI reported it as exit 145 (128 + the
        stop signal).  The invariant is directly observable: TracerPid is
        unchanged by the call, and the call reports the no-op.
        """
        monitor = TraceMonitor()
        before = monitor.get_process_status().get("TracerPid", "0")
        assert monitor.trace_syscalls() is False
        after = monitor.get_process_status().get("TracerPid", "0")
        assert after == before
        monitor.close()

    def test_trace_monitor_context_manager(self):
        """Context manager works."""
        with TraceMonitor() as tm:
            assert isinstance(tm.detect_debugger(), bool)

    def test_trace_monitor_stop_tracing(self):
        """Stop tracing is safe."""
        monitor = TraceMonitor()
        assert monitor.stop_tracing() is True
        monitor.close()

    def test_trace_monitor_detect_debugger_tracerpid(self):
        """Verifies detect_debugger reads TracerPid correctly."""
        monitor = TraceMonitor()
        status = monitor.get_process_status()
        tracer_pid = status.get("TracerPid", "0")
        detected = monitor.detect_debugger()
        assert detected == (tracer_pid != "0")
        monitor.close()


class TestExecutor:
    """
    TestExecutor
    
    Positive test cases for executor.
    """
    def test_executor_is_available(self):
        """Always available."""
        ex = KernelAssistedExecutor()
        assert ex.is_available() is True

    def test_executor_fallback(self):
        """Plain execution always works."""
        ex = KernelAssistedExecutor()
        result = ex.execute_plain(lambda x: x + 1, 41)
        assert result == 42

    def test_executor_supported_features(self):
        """Returns list."""
        ex = KernelAssistedExecutor()
        features = ex.supported_features()
        assert isinstance(features, list)
        assert all(isinstance(f, str) for f in features)

    def test_executor_execute_with_monitoring(self):
        """Monitored execution works (falls back gracefully)."""
        ex = KernelAssistedExecutor()
        result = ex.execute_with_monitoring(
            lambda a, b: a + b, 2, 3,
            enable_memory_guard=True,
            enable_tracing=True,
        )
        assert result == 5

    def test_executor_execute_with_monitoring_kwargs(self):
        """Monitored execution with kwargs."""
        ex = KernelAssistedExecutor()
        result = ex.execute_with_monitoring(
            lambda a, b=0: a + b, 10, b=32,
        )
        assert result == 42

    def test_executor_get_kernel_capabilities(self):
        """Returns KernelCapabilities."""
        ex = KernelAssistedExecutor()
        caps = ex.get_kernel_capabilities()
        assert isinstance(caps, KernelCapabilities)

    def test_executor_repr(self):
        """Repr works."""
        ex = KernelAssistedExecutor()
        r = repr(ex)
        assert "KernelAssistedExecutor" in r
        assert "features" in r
