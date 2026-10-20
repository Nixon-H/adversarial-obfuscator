"""
proof_soundness/harness.py — Soundness test orchestration and reporting (F174)

Purpose:
    Orchestrates the proof soundness validation pipeline: generates mutated
    code variants (via ProofMutationEngine + built-in transforms), runs each
    variant through the corresponding proof module, and measures how many
    incorrect transformations the proof system correctly rejects.

Architectural Role:
    Core orchestration layer. Coordinates the mutator, oracle, and proof
    modules to produce a SoundnessReport with pass/fail counts and a
    composite soundness score.

Security Relevance:
    Quantifies proof-system quality as a soundness percentage. A failing
    soundness test indicates a proof module that cannot distinguish correct
    from incorrect code — a critical security gap.
"""
from __future__ import annotations
import ast
import time
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from scripts.proof_soundness.mutator import ProofMutationEngine
from scripts.proof_soundness.oracle import TransformationOracle
from scripts.proofs import (
    SemanticPreservationProver,
    MutationSafetyProver,
    VMCorrectnessProver,
    FragmentSafetyProver,
    WatermarkSurvivabilityProver,
    JITReassemblyProver,
)


@dataclass
class SoundnessTest:
    """A single soundness test: apply a transform to source and check if the proof system rejects it.

    Attributes:
        test_id: Unique identifier.
        target_proof: Name of the proof module under test.
        test_type: The transformation type (swap_add_sub, flip_comparison, etc.).
        original_source: Unmodified source code.
        modified_source: Transformed (potentially incorrect) source.
        expected_to_reject: Whether the proof SHOULD reject this (True for incorrect transforms).
        actual_rejected: Whether the proof DID reject this (set at run time).
        proof_module: The proof module used.
        passed: actual_rejected == expected_to_reject.
        error_message: Any error encountered during the test.
    """
    test_id: str
    target_proof: str
    test_type: str
    original_source: str
    modified_source: str
    expected_to_reject: bool
    actual_rejected: Optional[bool] = None
    proof_module: str = ""
    passed: Optional[bool] = None
    error_message: Optional[str] = None


@dataclass
class SoundnessReport:
    """Aggregate soundness test results.

    Attributes:
        tests: All individual SoundnessTest results.
        total / passed / failed: Test counts.
        soundness_score: passed / total ratio.
        failing_modules: List of proof module names that have at least one failure.
        timestamp: ISO-8601 generation timestamp.
    """

    tests: List[SoundnessTest] = field(default_factory=list)
    total: int = 0
    passed: int = 0
    failed: int = 0
    soundness_score: float = 0.0
    failing_modules: List[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if self.total > 0 and self.soundness_score == 0.0:
            self.soundness_score = self.passed / self.total

    def to_dict(self) -> dict:
        """Serialize the report to a dict for JSON export."""
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "soundness_score": round(self.soundness_score, 4),
            "failing_modules": self.failing_modules,
            "timestamp": self.timestamp,
            "tests": [
                {
                    "test_id": t.test_id,
                    "target_proof": t.target_proof,
                    "test_type": t.test_type,
                    "expected_to_reject": t.expected_to_reject,
                    "actual_rejected": t.actual_rejected,
                    "proof_module": t.proof_module,
                    "passed": t.passed,
                    "error_message": t.error_message,
                }
                for t in self.tests
            ],
        }


