"""
phase13_ssa_mutation.py

Purpose:
Generates SSA-form instruction variants per function by mutating opcode
sequences, producing a configuration the runtime uses to permute
instruction encodings on each execution.

Architectural Role:
Post-IR-generation phase.  Produces ssa_mutation_variants.json for the
runtime's SSA scrambling subsystem.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, ..common, irgen.ssa_mutation

Security Relevance:
SSA mutation varies instruction encoding across executions, defeating
signature-based detection.
"""

import json
import os

from ..common import log, BUILD_DIR


def phase_ssa_mutation(ir_path=None, num_variants=4):
    """
    Generate SSA instruction variants per function.

    Args:
        ir_path: optional path to the .ir file (falls back to example data)
        num_variants: number of variants to generate per function
    """
    log("SSA_MUTATION", f"Generating {num_variants} SSA variants per function")
    log("SSA_MUTATION", f"Generating {num_variants} SSA variants per function")
    try:
        from irgen.ssa_mutation import generate_ssa_mutation_config, generate_ssa_variants
    except ImportError:
        log("SKIP", "irgen.ssa_mutation not importable")
        return

    functions_ir = {}
    if ir_path and os.path.exists(ir_path):
        try:
            from irgen.compile import compile_py_to_ir
            with open(ir_path) as f:
                source = f.read()
            ir_mod = compile_py_to_ir(source)
            for func in getattr(ir_mod, 'functions', []):
                functions_ir[func.name] = [
                    {"opcode": instr.opcode, "operands": list(instr.operands)}
                    for instr in getattr(func, 'instructions', [])
                ]
        except Exception as e:
            log("SKIP", f"Could not parse IR for SSA mutation: {e}")
            return

    if not functions_ir:
        functions_ir = {
            "example_func": [
                {"opcode": "add", "operands": ["%a", "%b"]},
                {"opcode": "mul", "operands": ["%c", "%d"]},
                {"opcode": "store", "operands": ["%a", "%r"]},
            ],
        }

    config = generate_ssa_mutation_config(functions_ir, num_variants)
    out_path = os.path.join(BUILD_DIR, "ssa_mutation_variants.json")
    with open(out_path, "w") as f:
        json.dump(config, f, indent=2)
    log("SSA_MUTATION", f"Written to {out_path} ({len(config)} functions, {num_variants} variants each)")
