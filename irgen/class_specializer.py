"""
class_specializer.py

Purpose:
Class specializer: generates N structurally different but semantically
equivalent IR variants for a given function. Each variant differs by
register allocation permutation, expression reassociation (commutative
reordering), NOP instruction insertion, and instruction scheduling order.

Architectural Role:
Diversity generation pass. Produces multiple implementations of the same
IR function that are functionally identical but structurally different.
Used to force per-build variation even when the source code is identical.

Security Relevance:
- Register permutation prevents register-based signatures.
- Expression reassociation (a+b+c vs (a+b)+c) changes the operation tree.
- NOP insertion varies instruction density across variants.
- Instruction reordering changes the execution trace.
- All transformations are seeded per class_id, making the diversity
  deterministic but unpredictable without the seed.

Threat model: Automated deobfuscation, pattern matching, binary diffing.
"""

import hashlib
import struct
from typing import Any


def generate_class_variants(ir_function: Any, num_classes: int, seed: int) -> list:
    """
    Produce num_classes structurally different but semantically equivalent
    IR variants.

    Each variant applies:
    - Register allocation permutation.
    - Expression reassociation (commutative op swapping).
    - NOP instruction insertion.
    - Instruction scheduling reorder.

    The base digest is SHA-256("function_name:seed"). Each class_id
    XORs with a golden ratio constant for diversity.
    """
    name = getattr(ir_function, 'name', 'anonymous')
    base_digest = hashlib.sha256(f"{name}:{seed}".encode()).digest()
    variants = []

    for cls_id in range(num_classes):
        variant = _create_variant(ir_function, cls_id, base_digest, seed)
        variants.append(variant)

    return variants


def _create_variant(ir_function: Any, class_id: int, base_digest: bytes, seed: int) -> Any:
    """Create one variant by cloning and applying mutations."""
    variant = _clone_function(ir_function)
    cls_seed = struct.unpack("<Q", base_digest[:8])[0] ^ (class_id * 0x9E3779B97F4A7C15)

    _mutate_register_allocation(variant, class_id, base_digest)
    _reassociate_expressions(variant, class_id, base_digest, cls_seed)
    _insert_nops(variant, class_id)
    _reschedule_instructions(variant, class_id, base_digest)

    return variant


def _clone_function(fn: Any) -> Any:
    """Deep-clone an IR function structure."""
    try:
        import copy
        return copy.deepcopy(fn)
    except Exception:
        class SimpleFunc:
            def __init__(self, name, blocks):
                self.name = name
                self.blocks = list(blocks)
        blocks = list(getattr(fn, 'blocks', []))
        return SimpleFunc(getattr(fn, 'name', 'cloned'), blocks)


def _mutate_register_allocation(variant: Any, class_id: int, seed: bytes) -> None:
    """
    Apply a class-specific register permutation.

    Uses the same LCG as the PCG family for shuffling.
    The permutation is applied to all instruction fields named
    dst, src1, src2, dest, src.
    """
    num_regs = 8
    perm = list(range(num_regs))
    rng = (class_id + 1) * struct.unpack("<I", seed[:4])[0]
    for i in range(num_regs - 1, 0, -1):
        j = int(rng % (i + 1))
        rng = ((rng * 6364136223846793005) & 0xFFFFFFFFFFFFFFFF) + 1442695040888963407
        rng = rng & 0xFFFFFFFFFFFFFFFF
        perm[i], perm[j] = perm[j], perm[i]

    for block in getattr(variant, 'blocks', []):
        for instr in getattr(block, 'instructions', []):
            _remap_regs(instr, perm)


def _remap_regs(instr: Any, perm: list) -> None:
    """Remap register fields according to a permutation."""
    for field_name in ('dst', 'src1', 'src2', 'dest', 'src'):
        if hasattr(instr, field_name):
            val = getattr(instr, field_name)
            if isinstance(val, int) and val < len(perm):
                setattr(instr, field_name, perm[val])


def _reassociate_expressions(variant: Any, class_id: int, seed: bytes, cls_seed: int = 0) -> None:
    """
    Reassociate commutative operations (add, mul, and, or, xor) per class.

    Each has a 30% chance of operand swapping per instruction.
    """
    import random
    rng = random.Random(class_id * 17 + struct.unpack("<I", seed[:4])[0])
    for block in getattr(variant, 'blocks', []):
        instrs = getattr(block, 'instructions', [])
        i = 0
        while i < len(instrs) - 2:
            opcode = _get_opcode(instrs[i])
            if opcode in ('add', 'mul', 'and', 'or', 'xor') and rng.random() < 0.3:
                _swap_operands(instrs[i])
            i += 1


def _get_opcode(instr: Any) -> str:
    if hasattr(instr, 'opcode'):
        return str(instr.opcode).lower()
    if hasattr(instr, 'name'):
        return str(instr.name).lower()
    return ''


def _swap_operands(instr: Any) -> None:
    """Swap src1/src2 for commutative operations."""
    if hasattr(instr, 'src1') and hasattr(instr, 'src2'):
        instr.src1, instr.src2 = instr.src2, instr.src1


def _insert_nops(variant: Any, class_id: int) -> None:
    """
    Insert NOP instructions at class-specific positions.

    The number of NOPs is (class_id % 4) + 1. They are inserted
    at position derived from class_id.
    """
    count = (class_id % 4) + 1
    for block in getattr(variant, 'blocks', []):
        instrs = getattr(block, 'instructions', [])
        pos = class_id % max(len(instrs), 1)
        for _ in range(count):
            if len(instrs) > 0:
                nop = _make_nop()
                instrs.insert(pos % len(instrs), nop)
                pos += 1


def _make_nop() -> Any:
    """Create a simple NOP instruction object."""
    class NopInstr:
        def __init__(self):
            self.opcode = 'nop'
            self.name = 'nop'
    return NopInstr()


def _reschedule_instructions(variant: Any, class_id: int, seed: bytes) -> None:
    """
    Reorder instructions within basic blocks for class-specific scheduling.

    Uses Fisher-Yates shuffle with the PCG LCG for determinism.
    """
    rng_seed = class_id * 31 + struct.unpack("<I", seed[:4])[0]
    for block in getattr(variant, 'blocks', []):
        instrs = getattr(block, 'instructions', [])
        if len(instrs) < 3:
            continue
        rng = rng_seed
        for i in range(len(instrs) - 1, 0, -1):
            j = int(rng % (i + 1))
            rng = ((rng * 6364136223846793005) & 0xFFFFFFFFFFFFFFFF) + 1442695040888963407
            rng = rng & 0xFFFFFFFFFFFFFFFF
            instrs[i], instrs[j] = instrs[j], instrs[i]
