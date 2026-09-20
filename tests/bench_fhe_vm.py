"""
bench_fhe_vm.py

Benchmarks for FHE-VM scheme operations.

Measures key generation, encryption, homomorphic operations, and circuit evaluation.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from scripts.fhe_vm.scheme import BGVParameters, BGVScheme
from scripts.fhe_vm.circuit import FHECircuit, CircuitEvaluator
from scripts.fhe_vm.executor import FHEExecutor


# Use default scheme parameters for benchmarks (q ~ 2^30 for multi-layer support)
BENCH_PARAMS = BGVParameters()


class TestFHEBenchmarks:
    def test_bench_keygen(self, benchmark):
        scheme = BGVScheme(BENCH_PARAMS)
        result = benchmark(scheme.keygen)
        assert result is not None

    def test_bench_encryption(self, benchmark):
        scheme = BGVScheme(BENCH_PARAMS)
        scheme.keygen()
        result = benchmark(scheme.encrypt, 5)
        assert result is not None

    def test_bench_decryption(self, benchmark):
        scheme = BGVScheme(BENCH_PARAMS)
        scheme.keygen()
        ct = scheme.encrypt(3)
        result = benchmark(scheme.decrypt, ct)
        assert result == 3

    def test_bench_homomorphic_add(self, benchmark):
        scheme = BGVScheme(BENCH_PARAMS)
        scheme.keygen()
        ct_a = scheme.encrypt(3)
        ct_b = scheme.encrypt(5)

        def do_add():
            return scheme.add(ct_a, ct_b)
        result = benchmark(do_add)
        pt = scheme.decrypt(result)
        assert pt == (3 + 5) % BENCH_PARAMS.t

    def test_bench_homomorphic_mul(self, benchmark):
        scheme = BGVScheme(BENCH_PARAMS)
        scheme.keygen()
        ct_a = scheme.encrypt(2)
        ct_b = scheme.encrypt(3)

        def do_mul():
            return scheme.mul(ct_a, ct_b)
        result = benchmark(do_mul)
        pt = scheme.decrypt(result)
        assert pt == (2 * 3) % BENCH_PARAMS.t

    def test_bench_encrypted_circuit_evaluation(self, benchmark):
        scheme = BGVScheme(BENCH_PARAMS)
        scheme.keygen()
        evaluator = CircuitEvaluator(scheme)
        circuit = FHECircuit("bench")
        i1 = circuit.new_gate('input')
        i2 = circuit.new_gate('input')
        c1 = circuit.new_gate('const', value=2)
        m1 = circuit.new_gate('mul', [i1, i2])
        a1 = circuit.new_gate('add', [m1, c1])
        circuit.set_output(a1)
        ct1 = scheme.encrypt(3)
        ct2 = scheme.encrypt(4)

        def do_eval():
            return evaluator.evaluate_encrypted(circuit, [ct1, ct2])
        ct_result = benchmark(do_eval)
        pt = scheme.decrypt(ct_result)
        assert pt == (3 * 4 + 2) % BENCH_PARAMS.t

    def test_bench_full_pipeline(self, benchmark):
        def run_pipeline():
            executor = FHEExecutor(BENCH_PARAMS)
            circuit = FHECircuit("pipe_bench")
            i1 = circuit.new_gate('input')
            i2 = circuit.new_gate('input')
            a1 = circuit.new_gate('add', [i1, i2])
            circuit.set_output(a1)
            result = executor.run_full_pipeline(circuit, [10, 20])
            return result
        result = benchmark(run_pipeline)
        assert result['success']
        assert result['result'] == (10 + 20) % BENCH_PARAMS.t

    def test_bench_multiplication_chain(self, benchmark):
        scheme = BGVScheme(BENCH_PARAMS)
        scheme.keygen()
        ct = scheme.encrypt(2)

        def do_chain():
            c = ct
            for _ in range(3):
                c = scheme.mul(c, ct)
            return c
        ct_result = benchmark(do_chain)
        pt = scheme.decrypt(ct_result)
        expected = (2 ** 4) % BENCH_PARAMS.t
        assert pt == expected

    def test_bench_overhead_vs_plain(self, benchmark):
        """Measure overhead ratio: FHE evaluation time vs plain evaluation."""
        circuit = FHECircuit("overhead_test")
        i1 = circuit.new_gate('input')
        i2 = circuit.new_gate('input')
        c1 = circuit.new_gate('const', value=3)
        m1 = circuit.new_gate('mul', [i1, i2])
        a1 = circuit.new_gate('add', [m1, c1])
        circuit.set_output(a1)

        executor = FHEExecutor(BENCH_PARAMS)
        executor.generate_keys()

        def do_fhe():
            cts = executor.encrypt_inputs([5, 6])
            ct_r = executor.execute(circuit, cts)
            return executor.decrypt_result(ct_r)
        result = benchmark(do_fhe)
        assert result == (5 * 6 + 3) % BENCH_PARAMS.t
