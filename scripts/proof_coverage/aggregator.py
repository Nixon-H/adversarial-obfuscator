"""
proof_coverage/aggregator.py

Purpose:
Aggregates per-stage proof coverage into an overall score, generates
recommendations for improving coverage, and merges multiple reports.

Security Relevance:
The overall score is a summary metric used to evaluate pipeline trustworthiness.
A low score indicates high risk. Recommendations guide security investment.

Dependencies:
- scripts.proof_coverage.coverage (ProofCoverage, ProofCoverageReport)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from scripts.proof_coverage.coverage import ProofCoverage, ProofCoverageReport

STAGE_WEIGHTS = {
    "ast_ir": 0.15,
    "ir_llvm": 0.15,
    "llvm_vm": 0.20,
    "watermark": 0.10,
    "fragmentation": 0.15,
    "mutation": 0.10,
    "jit": 0.15,
}


def aggregate_proof_coverage(
    scanner_results: Dict[str, ProofCoverage],
) -> Dict[str, ProofCoverage]:
    if not scanner_results:
        return {}
    for stage in STAGE_WEIGHTS:
        if stage not in scanner_results:
            scanner_results[stage] = ProofCoverage(stage=stage)
    return scanner_results


def compute_overall_score(
    stage_scores: Dict[str, ProofCoverage],
) -> float:
    if not stage_scores:
        return 0.0
    total_weight = 0.0
    weighted_score = 0.0
    for stage, weight in STAGE_WEIGHTS.items():
        pc = stage_scores.get(stage)
        if pc is None:
            continue
        total_weight += weight
        if pc.has_proof and pc.proof_validated:
            weighted_score += weight * 1.0
        elif pc.has_proof:
            weighted_score += weight * 0.5
    if total_weight == 0.0:
        return 0.0
    return (weighted_score / total_weight) * 100.0


def generate_recommendations(
    stage_scores: Dict[str, ProofCoverage],
    z3_ok: bool = True,
) -> List[str]:
    recommendations: List[str] = []
    if not stage_scores:
        recommendations.append("No stages scanned. Run the proof coverage scanner first.")
        return recommendations

    uncovered = [s for s, pc in stage_scores.items() if not pc.has_proof]
    if uncovered:
        recommendations.append(
            f"Uncovered stages: {', '.join(sorted(uncovered))}. "
            f"Implement formal proof modules for each."
        )

    partial = [s for s, pc in stage_scores.items() if pc.has_proof and not pc.proof_validated]
    if partial:
        recommendations.append(
            f"Stages with unvalidated proofs: {', '.join(sorted(partial))}. "
            f"Run proof validation to confirm correctness."
        )

    low_coverage = [
        s for s, pc in stage_scores.items()
        if pc.has_proof and pc.coverage_percent < 50.0
    ]
    if low_coverage:
        recommendations.append(
            f"Low proof coverage stages: {', '.join(sorted(low_coverage))}. "
            f"Expand proof coverage to at least 80% per stage."
        )

        if not z3_ok:
            recommendations.append(
                "Z3 solver not available. Install z3-solver to enable SMT-based formal proofs."
            )

    weights = {
        "llvm_vm": "LLVM to VM transformation is the highest-weighted stage (20%). "
                   "Prioritize proof coverage here for maximum overall score impact.",
        "fragmentation": "Fragment safety carries 15% weight. "
                         "Ensure all fragment chain and isolation properties are proven.",
        "jit": "JIT reassembly correctness carries 15% weight. "
               "Formal verification of reassembly ensures runtime integrity.",
    }
    for stage, msg in weights.items():
        pc = stage_scores.get(stage)
        if pc and (not pc.has_proof or not pc.proof_validated):
            recommendations.append(msg)

    if not recommendations:
        recommendations.append("All stages have validated formal proofs. Maintain coverage with CI checks.")

    return recommendations


def merge_reports(reports: List[ProofCoverageReport]) -> ProofCoverageReport:
    if not reports:
        return ProofCoverageReport()

    all_stage_scores: Dict[str, List[ProofCoverage]] = {}
    for report in reports:
        for stage, pc in report.stage_scores.items():
            if stage not in all_stage_scores:
                all_stage_scores[stage] = []
            all_stage_scores[stage].append(pc)

    merged_scores: Dict[str, ProofCoverage] = {}
    for stage, scores in all_stage_scores.items():
        avg_covered = sum(s.functions_covered for s in scores) // max(len(scores), 1)
        avg_total = sum(s.functions_total for s in scores) // max(len(scores), 1)
        any_proof = any(s.has_proof for s in scores)
        best_type = "none"
        for s in scores:
            if s.proof_type != "none":
                best_type = s.proof_type
                break
        all_validated = all(s.proof_validated for s in scores)
        merged_scores[stage] = ProofCoverage(
            stage=stage,
            has_proof=any_proof,
            proof_type=best_type,
            functions_covered=avg_covered,
            functions_total=avg_total,
            proof_validated=all_validated,
        )

    overall = compute_overall_score(merged_scores)
    uncovered = [s for s, pc in merged_scores.items() if not pc.has_proof]
    partial = [s for s, pc in merged_scores.items() if pc.has_proof and not pc.proof_validated]
    recommendations = generate_recommendations(merged_scores, z3_ok=True)

    return ProofCoverageReport(
        overall_coverage=overall,
        stage_scores=merged_scores,
        uncovered_stages=uncovered,
        partially_covered_stages=partial,
        recommendations=recommendations,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
