"""
mutation.py

Purpose:
Opcode-level mutation and fusion (Advanced Protection). Provides seeded
permutation of opcode assignments, handler reordering for instruction
dispatch, and fusion/splitting of VM operations. Each build produces a
different opcode mapping and handler permutation.

Architectural Role:
Pre-build mutation pass for the Nixon VM bytecode. Changes the physical
opcode assignments and handler dispatch order so that the same logical
bytecode produces different instruction encoding in each build.

Security Relevance:
- Opcode mutation: each logical opcode maps to a different physical value
  per build, preventing opcode-based signatures.
- Handler permutation: instruction dispatch order within the VM handler
  loop is shuffled, making control-flow signatures non-portable.
- Fusion/splitting: adjacent VM operations can be fused into single
  compound operations or split into multiple steps, changing the
  instruction-level execution trace.

Threat model: Binary diffing, VM opcode recovery, signature detection.

Dependencies:
    - irgen.compile (IrModule)
    - vm.vm_isa (VMOpcode)
    - config/default.json (for phase2 gate)
"""

from __future__ import annotations
import hashlib
import json
import os
import struct



def _phase2_enabled() -> bool:
    """Check if phase2 (advanced protection) is enabled in config."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "default.json")
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        return cfg.get("shadow_compiler", {}).get("advanced_protection", cfg.get("shadow_compiler", {}).get("phase2", {})).get("enabled", False)
    except (FileNotFoundError, json.JSONDecodeError):
        return False


_L1_OPCODES = [
    "NOP", "ADD", "SUB", "MUL", "DIV", "MOD",
    "AND", "OR", "XOR", "NOT", "SHL", "SHR",
    "LOAD", "STORE", "MOV", "LEA",
    "JMP", "JZ", "JNZ", "JG", "JL", "JGE", "JLE",
    "CALL", "RET", "PUSH", "POP", "ENTER", "LEAVE",
    "ENC_LOAD", "ENC_STORE", "ENC_ADD", "ENC_MUL",
    "FUSED_LOAD_ADD_STORE", "FUSED_CMP_JMP",
]


def generate_opcode_map(seed: bytes, num_opcodes: int = 256) -> dict[int, int]:
    """
    Generate a seeded permutation of opcode assignments.

    Uses a SHA-256-based Fisher-Yates shuffle to deterministically
    permute the opcode space. Each logical opcode maps to a unique
    physical value.

    Args:
        seed: Build seed for deterministic permutation.
        num_opcodes: Size of the opcode space (default 256).

    Returns:
        Dict mapping logical opcode index -> physical opcode value.
    """
    if not _phase2_enabled():
        raise RuntimeError("Advanced Protection (IR mutation) is disabled in config")

    rng_state = bytearray(hashlib.sha256(seed).digest())

    values = list(range(num_opcodes))
    for i in range(num_opcodes - 1, 0, -1):
        rng_state = bytearray(hashlib.sha256(bytes(rng_state)).digest())
        j = struct.unpack('<I', rng_state[:4])[0] % (i + 1)
        values[i], values[j] = values[j], values[i]

    logical_map = {}
    for idx, name in enumerate(_L1_OPCODES):
        if idx < num_opcodes:
            logical_map[idx] = values[idx]

    return logical_map


def remap_bytecode(bytecode: bytearray, opcode_map: dict[int, int]) -> bytearray:
    """
    Remap bytecode opcodes using the given opcode map.

    Each byte in the input bytecode is mapped through the inverse
    of the opcode map to find its logical opcode, then through
    the forward map to its new physical value.
    """
    if len(bytecode) == 0:
        return bytearray(bytecode)

    remapped = bytearray(len(bytecode))
    inverse = {v: k for k, v in opcode_map.items()}

    i = 0
    while i < len(bytecode):
        raw_op = bytecode[i]
        logical = inverse.get(raw_op, raw_op)
        physical = opcode_map.get(logical, raw_op)
        remapped[i] = physical & 0xFF
        i += 1

    return remapped


def permute_handler(
    handler_ops: list[str],
    seed: bytes,
) -> list[str]:
    """
    Permute the order of handler operations for VM dispatch.

    Groups operations into categories (loads, computes, stores,
    advance, movable) and shuffles each group independently before
    concatenating in a fixed order. This preserves the semantics
    (all loads before computes before stores) while changing the
    internal order within each group.
    """
    if not _phase2_enabled():
        raise RuntimeError("Advanced Protection (IR mutation) is disabled in config")

    loads = [op for op in handler_ops if "load" in op.lower()]
    computes = [op for op in handler_ops if "compute" in op.lower()]
    stores = [op for op in handler_ops if "store" in op.lower() or "writeback" in op.lower()]
    advance = [op for op in handler_ops if "advance" in op.lower() or "pc" in op.lower()]
    movable = [op for op in handler_ops if op not in set(loads + computes + stores + advance)]

    rng_state = bytearray(hashlib.sha256(seed).digest())

    def shuffle(items):
        """Fisher-Yates shuffle using SHA-256 for randomness."""
        nonlocal rng_state
        items = list(items)
        for i in range(len(items) - 1, 0, -1):
            rng_state = bytearray(hashlib.sha256(bytes(rng_state)).digest())
            j = struct.unpack('<I', rng_state[:4])[0] % (i + 1)
            items[i], items[j] = items[j], items[i]
        return items

    shuffled_loads = shuffle(loads)
    shuffled_computes = shuffle(computes)
    shuffled_stores = shuffle(stores)
    shuffled_advance = shuffle(advance)
    shuffled_movable = shuffle(movable)

    result = []
    for item in shuffled_movable:
        result.append(item)

    for item in shuffled_loads:
        result.append(item)

    for item in shuffled_advance:
        result.append(item)

    for item in shuffled_computes:
        result.append(item)

    for item in shuffled_stores:
        result.append(item)

    return result


def generate_handler_variants(
    handler_template: list[str],
    num_variants: int = 8,
    seed: bytes = None,
) -> list[list[str]]:
    """
    Generate multiple handler permutation variants.

    Each variant uses a different seed derived from the base seed
    and variant index.
    """
    if not _phase2_enabled():
        raise RuntimeError("Advanced Protection (IR mutation) is disabled in config")

    if seed is None:
        seed = os.urandom(32)

    variants = []
    for i in range(num_variants):
        variant_seed = hashlib.sha256(seed + struct.pack('<I', i)).digest()
        variant = permute_handler(handler_template, variant_seed)
        variants.append(variant)

    return variants


def generate_fusion_plan(
    seed: bytes,
    available_opcodes: list[tuple[str, str]] | None = None,
) -> list[dict]:
    """
    Generate a plan for fusing and splitting VM operations.

    Selects a random subset of opcode pairs to fuse into compound
    operations, and randomly selects individual opcodes to split
    into multiple steps.

    Returns a list of dicts with 'type' ('fuse' or 'split') and
    relevant opcode information.
    """
    if not _phase2_enabled():
        raise RuntimeError("Advanced Protection (IR mutation) is disabled in config")

    if available_opcodes is None:
        available_opcodes = [
            ("LOAD", "ADD"),
            ("LOAD", "STORE"),
            ("ADD", "STORE"),
            ("SUB", "STORE"),
            ("XOR", "ROT"),
            ("CMP", "JMP"),
            ("MUL", "ADD"),
        ]

    rng_state = bytearray(hashlib.sha256(seed).digest())

    def rand(max_val):
        """Deterministic random integer using SHA-256."""
        nonlocal rng_state
        rng_state = bytearray(hashlib.sha256(bytes(rng_state)).digest())
        return struct.unpack('<I', rng_state[:4])[0] % max_val

    plan = []

    shuffle_indices = list(range(len(available_opcodes)))
    for i in range(len(shuffle_indices) - 1, 0, -1):
        rng_state = bytearray(hashlib.sha256(bytes(rng_state)).digest())
        j = struct.unpack('<I', rng_state[:4])[0] % (i + 1)
        shuffle_indices[i], shuffle_indices[j] = shuffle_indices[j], shuffle_indices[i]

    num_fusions = min(rand(4) + 1, len(available_opcodes))
    for i in range(num_fusions):
        idx = shuffle_indices[i]
        ops = list(available_opcodes[idx])
        fused_name = "_".join(ops)
        plan.append({
            "type": "fuse",
            "ops": ops,
            "new_op": fused_name,
        })

    split_candidates = ["MUL", "DIV", "LOAD"]
    split_parts_map = {
        "MUL": ["SHL_ADD", "SHL_ADD", "SHL_ADD"],
        "DIV": ["SUB", "CMP", "JMP"],
        "LOAD": ["MOV", "LOAD"],
    }

    for op in split_candidates:
        if rand(3) == 0:
            parts = split_parts_map.get(op, [op])
            plan.append({
                "type": "split",
                "op": op,
                "parts": parts,
            })

    return plan


def apply_fusion_plan(
    bytecode: bytearray,
    fusion_plan: list[dict],
    opcode_map: dict,
) -> bytearray:
    """
    Apply a fusion plan to remap bytecode.

    Currently a stub; the actual fusion/splitting logic requires
    a more detailed understanding of each opcode's operand layout.
    Returns the bytecode unchanged for now.
    """
    if not _phase2_enabled():
        raise RuntimeError("Advanced Protection (IR mutation) is disabled in config")



    result = bytearray(bytecode)

    for decision in fusion_plan:
        if decision["type"] == "fuse":
            pass

        elif decision["type"] == "split":
            pass

    return result


def mutate_instruction_universe(
    bytecode: bytearray,
    seed: bytes,
    level: int = 3,
) -> tuple[bytearray, dict]:
    """
    Apply all mutation transformations at the specified level.

    Level 1: opcode map permutation only.
    Level 2: adds handler permutation.
    Level 3: adds fusion/splitting plan.

    Returns the mutated bytecode and metadata describing the mutations.
    """
    if not _phase2_enabled():
        raise RuntimeError("Advanced Protection (IR mutation) is disabled in config")

    metadata = {
        "level": level,
        "opcode_map": {},
        "handler_permutations": {},
        "fusion_plan": [],
    }

    opcode_map = generate_opcode_map(seed)
    metadata["opcode_map"] = opcode_map

    bytecode = remap_bytecode(bytecode, opcode_map)

    if level >= 2:
        from vm.vm_isa import VMOpcode
        handler_templates = {}
        for logical, name in VMOpcode.LOGICAL_NAMES.items():
            handler_templates[logical] = [
                f"load_{name.lower()}",
                f"compute_{name.lower()}",
                f"store_{name.lower()}",
                f"advance_pc_{name.lower()}",
            ]

        for opcode, template in handler_templates.items():
            variant_seed = hashlib.sha256(seed + struct.pack('<I', opcode)).digest()
            permutation = permute_handler(template, variant_seed)
            metadata["handler_permutations"][opcode] = permutation

    if level >= 3:
        fusion_plan = generate_fusion_plan(seed)
        metadata["fusion_plan"] = fusion_plan
        bytecode = apply_fusion_plan(bytecode, fusion_plan, opcode_map)

    return bytecode, metadata


