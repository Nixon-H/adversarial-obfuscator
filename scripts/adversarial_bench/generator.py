"""
adversarial_bench/generator.py — Adversarial test case generator (F175)

Purpose:
    Generates targeted adversarial test cases for proof systems, watermarking,
    coverage analysis, synthesis, and leakage metrics. Each test includes
    source code designed to trigger a specific failure mode.

Architectural Role:
    Data-generation layer. Produces AdversarialTest instances consumed by
    AdversarialTestSuite for execution and reporting.

Security Relevance:
    Purpose-built adversarial cases probe system boundaries that random
    fuzzing may miss, such as deeply nested expressions, identity variants,
    side-effect equivalence, and dynamic dispatch.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class AdversarialTest:
    """A single adversarial test case.

    Attributes:
        test_id: Unique identifier (e.g. "PROOF-0001").
        target_system: System under test (proof, watermark, coverage, synthesis, leakage).
        attack_type: Type of adversarial attack (timeout, bypass, edge_case, overload, confuse, pathological).
        source_code: Python source code carrying the attack.
        expected_failure: Human-readable description of the expected failure mode.
        actual_result: Populated at run time with execution output.
        severity: high / medium / low.
    """
    test_id: str
    target_system: str
    attack_type: str
    source_code: str
    expected_failure: str
    actual_result: Optional[Any] = None
    severity: str = "medium"


@dataclass
class AdversarialSuite:
    """Result of running a suite of adversarial tests.

    Attributes:
        tests: The tests that were run.
        total: Number of tests.
        vulnerabilities_found: Number of tests that caused errors / failures.
        failing_targets: Unique target systems that had failures.
        timestamp: ISO-8601 runtime timestamp.
    """

    tests: List[AdversarialTest] = field(default_factory=list)
    total: int = 0
    vulnerabilities_found: int = 0
    failing_targets: List[str] = field(default_factory=list)
    timestamp: str = ""


class AdversarialBenchGenerator:
    """Generates adversarial test cases targeting proof, watermark, coverage, synthesis, and leakage subsystems."""
    def __init__(self, seed: Optional[int] = None):
        self._seed = seed if seed is not None else secrets.randbits(32)
        self._counter = 0

    def _next_id(self, prefix: str = "ADV") -> str:
        """Generate a monotonically increasing test ID with the given prefix."""
        self._counter += 1
        return f"{prefix}-{self._counter:04d}"

    def generate_for_proofs(self) -> List[AdversarialTest]:
        """Generate adversarial tests targeting proof systems: Z3 timeout, bypass, side effects, memory exhaustion."""
        tests = []

        tests.append(AdversarialTest(
            test_id=self._next_id("PROOF"),
            target_system="proof",
            attack_type="timeout",
            source_code="""
def deeply_nested_expr(x):
    return (((((((((((((((((((x + 1) * 2) - 3) / 4) ** 5) % 6) & 7) | 8) ^ 9) << 1) >> 2) + x) * x) - x) / (x + 1)) ** (x % 5)) % 257) & 0xFF) | 0x100) ^ 0x200
""",
            expected_failure="Z3 solver timeout on deeply nested expression tree",
            severity="high",
        ))

        tests.append(AdversarialTest(
            test_id=self._next_id("PROOF"),
            target_system="proof",
            attack_type="bypass",
            source_code="""
def ident_a(x):
    return x

def ident_b(x):
    return x + 0

def ident_c(x):
    return x * 1

def ident_d(x):
    return x & 0xFFFFFFFFFFFFFFFF

def ident_e(x):
    return x | 0
""",
            expected_failure="Proof system fails to detect behavioral equivalence across all 5 identity variants",
            severity="high",
        ))

        tests.append(AdversarialTest(
            test_id=self._next_id("PROOF"),
            target_system="proof",
            attack_type="edge_case",
            source_code="""
def side_effect_add(a, b):
    global _call_count
    _call_count = _call_count + 1
    return a + b

def side_effect_mul(a, b):
    global _call_count
    _call_count = _call_count + 1
    return a * b
""",
            expected_failure="Proof system ignores side effects when comparing equivalence",
            severity="high",
        ))

        tests.append(AdversarialTest(
            test_id=self._next_id("PROOF"),
            target_system="proof",
            attack_type="overload",
            source_code="""
def z3_mem_exhaust(x):
    acc = x
    for i in range(10000):
        acc = acc + (acc % (i + 1)) * (i & 0xFF) - (i | 0xFFFF) ^ (i << (i % 8))
    return acc
""",
            expected_failure="Z3 memory exhaustion on loop-unrolled symbolic execution",
            severity="high",
        ))

        return tests

    def generate_for_watermark(self) -> List[AdversarialTest]:
        """Generate adversarial tests targeting watermarking: no room, linear code, high entropy, single instruction."""
        tests = []

        tests.append(AdversarialTest(
            test_id=self._next_id("WM"),
            target_system="watermark",
            attack_type="bypass",
            source_code="""def f(x): return x + 1""",
            expected_failure="No room for watermark in 1-line function with no control flow",
            severity="high",
        ))

        tests.append(AdversarialTest(
            test_id=self._next_id("WM"),
            target_system="watermark",
            attack_type="bypass",
            source_code="""
