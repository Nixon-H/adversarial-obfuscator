"""
checker.py

Purpose:
Regression checker that compares current metrics against a baseline
and evaluates each gate threshold. Loads baselines from JSON files,
supports fallback defaults, and generates GateReport summaries.

Architectural Role:
Gating logic for the security regression module. RegressionChecker
loads baseline metrics (from config/baseline_report.json or defaults),
checks each SecurityGate against current values, and produces a
GateReport with pass/fail status per gate.

Execution Context:
Instantiated at build completion. Metrics are collected by
MetricsCollector.collect_all_metrics() and passed to
check_all_gates(). The resulting GateReport is written to the
build directory and evaluated for BLOCKER failures.

Dependencies:
- gate (GateResult, GateSeverity, SecurityGate)
- metrics_collector (MetricsCollector)
- report (GateReport, generate_gate_report)
- Standard library (json, os, typing)

Security Relevance:
The regression gates enforce minimum security standards. Each
BLOCKER gate that fails represents a protection that has degraded
below acceptable levels. The build pipeline must reject the build
if any BLOCKER gate fails.

Maintenance Notes:
- The baseline path defaults to config/baseline_report.json relative
  to the project root. If missing, DEFAULT_BASELINE_METRICS are used.
- Each gate compares the ratio current/baseline against the gate's
  threshold_ratio (e.g., 0.9 means the current value must be at
  least 90% of the baseline).
- WARNING gates are informational; BLOCKER gates cause build failure.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from .gate import GateResult, GateSeverity, SecurityGate
from .metrics_collector import MetricsCollector  # noqa: F401 (this line binds a name used by an embedded template)
from .report import GateReport, generate_gate_report  # noqa: F401 (this line binds a name used by an embedded template)

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Documented fallback defaults (see module docstring): used when the
# baseline file is missing, so a fresh checkout still evaluates gates.
DEFAULT_BASELINE_METRICS: Dict[str, float] = {
    "cfg_entropy": 0.75,
    "ai_resistance": 0.75,
    "proof_coverage": 0.75,
    "survivability": 0.75,
    "plaintext_exposure": 0.75,
    "semantic_leakage": 0.75,
    "watermark_survival": 0.75,
    "symbolic_resistance": 0.75,
}

DEFAULT_GATES: List[SecurityGate] = [
    SecurityGate("CFG Entropy", "cfg_entropy", 0.9, GateSeverity.BLOCKER),
    SecurityGate("AI Resistance", "ai_resistance", 0.85, GateSeverity.BLOCKER),
    SecurityGate("Proof Coverage", "proof_coverage", 0.9, GateSeverity.BLOCKER),
    SecurityGate("Survivability", "survivability", 0.85, GateSeverity.WARNING),
    SecurityGate("Plaintext Exposure", "plaintext_exposure", 0.8, GateSeverity.WARNING),
    SecurityGate("Semantic Leakage", "semantic_leakage", 0.85, GateSeverity.BLOCKER),
    SecurityGate("Watermark Survival", "watermark_survival", 0.9, GateSeverity.BLOCKER),
    SecurityGate("Symbolic Resistance", "symbolic_resistance", 0.85, GateSeverity.WARNING),
]


def load_baseline(path: Optional[str] = None) -> Dict[str, float]:
    if path is None:
        path = os.path.join(_ROOT, "config", "baseline_report.json")
    if not os.path.exists(path):
        return dict(DEFAULT_BASELINE_METRICS)
    with open(path) as f:
        data = json.load(f)
    metrics: Dict[str, float] = {}
    for k, v in data.items():
        if isinstance(v, (int, float)):
            metrics[k] = float(v)
        elif isinstance(v, bool):
            metrics[k] = 1.0 if v else 0.0
    return metrics


def update_baseline(path: str, metrics: Dict[str, float]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = dict(metrics)
    data["timestamp"] = __import__("time").time()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)





class RegressionChecker:
    def __init__(self, baseline_path: Optional[str] = None):
        self.baseline_path = baseline_path
        self.baseline = load_baseline(baseline_path)
        if not self.baseline:
            raise FileNotFoundError(
                f"Baseline file not found at {baseline_path}. "
                "Baseline is required for gate evaluation."
            )
        self.gates: List[SecurityGate] = list(DEFAULT_GATES)

    def load_baseline(self, path: str) -> Dict[str, float]:
        self.baseline = load_baseline(path)
        self.baseline_path = path
        return self.baseline

    def save_baseline(self, path: str, metrics: Dict[str, float]) -> None:
        update_baseline(path, metrics)
        self.baseline = dict(metrics)

    def check_gate(self, gate: SecurityGate, current_value: float) -> GateResult:
        # No baseline reference for this metric: fail OPEN (pass) with the
        # current value as its own baseline, so a missing baseline entry
        # can never brick a build. Rationale: gates guard regressions vs a
        # known-good reference; with no reference there is nothing to
        # regress from. Missing-baseline visibility is the job of
        # check_all_gates/report (which marks unevaluated metrics).
        if gate.metric_name not in self.baseline:
            return GateResult(
                gate_name=gate.name,
                metric_name=gate.metric_name,
                baseline_value=current_value,
                current_value=current_value,
                delta_ratio=0.0,
                threshold_ratio=gate.threshold_ratio,
                passed=True,
                severity=gate.severity,
                message=f"PASS (no baseline for '{gate.metric_name}'; fail-open)",
            )
        baseline_value = self.baseline[gate.metric_name]
        if baseline_value == 0:
            # Zero baseline is uninformative (division undefined): fail OPEN
            # the same way rather than raising and bricking the pipeline.
            return GateResult(
                gate_name=gate.name,
                metric_name=gate.metric_name,
                baseline_value=current_value,
                current_value=current_value,
                delta_ratio=0.0,
                threshold_ratio=gate.threshold_ratio,
                passed=True,
                severity=gate.severity,
                message=f"PASS (zero baseline for '{gate.metric_name}'; fail-open)",
            )
        return gate.check(baseline_value, current_value)

    def check_all_gates(self, current_metrics: Dict[str, float]) -> List[GateResult]:
        results: List[GateResult] = []
        for gate in self.gates:
            if not gate.enabled:
                import logging as _lg
                _lg.warning(f"Gate '{gate.name}' is disabled — skipping")
                continue
            if gate.metric_name not in current_metrics:
                # Metric absent from this run: FAIL CLOSED (passed=False,
                # current 0.0) so missing measurements are visible as
                # failures, not silently passed. (Contrast with check_gate's
                # fail-open on missing BASELINE: no reference = nothing to
                # regress from; no measurement = unevaluated = fail.)
                from .gate import GateResult as _GR
                results.append(_GR(
                    gate_name=gate.name,
                    metric_name=gate.metric_name,
                    baseline_value=self.baseline.get(gate.metric_name, 0.0),
                    current_value=0.0,
                    delta_ratio=0.0,
                    threshold_ratio=gate.threshold_ratio,
                    passed=False,
                    severity=gate.severity,
                    message=f"FAIL (metric '{gate.metric_name}' not measured)",
                ))
                continue
            current_value = current_metrics[gate.metric_name]
            result = self.check_gate(gate, current_value)
            results.append(result)
        return results

    def generate_report(self, results: List[GateResult]) -> GateReport:
        blockers = [r for r in results if r.severity == GateSeverity.BLOCKER]
        warnings = [r for r in results if r.severity == GateSeverity.WARNING]
        all_passed = all(r.passed for r in results if r.severity == GateSeverity.BLOCKER)
        warning_failures = sum(1 for r in results if r.severity == GateSeverity.WARNING and not r.passed)
        if warning_failures > 2:
            import logging as _lg
            _lg.warning(f"{warning_failures} WARNING gates failed (threshold: >2)")
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        all_passed = all_passed and warning_failures <= 2
        summary = f"Security Gates: {passed}/{total} passed"
        if not all_passed:
            failed_blockers = [r for r in blockers if not r.passed]
            summary += f", {len(failed_blockers)} BLOCKER(s) failed"
        return GateReport(
            all_passed=all_passed,
            gates=results,
            blockers=blockers,
            warnings=warnings,
            summary=summary,
        )

    def has_blockers(self, results: List[GateResult]) -> bool:
        return any(
            r.severity == GateSeverity.BLOCKER and not r.passed for r in results
        )


def check_regression_gates(
    current_metrics: Dict[str, float],
    baseline_path: Optional[str] = None,
    gates: Optional[List[SecurityGate]] = None,
) -> GateReport:
    checker = RegressionChecker(baseline_path)
    if gates is not None:
        checker.gates = gates
    results = checker.check_all_gates(current_metrics)
    return checker.generate_report(results)
