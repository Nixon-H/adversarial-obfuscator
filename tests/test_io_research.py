"""
test_io_research.py

Tests for the approximate indistinguishability obfuscation (iO) research path.

Test Categories:
- Positive tests verify matrix branching program (BP) construction, evaluation,
  Kilian randomization, obfuscator equivalence, and metrics computation.
- Negative tests verify rejection of non-linear operations, control flow,
  variable×variable multiplication, and excessive op counts.

Coverage:
- BP construction: basic, single-matrix, empty
- BP evaluation: identity, linear transformations
- Kilian randomization: product preservation, single/two-matrix cases
- Obfuscator equivalence: add/sub/mul/combined, metrics presence
- IR adapter: conversion, rejection of incompatible functions
- Metrics: program distance, entropy, indistinguishability score
"""

from __future__ import annotations

import numpy as np

from scripts.io_research import (
    MatrixBranchingProgram,
    randomize_bp,
    evaluate_bp,
    IndistinguishabilityObfuscator,
    verify_equivalence,
    compute_equivalence_score,
    compute_program_distance,
    compute_entropy,
    indistinguishability_score,
    is_io_compatible,
    ir_to_branching_program,
)
from irgen.compile import compile_py_to_ir


def _make_simple_bp() -> MatrixBranchingProgram:
    m0 = np.array([[2.0, 0.0], [1.0, 1.0]])
    m1 = np.array([[2.0, 0.0], [1.0, 1.0]])
    pairs = [(m0, m1), (m0, m1)]
    return MatrixBranchingProgram(
        pairs,
        start_vector=np.array([3.0, 1.0]),
        output_index=0,
    )


class TestBPConstruction:
    """
    TestBPConstruction

    Positive test cases for constructing MatrixBranchingProgram instances
    with various numbers of matrix pairs and dimensions.
    """
    def test_bp_construction_basic(self):
        bp = _make_simple_bp()
        assert bp.dim == 2
        assert bp.num_matrices() == 2
        assert bp.output_index == 0

    def test_bp_construction_single_matrix(self):
        m = np.array([[1.0, 0.0], [0.0, 1.0]])
        bp = MatrixBranchingProgram(
            [(m, m)],
            start_vector=np.array([5.0, 1.0]),
            output_index=0,
        )
        assert bp.num_matrices() == 1
        result = bp.evaluate([0])
        assert abs(result - 5.0) < 1e-6

    def test_bp_construction_empty(self):
        bp = MatrixBranchingProgram([], start_vector=np.array([1.0]), output_index=0)
        assert bp.num_matrices() == 0
        result = bp.evaluate([0])
        assert abs(result - 1.0) < 1e-6


class TestBPEvaluation:
    """
    TestBPEvaluation

    Positive test cases for evaluating matrix branching programs
    over various input bit selections.
    """
    def test_bp_evaluation_identity(self):
        m = np.eye(3)
        bp = MatrixBranchingProgram(
            [(m, m)],
            start_vector=np.array([7.0, 3.0, 1.0]),
            output_index=0,
        )
        result = bp.evaluate([0])
        assert abs(result - 7.0) < 1e-6

    def test_bp_evaluation_linear(self):
        m = np.array([[2.0, 0.0, 0.0], [0.0, 1.0, 0.0], [3.0, 0.0, 1.0]])
        bp = MatrixBranchingProgram(
            [(m, m)],
            start_vector=np.array([0.0, 0.0, 1.0]),
            output_index=0,
        )
        result = bp.evaluate([0])
        assert abs(result - 3.0) < 1e-6

    def test_evaluate_bp_function(self):
        matrices = [np.eye(2)]
        vec = np.array([4.0, 1.0])
        result = evaluate_bp(matrices, vec)
        assert np.allclose(result, [4.0, 1.0])


