from __future__ import annotations

import numpy as np


class MatrixBranchingProgram:
    """A matrix branching program representing a small arithmetic function.

    Evaluation computes: start_vector @ M_1 @ M_2 @ ... @ M_n
    and extracts the output_index component of the result.

    Matrices are stored as a list of (matrix0, matrix1) pairs to support
    bit-selection in the standard branching-program model.  For deterministic
    arithmetic functions all matrices in a pair are identical so that the
    product is independent of the selection bits used during evaluation.
    """

    def __init__(
        self,
        matrices: list,
        start_vector: np.ndarray | None = None,
        output_index: int = 0,
    ):
        self.matrices = matrices
        self.start_vector = start_vector if start_vector is not None else np.eye(1)
        self.output_index = output_index
        self.dim = matrices[0][0].shape[0] if matrices else 1

    def evaluate(self, input_bits: list[int], param_values: np.ndarray | None = None) -> float:
        result = self.start_vector.copy()
        if param_values is not None:
            n = min(len(param_values), len(result))
            result[:n] = param_values[:n]
        for i, (m0, m1) in enumerate(self.matrices):
            bit_idx = i % len(input_bits) if input_bits else 0
            bit = input_bits[bit_idx] if bit_idx < len(input_bits) else 0
            m = m1 if bit else m0
            result = result @ m
        idx = self.output_index
        if idx < len(result):
            return float(result[idx])
        return float(result[0] if len(result) > 0 else 0.0)

    def evaluate_vector(self, input_vector: np.ndarray) -> np.ndarray:
        result = input_vector.copy()
        for m0, m1 in self.matrices:
            result = result @ m0
        return result

    def num_matrices(self) -> int:
        return len(self.matrices)


def randomize_bp(matrices: list[np.ndarray]) -> list[np.ndarray]:
    """Apply Kilian-style randomization to a sequence of matrices.

    Given M_1, ..., M_n, picks random invertible matrices R_1, ..., R_{n-1}
    and returns the randomized sequence:

        M'_1   = M_1 @ R_1^{-1}
        M'_i   = R_{i-1} @ M_i @ R_i^{-1}    for i = 2 .. n-1
        M'_n   = R_{n-1} @ M_n

    The product M'_1 @ ... @ M'_n == M_1 @ ... @ M_n is preserved.
    """
    n = len(matrices)
    if n <= 1:
        return list(matrices)

    d = matrices[0].shape[0]
    rng = np.random.default_rng()

    rand_mats = [_random_invertible(d, rng) for _ in range(n - 1)]

    result = []
    for i in range(n):
        if i == 0:
            r_inv = np.linalg.inv(rand_mats[0])
            result.append(matrices[0] @ r_inv)
        elif i < n - 1:
            r_prev = rand_mats[i - 1]
            r_inv = np.linalg.inv(rand_mats[i])
            result.append(r_prev @ matrices[i] @ r_inv)
        else:
            r_prev = rand_mats[-1]
            result.append(r_prev @ matrices[i])

    return result


def _random_invertible(d: int, rng: np.random.Generator) -> np.ndarray:
    for _attempt in range(100):
        m = rng.standard_normal((d, d))
        m = m @ m.T + np.eye(d) * 0.1
        try:
            _ = np.linalg.inv(m)
            return m
        except np.linalg.LinAlgError:
            continue
    return np.eye(d)


def evaluate_bp(matrices: list[np.ndarray], input_vector: np.ndarray) -> np.ndarray:
    bp = MatrixBranchingProgram(
        [(m, m) for m in matrices],
        start_vector=input_vector,
        output_index=0,
    )
    return bp.evaluate_vector(input_vector)
