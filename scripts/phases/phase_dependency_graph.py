"""
phase_dependency_graph.py

Purpose:
Validates the module dependency graph — detects circular dependencies,
computes dependency depth per module, and calculates a circular score
indicating how well-structured the dependency graph is.

Architectural Role:
Code quality/architecture audit phase.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, typing, scripts.common, scripts.dependency_graph.*

Security Relevance:
Circular dependencies can enable unexpected code paths and make
security analysis incomplete; a clean dependency graph is a prerequisite
for sound security reasoning.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.common import BUILD_DIR, atomic_write, log
from scripts.dependency_graph.validator import DependencyGraphValidator


def phase_dependency_graph(args: Any) -> dict:
    """
    Validate the module dependency graph and detect cycles.

    Args:
        args: argparse.Namespace

    Returns:
        dict with total_modules, cycles_found, circular_score
    """
    log("DEPENDENCY_GRAPH", "Validating dependency graph for all script modules...")

    validator = DependencyGraphValidator()
    result = validator.validate_dependency_graph()

    os.makedirs(BUILD_DIR, exist_ok=True)
    report_path = os.path.join(BUILD_DIR, "dependency_graph_report.json")
    atomic_write(report_path, json.dumps(result, indent=2))
    log("DEPENDENCY_GRAPH", f"Report saved to {report_path}")

    print()
    print("=" * 60)
    print("  DEPENDENCY GRAPH VALIDATION")
    print("=" * 60)
    print(f"  Total modules:  {result['total_modules']}")
    print(f"  Cycles found:   {result['total_cycles']}")
    print(f"  Circular score: {result['circular_score']:.1f}/100")
    print(f"  Max depth:      {max(result['per_module_depth'].values()) if result['per_module_depth'] else 0}")
    print("=" * 60)
    print()

    for cycle in result["cycles_found"]:
        path_str = " -> ".join(cycle["cycle_path"])
        print(f"  CYCLE ({cycle['length']} nodes): {path_str}")

    if result["cycles_found"]:
        print()
    print("=" * 60)
    print()

    return result