def no_control_flow(a, b, c, d, e, f, g, h, i, j):
    return a + b - c * d / e + f ** g - h * i + j
""",
            expected_failure="Watermark requires control flow to embed; linear arithmetic provides none",
            severity="high",
        ))

        tests.append(AdversarialTest(
            test_id=self._next_id("WM"),
            target_system="watermark",
            attack_type="confuse",
            source_code="""
import os, sys, struct, json, hashlib, base64, zlib, random, math, statistics

def max_entropy(x):
    _ = os.urandom(32)
    _ = random.randint(0, 2**256)
    _ = hashlib.sha512(os.urandom(64)).digest()
    _ = zlib.compress(os.urandom(1024))
    return x ^ 0xDEADBEEFCAFEBABE
""",
            expected_failure="Maximum entropy code obscures watermark embedding signal",
            severity="medium",
        ))

        tests.append(AdversarialTest(
            test_id=self._next_id("WM"),
            target_system="watermark",
            attack_type="pathological",
            source_code="""
def single_instruction():
    return 42
""",
            expected_failure="Single-instruction function cannot carry a watermark",
            severity="high",
        ))

        return tests

    def generate_for_coverage(self) -> List[AdversarialTest]:
        """Generate adversarial tests targeting coverage analysis: many blocks, dynamic dispatch, random paths, recursion."""
        tests = []

        blocks = []
        for i in range(2000):
            blocks.append(f"""
    if _state == {i}:
        _acc = _acc + {i}
        _state = {i + 1}
""")
        block_code = "".join(blocks)

        tests.append(AdversarialTest(
            test_id=self._next_id("COV"),
            target_system="coverage",
            attack_type="overload",
            source_code=f"""
def thousand_blocks(x):
    _acc = x
    _state = 0
{block_code}
    return _acc
""",
            expected_failure="Coverage system overwhelmed by 2000+ basic blocks in single function",
            severity="high",
        ))

        tests.append(AdversarialTest(
            test_id=self._next_id("COV"),
            target_system="coverage",
            attack_type="confuse",
            source_code="""
def dynamic_dispatch(op, a, b):
    _table = {
        0: lambda x, y: x + y,
        1: lambda x, y: x - y,
        2: lambda x, y: x * y,
        3: lambda x, y: x // (y + 1),
        4: lambda x, y: x ** (y % 8),
        5: lambda x, y: x & y,
        6: lambda x, y: x | y,
        7: lambda x, y: x ^ y,
        8: lambda x, y: (x << (y % 16)) & 0xFFFFFFFF,
        9: lambda x, y: (x >> (y % 16)) & 0xFFFFFFFF,
    }
    return _table.get(op % 10, lambda x, y: 0)(a, b)
""",
            expected_failure="Dynamic dispatch hides actual execution paths from static coverage analysis",
            severity="high",
        ))

        tests.append(AdversarialTest(
            test_id=self._next_id("COV"),
            target_system="coverage",
            attack_type="pathological",
            source_code="""
import random
import hashlib

def random_structure(seed):
    random.seed(seed)
    acc = 0
    for _ in range(100):
        r = random.randint(0, 5)
        if r == 0:
            acc = acc + random.randint(0, 100)
        elif r == 1:
            acc = acc - random.randint(0, 100)
        elif r == 2:
            acc = (acc * random.randint(0, 100)) & 0xFFFFFFFF
        elif r == 3:
            acc = acc ^ random.randint(0, 0xFFFFFFFF)
        elif r == 4:
            acc = (acc << (random.randint(0, 16))) & 0xFFFFFFFF
        else:
            acc = hashlib.md5(str(acc).encode()).digest()[0]
    return acc
""",
            expected_failure="Random structure produces unpredictable coverage paths that coverage tracker cannot map",
            severity="medium",
        ))

        tests.append(AdversarialTest(
            test_id=self._next_id("COV"),
            target_system="coverage",
            attack_type="edge_case",
            source_code="""
def recursive_coverage(n):
    if n <= 0:
        return 1
    return n * recursive_coverage(n - 1)
""",
            expected_failure="Recursive function with variable call depth confuses static coverage analysis",
            severity="medium",
        ))

        return tests

    def generate_for_synthesis(self) -> List[AdversarialTest]:
        """Generate adversarial tests targeting synthesis: all ops, trivial identity, boundary conditions, mixed types."""
        tests = []

        tests.append(AdversarialTest(
            test_id=self._next_id("SYNTH"),
            target_system="synthesis",
            attack_type="bypass",
            source_code="""
