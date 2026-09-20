"""
phase_proof_coverage.py

Purpose:
Scans the entire pipeline for proof coverage — which stages have formal
proofs, which proofs have been validated, and which stages are unproven.
Generates a coverage report with recommendations.

Architectural Role:
Audit/verification phase — runs late in the pipeline to measure proof
completeness.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.proof_coverage.*

Security Relevance:
Proof coverage is the primary metric for pipeline verification rigor —
it determines which protection claims are formally substantiated.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.proof_coverage.coverage import ProofCoverageReport
from scripts.proof_coverage.scanner import ProofCoverageScanner
from scripts.proof_coverage.aggregator import (
    aggregate_proof_coverage,
    compute_overall_score,
    generate_recommendations,
)


def phase_proof_coverage(args: Any) -> Optional[ProofCoverageReport]:
    """
    Scan all pipeline stages for proof coverage.

    Args:
        args: argparse.Namespace

    Returns:
        ProofCoverageReport or None
    """
    log("PROOF_COVERAGE", "Scanning pipeline for proof coverage...")

    scanner = ProofCoverageScanner()
    results = scanner.scan_all()

    aggregated = aggregate_proof_coverage(results)

    overall = compute_overall_score(aggregated)

    uncovered = [s for s, pc in aggregated.items() if not pc.has_proof]
    partial = [s for s, pc in aggregated.items() if pc.has_proof and not pc.proof_validated]

    recommendations = generate_recommendations(aggregated, z3_ok=scanner.z3_ok)

    report = ProofCoverageReport(
        overall_coverage=overall,
        stage_scores=aggregated,
        uncovered_stages=uncovered,
        partially_covered_stages=partial,
        recommendations=recommendations,
    )

    print()
    print("=" * 60)
    print("  PROOF COVERAGE REPORT")
    print("=" * 60)
    print(f"  Overall coverage: {overall:.2f}%")
    print()
    for stage in ["ast_ir", "ir_llvm", "llvm_vm", "watermark", "fragmentation", "mutation", "jit"]:
        pc = aggregated.get(stage)
        if pc is None:
            continue
        status = "PROVEN" if pc.has_proof and pc.proof_validated else "PARTIAL" if pc.has_proof else "UNPROVEN"
        ptype = pc.proof_type if pc.has_proof else "-"
        cov = pc.coverage_percent
        print(f"  {stage:20s} {status:9s} type={ptype:12s} coverage={cov:5.1f}%")
    print()
    if uncovered:
        print(f"  Uncovered stages:       {', '.join(uncovered)}")
    if partial:
        print(f"  Partially covered:      {', '.join(partial)}")
    print()
    print("  Recommendations:")
    for rec in recommendations:
        print(f"    - {rec}")
    print("=" * 60)
    print()

    report_path = os.path.join(BUILD_DIR, "proof_coverage_report.json")
    os.makedirs(BUILD_DIR, exist_ok=True)
    atomic_write(report_path, json.dumps(report.to_dict(), indent=2))
    log("PROOF_COVERAGE", f"Report saved to {report_path}")

    return report
