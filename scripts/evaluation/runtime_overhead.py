"""Measure actual runtime overhead of protected vs unprotected code."""
import time
import subprocess
import sys
from typing import Dict


def measure_execution_time(script_path: str, iterations: int = 3) -> Dict:
    """Measure average execution time of a script over N iterations."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        subprocess.run([sys.executable, script_path], capture_output=True, timeout=30)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return {
        "mean": sum(times) / len(times),
        "min": min(times),
        "max": max(times),
        "iterations": iterations,
    }


def measure_runtime_overhead(unprotected_path: str, protected_path: str, iterations: int = 3) -> Dict:
    """Measure runtime overhead of protection as (protected_time / unprotected_time)."""
    unprotected = measure_execution_time(unprotected_path, iterations)
    protected = measure_execution_time(protected_path, iterations)
    overhead_ratio = protected["mean"] / unprotected["mean"] if unprotected["mean"] > 0 else float('inf')
    return {
        "unprotected": unprotected,
        "protected": protected,
        "overhead_ratio": overhead_ratio,
        "overhead_percentage": (overhead_ratio - 1.0) * 100,
    }
