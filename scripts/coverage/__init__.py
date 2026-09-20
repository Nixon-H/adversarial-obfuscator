"""
__init__.py

Purpose:
Package initializer for the protection coverage module. Tracks which
protections are applied to each function in an IR module.

Architectural Role:
Provides a real-time snapshot of protection coverage during pipeline
execution. The CoverageMap and PipelineTracker are consumed by the
knowledge graph, synthesis engine, and artifact generators.

Security Relevance:
Coverage gaps are the most common source of protection failure. This
module surfaces exactly which functions are missing which protections,
enabling targeted remediation before deployment.
"""

from .coverage_map import CoverageMap, FunctionCoverage, generate_coverage_map, merge_coverage_maps, coverage_to_json, coverage_to_html, coverage_to_text
from .pipeline_tracker import PipelineTracker
from .ir_scanner import scan_ir_module, classify_function

__all__ = [
    "CoverageMap", "FunctionCoverage", "generate_coverage_map",
    "merge_coverage_maps", "coverage_to_json", "coverage_to_html",
    "coverage_to_text", "PipelineTracker", "scan_ir_module",
    "classify_function",
]