def require_all_protections(x):
    _ = x + 1
    _ = x - 1
    _ = x * 2
    _ = x // 2
    _ = x ** 2
    _ = x & 0xFF
    _ = x | 0xFF
    _ = x ^ 0xFF
    _ = x << 4
    _ = x >> 4
    _ = ~x
    _ = -x
    _ = abs(x)
    _ = pow(x, 3, 100)
    _ = divmod(x, 7)
    return _
""",
            expected_failure="Synthesis engine fails to generate protection plan covering all operation types",
            severity="high",
        ))

        tests.append(AdversarialTest(
            test_id=self._next_id("SYNTH"),
            target_system="synthesis",
            attack_type="edge_case",
            source_code="""
def no_protection_helps(x):
    return x
""",
            expected_failure="Synthesis engine cannot optimize when no protection is useful for trivial identity",
            severity="high",
        ))

        tests.append(AdversarialTest(
            test_id=self._next_id("SYNTH"),
            target_system="synthesis",
            attack_type="edge_case",
            source_code="""
def boundary_condition(x):
    if x == 0:
        return 0
    elif x == 1:
        return 1
    elif x == 2:
        return 2
    elif x == 3:
        return 3
    elif x == 4:
        return 4
    elif x == 5:
        return 5
    elif x == 6:
        return 6
    elif x == 7:
        return 7
    elif x == 8:
        return 8
    elif x == 9:
        return 9
    else:
        return 10
""",
            expected_failure="Synthesis engine boundary condition with exactly N branches confuses cost modeling",
            severity="medium",
        ))

        tests.append(AdversarialTest(
            test_id=self._next_id("SYNTH"),
            target_system="synthesis",
            attack_type="confuse",
            source_code="""
def mixed_types(a: int, b: float, c: str, d: bytes) -> bool:
    return len(str(int(a) + int(b))) > len(c) and len(d) > 0
""",
            expected_failure="Synthesis engine cannot handle mixed-type function signatures",
            severity="medium",
        ))

        return tests

    def generate_for_leakage(self) -> List[AdversarialTest]:
        """Generate adversarial tests targeting leakage metrics: trivially obfuscated identity, empty functions, symmetry, all-ops."""
        tests = []

        tests.append(AdversarialTest(
            test_id=self._next_id("LEAK"),
            target_system="leakage",
            attack_type="bypass",
            source_code="""
def trivially_obfuscated(x):
    a = x
    b = a + 0
    c = b * 1
    d = c | 0
    e = d ^ 0
    f = e & 0xFFFFFFFFFFFFFFFF
    g = f + 0x0
    h = g // 1
    i = h ** 1
    return i
""",
            expected_failure="Leakage metric reports high leakage for trivially obfuscated identity function",
            severity="high",
        ))

        tests.append(AdversarialTest(
            test_id=self._next_id("LEAK"),
            target_system="leakage",
            attack_type="confuse",
            source_code="""
def no_semantic_content(*args, **kwargs):
    pass
""",
            expected_failure="Leakage metric produces undefined result for empty function with no semantic content",
            severity="high",
        ))

        tests.append(AdversarialTest(
            test_id=self._next_id("LEAK"),
            target_system="leakage",
            attack_type="confuse",
            source_code="""
def mirror_a(x, y):
    return x + y

def mirror_b(x, y):
    return y + x
""",
            expected_failure="Leakage metric should report zero leakage for mirror-image symmetric functions",
            severity="medium",
        ))

        tests.append(AdversarialTest(
            test_id=self._next_id("LEAK"),
            target_system="leakage",
            attack_type="pathological",
            source_code="""
def all_ops_in_one(x):
    return (((((x + 1) - 2) * 3) // 4) ** 5) % 6 & 0xFF | 0x100 ^ 0x200 << 2 >> 1
""",
            expected_failure="Leakage metric overwhelmed by all operations combined in single expression",
            severity="medium",
        ))

        return tests

    def generate_all(self, count: int = 20) -> List[AdversarialTest]:
        """Generate up to `count` adversarial tests by cycling through all 5 generator domains.

        If the pool is smaller than count, cycles are repeated with fresh IDs.
        """
        all_tests = []
        generators = [
            self.generate_for_proofs,
            self.generate_for_watermark,
            self.generate_for_coverage,
            self.generate_for_synthesis,
            self.generate_for_leakage,
        ]

        pool = []
        for gen_fn in generators:
            pool.extend(gen_fn())

        if len(pool) >= count:
            return pool[:count]

        cycles_needed = (count + len(pool) - 1) // len(pool)
        for _ in range(cycles_needed):
            for t in pool:
                if len(all_tests) >= count:
                    break
                t2 = AdversarialTest(
                    test_id=self._next_id(t.target_system.upper()),
                    target_system=t.target_system,
                    attack_type=t.attack_type,
                    source_code=t.source_code,
                    expected_failure=t.expected_failure,
                    severity=t.severity,
                )
                all_tests.append(t2)

        return all_tests[:count]