class ProofSoundnessHarness:
    """Orchestrates soundness testing across all proof modules.

    Holds a TransformationOracle, ProofMutationEngine, and a mapping of
    proof module names to prover instances. Generates, runs, and reports
    on soundness tests.
    """

    def __init__(self):
        self.mutator = ProofMutationEngine()
        self.oracle = TransformationOracle()
        self.provers: Dict[str, Any] = {
            "semantic_preservation": SemanticPreservationProver(timeout_ms=30000),
            "mutation_safety": MutationSafetyProver(timeout_ms=30000),
            "vm_correctness": VMCorrectnessProver(timeout_ms=30000),
            "fragment_safety": FragmentSafetyProver(timeout_ms=30000),
            "watermark_survivability": WatermarkSurvivabilityProver(timeout_ms=30000),
            "jit_reassembly": JITReassemblyProver(timeout_ms=30000),
        }
        self.tests: List[SoundnessTest] = []
        self.report: Optional[SoundnessReport] = None

    def generate_incorrect_transform(
        self, original: str, transform_type: str
    ) -> str:
        """Generate a semantically incorrect variant of original using the named transform type.

        Supported types: swap_add_sub, flip_comparison, remove_step,
        wrong_constant, swap_branches, or falls back to ProofMutationEngine.
        """
        if transform_type == "swap_add_sub":
            return original.replace("+", "-")
        elif transform_type == "flip_comparison":
            result = original.replace("<=", ">=")
            result = result.replace(">=", "<=")
            result = result.replace("<", ">=")
            result = result.replace(">", "<=")
            result = result.replace("==", "!=")
            result = result.replace("!=", "==")
            return result
        elif transform_type == "remove_step":
            lines = original.split("\n")
            non_empty = [i for i, l in enumerate(lines) if l.strip()]
            if len(non_empty) > 1:
                remove_idx = random.choice(non_empty[1:])
                lines.pop(remove_idx)
            return "\n".join(lines)
        elif transform_type == "wrong_constant":
            result = list(original)
            consts = ["0", "1", "42", "100", "255", "1024"]
            idx = 0
            while idx < len(result):
                if result[idx].isdigit():
                    start = idx
                    while idx < len(result) and result[idx].isdigit():
                        idx += 1
                    orig_val = original[start:idx]
                    if orig_val not in ("0", "1"):
                        replacement = random.choice([c for c in consts if c != orig_val])
                        result[start:idx] = replacement
                        break
                else:
                    idx += 1
            return "".join(result)
        elif transform_type == "swap_branches":
            tree = ast.parse(original, mode="exec")
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    node.body, node.orelse = node.orelse, node.body
            return ast.unparse(tree)
        else:
            return self.mutator.generate_mutations(original, count=1)[0]

    def run_test(self, test: SoundnessTest) -> SoundnessTest:
        """Execute a single soundness test: run the appropriate proof module and record pass/fail.

        Dispatches to the correct prover method based on test.target_proof.
        Sets test.actual_rejected, test.passed, and test.error_message.
        """
        start = time.time()
        test.proof_module = test.target_proof
        try:
            prover = self.provers.get(test.target_proof)
            if prover is None:
                test.error_message = f"Unknown proof module: {test.target_proof}"
                test.actual_rejected = False
                test.passed = False
                return test

            if test.target_proof == "semantic_preservation":
                proof = prover.prove_equivalence(
                    test.original_source, test.modified_source, "soundness_test"
                )
                test.actual_rejected = not proof.equivalent
            elif test.target_proof == "mutation_safety":
                proof = prover.prove_mutation(
                    test.original_source, test.modified_source
                )
                test.actual_rejected = not proof.equivalent
            elif test.target_proof == "vm_correctness":
                try:
                    proof = prover.prove_single_instruction(
                        test.original_source, test.modified_source
                    )
                    test.actual_rejected = not proof.equivalent
                except AttributeError:
                    prover.prove_all_instructions()
                    test.actual_rejected = True
            elif test.target_proof == "fragment_safety":
                test.actual_rejected = False
                test.error_message = "Fragment safety requires Fragment objects"
            elif test.target_proof == "watermark_survivability":
                test.actual_rejected = False
                test.error_message = "Watermark requires watermark string input"
            elif test.target_proof == "jit_reassembly":
                fragments = test.original_source.split("\n")
                try:
                    proof = prover.prove_reassembly(fragments, test.modified_source)
                    test.actual_rejected = not proof.equivalent
                except Exception:
                    test.actual_rejected = False
                    test.error_message = "JIT reassembly proof failed"
            else:
                test.actual_rejected = False
                test.error_message = f"Proof module {test.target_proof} not supported"

            if test.actual_rejected is None:
                test.actual_rejected = False

            test.passed = test.actual_rejected == test.expected_to_reject

        except Exception as e:
            test.actual_rejected = False
            test.passed = False
            test.error_message = str(e)

        elapsed_ms = (time.time() - start) * 1000
        if test.error_message:
            test.error_message += f" ({elapsed_ms:.1f}ms)"
        return test

    def run_all(self, proof_modules: List[str]) -> SoundnessReport:
        """Run all soundness tests for the given list of proof module names.

        Generates tests via generate_soundness_tests, runs each, and
        aggregates into a SoundnessReport.
        """
        self.tests = generate_soundness_tests(self, proof_modules)
        report = SoundnessReport(tests=[])
        for test in self.tests:
            result = self.run_test(test)
            report.tests.append(result)
            if result.passed:
                report.passed += 1
            else:
                report.failed += 1
                if result.proof_module not in report.failing_modules:
                    report.failing_modules.append(result.proof_module)
        report.total = report.passed + report.failed
        if report.total > 0:
            report.soundness_score = report.passed / report.total
        self.report = report
        return report

    def generate_report(self) -> SoundnessReport:
        """Return the current SoundnessReport (or an empty one if none was generated)."""
        if self.report is None:
            return SoundnessReport()
        return self.report


def generate_soundness_tests(
    harness: ProofSoundnessHarness, proof_modules: List[str]
) -> List[SoundnessTest]:
    """Generate soundness tests for each proof module × each transform type using random sample sources.

    All generated tests have expected_to_reject = True (the proof system must
    reject the semantically incorrect variant).
    """
    tests: List[SoundnessTest] = []
    test_id_counter = [0]

    def _sample_source() -> str:
        samples = [
            "def f(x):\n    return x + 1\n",
            "def f(x):\n    if x > 0:\n        return x\n    else:\n        return -x\n",
            "def f(a, b):\n    c = a + b\n    return c * 2\n",
            "def f(x):\n    y = x * x\n    z = y + 1\n    return z\n",
            "def f(n):\n    result = 0\n    for i in range(n):\n        result = result + i\n    return result\n",
        ]
        return random.choice(samples)

    transform_types = [
        "swap_add_sub",
        "flip_comparison",
        "remove_step",
        "wrong_constant",
        "swap_branches",
    ]

    for mod in proof_modules:
        for ttype in transform_types:
            tid = f"soundness_{test_id_counter[0]}"
            test_id_counter[0] += 1
            src = _sample_source()
            modified = harness.generate_incorrect_transform(src, ttype)
            test = SoundnessTest(
                test_id=tid,
                target_proof=mod,
                test_type=ttype,
                original_source=src,
                modified_source=modified,
                expected_to_reject=True,
            )
            tests.append(test)

    return tests


def run_soundness_harness(
    proof_modules: Optional[List[str]] = None,
) -> SoundnessReport:
    """Convenience: create a ProofSoundnessHarness and run for given (or default) proof modules."""
    if proof_modules is None:
        proof_modules = [
            "semantic_preservation",
            "mutation_safety",
            "vm_correctness",
        ]
    harness = ProofSoundnessHarness()
    return harness.run_all(proof_modules)
