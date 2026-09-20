"""
bench_leakage.py

Benchmarks for Semantic Leakage Metric (Feature 152).

Measures leakage analysis across all four levels (variable through architecture).
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from irgen.compile import compile_py_to_ir, IrValue
from scripts.leakage.scorer import compute_sli
from scripts.leakage.analyzers import (
    VariableLeakageAnalyzer,
    FunctionLeakageAnalyzer,
    IntentLeakageAnalyzer,
    ArchitectureLeakageAnalyzer,
)
from scripts.leakage.metrics import (
    compute_cfg_similarity,
    compute_opcode_histogram,
    compute_entropy,
    compute_name_preservation,
    compute_call_graph_similarity,
)


BENCH_SRC = """
def add(a, b):
    return a + b

def sub(a, b):
    return a - b

def mul(a, b):
    return a * b

def div(a, b):
    return a // b

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

def process_list(items):
    total = 0
    for item in items:
        total = total + item
    return total

def nested_loops(n):
    result = 0
    for i in range(n):
        for j in range(n):
            result = result + i * j
    return result

def conditional_chain(x):
    if x > 100:
        return "large"
    elif x > 50:
        return "medium"
    elif x > 10:
        return "small"
    else:
        return "tiny"

def compute(a, b, c):
    x = add(a, b)
    y = mul(x, c)
    z = sub(y, a)
    return div(z, b)

def main():
    a = 10
    b = 20
    c = 30
    r1 = compute(a, b, c)
    r2 = factorial(5)
    r3 = fibonacci(10)
    r4 = conditional_chain(r1)
    items = [1, 2, 3, 4, 5]
    r5 = process_list(items)
    r6 = nested_loops(3)
    return r1 + r2 + r3 + r5 + r6
"""


@pytest.fixture(autouse=True)
def reset_counters():
    IrValue.reset_counter()


@pytest.fixture
def bench_ir():
    return compile_py_to_ir(BENCH_SRC)


@pytest.fixture
def bench_ir_identical():
    return compile_py_to_ir(BENCH_SRC)


class TestBenchLeakage:
    def test_full_sli_computation_time(self, bench_ir, bench_ir_identical):
        start = time.perf_counter()
        for _ in range(10):
            compute_sli(bench_ir, bench_ir_identical)
        elapsed = time.perf_counter() - start
        avg_ms = elapsed / 10 * 1000
        assert avg_ms < 5000.0

    def test_variable_analyzer_time(self, bench_ir, bench_ir_identical):
        analyzer = VariableLeakageAnalyzer()
        start = time.perf_counter()
        for _ in range(100):
            analyzer.analyze(bench_ir, bench_ir_identical)
        elapsed = time.perf_counter() - start
        avg_ms = elapsed / 100 * 1000
        assert avg_ms < 500.0

    def test_function_analyzer_time(self, bench_ir, bench_ir_identical):
        analyzer = FunctionLeakageAnalyzer()
        start = time.perf_counter()
        for _ in range(100):
            analyzer.analyze(bench_ir, bench_ir_identical)
        elapsed = time.perf_counter() - start
        avg_ms = elapsed / 100 * 1000
        assert avg_ms < 500.0

    def test_intent_analyzer_time(self, bench_ir, bench_ir_identical):
        analyzer = IntentLeakageAnalyzer()
        start = time.perf_counter()
        for _ in range(100):
            analyzer.analyze(bench_ir, bench_ir_identical)
        elapsed = time.perf_counter() - start
        avg_ms = elapsed / 100 * 1000
        assert avg_ms < 1000.0

    def test_architecture_analyzer_time(self, bench_ir, bench_ir_identical):
        analyzer = ArchitectureLeakageAnalyzer()
        start = time.perf_counter()
        for _ in range(100):
            analyzer.analyze(bench_ir, bench_ir_identical)
        elapsed = time.perf_counter() - start
        avg_ms = elapsed / 100 * 1000
        assert avg_ms < 1000.0

    def test_opcode_histogram_time(self, bench_ir):
        start = time.perf_counter()
        for _ in range(100):
            compute_opcode_histogram(bench_ir)
        elapsed = time.perf_counter() - start
        avg_ms = elapsed / 100 * 1000
        assert avg_ms < 100.0

    def test_entropy_time(self, bench_ir):
        start = time.perf_counter()
        for _ in range(100):
            compute_entropy(bench_ir)
        elapsed = time.perf_counter() - start
        avg_ms = elapsed / 100 * 1000
        assert avg_ms < 100.0

    def test_name_preservation_time(self, bench_ir, bench_ir_identical):
        start = time.perf_counter()
        for _ in range(100):
            compute_name_preservation(bench_ir, bench_ir_identical)
        elapsed = time.perf_counter() - start
        avg_ms = elapsed / 100 * 1000
        assert avg_ms < 500.0

    def test_cfg_similarity_time(self):
        cfg = {f"bb{i}": [f"bb{i+1}"] for i in range(50)}
        cfg["bb49"] = []
        cfg2 = dict(cfg)
        start = time.perf_counter()
        for _ in range(100):
            compute_cfg_similarity(cfg, cfg2)
        elapsed = time.perf_counter() - start
        avg_ms = elapsed / 100 * 1000
        assert avg_ms < 100.0

    def test_call_graph_similarity_time(self):
        cg = {f"func{i}": [f"func{i+1}"] for i in range(50)}
        cg["func49"] = []
        cg2 = dict(cg)
        start = time.perf_counter()
        for _ in range(100):
            compute_call_graph_similarity(cg, cg2)
        elapsed = time.perf_counter() - start
        avg_ms = elapsed / 100 * 1000
        assert avg_ms < 100.0
