"""
adversarial_bench — Adversarial Benchmark Generator (F175)

Purpose:
    Generates and runs adversarial test cases designed to stress-test
    pipeline subsystems: proof systems, watermarking, coverage analysis,
    synthesis engine, and leakage metrics. Each test targets a known
    weakness or edge case.

Architectural Role:
    Fuzzing / stress-test layer. Complements the Proof Soundness Harness
    by testing higher-level system properties rather than individual
    proof modules.

Security Relevance:
    Adversarial tests surface boundary conditions and failure modes that
    standard testing misses. A passing adversarial suite increases confidence
    in subsystem robustness.
"""

from .generator import AdversarialBenchGenerator, AdversarialTest, AdversarialSuite
from .suite import AdversarialTestSuite

def generate_adversarial_tests(count=20):
    """Convenience: create a generator and produce `count` adversarial tests."""
    gen = AdversarialBenchGenerator()
    return gen.generate_all(count=count)

def run_adversarial_suite(tests, pipeline=None):
    """Convenience: create an AdversarialTestSuite, assign tests, and run_all."""
    suite = AdversarialTestSuite()
    suite.tests = tests
    return suite.run_all(pipeline)

__all__ = [
    "AdversarialBenchGenerator",
    "AdversarialTest",
    "AdversarialSuite",
    "AdversarialTestSuite",
    "generate_adversarial_tests",
    "run_adversarial_suite",
]
