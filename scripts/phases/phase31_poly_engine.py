"""
phase31_poly_engine.py

Purpose:
Runs the poly-engine phase (Item 58) — profiles the build environment,
then encrypts the payload with an environment-specific key so that it
can only be decrypted in a matching environment.

Architectural Role:
Post-obfuscation environment-binding phase.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, secrets, ..common, scripts.poly.poly_engine

Security Relevance:
Environment-bound encryption ensures the payload will not run correctly
in any environment that differs from the original build target.
"""

import json
import os
import secrets

from ..common import log, atomic_write, BUILD_DIR


def phase_poly_engine(payload_path: str, opts) -> dict:
    """
    Profile the environment and encrypt the payload for that environment.

    Args:
        payload_path: path to the payload source file
        opts: argparse.Namespace

    Returns:
        dict with environment profile and decrypt code
    """
    log("POLY_ENGINE", "Running poly-engine phase (Item 58)...")
    log("POLY_ENGINE", "Running poly-engine phase (Item 58)...")
    try:
        from scripts.poly.poly_engine import PolyEngine
        pe = PolyEngine(seed=secrets.randbits(32))
        profile = pe.get_environment_profile()
        with open(payload_path, encoding="utf-8") as f:
            code = f.read()
        encrypted = pe.encrypt_for_environment(code.encode("utf-8"))
        poly_config = {
            "environment_profile": profile,
            "fingerprint": profile["fingerprint"],
            "encrypted_len": len(encrypted["ciphertext"]),
            "decrypt_code": encrypted["decrypt_code"],
            "enabled": True,
        }
        poly_config_path = os.path.join(BUILD_DIR, "poly_engine_config.json")
        atomic_write(poly_config_path, json.dumps(poly_config, indent=2))
        log("POLY_ENGINE", f"Profile: {profile['os']} / {profile['arch']} / {profile['fingerprint'][:16]}...")
        return poly_config
    except Exception as e:
        log("ERROR", f"Poly-engine phase failed: {e}")
        raise