class TestKilianRandomization:
    """
    TestKilianRandomization

    Positive test cases for Kilian-style randomization, verifying that
    the matrix product is preserved after randomization for various
    matrix counts.
    """
    def test_randomization_preserves_product(self):
        rng = np.random.default_rng(42)
        d = 4
        original = []
        for _ in range(5):
            m = rng.standard_normal((d, d))
            original.append(m)

        product_orig = np.eye(d)
        for m in original:
            product_orig = product_orig @ m

        randomized = randomize_bp(original)
        product_rand = np.eye(d)
        for m in randomized:
            product_rand = product_rand @ m

        assert np.allclose(product_orig, product_rand, atol=1e-8)

    def test_randomization_single_matrix(self):
        m = np.array([[3.0, 1.0], [2.0, 4.0]])
        randomized = randomize_bp([m])
        assert len(randomized) == 1
        assert np.allclose(randomized[0], m)

    def test_randomization_two_matrices(self):
        rng = np.random.default_rng(99)
        m1 = rng.standard_normal((3, 3))
        m2 = rng.standard_normal((3, 3))
        orig_product = m1 @ m2

        randomized = randomize_bp([m1, m2])
        rand_product = randomized[0] @ randomized[1]

        assert np.allclose(orig_product, rand_product, atol=1e-8)


class TestObfuscatorEquivalence:
    """
    TestObfuscatorEquivalence

    Positive test cases verifying that obfuscated branching programs
    are semantically equivalent to the original IR functions.
    """
    def test_obfuscator_equivalence_add(self):
        source = """
def add(a, b):
    return a + b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]

        obfuscator = IndistinguishabilityObfuscator()
        result = obfuscator.obfuscate_fragment(func)

        assert 'error' not in result
        eq = result.get('equivalence', {})
        assert eq.get('equivalent', False), f"Equivalence failed: {eq.get('mismatches', [])}"
        assert eq.get('score', 0) >= 0.9

    def test_obfuscator_equivalence_sub(self):
        source = """
def sub(a, b):
    return a - b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]

        obfuscator = IndistinguishabilityObfuscator()
        result = obfuscator.obfuscate_fragment(func)

        assert 'error' not in result
        eq = result.get('equivalence', {})
        assert eq.get('equivalent', False)

    def test_obfuscator_equivalence_mul(self):
        source = """
def mul(a):
    return a * 2
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]

        obfuscator = IndistinguishabilityObfuscator()
        result = obfuscator.obfuscate_fragment(func)

        assert 'error' not in result
        eq = result.get('equivalence', {})
        assert eq.get('equivalent', False)

    def test_obfuscator_equivalence_combined(self):
        source = """
def compute(a, b):
    x = a + b
    y = x * 2
    return y
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]

        obfuscator = IndistinguishabilityObfuscator()
        result = obfuscator.obfuscate_fragment(func)

        assert 'error' not in result
        eq = result.get('equivalence', {})
        assert eq.get('equivalent', False)

    def test_metrics_present(self):
        source = """
def add(a, b):
    return a + b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]

        obfuscator = IndistinguishabilityObfuscator()
        result = obfuscator.obfuscate_fragment(func)

        metrics = result.get('metrics', {})
        assert 'program_distance' in metrics
        assert 'entropy' in metrics
        assert 'indistinguishability_score' in metrics
        assert 'note' in metrics
        assert 'MEASURED' in metrics['note']


class TestIRAdapter:
    """
    TestIRAdapter

    Positive and negative test cases for converting IR functions into
    branching programs, including compatibility checks and rejection
    of non-iO-compatible functions.
    """
    def test_ir_adapter_conversion(self):
        source = """
def add(a, b):
    return a + b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]

        bp = ir_to_branching_program(func)
        assert bp is not None
        assert bp.num_matrices() >= 1

    def test_ir_rejection_more_than_5_ops(self):
        source = """
def many_ops(a, b, c, d):
    x = a + b
    y = x - c
    z = y * 2
    w = z + a
    v = w - b
    u = v + c
    return u
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]

        compatible, reason = is_io_compatible(func)
        assert not compatible
        assert 'too many' in reason

    def test_ir_rejection_var_var_mul(self):
        source = """
def var_mul(a, b):
    return a * b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]

        compatible, reason = is_io_compatible(func)
        assert not compatible
        assert 'variable×variable multiplication' in reason

    def test_ir_rejection_non_linear_div(self):
        source = """
def div_op(a, b):
    return a // b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]

        compatible, reason = is_io_compatible(func)
        assert not compatible
        assert 'non-linear' in reason

    def test_ir_rejection_non_linear_mod(self):
        source = """
