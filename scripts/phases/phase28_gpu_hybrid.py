"""
phase28_gpu_hybrid.py

Purpose:
Runs CPU/GPU hybrid protection.  Partitions operations between CPU and
GPU paths, executing them in parallel to create divergent execution
traces that are harder to follow and analyze.

Architectural Role:
Experimental protection phase — leverages GPU availability for
parallel obfuscation paths.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, ..common, scripts.gpu.*

Security Relevance:
GPU hybrid execution creates two distinct execution paths for the same
operation, doubling the analysis surface and confusing static/dynamic
analyzers.
"""

import json
import os
import sys
from ..common import log, BUILD_DIR


def phase_gpu_hybrid():
    """
    Initialize CPU/GPU hybrid protection.

    Partitions test operations into CPU and GPU paths, executes both,
    and writes the result manifest.

    Returns:
        dict with status and trace information
    """
    log("GPU_HYBRID", "Running CPU/GPU hybrid protection")
    log("GPU_HYBRID", "Running CPU/GPU hybrid protection")
    try:
        from scripts.gpu.gpu_execution import GPUExecutor, is_gpu_available
        from scripts.gpu.hybrid_protection import HybridProtector, cpu_obfuscation_pass, gpu_parallel_transform

        gpu_avail = is_gpu_available()
        hybrid = HybridProtector(seed=0xCAFEBABE)

        ops = [
            {"type": "crypto", "name": "encrypt_data", "data": b"test"},
            {"type": "control_flow", "name": "branch_main"},
            {"type": "key_derive", "name": "derive_key"},
        ]
        cpu_ops, gpu_ops = hybrid.partition(ops)
        log("GPU_HYBRID", f"CPU ops: {len(cpu_ops)}, GPU ops: {len(gpu_ops)}")

        test_data = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        cpu_result = hybrid.execute_cpu_path(test_data)
        gpu_result = hybrid.execute_gpu_path(test_data)
        paths_distinct = cpu_result != gpu_result

        log("GPU_HYBRID", f"GPU available: {gpu_avail}, paths distinct: {paths_distinct}")

        out_path = os.path.join(BUILD_DIR, "gpu_hybrid_result.json")
        with open(out_path, "w") as f:
            json.dump({
                "status": "ok",
                "gpu_available": gpu_avail,
                "hybrid_available": True,
                "cpu_ops": len(cpu_ops),
                "gpu_ops": len(gpu_ops),
                "paths_distinct": paths_distinct,
                "cpu_trace": hybrid.get_cpu_trace(),
                "gpu_trace": hybrid.get_gpu_trace(),
            }, f, indent=2)
        log("GPU_HYBRID", "GPU hybrid protection initialized")
    except Exception as e:
        log("SKIP", f"GPU hybrid protection not available: {e}")
