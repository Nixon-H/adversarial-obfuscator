"""
simulator.py

Purpose:
Simulates plaintext exposure flows for different protection
configurations without running the full protection pipeline.
Enables rapid what-if analysis of exposure outcomes.

Architectural Role:
Testing and analysis tool for the exposure module. Generates
synthetic event streams based on protection configuration flags
(microjit, fragmentation, history_bound, fhe_vm) and computes
the resulting exposure score.

Execution Context:
Used during development and testing. Not part of the main build
pipeline. The simulate_plaintext_flow() method accepts a protection
config dict and returns a (events, score) tuple.

Dependencies:
- tracker (ExposureEventType, ExposureTracker)
- metric (PlaintextExposureMetric, ExposureReport)

Security Relevance:
Enables pre-deployment exposure estimation. The simulator can
predict which protection configuration yields the lowest exposure
score, helping select the optimal protection strategy before
committing to a build.

Maintenance Notes:
- The simulated event stream is simplistic (one appears/disappears
  per function per component). It does NOT model overlapping
  exposure windows, re-entrancy, or concurrent access.
- The default function names are ["main", "transform", "decrypt"];
  these are overridden by the IR module's function names if available.
"""

from __future__ import annotations
import time
from typing import Any, Dict, List, Optional, Tuple

from .tracker import ExposureEventType, ExposureTracker
from .metric import PlaintextExposureMetric, ExposureReport


class ExposureSimulator:
    def __init__(self) -> None:
        self._tracker = ExposureTracker()

    def simulate_plaintext_flow(
        self,
        ir_module: Optional[Any] = None,
        protection_config: Optional[Dict[str, bool]] = None,
    ) -> Tuple[List[Any], float]:
        if protection_config is None:
            protection_config = {}
        self._tracker.clear()

        start_time = time.monotonic_ns()
        functions = getattr(ir_module, "functions", None) if ir_module else []
        function_names: List[str] = []
        if functions:
            for func in functions:
                name = func.name if hasattr(func, "name") else "anonymous"
                function_names.append(name) if name else None

        if not function_names:
            function_names = ["main", "transform", "decrypt"]

        for fn_name in function_names:
            has_any = any([
                protection_config.get("microjit", False),
                protection_config.get("fragmentation", False),
                protection_config.get("history_bound", False),
                protection_config.get("fhe_vm", False),
            ])
            if not has_any:
                self._tracker.record_appearance("bare", fn_name, b"sim_bare_pt")
                self._tracker.record_disappearance("bare", fn_name, b"sim_bare_pt")

            if protection_config.get("microjit", False):
                self._tracker.record_appearance("microjit", fn_name, b"sim_microjit_pt")
                self._tracker.record_encryption("microjit", fn_name)
                self._tracker.record_disappearance("microjit", fn_name, b"sim_microjit_ct")

            if protection_config.get("fragmentation", False):
                for fid in range(2):
                    self._tracker.record_appearance("fragmentation", f"{fn_name}.frag_{fid}", b"sim_frag_pt")
                    self._tracker.record_encryption("fragmentation", f"{fn_name}.frag_{fid}")
                    self._tracker.record_disappearance("fragmentation", f"{fn_name}.frag_{fid}", b"sim_frag_ct")

            if protection_config.get("history_bound", False):
                self._tracker.record_decryption("history_bound", fn_name)
                self._tracker.record_appearance("history_bound", fn_name, b"sim_history_pt")
                self._tracker.record_disappearance("history_bound", fn_name, b"sim_history_ct")
                self._tracker.record_encryption("history_bound", fn_name)

            if protection_config.get("fhe_vm", False):
                self._tracker.record_appearance("fhe_vm", fn_name, b"sim_fhe_pt")
                self._tracker.record_encryption("fhe_vm", fn_name)

        end_time = time.monotonic_ns()
        total_execution_ns = end_time - start_time

        metric = PlaintextExposureMetric(self._tracker)
        score = metric.compute_exposure_score(total_execution_ns)
        events = self._tracker.get_events()

        return events, score

    def get_tracker(self) -> ExposureTracker:
        return self._tracker
