"""
reachability — Reachability Coverage (F169)

Purpose:
    Analyzes whether each protection feature is actually reachable from the
    pipeline's entry point (build.py) through CLI flags, phase calls, import
    chains, runtime source, and test files.

Architectural Role:
    Coverage-analysis layer. Detects "dead" features that are defined but
    never wired into the CLI or build pipeline, causing false confidence.

Security Relevance:
    A feature that cannot be triggered at build time provides zero protection.
    Reachability analysis surfaces these gaps before they reach production.
"""

from .analyzer import ReachabilityAnalyzer, ReachabilityReport, ReachabilityStatus
from .feature_map import ALL_FEATURES

def analyze_feature_reachability(feature_name: str) -> dict:
    """Convenience: analyze a single feature's reachability and return a dict summary."""
    analyzer = ReachabilityAnalyzer()
    fr = analyzer.analyze_feature(feature_name)
    return {
        "feature_name": fr.feature_name,
        "status": fr.status.value,
        "cli_flag_found": fr.cli_flag_found,
        "cli_flag_path": fr.cli_flag_path,
        "phase_found": fr.phase_found,
        "phase_path": fr.phase_path,
        "import_chain": fr.import_chain,
        "implementation_found": fr.implementation_found,
        "implementation_path": fr.implementation_path,
        "runtime_paths": fr.runtime_paths,
        "test_files": fr.test_files,
        "missing_links": fr.missing_links,
    }

def generate_reachability_report() -> ReachabilityReport:
    """Convenience: run a full reachability analysis and return the report object."""
    analyzer = ReachabilityAnalyzer()
    return analyzer.generate_report()

__all__ = [
    "ReachabilityAnalyzer",
    "ReachabilityReport",
    "ReachabilityStatus",
    "analyze_feature_reachability",
    "generate_reachability_report",
    "ALL_FEATURES",
]
