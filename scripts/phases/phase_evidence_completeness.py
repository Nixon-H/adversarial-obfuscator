"""
phase_evidence_completeness.py

Purpose:
Computes evidence completeness score — evaluates how thoroughly each
security claim is supported by evidence across the codebase.  Identifies
missing links between claims and their supporting evidence.

Architectural Role:
Audit phase — quantifies the evidential support for security claims.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.evidence_completeness.*

Security Relevance:
Evidence completeness is a direct measure of claim substantiation;
low scores indicate gaps between promises and proof.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.evidence_completeness.scorer import EvidenceCompletenessScorer


def phase_evidence_completeness(args: Any) -> dict:
    """
    Compute evidence completeness score for all claims.

    Args:
        args: argparse.Namespace

    Returns:
        dict with overall_score, total_claims, per_claim_results
    """
    log("EVIDENCE_COMPLETENESS", "Computing evidence completeness score for all claims...")

    scorer = EvidenceCompletenessScorer()
    result = scorer.compute_evidence_completeness()

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "evidence_completeness_report.json")
    atomic_write(report_path, json.dumps(result, indent=2))
    log("EVIDENCE_COMPLETENESS", f"Report saved to {report_path}")

    print()
    print("=" * 60)
    print("  EVIDENCE COMPLETENESS SCORE")
    print("=" * 60)
    print(f"  Overall score: {result['overall_score']:.1f}/100")
    print(f"  Total claims:  {result['total_claims']}")
    print(f"  Missing links: {len(result['missing_links'])}")
    print("=" * 60)
    print()

    for claim in result["per_claim_results"][:10]:
        print(f"  [{claim['score']:5.1f}] {claim['source_file']}:{claim['line_number']} "
              f"\"{claim['claim_text'][:60]}...\"")
        if claim["missing_links"]:
            print(f"       MISSING: {', '.join(claim['missing_links'])}")
    print("=" * 60)
    print()

    return result
