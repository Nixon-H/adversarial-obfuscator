"""
phase14_per_exec_recompile.py

Purpose:
Configures per-execution recompilation — each invocation JIT-recompiles
a variant of the payload.  Common classes are cached; unique classes
trigger fresh compilation.

Architectural Role:
Post-build configuration phase.  Writes per_exec_recompile_config.json
for the runtime.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, ..common

Security Relevance:
Per-execution recompilation ensures each run has a unique binary layout,
defeating memory-signature and static-analysis approaches.
"""

import json
import os

from ..common import log, BUILD_DIR


def phase_per_exec_recompile(config_path=None):
    """
    Generate the per-execution recompilation configuration.

    Args:
        config_path: optional path (unused, config always goes to BUILD_DIR)
    """
    log("PER_EXEC_RECOMPILE", "Configuring per-execution recompilation")
    log("PER_EXEC_RECOMPILE", "Configuring per-execution recompilation")
    config = {
        "enabled": True,
        "classifier": "fnv1a",
        "cache_common": True,
        "common_class_threshold": 3,
        "fallback_to_generic": True,
        "emit_jit_code": True,
    }
    out_path = os.path.join(BUILD_DIR, "per_exec_recompile_config.json")
    with open(out_path, "w") as f:
        json.dump(config, f, indent=2)
    log("PER_EXEC_RECOMPILE", f"Written to {out_path}")
