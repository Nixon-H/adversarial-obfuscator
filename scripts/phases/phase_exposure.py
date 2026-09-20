"""
phase_exposure.py

Purpose:
Measures plaintext exposure — how much time the payload spends in
decrypted/unprotected form during execution.  Simulates event flows
through MicroJIT, fragmentation, history-bound, and FHE paths to
compute an exposure score.

Architectural Role:
Measurement/audit phase — quantifies the residual plaintext window.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
csv, json, os, time, typing, ..common, ..exposure.*

Security Relevance:
Exposure measurement is critical — even the best encryption is useless
if the plaintext window is large enough to be exploited.
"""

from __future__ import annotations
import csv
import json
import os
import time
from typing import Any, Dict, Optional

from ..common import log, BUILD_DIR
from ..exposure.tracker import ExposureTracker
from ..exposure.metric import PlaintextExposureMetric, ExposureReport
from ..exposure.instrumentors import (
    MicroJITExposureInstrumentor,
    FragmentationExposureInstrumentor,
    HistoryBoundExposureInstrumentor,
    FHEExposureInstrumentor,
)
from ..exposure.simulator import ExposureSimulator


def compute_exposure_score(tracker: ExposureTracker) -> float:
    """
    Compute the plaintext exposure score from a tracker's event data.

    Args:
        tracker: populated ExposureTracker

    Returns:
        exposure score float
    """
    metric = PlaintextExposureMetric(tracker)
    return metric.compute_exposure_score()


def phase_exposure(
    args: Any,
    ir_module: Any = None,
    protection_config: Optional[dict] = None,
) -> Optional[float]:
    """
    Measure plaintext exposure across all protection instrumentors.

    Args:
        args: argparse.Namespace
        ir_module: optional IrModule for function enumeration
        protection_config: optional dict of enabled protections

    Returns:
        ExposureReport or None
    """
    log("EXPOSURE", "Starting plaintext exposure metric analysis...")

    if protection_config is None:
        protection_config = {}
        if hasattr(args, "microjit") and args.microjit:
            protection_config["microjit"] = True
        if hasattr(args, "fragment") and args.fragment:
            protection_config["fragmentation"] = True
        if hasattr(args, "history_bound_decryption") and args.history_bound_decryption:
            protection_config["history_bound"] = True
        if hasattr(args, "fhe_vm") and args.fhe_vm:
            protection_config["fhe_vm"] = True

    tracker = ExposureTracker()

    microjit_inst = MicroJITExposureInstrumentor(tracker)
    frag_inst = FragmentationExposureInstrumentor(tracker)
    history_inst = HistoryBoundExposureInstrumentor(tracker)
    fhe_inst = FHEExposureInstrumentor(tracker)

    functions = getattr(ir_module, "functions", None) if ir_module else []
    function_names: list[str] = []
    if functions:
        for func in functions:
            name = getattr(func, "name", "anonymous")
            if name:
                function_names.append(name)

    if not function_names:
        function_names = ["main", "transform", "decrypt"]

    for fn_name in function_names:
        if protection_config.get("microjit", False):
            microjit_inst.instrument_microjit(getattr(ir_module, "functions", [None])[0] if ir_module else None)
        if protection_config.get("fragmentation", False):
            frag_inst.instrument_fragment(None)
        if protection_config.get("history_bound", False):
            history_inst.instrument_decryption(fn_name)
            history_inst.instrument_encryption(fn_name)
        if protection_config.get("fhe_vm", False):
            fhe_inst.instrument_encryption(fn_name)

    simulator = ExposureSimulator()
    sim_events, sim_score = simulator.simulate_plaintext_flow(ir_module, protection_config)
    for ev in sim_events:
        tracker._events.append(ev)

    end_time = time.monotonic_ns()
    total_execution_ns = end_time - (end_time - len(tracker.get_events()) * 1000)

    metric = PlaintextExposureMetric(tracker)
    report = metric.generate_report(total_execution_ns)

    report_path = os.path.join(BUILD_DIR, "exposure_report.json")
    try:
        with open(report_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        log("EXPOSURE", f"Report written to {report_path}")
    except Exception as e:
        log("EXPOSURE", f"Failed to write report JSON: {e}")

    csv_path = os.path.join(BUILD_DIR, "exposure_timeline.csv")
    try:
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["component", "function", "event_type", "timestamp_ns", "data_hash"])
            for ev in tracker.get_events():
                writer.writerow([
                    ev.component, ev.function, ev.event_type.value,
                    ev.timestamp_ns, ev.data_hash,
                ])
        log("EXPOSURE", f"Timeline CSV written to {csv_path}")
    except Exception as e:
        log("EXPOSURE", f"Failed to write timeline CSV: {e}")

    print()
    print("  " + "=" * 58)
    print("  PLAINTEXT EXPOSURE METRIC REPORT")
    print("  " + "=" * 58)
    print(f"  Overall Exposure Score:     {report.overall_score:.2f} / 100")
    print(f"  Total Exposure Time:        {report.total_exposure_ns} ns")
    print(f"  Total Execution Time:       {report.total_execution_ns} ns")
    print(f"  Event Count:                {report.event_count}")
    print(f"  Component Scores:")
    for comp, score in sorted(report.component_scores.items()):
        print(f"    {comp:30s}: {score:.2f}")
    print(f"  Recommendations:")
    for rec in report.recommendations:
        print(f"    - {rec}")
    print("  " + "=" * 58)
    print()

    log("EXPOSURE", f"Exposure score: {report.overall_score:.2f}/100")

    return report
