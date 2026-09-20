"""
bench_kernel_assist.py

Benchmarks for Kernel-Assisted Execution.

Measures detector, memory guard, and executor initialization performance.
"""
from __future__ import annotations

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from scripts.kernel_assist.detector import (
    detect_kernel_capabilities,
    KernelCapabilities,
)
from scripts.kernel_assist.memory_guard import MemoryGuard
from scripts.kernel_assist.trace_monitor import TraceMonitor
from scripts.kernel_assist.executor import KernelAssistedExecutor


def _empty_func():
    return 42


def _compute_func(n: int = 1000) -> int:
    total = 0
    for i in range(n):
        total += i * i
    return total


class TestBenchDetector:
    def test_bench_detector_init(self, benchmark):
        def _run():
            return detect_kernel_capabilities()
        benchmark(_run)

    def test_bench_detector_to_dict(self, benchmark):
        caps = detect_kernel_capabilities()
        benchmark(caps.to_dict)


class TestBenchMemoryGuard:
    def test_bench_memory_guard_protect(self, benchmark):
        def _run():
            guard = MemoryGuard(KernelCapabilities())
            guard.protect_region(0, 4096)
            guard.close()
        benchmark(_run)

    def test_bench_memory_guard_alloc(self, benchmark):
        def _run():
            guard = MemoryGuard()
            mv = guard.allocate_guarded_page(4096)
            guard.close()
            return mv
        benchmark(_run)

    def test_bench_memory_guard_context(self, benchmark):
        def _run():
            with MemoryGuard() as guard:
                guard.allocate_guarded_page()
        benchmark(_run)


class TestBenchTraceMonitor:
    def test_bench_trace_monitor_maps(self, benchmark):
        monitor = TraceMonitor()
        benchmark(monitor.read_memory_maps)
        monitor.close()

    def test_bench_trace_monitor_status(self, benchmark):
        monitor = TraceMonitor()
        benchmark(monitor.get_process_status)
        monitor.close()

    def test_bench_trace_monitor_debugger(self, benchmark):
        monitor = TraceMonitor()
        benchmark(monitor.detect_debugger)
        monitor.close()


class TestBenchExecutor:
    def test_bench_executor_plain(self, benchmark):
        ex = KernelAssistedExecutor()
        benchmark(ex.execute_plain, _empty_func)

    def test_bench_executor_monitored(self, benchmark):
        ex = KernelAssistedExecutor()
        benchmark(
            ex.execute_with_monitoring,
            _compute_func,
            100,
            enable_memory_guard=True,
            enable_tracing=True,
        )

    def test_bench_executor_init(self, benchmark):
        benchmark(KernelAssistedExecutor)

    def test_bench_executor_supported_features(self, benchmark):
        ex = KernelAssistedExecutor()
        benchmark(ex.supported_features)
