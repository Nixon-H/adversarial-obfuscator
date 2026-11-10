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
        dict with bucket_seconds, current_bucket, enabled -- scheduling
        metadata only; no key material is returned or written to disk
    """
    log("TEMPORAL_KEYS", "Running temporal key evolution phase (Item 59)...")
    try:
        from scripts.binding.temporal_key import TemporalKeyChain
        master_key = secrets.token_bytes(32)
        window_seconds = getattr(opts, "temporal_window", 60.0)
        chain = TemporalKeyChain(
            genesis_secret=master_key,
            window_seconds=window_seconds,
        )
        current_key = chain.derive_key_for_window()
        # No key material on disk.
        #
        # This file used to carry "master_key" (the genesis secret, hex) and
        # "key_hex" (the derived window key). Both are the thing the temporal
        # chain exists to protect, and neither had a reader: grepping for
        # temporal_key_config.json finds only this write. So the build printed
        # the secrets to a file in build/ that nothing consumed -- a leak with
        # no benefit at all.
        #
        # What remains is scheduling metadata: which bucket, how long a bucket
        # is, whether the feature was on. That is safe to write and it is what
        # any future consumer would actually need to locate the window.
        tk_config = {
            "bucket_seconds": window_seconds,
            "current_bucket": current_key.index,
            "enabled": True,
        }
        tk_config_path = os.path.join(BUILD_DIR, "temporal_key_config.json")
        atomic_write(tk_config_path, json.dumps(tk_config, indent=2))
        log("TEMPORAL_KEYS", f"Key derived for bucket {tk_config['current_bucket']}")
        return tk_config
    except Exception as e:
        log("ERROR", f"Temporal key phase failed: {e}")
        raise
