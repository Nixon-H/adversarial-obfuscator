"""
phase_kernel_assist.py

Purpose:
Detects kernel-level capabilities (e.g., anonymous page protections,
seccomp, perf events) and configures the runtime to use them for
hardware-assisted protection.

Architectural Role:
Research phase — probes kernel features and generates a capabilities
manifest for the runtime.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, logging, os, ..common, ..kernel_assist.*

Security Relevance:
Kernel-assisted features provide OS-backed protection that is harder
to bypass than user-space-only protections.
"""

from __future__ import annotations

import json
import logging
import os

from ..common import BUILD_DIR, log

logging.basicConfig(level=logging.INFO)


def phase_kernel_assist(args, ir_module=None):
    """Kernel-Assisted Execution Research phase.

    Runtime detection of kernel capabilities, generates runtime config
    with available features, wires MemoryGuard configuration for
    protected regions, and generates kernel assist manifest.

    Never fails - always has fallback when kernel features unavailable.

    Args:
        args: argparse namespace with .kernel_assist and .kernel_assist_features.
        ir_module: Optional IR module (unused, kept for interface compat).

    Returns:
        dict with manifest info describing available features.
    """
    from ..kernel_assist.detector import detect_kernel_capabilities
    from ..kernel_assist.executor import KernelAssistedExecutor

    log("KERNEL_ASSIST", "Kernel-assisted execution research enabled")

    caps = detect_kernel_capabilities()
    caps_dict = caps.to_dict()
    available = [k for k, v in caps_dict.items() if v]
    unavailable = [k for k, v in caps_dict.items() if not v]

    log("KERNEL_ASSIST", f"Detected capabilities: {available or 'none'}")
    if unavailable:
        log("KERNEL_ASSIST", f"Unavailable features: {unavailable}")

    feature_filter = getattr(args, 'kernel_assist_features', None)
    enabled_features = {}
    if feature_filter:
        requested = set(f.strip().lower() for f in feature_filter.split(',') if f.strip())
        for feat in requested:
            if feat in caps_dict:
                enabled_features[feat] = caps_dict[feat]
                log("KERNEL_ASSIST", f"  Feature '{feat}': {'available' if caps_dict[feat] else 'UNAVAILABLE'}")
            else:
                log("KERNEL_ASSIST", f"  Feature '{feat}': UNKNOWN (ignored)")
    else:
        enabled_features = dict(caps_dict)

    executor = KernelAssistedExecutor(caps)
    log("KERNEL_ASSIST", f"Executor features: {executor.supported_features() or 'fallback only'}")
    log("KERNEL_ASSIST", f"Executor available: {executor.is_available()}")

    manifest = {
        'enabled': True,
        'capabilities': caps_dict,
        'available_features': available,
        'unavailable_features': unavailable,
        'enabled_features': enabled_features,
        'executor_available': executor.is_available(),
        'executor_features': executor.supported_features(),
        'fallback_active': len(available) == 0,
    }

    manifest_path = os.path.join(BUILD_DIR, 'kernel_assist_manifest.json')
    try:
        os.makedirs(BUILD_DIR, exist_ok=True)
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2, default=str)
        log("KERNEL_ASSIST", f"Manifest written to {manifest_path}")
    except Exception as e:
        log("KERNEL_ASSIST", f"Failed to write manifest: {e}")

    if available:
        log("KERNEL_ASSIST",
            f"Kernel-assisted execution: {len(available)} feature(s) available")
    else:
        log("KERNEL_ASSIST",
            "Kernel-assisted execution: NO features available, using plain fallback")

    return manifest
