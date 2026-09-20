"""
__init__.py

Purpose:
Package initializer for the semantic leakage metric module. Measures
how much semantic information about the original program leaks through
obfuscation at four hierarchical levels: variable, function, intent,
architecture.

Architectural Role:
Core security metric that quantifies obfuscation quality. The Semantic
Leakage Index (SLI) is computed by compute_sli() and consumed by the
security regression gates and the artifact report generator.

Execution Context:
Called after obfuscation completes, comparing original and obfuscated
IR modules. The result is a LeakageReport with per-level scores and
remediation recommendations.

Dependencies:
- taxonomy (LeakageLevel, LeakageScore, LeakageReport)
- analyzers (Variable/Function/Intent/Architecture LeakageAnalyzer)
- metrics (compute_cfg_similarity, compute_opcode_histogram, etc.)
- scorer (compute_sli)

Security Relevance:
Each leakage level corresponds to a different attacker capability:
variable leakage = symbol recovery, function leakage = boundary
recovery, intent leakage = algorithm recovery, architecture leakage
= program structure recovery. High SLI means the obfuscation is
ineffective.

Maintenance Notes:
- Adding a new analysis level requires: (1) a new LeakageLevel enum,
  (2) a new analyzer class, (3) registration in scorer.compute_sli(),
  (4) a weight in the SLI formula.
"""

from .taxonomy import LeakageLevel, LeakageScore, LeakageReport
from .analyzers import (
    VariableLeakageAnalyzer,
    FunctionLeakageAnalyzer,
    IntentLeakageAnalyzer,
    ArchitectureLeakageAnalyzer,
)
from .metrics import (
    compute_cfg_similarity,
    compute_opcode_histogram,
    compute_entropy,
    compute_name_preservation,
    compute_call_graph_similarity,
)
from .scorer import compute_sli

__all__ = [
    "LeakageLevel",
    "LeakageScore",
    "LeakageReport",
    "VariableLeakageAnalyzer",
    "FunctionLeakageAnalyzer",
    "IntentLeakageAnalyzer",
    "ArchitectureLeakageAnalyzer",
    "compute_cfg_similarity",
    "compute_opcode_histogram",
    "compute_entropy",
    "compute_name_preservation",
    "compute_call_graph_similarity",
    "compute_sli",
]
