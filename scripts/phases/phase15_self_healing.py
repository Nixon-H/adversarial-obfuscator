"""
phase15_self_healing.py

Purpose:
Configures the runtime's self-healing subsystem — redundant code copies
that can repair tampered regions on-the-fly.

Architectural Role:
Post-build configuration phase.  Writes self_healing_config.json for
the runtime.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, ..common

Security Relevance:
Self-healing allows the payload to recover from targeted modifications
and maintain integrity during execution.
"""

import json
import os

from ..common import log, BUILD_DIR


def phase_self_healing(config_path=None):
    """
    Generate the self-healing runtime configuration.

    Args:
        config_path: optional path (unused)
    """
    log("SELF_HEALING", "Configuring self-healing runtime")
    config = {
        "enabled": True,
        "num_redundant_copies": 3,
        "max_regions": 32,
        "verify_interval_ms": 1000,
        "heal_on_verify": True,
    }
    out_path = os.path.join(BUILD_DIR, "self_healing_config.json")
    with open(out_path, "w") as f:
        json.dump(config, f, indent=2)
    log("SELF_HEALING", f"Written to {out_path}")
