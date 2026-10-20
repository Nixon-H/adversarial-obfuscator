"""
gate.py

Purpose:
Defines the security gate data model: GateSeverity (BLOCKER, WARNING,
INFO), GateResult (computed comparison outcome), and SecurityGate
(a gate definition with name, metric, threshold, and severity).

Architectural Role:
Foundation types for the security regression module. SecurityGate
defines what is being measured and the threshold. GateResult captures
the computed comparison between baseline and current values.

Execution Context:
SecurityGate instances are created in DEFAULT_GATES (checker.py) and
evaluated by RegressionChecker.check_gate(). The GateResult is
produced by SecurityGate.check().

Dependencies:
- Standard library (enum, dataclasses, typing)

Security Relevance:
Each SecurityGate encodes a security requirement. The threshold_percent
(e.g., 0.9) means the current metric must be at least 90% of the
baseline. A BLOCKER gate failure means the build must be rejected.

Maintenance Notes:
- GateResult.delta_percent is computed as (current/baseline) - 1.
  A negative delta means regression (current < baseline).
- The threshold_percent is compared as a ratio, not an absolute
  difference. This scales naturally for metrics at different orders
  of magnitude.
- The `enabled` flag on SecurityGate allows temporarily disabling
  gates without removing their definitions.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


class GateSeverity(enum.Enum):
    BLOCKER = "blocker"
    WARNING = "warning"
    INFO = "info"


@dataclass
class GateResult:
    gate_name: str
    metric_name: str
    baseline_value: float
    current_value: float
    delta_percent: float
    threshold_percent: float
    passed: bool
    severity: GateSeverity
    message: str = ""

    def __post_init__(self):
        # Explicit FAIL (passed=False) always wins: callers like
        # check_all_gates construct unevaluated-metric failures with
        # baseline 0.0, and __post_init__ must not flip them to pass.
        if self.passed is False and self.delta_percent == 0.0 and self.current_value == 0.0:
            return
        if self.baseline_value > 0:
            self.delta_percent = (self.current_value / self.baseline_value) - 1.0
        else:
            # Zero baseline is uninformative (division undefined): fail OPEN
            # rather than bricking the pipeline on a missing reference.
            self.delta_percent = 0.0
        if self.baseline_value > 0:
            self.passed = (self.current_value / self.baseline_value) >= self.threshold_percent
        else:
            self.passed = True


@dataclass
class SecurityGate:
    name: str
    metric_name: str
    threshold_percent: float
    severity: GateSeverity
    enabled: bool = True

    def check(self, baseline_value: float, current_value: float) -> GateResult:
        if baseline_value <= 0:
            # Fail OPEN on uninformative baseline (see GateResult).
            return GateResult(
                gate_name=self.name,
                metric_name=self.metric_name,
                baseline_value=current_value,
                current_value=current_value,
                delta_percent=0.0,
                threshold_percent=self.threshold_percent,
                passed=True,
                severity=self.severity,
                message=f"PASS (zero baseline for '{self.metric_name}'; fail-open)",
            )
        ratio = current_value / baseline_value
        delta = ratio - 1.0
        passed = ratio >= self.threshold_percent
        msg = (
            f"PASS: {self.name} ({current_value:.4f} >= {self.threshold_percent * 100:.1f}% of {baseline_value:.4f})"
            if passed
            else f"FAIL: {self.name} ({current_value:.4f} < {self.threshold_percent * 100:.1f}% of {baseline_value:.4f}, delta={delta * 100:+.2f}%)"
        )
        return GateResult(
            gate_name=self.name,
            metric_name=self.metric_name,
            baseline_value=baseline_value,
            current_value=current_value,
            delta_percent=delta,
            threshold_percent=self.threshold_percent,
            passed=passed,
            severity=self.severity,
            message=msg,
        )
