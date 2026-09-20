"""
bench_conflicts.py

Benchmarks for protection conflict detection.

Measures conflict detection and graph construction performance.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.conflicts import KNOWN_CONFLICTS, ConflictDetector, ConflictGraph


def _make_full_flag_set():
    return {
        "skip_obfuscate": False,
        "skip_irgen": False,
        "skip_llvmgen": False,
        "skip_encrypt": False,
        "obfuscate": True,
        "fhe_vm": False,
        "io_research": False,
        "verify_preservation": False,
        "prove_vm": True,
        "rop": False,
        "tee": True,
        "sgx": True,
        "gpu_execution": False,
        "cpu_gpu_hybrid": False,
        "multi_binary": False,
        "single_binary": True,
        "phase2": True,
        "phase2_only": False,
        "cfg_flatten": True,
        "no_cfg_flatten": False,
        "opaque_predicates": True,
        "no_opaque_predicates": False,
        "mba_subs": True,
        "no_mba_subs": False,
        "speculation_obfuscation": False,
        "function_intent": False,
        "distributed_vm": False,
        "kernel_assist": False,
        "zk_state": False,
        "watermark": None,
        "payload": "test.py",
        "output": None,
        "verify_mutations": False,
    }


def bench_conflict_check():
    detector = ConflictDetector(KNOWN_CONFLICTS)
    flags = _make_full_flag_set()

    start = time.perf_counter()
    for _ in range(1000):
        detector.check_flags(flags)
    elapsed = time.perf_counter() - start

    print(f"Conflict check (1000 runs): {elapsed:.4f}s ({elapsed/1000*1e6:.2f}µs/run)")


def bench_graph_generation():
    g = ConflictGraph()
    for c in KNOWN_CONFLICTS:
        g.add_conflict_obj(c)

    start = time.perf_counter()
    for _ in range(1000):
        _ = g.to_dict()
    elapsed = time.perf_counter() - start
    print(f"Graph serialization (1000 runs): {elapsed:.4f}s ({elapsed/1000*1e6:.2f}µs/run)")

    start = time.perf_counter()
    for _ in range(1000):
        _ = g.generate_dot()
    elapsed = time.perf_counter() - start
    print(f"DOT generation (1000 runs): {elapsed:.4f}s ({elapsed/1000*1e6:.2f}µs/run)")


def bench_report_generation():
    detector = ConflictDetector(KNOWN_CONFLICTS)
    flags = _make_full_flag_set()
    conflicts = detector.check_flags(flags)

    start = time.perf_counter()
    for _ in range(1000):
        detector.generate_report(conflicts)
    elapsed = time.perf_counter() - start
    print(f"Report generation (1000 runs): {elapsed:.4f}s ({elapsed/1000*1e6:.2f}µs/run)")


def run_all():
    bench_conflict_check()
    bench_graph_generation()
    bench_report_generation()


if __name__ == "__main__":
    run_all()
