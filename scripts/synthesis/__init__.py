"""
__init__.py

Purpose:
Package initializer for the protection synthesis engine. Exports
the core data types (ProtectionPlan, ProtectionCost), the engine
(SynthesisEngine), the multi-strategy optimizer (ProtectionOptimizer),
and the cost database (PROTECTION_COSTS).

Architectural Role:
The synthesis engine is the brain of the protection pipeline. It
takes security requirements (target score, max overhead, max size)
and produces an optimal protection plan by selecting from available
features, respecting conflicts and dependencies.

Execution Context:
Called early in the build pipeline after the knowledge graph is
built. The resulting ProtectionPlan is serialized to the build
directory and its flags are merged into the CLI arguments for
subsequent protection passes.

Dependencies:
- engine (SynthesisEngine, ProtectionPlan, ProtectionCost)
- costs (PROTECTION_COSTS)
- optimizer (ProtectionOptimizer)

Security Relevance:
The synthesis engine determines which protections are applied.
A poorly-chosen plan can leave crown-jewel functions under-protected
or cause excessive overhead. The optimizer balances security gain
against cost and conflict constraints.

Maintenance Notes:
- Adding a new protection to the synthesis engine requires:
  (1) an entry in PROTECTION_COSTS in costs.py
  (2) the feature ID must match a knowledge-graph node ID
  (3) optionally: add to _base_protections in engine.py if it
      should be included in every plan by default
"""

from scripts.synthesis.engine import (
    SynthesisEngine,
    ProtectionPlan,
    ProtectionCost,
    optimize_protections,
    plan_to_cli_args,
)
from scripts.synthesis.costs import PROTECTION_COSTS
from scripts.synthesis.optimizer import ProtectionOptimizer

__all__ = [
    "SynthesisEngine",
    "ProtectionPlan",
    "ProtectionCost",
    "ProtectionOptimizer",
    "optimize_protections",
    "plan_to_cli_args",
    "PROTECTION_COSTS",
]
