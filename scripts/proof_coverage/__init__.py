"""
proof_coverage/__init__

Purpose:
Proof coverage measurement and reporting. Tracks which pipeline stages have
formal proof modules, whether those proofs validate, and how many functions
are covered. Generates recommendations for improving proof coverage.

Security Relevance:
Proof coverage directly corresponds to trustworthiness of the obfuscation
pipeline. Low coverage means transformations exist without formal guarantees.
The coverage report is the primary management tool for prioritizing proof
development.

Dependencies:
- scripts.proof_coverage.coverage     (data structures)
- scripts.proof_coverage.aggregator   (aggregation + scoring)
- scripts.proof_coverage.scanner      (stage scanning)
- scripts.proof_coverage.inspector    (module inspection)
"""
from .coverage import ProofCoverage, ProofCoverageReport
from .aggregator import aggregate_proof_coverage, compute_overall_score, generate_recommendations, merge_reports
from .scanner import ProofCoverageScanner
from .inspector import inspect_preservation_module, inspect_proofs_module, probe_z3_availability, check_proof_validity

__all__ = [
    "ProofCoverage",
    "ProofCoverageReport",
    "ProofCoverageScanner",
    "aggregate_proof_coverage",
    "compute_overall_score",
    "generate_recommendations",
    "merge_reports",
    "inspect_preservation_module",
    "inspect_proofs_module",
    "probe_z3_availability",
    "check_proof_validity",
]
