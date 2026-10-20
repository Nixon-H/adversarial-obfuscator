"""
bench_conftest.py

Benchmark fixtures and shared configuration.

Provides common benchmark fixtures used across bench_*.py files.
"""
import pytest

@pytest.fixture
def benchmark_source():
    return "def add(a, b): return a + b\n" * 100  # 100 small functions

@pytest.fixture
def large_source():
    lines = []
    for i in range(50):
        lines.append(f"def func_{i}(x):")
        lines.append("    r = x")
        for j in range(50):
            lines.append(f"    r = r + {j} if r > {j} else r - {j}")
        lines.append("    return r")
    return "\n".join(lines)
