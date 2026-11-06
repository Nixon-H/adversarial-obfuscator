"""
bench_fhe_vm.py

Benchmarks for FHE-VM scheme operations.

Measures key generation, encryption, homomorphic operations, and circuit evaluation.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
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


class TestBGVArithmeticIsExact:
    """The two defects that made this suite fail roughly once in a few hundred runs.

    Neither could be reproduced from the failing run: the noise comes from
    random.SystemRandom(), so the draw that broke it was gone. Pinning the
    arithmetic directly is the only way to keep them fixed.
    """

    def test_ring_multiply_full_does_not_wrap_int64(self):
        """Eight products of ~2**60 sum past 2**63. np.convolve wrapped silently."""
        from scripts.fhe_vm.scheme import BGVPolynomial

        n, q = 8, 1073741827
        a = np.array([q - 1] * n, dtype=np.int64)
        b = np.array([q - 1] * n, dtype=np.int64)

        expected = [0] * n
        for i in range(n):
            for j in range(n):
                idx = i + j
                if idx < n:
                    expected[idx] += (q - 1) * (q - 1)
                else:
                    expected[idx - n] -= (q - 1) * (q - 1)

        assert sum(expected) > 2 ** 63 - 1, "this case no longer crosses the int64 edge"
        got = [int(x) for x in BGVPolynomial.ring_multiply_full(a, b)]
        assert got == expected, "ring product wrapped; it must be exact"

    def test_delta_scaling_matches_exact_rational_rounding(self):
        """The scaling must not route a >2**53 value through float64.

        np.round(x / delta) converts to double first and loses the low bits, so it
        disagrees with exact rounding exactly where the scheme needs it to be
        right. Fraction is the oracle: round() on a Fraction rounds half to even
        on the exact rational, with no float involved.

        delta is odd here, so an exact .5 tie cannot occur -- the disagreement is
        purely the float conversion, which is what the implementation removed.
        """
        from fractions import Fraction

        delta = 1073741827 // 7
        assert delta % 2 == 1, "an even delta would introduce real ties"

        def scale(x):
            quo, rem = divmod(int(x), delta)
            twice = 2 * rem
            if twice > delta:
                return quo + 1
            if twice < delta:
                return quo
            return quo + (quo & 1)

        probes = [k for k in range(-400, 400)]
        probes += [10 ** k for k in range(1, 19)]
        probes += [-(10 ** k) for k in range(1, 19)]
        probes += [2 ** 53, 2 ** 53 + 1, 2 ** 62, 2 ** 62 + 12345]

        for k in probes:
            for x in (k * delta + k, k * delta - k):
                assert scale(x) == round(Fraction(x, delta)), (
                    "scaling disagrees with exact rounding at x=%d" % x)
