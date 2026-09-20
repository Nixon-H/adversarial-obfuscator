from __future__ import annotations

import numpy as np

from .np_obfuscation import MatrixBranchingProgram


def compute_program_distance(bp1: MatrixBranchingProgram, bp2: MatrixBranchingProgram) -> float:
    """Matrix-wise Frobenius norm distance between two branching programs.

    NOTE: MEASURED metric — not a theoretical security bound.
    """
    m1 = _flatten_matrices(bp1)
    m2 = _flatten_matrices(bp2)
    max_len = max(len(m1), len(m2))
    total = 0.0
    for i in range(max_len):
        a = m1[i] if i < len(m1) else np.zeros_like(m1[0]) if m1 else np.zeros((1, 1))
        b = m2[i] if i < len(m2) else np.zeros_like(m2[0]) if m2 else np.zeros((1, 1))
        if a.shape != b.shape:
            a = _pad_to(a, max(a.shape[0], b.shape[0]))
            b = _pad_to(b, max(a.shape[0], b.shape[0]))
        total += float(np.linalg.norm(a - b, ord='fro'))
    return total / max(max_len, 1)


def compute_entropy(bp: MatrixBranchingProgram) -> float:
    """Shannon entropy of matrix coefficients.

    NOTE: MEASURED metric — higher values indicate more randomness in coefficients.
    """
    all_coeffs = []
    for m0, _m1 in bp.matrices:
        all_coeffs.extend(m0.flatten().tolist())
    if not all_coeffs:
        return 0.0

    all_coeffs = np.array(all_coeffs)
    if all_coeffs.std() < 1e-10:
        return 0.0

    normalized = (all_coeffs - all_coeffs.mean()) / (all_coeffs.std() + 1e-10)
    counts, _ = np.histogram(normalized, bins=20, range=(-3, 3))
    total = float(counts.sum())
    if total == 0:
        return 0.0
    probs = counts / total
    probs = probs[probs > 0]
    if len(probs) == 0:
        return 0.0
    return float(-np.sum(probs * np.log2(probs)))


def indistinguishability_score(
    obfuscated: MatrixBranchingProgram,
    reference: MatrixBranchingProgram,
) -> float:
    """Combined MEASURED indistinguishability metric (0..1).

    1.0 = maximally indistinguishable from reference.
    NOTE: MEASURED metric — not a theoretical security guarantee.
    """
    dist = compute_program_distance(obfuscated, reference)
    entropy = compute_entropy(obfuscated)

    # Convert distance to a similarity score (0..1), higher = more similar structure
    # Larger distance = more different = better for obfuscation
    if dist < 1e-10:
        struct_score = 0.0
    else:
        struct_score = min(1.0, dist / 10.0)

    # Normalize entropy to 0..1 (max ~ log2(20) ≈ 4.32 for 20 bins)
    max_entropy = np.log2(20)
    entropy_score = min(1.0, entropy / max_entropy) if max_entropy > 0 else 0.0

    score = 0.5 * struct_score + 0.5 * entropy_score
    return float(min(1.0, max(0.0, score)))


def _flatten_matrices(bp: MatrixBranchingProgram) -> list[np.ndarray]:
    result = []
    for m0, _m1 in bp.matrices:
        result.append(m0)
    return result


def _pad_to(m: np.ndarray, size: int) -> np.ndarray:
    if m.shape[0] >= size and m.shape[1] >= size:
        return m[:size, :size]
    padded = np.zeros((size, size))
    padded[:m.shape[0], :m.shape[1]] = m
    return padded
