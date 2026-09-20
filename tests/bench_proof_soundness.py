"""
bench_proof_soundness.py

Benchmarks for Proof Soundness Verification (Feature 174).

Measures mutation, oracle checks, and harness execution performance.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.proof_soundness.harness import (
    ProofSoundnessHarness,
    SoundnessTest,
    generate_soundness_tests,
)
from scripts.proof_soundness.mutator import ProofMutationEngine
from scripts.proof_soundness.oracle import TransformationOracle


def bench_mutation_generation():
    engine = ProofMutationEngine(seed=42)
    source = "def f(a, b):\n    c = a + b\n    d = c * 2\n    if d > 10:\n        return d\n    return 0\n"
    start = time.perf_counter()
    for _ in range(100):
        engine.generate_mutations(source, count=10)
    elapsed = (time.perf_counter() - start) / 100
    print(f"  ProofMutationEngine.generate_mutations x10: {elapsed * 1000:.2f}ms avg ({100} runs)")
    return elapsed


def bench_oracle_equivalence():
    oracle = TransformationOracle(random_inputs=50)
    src1 = "def f(x):\n    return x + 1\n"
    src2 = "def f(x):\n    return x + 1\n"
    start = time.perf_counter()
    for _ in range(50):
        oracle.check_semantic_equivalence(src1, src2)
    elapsed = (time.perf_counter() - start) / 50
    print(f"  TransformationOracle.check_semantic_equivalence: {elapsed * 1000:.2f}ms avg ({50} runs)")
    return elapsed


def bench_oracle_classify():
    oracle = TransformationOracle(random_inputs=50)
    src1 = "def f(x):\n    return x + 1\n"
    src2 = "def f(x):\n    return 42\n"
    start = time.perf_counter()
    for _ in range(50):
        oracle.classify_difference(src1, src2)
    elapsed = (time.perf_counter() - start) / 50
    print(f"  TransformationOracle.classify_difference: {elapsed * 1000:.2f}ms avg ({50} runs)")
    return elapsed


def bench_harness_generate_tests():
    harness = ProofSoundnessHarness()
    start = time.perf_counter()
    for _ in range(50):
        generate_soundness_tests(harness, ["semantic_preservation", "mutation_safety"])
    elapsed = (time.perf_counter() - start) / 50
    print(f"  generate_soundness_tests: {elapsed * 1000:.2f}ms avg ({50} runs)")
    return elapsed


def bench_harness_run_test():
    harness = ProofSoundnessHarness()
    src = "def f(x):\n    return x + 1\n"
    modified = "def f(x):\n    return x - 1\n"
    test = SoundnessTest(
        test_id="bench_test",
        target_proof="semantic_preservation",
        test_type="incorrect_transform",
        original_source=src,
        modified_source=modified,
        expected_to_reject=True,
    )
    start = time.perf_counter()
    for _ in range(20):
        harness.run_test(test)
    elapsed = (time.perf_counter() - start) / 20
    print(f"  ProofSoundnessHarness.run_test: {elapsed * 1000:.2f}ms avg ({20} runs)")
    return elapsed


def bench_full_harness_run():
    harness = ProofSoundnessHarness()
    start = time.perf_counter()
    harness.run_all(["semantic_preservation"])
    elapsed = (time.perf_counter() - start)
    print(f"  ProofSoundnessHarness.run_all (full): {elapsed * 1000:.2f}ms (1 run)")
    return elapsed


if __name__ == "__main__":
    print("Proof Soundness Benchmarks")
    print("=" * 50)
    t1 = bench_mutation_generation()
    t2 = bench_oracle_equivalence()
    t3 = bench_oracle_classify()
    t4 = bench_harness_generate_tests()
    t5 = bench_harness_run_test()
    t6 = bench_full_harness_run()
    print("=" * 50)
    total = (t1 + t2 + t3 + t4 + t5 + t6) * 1000
    print(f"  Total benchmark time: {total:.2f}ms")
