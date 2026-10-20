"""
ir_scanner.py

Purpose:
Scans IR modules to extract structural metadata about each function:
block count, instruction count, opcode types, control flow, calls,
and memory operations.

Architectural Role:
Supports the coverage map by providing per-function IR-level metadata.
This data is used to classify functions and identify unprotected code.

Execution Context:
Called by generate_coverage_map() for every function in the IR module.
Results are stored in FunctionCoverage.protection_details["ir_scan"].

Dependencies:
- irgen.compile (IrModule, IrFunction) for IR traversal

Security Relevance:
IR scanning detects whether functions contain calls, control flow, or
memory ops — patterns that determine which protections are viable.
For example, a function with no control flow cannot benefit from CFG
flattening.

Maintenance Notes:
- The opcode classification in classify_function uses keyword matching
  on call target names; adding new crypto/IO keywords here will
  improve classification accuracy.
- _scan_function must remain a pure function with no side effects.
"""

from __future__ import annotations

from typing import Dict, Set


def scan_ir_module(ir_module) -> Dict[str, dict]:
    """
    Scan all functions in an IR module and return a dict of
    function-name -> scan metadata (block count, instruction count,
    op types, control flow presence, call targets, memory ops).
    """
    from irgen.compile import IrModule  # noqa: F401 (this line binds a name used by an embedded template)
    result: Dict[str, dict] = {}
    for func in ir_module.functions:
        info = _scan_function(func)
        result[func.name] = info
    return result


def _scan_function(func) -> dict:
    """
    Scan a single IR function and return its structural metadata.
    """
    blocks = func.blocks
    total_instructions = 0
    op_types: Set[str] = set()
    has_control_flow = False
    has_calls = False
    has_memory_ops = False
    call_targets = []

    for block in blocks:
        for inst in block.instructions:
            total_instructions += 1
            op_types.add(inst.opcode)
            if inst.opcode in ("jmp", "br", "phi"):
                has_control_flow = True
            if inst.opcode == "call":
                has_calls = True
                if inst.func_name:
                    call_targets.append(inst.func_name)
            if inst.opcode in ("load", "store", "alloca", "gep"):
                has_memory_ops = True
        term = block.terminator
        if term:
            total_instructions += 1
            op_types.add(term.opcode)
            if term.opcode in ("jmp", "br"):
                has_control_flow = True
            if term.opcode == "call":
                has_calls = True
                if term.func_name:
                    call_targets.append(term.func_name)

    return {
        "block_count": len(blocks),
        "instruction_count": total_instructions,
        "op_types": sorted(op_types),
        "has_control_flow": has_control_flow,
        "has_calls": has_calls,
        "has_memory_ops": has_memory_ops,
        "call_targets": call_targets,
    }


def classify_function(ir_function) -> str:
    """
    Classify an IR function into a high-level category based on
    its structural scan.

    Categories: 'dispatch', 'crypto', 'io', 'arithmetic', 'control',
    'memory_intensive', 'general'. Used by the coverage map to
    provide human-readable labels and by the synthesis engine for
    cost estimation.
    """
    scan = _scan_function(ir_function)
    if not scan["has_control_flow"] and scan["has_calls"]:
        return "dispatch"
    if scan["has_calls"]:
        calls = scan["call_targets"]
        crypto_keywords = {"encrypt", "decrypt", "hash", "aes", "sha", "hmac", "cipher", "key", "sign"}
        io_keywords = {"read", "write", "open", "close", "send", "recv", "ioctl", "mmap"}
        for c in calls:
            c_lower = c.lower()
            if any(kw in c_lower for kw in crypto_keywords):
                return "crypto"
            if any(kw in c_lower for kw in io_keywords):
                return "io"
    op_types = set(scan["op_types"])
    arith_ops = {"add", "sub", "mul", "div", "mod", "and", "or", "xor", "shl", "shr"}
    if op_types.issubset(arith_ops | {"ret", "alloca", "load", "store", "zext", "trunc"}):
        return "arithmetic"
    if scan["has_control_flow"]:
        return "control"
    if scan["has_memory_ops"]:
        return "memory_intensive"
    return "general"
