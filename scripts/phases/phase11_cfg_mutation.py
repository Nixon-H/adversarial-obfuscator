"""
phase11_cfg_mutation.py

Purpose:
Generates multiple control-flow graph orderings per function, creating
variant data that the runtime can use to permute basic-block layout
on each execution.

Architectural Role:
Post-IR-generation phase.  Produces cfg_mutation_variants.json for
the runtime's CFG scrambling subsystem.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
hashlib, json, os, struct, ..common, llvmgen.lower

Security Relevance:
CFG mutation defeats static analysis by providing multiple legal
block orderings that change per execution.
"""

import hashlib
import json
import os
import struct

from ..common import log, BUILD_DIR


def phase_cfg_mutation(ir_module_path, num_variants=4):
    """
    Generate CFG ordering variants for each function in the IR module.

    Args:
        ir_module_path: path to the .ir module file
        num_variants: number of orderings to generate per function
    """
    log("CFG_MUTATION", f"Generating {num_variants} CFG orderings per function")
    try:
        from llvmgen.lower import NixonIRParser
        parser = NixonIRParser()
        ir_mod = parser.parse_file(ir_module_path)
    except Exception as e:
        log("SKIP", f"CFG mutation could not parse IR: {e}")
        return

    variant_data = {}
    for func in ir_mod.functions:
        num_blocks = len(getattr(func, 'blocks', []))
        if num_blocks < 2:
            log("CFG_MUTATION", f"  {func.name}: {num_blocks} block(s), skipping")
            continue
        orderings = _generate_orderings(num_blocks, num_variants, func.name)
        variant_data[func.name] = {
            "num_blocks": num_blocks,
            "num_variants": num_variants,
            "orderings": orderings,
        }
        log("CFG_MUTATION", f"  {func.name}: {num_blocks} blocks, {num_variants} variants")

    out_path = os.path.join(BUILD_DIR, "cfg_mutation_variants.json")
    with open(out_path, "w") as f:
        json.dump(variant_data, f, indent=2)
    log("CFG_MUTATION", f"Written to {out_path}")


def _generate_orderings(num_blocks, num_variants, name_seed):
    digest = hashlib.sha256(name_seed.encode()).digest()
    base_rng = struct.unpack("<Q", digest[:8])[0]
    MASK = 0xFFFFFFFFFFFFFFFF
    orderings = []
    for v in range(num_variants):
        order = list(range(num_blocks))
        rng = (base_rng + v) & MASK
        for i in range(num_blocks - 1, 0, -1):
            j = int(rng % (i + 1))
            rng = ((rng * 6364136223846793005) & MASK) + 1442695040888963407
            rng = rng & MASK
            order[i], order[j] = order[j], order[i]
        orderings.append(order)
    return orderings
