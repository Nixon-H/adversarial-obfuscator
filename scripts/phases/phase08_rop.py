"""
phase08_rop.py

Purpose:
Compiles selected IR functions into ROP (Return-Oriented Programming)
chains.  Loads a gadget database from a reference binary, compiles
each target function to gadgets, and produces encrypted ROP blobs
with stack-pivot stubs.

Architectural Role:
Runs after IR generation.  Produces a ROP chain manifest consumed
by the runtime for function-level replacement with ROP-based execution.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, sys, ..common, irgen.rop_compiler, llvmgen.lower

Security Relevance:
ROP compilation replaces standard function bodies with gadget chains,
making static analysis and decompilation significantly harder.
"""

import json
import os
import sys  # noqa: F401 (this line binds a name used by an embedded template)

from ..common import log, atomic_write


def phase_rop_compile(input_ir, output_rop, config):
    """
    Compile IR functions to ROP chains using gadgets from a reference binary.

    Args:
        input_ir: path to the .ir module file
        output_rop: path for the ROP manifest JSON
        config: dict with target_functions list and reference_binary path

    Returns:
        dict {"ok": bool, "reason": str, "compiled": int} — never raises
        for config-level skips; raises only on unexpected I/O errors.
    """
    log("ROP", f"{input_ir} -> {output_rop}")
    if not os.path.exists(input_ir):
        log("ERROR", f"Input IR not found: {input_ir}")
        return {"ok": False, "reason": f"input IR not found: {input_ir}", "compiled": 0}

    try:
        from irgen.rop_compiler import RopFunctionCompiler, generate_gadget_database
        from llvmgen.lower import NixonIRParser
    except ImportError as e:
        log("SKIP", f"rop_compiler not importable: {e}")
        return {"ok": False, "reason": f"rop_compiler not importable: {e}", "compiled": 0}

    with open(input_ir, "r") as f:
        ir_text = f.read()

    parser = NixonIRParser(ir_text)
    module = parser.parse()

    target_funcs = config.get("target_functions", [])
    if not target_funcs:
        log("ROP", "No target functions specified")
        return {"ok": False, "reason": "no target functions specified", "compiled": 0}

    ref_binary = config.get("reference_binary")
    if not ref_binary:
        log("ERROR", "No reference_binary in config for ROP compilation")
        return {"ok": False, "reason": "no reference_binary in config", "compiled": 0}
    try:
        gadgets_db = generate_gadget_database(ref_binary)
        log("ROP", f"Loaded {len(gadgets_db)} gadgets from {ref_binary}")
    except (FileNotFoundError, RuntimeError) as e:
        log("ERROR", f"Gadget database generation failed: {e}")
        return {"ok": False, "reason": f"gadget DB failed: {e}", "compiled": 0}

    compiler = RopFunctionCompiler(gadgets_db)
    compiled = {}

    for func in module.get("functions", []):
        fname = func.get("name", "")
        if fname.startswith("@"):
            fname = fname[1:]
        if fname in target_funcs or "*" in target_funcs:
            log("ROP", f"Compiling {fname} to ROP chain...")
            try:
                chain = compiler.compile_ir_function(func)
                chain_size = len(chain) * 8
                log("ROP", f"  {fname}: {len(chain)} gadgets ({chain_size} bytes)")
                compiled[fname] = {
                    "chain": chain,
                    "size": chain_size,
                }

                stub = compiler.emit_stack_pivot(chain, 0)
                compiled[fname]["stub"] = list(stub)
                compiled[fname]["stub_size"] = len(stub)

                enc_key = [os.urandom(1)[0] for _ in range(32)]
                encrypted = compiler.generate_encrypted_rop_blob(chain, enc_key)
                compiled[fname]["encrypted"] = list(encrypted)
                compiled[fname]["enc_key"] = enc_key
            except (RuntimeError, ValueError) as e:
                log("ERROR", f"  Failed to compile {fname}: {e}")

    result = {
        "version": "1.0",
        "config": config,
        "compiled": compiled,
    }

    atomic_write(output_rop, json.dumps(result, indent=2))

    total = sum(v["size"] for v in compiled.values())
    log("ROP", f"Done: {len(compiled)} functions compiled, {total} bytes total")
    return {"ok": True, "reason": f"{len(compiled)} functions, {total} bytes", "compiled": len(compiled)}
