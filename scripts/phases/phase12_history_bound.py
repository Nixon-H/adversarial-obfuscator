"""
phase12_history_bound.py

Purpose:
Configures execution-history-bound decryption — a cryptographic scheme
where each fragment's decryption key depends on the hash of all prior
fragments, creating a linear chain that detects reordering or tampering.

Architectural Role:
Post-obfuscation phase.  Binds payload fragments into a hash chain and
persists the resulting state for the runtime.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
hashlib, json, os, struct, ..common, ..binding.crypto_binding

Security Relevance:
History-bound decryption ensures that fragments must be decrypted in
order — reordering or skipping is detectable at runtime.
"""

import hashlib
import json
import os
import struct

from ..common import log, BUILD_DIR


def phase_execution_history_binding(config=None):
    """
    Apply execution-history-bound decryption to payload fragments.

    Initializes the accumulator hash, fragments the payload, binds each
    fragment with a history-dependent key, and persists the state for
    runtime verification.

    Args:
        config: dict optionally containing payload_path
    """
    log("HISTORY_BOUND", "Applying execution-history-bound decryption")
    if config is None:
        config = {}
    try:
        from ..binding.crypto_binding import (
            CryptoFragmentBinder, Fragment,
        )
        log("HISTORY_BOUND", "History-bound decryption initialized")
        log("HISTORY_BOUND", "Key = HKDF(chain_secret, prev_output_hash || accumulated_hash || fragment_id || nonce)")
        log("HISTORY_BOUND", "accumulated_hash = SHA-256(accumulated_hash || output || fragment_id)")
        log("HISTORY_BOUND", "accumulated_hash initialized to SHA-256('EXECUTION_HISTORY_V1')")

        accumulator = hashlib.sha256(b"EXECUTION_HISTORY_V1").digest()
        log("HISTORY_BOUND", f"Initial accumulator: {accumulator.hex()[:16]}...")

        if config.get("payload_path"):
            with open(config["payload_path"], "rb") as f:
                data = f.read()
            chunk_size = max(32, len(data) // 4)
            fragments = [
                Fragment(fragment_id=str(i), payload=data[i:i+chunk_size])
                for i in range(0, len(data), chunk_size)
            ]
            chain_secret = os.urandom(32)
            binder = CryptoFragmentBinder(chain_secret=chain_secret, history_bound_mode=True)
            bound = binder.bind_fragments(fragments)
            log("HISTORY_BOUND", f"Bound {len(bound)} fragments with history-bound keys")

            history_state = {
                "accumulated_hash": binder._accumulated_hash.hex() if binder._accumulated_hash else None,
                "chain_secret": chain_secret.hex(),
                "num_fragments": len(bound),
                "fragment_ids": [bf.fragment_id for bf in bound],
            }
            history_path = os.path.join(BUILD_DIR, "history_bound_state.json")
            with open(history_path, "w") as f:
                json.dump(history_state, f, indent=2)
            log("HISTORY_BOUND", f"Persisted history-bound state to {history_path}")

            if len(bound) >= 2:
                swapped = [bound[1], bound[0]] + bound[2:]
                assert not binder.verify_chain(swapped), "Reorder must fail"
                log("HISTORY_BOUND", "Reorder verification: PASS (reordered chain rejected)")

        log("HISTORY_BOUND", "Execution-history-bound decryption configured")
    except Exception as e:
        log("ERROR", f"History-bound decryption failed: {e}")
        import traceback
        traceback.print_exc()
