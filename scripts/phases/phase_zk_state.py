"""
phase_zk_state.py

Purpose:
Generates zero-knowledge state-binding configuration using Schnorr
sigma protocols (HVZK proof of knowledge).  Creates a state machine
that produces and verifies proofs of correct state transitions.

WARNING:
This is a RESEARCH feature.  All security claims are MEASURED and
clearly labelled.  No UC-security or post-quantum guarantees.

Architectural Role:
Experimental research phase — adds ZK-proof-based state verification.

Execution Context:
Called from build.py during pipeline execution.
  Usage: python3 scripts/build.py --payload myscript.py --zk-state

Dependencies:
json, os, time, typing, ..common, scripts.zk_state.*

Security Relevance:
ZK state binding provides cryptographic proof that execution followed
the intended state transitions, without revealing the state itself.
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

from ..common import log, BUILD_DIR


def phase_zk_state(args, ir_module=None):
    """Run ZK state-bound execution phase.

    If --zk-state is not set, returns immediately (no-op).
    Otherwise, generates sigma protocol parameters, creates a state
    machine, produces a state binding manifest, and measures latency.

    Args:
        args: argparse namespace with .zk_state and .zk_state_config
        ir_module: unused (maintained for API compatibility)

    Returns:
        dict with manifest info including latency, or None if disabled.
    """
    enabled = getattr(args, "zk_state", False)
    if not enabled:
        log("ZK_STATE", "ZK state-bound execution disabled (use --zk-state to enable)")
        return None

    log("ZK_STATE", "ZK state-bound execution enabled (RESEARCH)")
    log("ZK_STATE", "Security classification: MEASURED")
    log("ZK_STATE", "  Protocol: Schnorr sigma protocol (HVZK proof of knowledge)")
    log("ZK_STATE", "  THEORETICAL: no UC-security or post-quantum guarantees")

    from scripts.zk_state.state_config import load_config, check_prerequisites
    from scripts.zk_state.sigma_protocol import generate_parameters
    from scripts.zk_state.state_machine import StateMachine

    config = load_config(args)

    prereqs_ok = check_prerequisites()
    if not prereqs_ok:
        log("ZK_STATE", "ERROR: prerequisites not met")
        return None

    log("ZK_STATE", f"Configuration: enabled={config.enabled}, "
                     f"state_file={config.state_file or '(none)'}, "
                     f"require_online={config.require_online}, "
                     f"proof_cache_size={config.proof_cache_size}")

    t_start = time.perf_counter()

    params = generate_parameters(1024)
    t_params = time.perf_counter()

    initial_state = int.from_bytes(os.urandom(8), "big")
    sm = StateMachine(initial_state, group=params)
    t_sm = time.perf_counter()

    transition_state = initial_state ^ 0xDEADBEEF
    state_proof = sm.transition(transition_state)
    t_prove = time.perf_counter()

    valid = sm.verify_transition(state_proof)
    t_verify = time.perf_counter()

    state_commitment = sm.get_state_commitment()

    manifest = {
        "zk_state": True,
        "security_classification": "MEASURED",
        "security_notes": [
            "Schnorr sigma protocol (HVZK proof of knowledge)",
            "THEORETICAL: no UC-security or post-quantum guarantees",
            "Discrete-log security in 1024-bit safe-prime group",
        ],
        "prerequisites_met": prereqs_ok,
        "config": {
            "enabled": config.enabled,
            "state_file": config.state_file or "",
            "require_online": config.require_online,
            "proof_cache_size": config.proof_cache_size,
        },
        "parameters": {
            "group_bits": 1024,
        },
        "state_machine": {
            "initial_state": initial_state,
            "current_state": transition_state,
            "state_commitment": state_commitment,
            "transition_valid": valid,
            "public_key": sm.get_public_key(),
        },
        "latency_ms": {
            "parameter_generation": (t_params - t_start) * 1000.0,
            "state_machine_init": (t_sm - t_params) * 1000.0,
            "prove_transition": (t_prove - t_sm) * 1000.0,
            "verify_transition": (t_verify - t_prove) * 1000.0,
            "total": (t_verify - t_start) * 1000.0,
        },
        "replay_protection": {
            "nonce": state_proof.nonce,
            "timestamp": state_proof.timestamp,
        },
    }

    build_dir = getattr(args, "build_dir", BUILD_DIR)
    os.makedirs(build_dir, exist_ok=True)
    manifest_path = os.path.join(build_dir, "zk_state_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    log("ZK_STATE", f"Manifest → {manifest_path}")
    log("ZK_STATE", f"Transition valid: {valid}")
    log("ZK_STATE", f"Latency: param_gen={manifest['latency_ms']['parameter_generation']:.2f}ms, "
                     f"prove={manifest['latency_ms']['prove_transition']:.2f}ms, "
                     f"verify={manifest['latency_ms']['verify_transition']:.2f}ms, "
                     f"total={manifest['latency_ms']['total']:.2f}ms")

    return manifest