def mod_op(a, b):
    return a % b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]

        compatible, reason = is_io_compatible(func)
        assert not compatible
        assert 'non-linear' in reason

    def test_ir_rejection_non_linear_bitops(self):
        source = """
def bitop(a, b):
    return a & b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]

        compatible, reason = is_io_compatible(func)
        assert not compatible
        assert 'non-linear' in reason

    def test_ir_rejection_control_flow(self):
        source = """
def with_if(a):
    if a > 0:
        return a + 1
    else:
        return a - 1
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]

        compatible, reason = is_io_compatible(func)
        assert not compatible
        assert 'control flow' in reason or 'multiple blocks' in reason

    def test_ir_rejection_zero_ops(self):
        source = """
def empty():
    return 0
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]

        compatible, reason = is_io_compatible(func)
        assert not compatible


class TestEquivalence:
    """
    TestEquivalence

    Positive test cases for computing equivalence scores and running
    verification between original IR functions and obfuscated BPs.
    """
    def test_equivalence_score_computation(self):
        source = """
def add(a, b):
    return a + b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]

        obfuscator = IndistinguishabilityObfuscator()
        result = obfuscator.obfuscate_fragment(func)
        bp = result.get('bp')

        score = compute_equivalence_score(func, bp)
        assert 0.0 <= score <= 1.0
        assert score >= 0.9

    def test_verify_equivalence_function(self):
        source = """
def add(a, b):
    return a + b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]

        obfuscator = IndistinguishabilityObfuscator()
        result = obfuscator.obfuscate_fragment(func)
        bp = result.get('bp')

        eq = verify_equivalence(func, bp, num_samples=50)
        assert eq['equivalent']
        assert eq['samples'] == 50


class TestMetrics:
    """
    TestMetrics

    Positive test cases for iO metrics: program distance, entropy,
    indistinguishability score, and their numerical bounds.
    """
    def test_program_distance(self):
        m = np.eye(2)
        bp1 = MatrixBranchingProgram([(m, m)], start_vector=np.array([1.0, 1.0]), output_index=0)
        bp2 = MatrixBranchingProgram([(m * 2, m * 2)], start_vector=np.array([1.0, 1.0]), output_index=0)

        dist = compute_program_distance(bp1, bp2)
        assert dist > 0.0

    def test_program_distance_identical(self):
        m = np.eye(2)
        bp1 = MatrixBranchingProgram([(m, m)], start_vector=np.array([1.0, 1.0]), output_index=0)

        dist = compute_program_distance(bp1, bp1)
        assert abs(dist) < 1e-10

    def test_entropy_computation(self):
        rng = np.random.default_rng(42)
        m = rng.standard_normal((3, 3))
        bp = MatrixBranchingProgram([(m, m)], start_vector=np.array([1.0, 0.0, 0.0]), output_index=0)

        entropy = compute_entropy(bp)
        assert entropy > 0.0

    def test_indistinguishability_metric(self):
        m = np.eye(2)
        bp1 = MatrixBranchingProgram([(m, m)], start_vector=np.array([1.0, 1.0]), output_index=0)

        m2 = np.array([[5.0, 0.0], [3.0, 1.0]])
        bp2 = MatrixBranchingProgram([(m2, m2)], start_vector=np.array([1.0, 1.0]), output_index=0)

        score = indistinguishability_score(bp1, bp2)
        assert 0.0 <= score <= 1.0

    def test_indistinguishability_metric_note(self):
        bp = _make_simple_bp()
        score = indistinguishability_score(bp, bp)
        assert 0.0 <= score <= 1.0


class TestCompatibility:
    """
    TestCompatibility

    Negative test cases for iO compatibility checks, verifying that
    incompatible function types are correctly rejected.
    """
    def test_compatible_function(self):
        source = """
def add(a, b):
    return a + b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]

        compatible, reason = is_io_compatible(func)
        assert compatible, reason

    def test_incompatible_float_params(self):
        source = """
def add(a, b):
    return a + b
"""
        ir_module = compile_py_to_ir(source)
        func = ir_module.functions[0]
        func.params[0] = ('a', type('IrType', (), {'kind': 'float'})())

        compatible, reason = is_io_compatible(func)
        assert not compatible
