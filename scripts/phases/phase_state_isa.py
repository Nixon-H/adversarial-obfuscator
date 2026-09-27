"""
phase_state_isa.py

Purpose:
Generates a state-dependent instruction set architecture (ISA)
configuration — the opcode meanings change based on execution history,
making static disassembly meaningless.

Architectural Role:
Post-IR ISA-generation phase.  Produces state_isa_config.json for runtime.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
hashlib, json, os, struct, ..common

Security Relevance:
State-dependent ISA means the same byte sequence decodes to different
instructions depending on execution history, defeating linear disassembly.
"""

import hashlib
import json
import os
import struct

from ..common import log, BUILD_DIR


def generate_state_rotation_schedule(seed: int) -> list[int]:
    """
    Deterministically generate a 16-entry rotation threshold schedule.

    Args:
        seed: RNG seed

    Returns:
        list of 16 threshold integers
    """
    rng_seed = seed
    schedule = []
    for i in range(16):
        data = hashlib.sha256(struct.pack("<QQ", rng_seed, i)).digest()
        val = struct.unpack("<Q", data[:8])[0]
        threshold = (val % 0xFFFFFFFF) | 0x10000000
        schedule.append(threshold)
        rng_seed = (rng_seed * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
    return schedule


def phase_state_isa(history_len: int = 8, seed: int = 0):
    """
    Generate the state-dependent ISA configuration.

    Args:
        history_len: how many prior instructions affect decoding
        seed: RNG seed for rotation schedule

    Returns:
        dict with ISA config
    """
    log("STATE_ISA", f"Generating state-dependent ISA config (history len: {history_len})")
    schedule = generate_state_rotation_schedule(seed)
    config = {
        "history_len": history_len,
        "seed": seed,
        "rotation_schedule": schedule,
        "schedule_len": len(schedule),
        "enabled": True,
    }
    config_path = os.path.join(BUILD_DIR, "state_isa_config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    log("STATE_ISA", f"Rotation schedule ({len(schedule)} thresholds) written to {config_path}")
    return config
