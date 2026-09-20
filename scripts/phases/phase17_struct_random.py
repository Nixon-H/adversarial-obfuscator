"""
phase17_struct_random.py

Purpose:
Configures structure randomization — stack slots, register allocation,
and heap layout are randomized at runtime, making each execution have
a unique memory layout.

Architectural Role:
Post-build configuration phase.  Writes struct_randomization_config.json
for the runtime.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, ..common, hashlib, struct

Security Relevance:
Structure randomization defeats attacks that depend on predictable
memory layouts (ASLR bypass, ROP gadget chaining).
"""

import json
import os

from ..common import log, BUILD_DIR


def phase_struct_randomization(seed=None, level=3):
    """
    Generate the structure randomization configuration.

    Args:
        seed: optional RNG seed (derived from hash of "struct_random_default")
        level: randomization intensity (1-10)
    """
    log("STRUCT_RANDOM", f"Configuring structure randomization (level {level})")
    log("STRUCT_RANDOM", f"Configuring structure randomization (level {level})")
    import hashlib
    import struct

    if seed is None:
        seed = struct.unpack("<Q", hashlib.sha256(b"struct_random_default").digest()[:8])[0]

    config = {
        "enabled": True,
        "seed": seed,
        "level": level,
        "randomize_stack_slots": True,
        "randomize_register_allocation": True,
        "randomize_heap_layout": True,
        "max_fields": 64,
    }
    out_path = os.path.join(BUILD_DIR, "struct_randomization_config.json")
    with open(out_path, "w") as f:
        json.dump(config, f, indent=2)
    log("STRUCT_RANDOM", f"Written to {out_path} (seed={seed:#018x})")
