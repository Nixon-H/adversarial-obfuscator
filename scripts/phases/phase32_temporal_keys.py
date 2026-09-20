"""
phase32_temporal_keys.py

Purpose:
Runs the temporal key evolution phase (Item 59).  Derives time-windowed
keys that change every N seconds, making captured keys expire quickly.

Architectural Role:
Post-obfuscation key-scheduling phase.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, secrets, ..common, scripts.binding.temporal_key

Security Relevance:
Temporal keys ensure that even if a key is extracted, it is only valid
for a short time window, limiting the window of opportunity for attack.
"""

import json
import os
import secrets

from ..common import log, atomic_write, BUILD_DIR


def phase_temporal_keys(opts) -> dict:
    """
    Derive time-windowed keys that evolve on a schedule.

    Args:
        opts: argparse.Namespace with temporal_window

    Returns:
        dict with master_key, bucket_seconds, current_bucket, key_hex
    """
    log("TEMPORAL_KEYS", "Running temporal key evolution phase (Item 59)...")
    log("TEMPORAL_KEYS", "Running temporal key evolution phase (Item 59)...")
    try:
        from scripts.binding.temporal_key import TemporalKeyEvolver
        master_key = secrets.token_bytes(32)
        window_seconds = getattr(opts, "temporal_window", 60.0)
        evolver = TemporalKeyEvolver(
            master_key=master_key,
            bucket_seconds=window_seconds,
        )
        current_key = evolver.derive_key()
        tk_config = {
            "master_key": master_key.hex(),
            "bucket_seconds": window_seconds,
            "current_bucket": evolver._get_bucket(),
            "key_hex": current_key.hex(),
            "enabled": True,
        }
        tk_config_path = os.path.join(BUILD_DIR, "temporal_key_config.json")
        atomic_write(tk_config_path, json.dumps(tk_config, indent=2))
        log("TEMPORAL_KEYS", f"Key derived for bucket {tk_config['current_bucket']}")
        return tk_config
    except Exception as e:
        log("ERROR", f"Temporal key phase failed: {e}")
        raise
