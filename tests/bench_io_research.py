"""
bench_io_research.py

Benchmarks for approximate indistinguishability obfuscation research.

Measures BP construction, randomization, and obfuscation performance.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from scripts.io_research import (
    MatrixBranchingProgram,
    randomize_bp,
    IndistinguishabilityObfuscator,
    indistinguishability_score,
)
from irgen.compile import compile_py_to_ir


def _make_large_bp(dim: int = 8, length: int = 10) -> MatrixBranchingProgram:
    rng = np.random.default_rng(1234)
    pairs = []
    for _ in range(length):
        m = rng.standard_normal((dim, dim))
        pairs.append((m.copy(), m.copy()))
    sv = np.ones(dim)
    return MatrixBranchingProgram(pairs, start_vector=sv, output_index=0)


class TestBenchBPConstruction:
    def test_bench_construction_small(self, benchmark):
        m = np.eye(2)
        benchmark(MatrixBranchingProgram, [(m, m)], np.array([1.0, 1.0]), 0)

    def test_bench_construction_large(self, benchmark):
        benchmark(_make_large_bp, 8, 10)

    def test_bench_randomization(self, benchmark):
        rng = np.random.default_rng(42)
        matrices = [rng.standard_normal((4, 4)) for _ in range(10)]
        benchmark(randomize_bp, matrices)


class TestBenchObfuscation:
    def setup_method(self):
        self.obfuscator = IndistinguishabilityObfuscator()
        source = """
def add(a, b):
    return a + b
"""
        self.ir_module = compile_py_to_ir(source)
        self.func = self.ir_module.functions[0]

    def test_bench_obfuscation(self, benchmark):
        benchmark(self.obfuscator.obfuscate_fragment, self.func)


class TestBenchEvaluation:
    def setup_method(self):
        self.bp = _make_large_bp(dim=8, length=10)
        self.input_bits = [1, 0, 1, 0, 1, 1, 0, 0]

    def test_bench_bp_evaluation(self, benchmark):
        benchmark(self.bp.evaluate, self.input_bits)


class TestBenchSizeOverhead:
    def setup_method(self):
        self.obfuscator = IndistinguishabilityObfuscator()
        source = """
def add(a, b):
    return a + b
"""
        self.ir_module = compile_py_to_ir(source)
        self.func = self.ir_module.functions[0]
        self.result = self.obfuscator.obfuscate_fragment(self.func)

    def test_bench_size_overhead_factor(self, benchmark):
        def _measure():
            obf_bp = self.result.get('bp')
            orig_bp = self.result.get('original_bp')
            obf_size = sum(m0.nbytes + m1.nbytes for m0, m1 in obf_bp.matrices)
            orig_size = sum(m0.nbytes + m1.nbytes for m0, m1 in orig_bp.matrices)
            return obf_size / max(orig_size, 1)
        benchmark(_measure)


class TestBenchIndistinguishability:
    def setup_method(self):
        self.obfuscator = IndistinguishabilityObfuscator()
        self.source = """
def add(a, b):
    return a + b
"""

    def test_bench_indistinguishability_over_runs(self, benchmark):
        def _run():
            ir_module = compile_py_to_ir(self.source)
            func = ir_module.functions[0]
            result = self.obfuscator.obfuscate_fragment(func)
            bp = result.get('bp')
            ref = result.get('original_bp')
            return indistinguishability_score(bp, ref)
        benchmark(_run)


class TestBenchCompileTimeCost:
    def setup_method(self):
        self.obfuscator = IndistinguishabilityObfuscator()
        source = """
def compute(a, b, c):
    x = a + b
    y = x - c
    z = y * 2
    return z
"""
        self.ir_module = compile_py_to_ir(source)
        self.func = self.ir_module.functions[0]

    def test_bench_compile_time_cost(self, benchmark):
        benchmark(self.obfuscator.obfuscate_fragment, self.func)
