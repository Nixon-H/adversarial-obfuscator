"""
phase_class_dispatch.py

Purpose:
Generates class dispatch variants — multiple functionally equivalent
implementations of a dispatch function that the runtime can swap
between, creating polymorphism at the class dispatch level.

Architectural Role:
IR-level variant generation phase.  Produces class_dispatch_config.json.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
hashlib, json, os, struct, ..common, ..binding.crypto_binding, irgen.class_specializer

Security Relevance:
Class dispatch polymorphism forces the analyst to track multiple
dispatch variants simultaneously.
"""

import hashlib
import json
import os
import struct
from ..common import log, BUILD_DIR


def phase_class_dispatch(num_classes=4):
    """
    Generate dispatch class variants and IR-level variants.

    Args:
        num_classes: number of class variants to generate

    Returns:
        list of (label, hash) tuples
    """
    log("CLASS_DISPATCH", f"Generating {num_classes} class dispatch variants")
    classes = []
    for i in range(num_classes):
        label = f"class_{i}"
        variant_data = struct.pack("<II", i, 0x9E3779B9)
        variant_hash = hashlib.sha256(variant_data).digest()
        classes.append((label, variant_hash))
    log("CLASS_DISPATCH", f"Generated {len(classes)} class dispatch variants")

    # Call class specializer for IR-level variant generation
    try:
        from irgen.class_specializer import generate_class_variants

        class SimpleInstr:
            def __init__(self, opcode="nop", dst=0, src1=0, src2=0):
                self.opcode = opcode
                self.dst = dst
                self.src1 = src1
                self.src2 = src2

        class SimpleBlock:
            def __init__(self, instructions=None):
                self.instructions = instructions or []

        class SimpleFunction:
            def __init__(self, name="dispatch_fn", blocks=None):
                self.name = name
                self.blocks = blocks or []

        ir_fn = SimpleFunction(
            name="dispatch_fn",
            blocks=[
                SimpleBlock([
                    SimpleInstr("mov", 0, 10, 0),
                    SimpleInstr("mov", 1, 20, 0),
                    SimpleInstr("add", 2, 0, 1),
                    SimpleInstr("mul", 3, 2, 2),
                    SimpleInstr("xor", 4, 3, 1),
                    SimpleInstr("ret", 0, 0, 0),
                ])
            ],
        )
        variants = generate_class_variants(ir_fn, num_classes, 42)
        log("CLASS_DISPATCH", f"Generated {len(variants)} IR-level class variants")

        config = {
            "num_classes": num_classes,
            "base_seed": 42,
            "variant_count": len(variants),
            "variant_metadata": [],
        }
        for i, v in enumerate(variants):
            v_info = {"class_id": i, "name": getattr(v, "name", f"class_{i}")}
            nop_count = 0
            for blk in getattr(v, "blocks", []):
                for instr in getattr(blk, "instructions", []):
                    if getattr(instr, "opcode", "") == "nop":
                        nop_count += 1
            v_info["nop_count"] = nop_count
            config["variant_metadata"].append(v_info)

        config_path = os.path.join(BUILD_DIR, "class_dispatch_config.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        log("CLASS_DISPATCH", f"Config written to {config_path}")
    except ImportError as e:
        log("SKIP", f"class_specializer not available: {e}")
    except Exception as e:
        log("ERROR", f"class_specializer variant generation failed: {e}")

    return classes
