"""
__init__.py

Purpose:
Package initializer for the security regression gates module. Exports
gate data types, the regression checker, metrics collector, gate
report generator, and default gate definitions.

Architectural Role:
Final quality gate before build acceptance. Each security metric
(CFG entropy, AI resistance, proof coverage, etc.) has a gate with
a threshold. If any BLOCKER gate fails, the build is rejected.

Execution Context:
Called at build completion after all protection passes and metrics
collection. The check_regression_gates() function reads current
metrics, compares against baseline, and produces a GateReport.

Dependencies:
- gate (GateSeverity, GateResult, SecurityGate)
- checker (RegressionChecker, check_regression_gates, etc.)
- metrics_collector (MetricsCollector)
- report (GateReport, generate_gate_report, etc.)

Security Relevance:
The regression gates are the last line of defense against protection
degradation. Each gate enforces a minimum quality threshold for a
specific security metric. BLOCKER gates can stop the build.

Maintenance Notes:
- Adding a new gate requires: (1) an entry in DEFAULT_GATES in
  checker.py, (2) the corresponding metric in MetricsCollector,
  (3) a fallback value in _apply_fallback().
"""

from .gate import GateSeverity, GateResult, SecurityGate
from .checker import RegressionChecker, check_regression_gates, load_baseline, update_baseline, DEFAULT_GATES
from .metrics_collector import MetricsCollector
from .report import GateReport, generate_gate_report, format_report_text, format_report_json

__all__ = [
    "SecurityGate",
    "GateResult",
    "GateSeverity",
    "RegressionChecker",
    "check_regression_gates",
    "load_baseline",
    "update_baseline",
    "DEFAULT_GATES",
    "MetricsCollector",
    "GateReport",
    "generate_gate_report",
    "format_report_text",
    "format_report_json",
]
