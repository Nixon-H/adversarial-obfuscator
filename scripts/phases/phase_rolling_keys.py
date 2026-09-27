"""
phase_rolling_keys.py

Purpose:
Configures rolling key schedules for fragment chains.  Each fragment
in the chain has a unique key derived from its predecessor, creating
a key chain that detects reordering and tampering.

Architectural Role:
Post-obfuscation key-binding phase.  Produces rolling_keys_config.json.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
hashlib, json, os, struct, ..common, ..binding.crypto_binding

Security Relevance:
Rolling keys ensure that fragments must be decrypted in order —
reordering is immediately detected.
"""

import hashlib
import json
import os
import struct
from ..common import log, BUILD_DIR
from ..binding.crypto_binding import CryptoFragmentBinder, Fragment


def phase_rolling_keys(payload_path=None):
    """
    Set up rolling key schedules for fragment chains.

    Args:
        payload_path: optional path to payload for fragment binding
    """
    log("ROLLING_KEYS", "Configuring rolling key schedules")
    chain_secret = os.urandom(32)
    binder = CryptoFragmentBinder(chain_secret=chain_secret, rolling_key_mode=True)
    if payload_path and os.path.exists(payload_path):
        with open(payload_path, "rb") as f:
            data = f.read()
        chunk_size = max(32, len(data) // 4)
        fragments = [
            Fragment(fragment_id=str(i), payload=data[i:i+chunk_size])
            for i in range(0, len(data), chunk_size)
        ]
        bound = binder.bind_fragments(fragments)
        assert binder.verify_chain(bound), "Rolling key chain verification must pass"
        log("ROLLING_KEYS", f"Bound {len(bound)} fragments with rolling keys")
        if len(bound) >= 2:
            swapped = [bound[1], bound[0]] + bound[2:]
            assert not binder.verify_chain(swapped), "Reorder must fail with rolling keys"
            log("ROLLING_KEYS", "Rolling key reorder detection: PASS")
    else:
        fragments = [
            Fragment(fragment_id=str(i), payload=b"test_data_" + str(i).encode())
            for i in range(4)
        ]
        bound = binder.bind_fragments(fragments)
        assert binder.verify_chain(bound), "Rolling key chain must verify"
        log("ROLLING_KEYS", f"Bound {len(bound)} test fragments with rolling keys")

    rolling_config = {
        "chain_secret": chain_secret.hex(),
        "rolling_key_mode": True,
        "num_fragments": len(bound),
        "fragment_ids": [bf.fragment_id for bf in bound],
        "roll_counter": binder._roll_counter,
        "rolling_key": binder._rolling_key.hex() if binder._rolling_key else None,
    }
    config_path = os.path.join(BUILD_DIR, "rolling_keys_config.json")
    with open(config_path, "w") as f:
        json.dump(rolling_config, f, indent=2)
    log("ROLLING_KEYS", f"Rolling key state persisted to {config_path}")
    log("ROLLING_KEYS", "Rolling key schedules configured successfully")
