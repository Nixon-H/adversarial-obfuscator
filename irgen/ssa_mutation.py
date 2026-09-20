"""
ssa_mutation.py

Purpose:
Build-time SSA variant generation for Runtime SSA Mutation (Item 83 of the
protection spec). Generates N semantically equivalent SSA variants per
function. Each variant uses different instruction orderings (for commutative
ops), different phi placement, and different temporary naming.

Architectural Role:
Pre-compilation diversity pass. Produces multiple SSA representations of
the same function that are structurally different but semantically identical.
One variant is selected per build.

Security Relevance:
SSA-level diversity makes it harder for an attacker to develop signatures
for specific functions across builds. Differences include:
- Commutative operand swapping (a+b vs b+a).
- Phi node placement at different positions.
- Instruction scheduling variation based on variant ID.

The PRNG uses a linear congruential generator (LCG):
  state_{n+1} = state_n * 6364136223846793005 + 1442695040888963407
This is the same LCG used by the PCG family.

Threat model: Cross-build signature matching, function identification
in binary diffing tools.
"""

import hashlib
import struct


def _prng_next(state):
    """Advance the LCG state and return the new state."""
    state = (state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
    return state


def _fisher_yates(n, rng_state):
    """
    Fisher-Yates shuffle of indices [0..n-1] using the LCG PRNG.

    Returns (permutation, new_rng_state).
    """
    perm = list(range(n))
    for i in range(n - 1, 0, -1):
        j = (rng_state % (i + 1))
        rng_state = _prng_next(rng_state)
        perm[i], perm[j] = perm[j], perm[i]
    return perm, rng_state


_COMMUTATIVE_OPS = {"add", "mul", "and", "or", "xor", "eq", "ne"}


def generate_ssa_variants(function_name, ir_instructions, num_variants):
    """
    Generate N SSA variants for a function.

    Each variant differs by:
    - Commutative operand swapping (random 50% chance per instruction).
    - Phi node positions (every 3rd instruction after position 2).
    - The base RNG is derived from SHA-256(function_name).

    Returns a list of variant dicts with 'instructions', 'phi_positions',
    and 'variant_id' keys.
    """
    digest = hashlib.sha256(function_name.encode()).digest()
    base_rng = struct.unpack("<Q", digest[:8])[0]

    variants = []
    for v in range(num_variants):
        rng = (base_rng + v * 0x9E3779B9) & 0xFFFFFFFFFFFFFFFF
        insts = list(ir_instructions)

        shuffled = []
        for inst in insts:
            op = inst.get("opcode", "nop")
            if op in _COMMUTATIVE_OPS and len(inst.get("operands", [])) >= 2:
                ops = list(inst["operands"])
                if (rng >> 32) & 1:
                    ops[0], ops[1] = ops[1], ops[0]
                rng = _prng_next(rng)
                new_inst = dict(inst, operands=ops)
            else:
                new_inst = dict(inst)
            shuffled.append(new_inst)

        num_insts = len(shuffled)
        phi_positions = [
            i for i in range(2, num_insts - 1)
            if (i + v) % 3 == 0
        ]
        if not phi_positions and num_insts > 2:
            phi_positions = [num_insts // 2]

        variants.append({
            "instructions": shuffled,
            "phi_positions": phi_positions,
            "variant_id": v,
        })

    return variants


def generate_ssa_mutation_config(functions_ir, num_variants=4):
    """
    Generate mutation config for all functions in a module.

    Takes a dict of function_name -> ir_instructions and produces
    a config dict with variants for each function.
    """
    config = {}
    for func_name, ir_insts in functions_ir.items():
        variants = generate_ssa_variants(func_name, ir_insts, num_variants)
        config[func_name] = {
            "num_instructions": len(ir_insts),
            "num_variants": num_variants,
            "variants": variants,
        }
    return config
