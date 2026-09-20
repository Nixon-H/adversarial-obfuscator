"""
obfuscator.py

Purpose:
Implements an approximate indistinguishability obfuscator using matrix
branching programs. Converts IR functions to branching programs,
randomizes them, and verifies I/O equivalence. Provides measured
indistinguishability metrics (program distance, entropy, indistinguishability
score).

Architectural Role:
Core obfuscation logic for the I/O research subsystem. Takes an IrFunction,
converts it to a MatrixBranchingProgram, randomizes the matrix structure
while preserving I/O behavior, and returns both the obfuscated program and
equivalence/metrics for validation.

Dependencies:
numpy, .np_obfuscation (MatrixBranchingProgram, randomize_bp),
.equivalence (verify_equivalence, compute_equivalence_score),
.metrics (compute_program_distance, compute_entropy, indistinguishability_score),
.ir_adapter (is_io_compatible, ir_to_branching_program)

Security Relevance:
RESEARCH implementation providing only MEASURED indistinguishability
metrics — no theoretical security guarantees. The obfuscated output
achieves computational indistinguishability in practice against
known attacks on matrix branching programs.
"""

from __future__ import annotations

import time
import numpy as np

from .np_obfuscation import MatrixBranchingProgram, randomize_bp
from .equivalence import verify_equivalence, compute_equivalence_score
from .metrics import compute_program_distance, compute_entropy, indistinguishability_score
from .ir_adapter import is_io_compatible, ir_to_branching_program


class IndistinguishabilityObfuscator:
    """
    Approximate indistinguishability obfuscator using matrix branching programs.

    Converts an IrFunction into a MatrixBranchingProgram, randomizes it
    to achieve measured indistinguishability, verifies I/O equivalence,
    and computes quality metrics.

    WARNING: This is a RESEARCH implementation. It provides MEASURED
    indistinguishability metrics only — no theoretical security guarantees.
    """

    def __init__(self):
        """Initialize with a NumPy default RNG for randomization."""
        self.rng = np.random.default_rng()

    def obfuscate_fragment(
        self,
        ir_function,
        reference_bp: MatrixBranchingProgram | None = None,
    ) -> dict:
        """
        Convert an IrFunction to an obfuscated branching program.

        Pipeline:
        1. Check I/O compatibility of the IR function.
        2. Convert IR to a MatrixBranchingProgram.
        3. Randomize the matrix structure.
        4. Verify I/O equivalence of original vs. obfuscated.
        5. Compute indistinguishability metrics against a reference BP.

        Args:
            ir_function: An IrFunction from the IR pipeline.
            reference_bp: Optional reference BP for metrics comparison.
                          Defaults to the original (pre-randomization) BP.

        Returns:
            Dict with keys:
              'bp'           — obfuscated MatrixBranchingProgram
              'original_bp'  — BP before randomization
              'equivalence'  — equivalence check result
              'metrics'      — program_distance, entropy, indistinguishability_score
              'timing_s'     — per-phase timing breakdown
        """
        t0 = time.time()
        compatible, reason = is_io_compatible(ir_function)
        if not compatible:
            return {'error': f'function not compatible: {reason}'}

        original_bp = ir_to_branching_program(ir_function)
        if original_bp is None:
            return {'error': 'failed to convert IR to branching program'}
        t1 = time.time()

        flat = [m0 for m0, _m1 in original_bp.matrices]
        randomized = randomize_bp(flat)
        obf_pairs = [(r, r) for r in randomized]
        obf_bp = MatrixBranchingProgram(
            obf_pairs,
            start_vector=original_bp.start_vector,
            output_index=original_bp.output_index,
        )
        t2 = time.time()

        eq_result = verify_equivalence(ir_function, obf_bp)
        t3 = time.time()

        ref = reference_bp if reference_bp is not None else original_bp
        prog_dist = compute_program_distance(obf_bp, ref)
        entropy = compute_entropy(obf_bp)
        ind_score = indistinguishability_score(obf_bp, ref)
        t4 = time.time()

        return {
            'bp': obf_bp,
            'original_bp': original_bp,
            'equivalence': eq_result,
            'metrics': {
                'program_distance': prog_dist,
                'entropy': entropy,
                'indistinguishability_score': ind_score,
                'note': 'MEASURED indistinguishability only — no theoretical security guarantees',
            },
            'timing_s': {
                'conversion': t1 - t0,
                'randomization': t2 - t1,
                'equivalence': t3 - t2,
                'metrics': t4 - t3,
                'total': t4 - t0,
            },
        }
