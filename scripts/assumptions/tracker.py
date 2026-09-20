"""
assumptions/tracker.py — Assumption data model and checking engine (F171)

Purpose:
    Defines the Assumption data class, the AssumptionReport aggregation, and
    the AssumptionTracker that checks each assumption against provided runtime
    capabilities (os, hardware, software modules).

Architectural Role:
    Core engine. Receives assumptions from registry.py, checks them against
    runtime_caps dict, and builds an AssumptionReport.

Security Relevance:
    Provides a structured way to verify preconditions before relying on a
    protection feature, reducing the risk of silent degradation.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class Assumption:
    """A single assumption about the runtime environment.

    Attributes:
        feature: Feature name this assumption belongs to.
        assumption: Description of the assumed capability (e.g. "Linux", "AES-NI").
        assumption_type: Category — OS, hardware, software, runtime, configuration.
        required: Whether this assumption is mandatory (True) or optional.
        checked_at_runtime: Whether a runtime check was performed.
        satisfied: True / False / None (unknown) result of the check.
        evidence: Human-readable evidence string from the check.
    """
    feature: str
    assumption: str
    assumption_type: str
    required: bool = True
    checked_at_runtime: bool = False
    satisfied: Optional[bool] = None
    evidence: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "feature": self.feature,
            "assumption": self.assumption,
            "assumption_type": self.assumption_type,
            "required": self.required,
            "checked_at_runtime": self.checked_at_runtime,
            "satisfied": self.satisfied,
            "evidence": self.evidence,
        }


@dataclass
class AssumptionReport:
    """Aggregate report of all assumptions after runtime checking.

    Provides convenience properties for total, satisfied, unsatisfied,
    and unknown counts, plus a filter for critical unsatisfied assumptions.
    """
    assumptions: List[Assumption] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def total_count(self) -> int:
        return len(self.assumptions)

    @property
    def satisfied_count(self) -> int:
        return sum(1 for a in self.assumptions if a.satisfied is True)

    @property
    def unsatisfied_count(self) -> int:
        return sum(1 for a in self.assumptions if a.satisfied is False)

    @property
    def unknown_count(self) -> int:
        return sum(1 for a in self.assumptions if a.satisfied is None)

    @property
    def critical_unsatisfied(self) -> List[Assumption]:
        return [a for a in self.assumptions if a.required and a.satisfied is False]

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "total_count": self.total_count,
            "satisfied_count": self.satisfied_count,
            "unsatisfied_count": self.unsatisfied_count,
            "unknown_count": self.unknown_count,
            "critical_unsatisfied": [a.to_dict() for a in self.critical_unsatisfied],
            "assumptions": [a.to_dict() for a in self.assumptions],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize the report to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class AssumptionTracker:
    """Manages registration and runtime checking of feature assumptions.

    Groups assumptions by feature name, provides a check_assumptions method
    that compares against a runtime_caps dict, and builds AssumptionReports.
    """

    def __init__(self):
        self._assumptions: Dict[str, List[Assumption]] = {}

    def register_assumption(
        self,
        feature: str,
        assumption: str,
        assumption_type: str,
        required: bool = True,
    ) -> Assumption:
        """Register a new assumption for a feature and return the created Assumption."""
        a = Assumption(
            feature=feature,
            assumption=assumption,
            assumption_type=assumption_type,
            required=required,
        )
        self._assumptions.setdefault(feature, []).append(a)
        return a

    def register(self, assumption: Assumption) -> None:
        """Register a pre-built Assumption instance."""
        self._assumptions.setdefault(assumption.feature, []).append(assumption)

    def check_assumptions(self, runtime_caps: dict) -> None:
        """Check all registered assumptions against a runtime-capabilities dictionary.

        Handles Python module imports, OS checks, architecture checks, and
        generic capability lookups. Sets satisfied / checked_at_runtime /
        evidence on each Assumption.
        """
        for feature, assumptions in self._assumptions.items():
            for a in assumptions:
                key = a.assumption.replace(" ", "_").replace("-", "_").lower()
                expected_os = runtime_caps.get("os", {}).get(key if key.startswith("linux") else None)
                if key in runtime_caps:
                    a.satisfied = bool(runtime_caps[key])
                    a.checked_at_runtime = True
                    a.evidence = str(runtime_caps[key])
                elif key.startswith("python") or key.startswith("z3") or key.startswith("numpy") or key == "hashlib":
                    a.satisfied = self._check_python_module(a.assumption)
                    a.checked_at_runtime = True
                    a.evidence = "imported" if a.satisfied else "not_found"
                elif "linux" in key or key == "linux":
                    a.satisfied = runtime_caps.get("os", {}).get("system", "").lower() == "linux"
                    a.checked_at_runtime = True
                    a.evidence = f"os={runtime_caps.get('os', {}).get('system', 'unknown')}"
                elif key == "x86_64":
                    machine = runtime_caps.get("os", {}).get("machine", "")
                    a.satisfied = machine in ("x86_64", "amd64")
                    a.checked_at_runtime = True
                    a.evidence = f"machine={machine}"
                else:
                    # Try runtime probing for common hardware features
                    a.checked_at_runtime = True
                    if key == "x86_64":
                        import platform
                        a.satisfied = platform.machine() in ("x86_64", "AMD64")
                    elif key == "linux":
                        import sys
                        a.satisfied = sys.platform == "linux"
                    elif key in ("sgx", "SGX"):
                        a.satisfied = os.path.exists("/dev/sgx_enclave") or os.path.exists("/dev/isgx")
                    elif key in ("tee", "TEE"):
                        a.satisfied = os.path.exists("/dev/tee0") or os.path.exists("/dev/sgx_enclave")
                    elif key in ("gpu", "GPU"):
                        a.satisfied = os.path.exists("/dev/dri") or os.path.exists("/dev/nvidia0")
                    elif key == "aes_ni" or key == "AES-NI":
                        import subprocess
                        try:
                            out = subprocess.check_output(["grep", "-c", "aes", "/proc/cpuinfo"], text=True).strip()
                            a.satisfied = int(out) > 0
                        except Exception:
                            a.satisfied = None
                    elif key == "rdrand" or key == "RDRAND":
                        import subprocess
                        try:
                            out = subprocess.check_output(["grep", "-c", "rdrand", "/proc/cpuinfo"], text=True).strip()
                            a.satisfied = int(out) > 0
                        except Exception:
                            a.satisfied = None
                    elif key == "bpf":
                        a.satisfied = os.path.exists("/proc/sys/kernel/unprivileged_bpf_disabled")
                    elif key in ("mprotect",):
                        a.satisfied = True  # Always available on Linux
                    else:
                        a.satisfied = None  # Unknown capability
                        a.evidence = "not_checked"
                        import logging as _lg
                        _lg.debug(f"Assumption '{key}' could not be checked at runtime")

    @staticmethod
    def _check_python_module(name: str) -> bool:
        """Try to import a Python module by name; return True if successful."""
        name = name.strip().lower()
        module_map = {
            "python3": "sys",
            "z3": "z3",
            "numpy": "numpy",
            "hashlib": "hashlib",
            "angr": "angr",
        }
        mod = module_map.get(name)
        if mod is None:
            return False
        try:
            __import__(mod)
            return True
        except ImportError:
            return False

    def get_feature_assumptions(self, feature: str) -> List[Assumption]:
        """Return all assumptions registered for a given feature."""
        return self._assumptions.get(feature, [])

    def get_critical_assumptions(self) -> List[Assumption]:
        """Return all required (critical) assumptions across all features."""
        return [a for assumptions in self._assumptions.values() for a in assumptions if a.required]

    def to_dict(self) -> dict:
        """Serialize all assumptions grouped by feature to a dict."""
        return {
            feature: [a.to_dict() for a in assumptions]
            for feature, assumptions in self._assumptions.items()
        }

    def build_report(self) -> AssumptionReport:
        """Flatten all feature-assumption groups into a single AssumptionReport."""
        all_assumptions = []
        for assumptions in self._assumptions.values():
            all_assumptions.extend(assumptions)
        return AssumptionReport(assumptions=all_assumptions)
