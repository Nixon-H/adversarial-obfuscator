"""
phase33_payload_dispersal.py

Purpose:
Splits the payload into N shares using Shamir-style dispersal (Item 69).
Any threshold of shares is sufficient to reconstruct, preventing single-
point-of-failure extraction.

Architectural Role:
Final payload protection phase — produces dispersal config for runtime.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, secrets, ..common, scripts.dispersal.payload_dispersal

Security Relevance:
Payload dispersal ensures that no single extracted fragment reveals
the complete payload; threshold reconstruction prevents single-point
compromise.
"""

import json
import os
import secrets

from ..common import log, atomic_write, BUILD_DIR


def phase_payload_dispersal(payload_path: str, opts) -> dict:
    """
    Disperse the payload into threshold-protected shares.

    Args:
        payload_path: path to the payload binary
        opts: argparse.Namespace with dispersal_slices

    Returns:
        dict with num_shares, threshold, share_indices, mmap_addresses
    """
    log("PAYLOAD_DISPERSAL", "Running payload dispersal phase (Item 69)...")
    try:
        from scripts.dispersal.payload_dispersal import PayloadDispersal
        with open(payload_path, "rb") as f:
            payload = f.read()
        num_shares = getattr(opts, "dispersal_slices", 3)
        threshold = (num_shares // 2) + 1
        disperser = PayloadDispersal(seed=secrets.randbits(32))
        shares = disperser.disperse(payload, num_shares=num_shares, threshold=threshold)
        pd_config = {
            "num_shares": len(shares),
            "threshold": threshold,
            "share_indices": [s.index for s in shares],
            "mmap_addresses": [hex(s.mmap_addr) for s in shares],
            "seed": disperser.seed,
            "enabled": True,
        }
        pd_config_path = os.path.join(BUILD_DIR, "payload_dispersal_config.json")
        atomic_write(pd_config_path, json.dumps(pd_config, indent=2))
        log("PAYLOAD_DISPERSAL", f"Split into {len(shares)} shares (threshold={threshold})")
        return pd_config
    except Exception as e:
        log("ERROR", f"Payload dispersal phase failed: {e}")
        raise
