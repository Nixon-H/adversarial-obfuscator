"""
__main__.py

Purpose:
CLI entry point for `python -m vm`. Provides three sub-commands:
  compile   — Compile IR functions to encrypted VM bytecode.
  mutate    — Apply opcode-mutation and fusion to existing bytecode.
  run       — Execute bytecode in the Python VM interpreter.

Architectural Role:
Command-line tool for the VM pipeline. Used during development and
build to compile, mutate, and test VM bytecode. All operations
require Advanced Protection to be enabled in config/default.json.

Security Relevance:
Entry point for build-time VM compilation. The --seed parameter
controls the build-specific key material; if predictable, all
ephemeral ISA mappings can be precomputed by an attacker.

Dependencies:
  - irgen.compile, irgen.mutation
  - vm.bytecode_compiler, vm.interpreter, vm.vm_isa
"""

from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
from typing import Optional


def _load_config():
    """Load project configuration from config/default.json."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "default.json")
    with open(config_path) as f:
        return json.load(f)


def main(argv: Optional[list[str]] = None) -> int:
    """
    Main entry point for the VM CLI.

    Parses args and dispatches to compile, mutate, or run commands.
    Returns 0 on success, 1 on error.

    Phase 2 gating: if advanced_protection is not enabled, all
    commands exit with code 1 immediately.
    """
    if argv is None:
        argv = sys.argv[1:]

    cfg = _load_config()
    phase2_enabled = cfg.get("shadow_compiler", {}).get("advanced_protection", cfg.get("shadow_compiler", {}).get("phase2", {})).get("enabled", False)

    parser = argparse.ArgumentParser(
        prog="python -m vm",
        description="Nixon Advanced Protection: Mutating VM for Crown Jewels",
    )

    sub = parser.add_subparsers(dest="command", help="Sub-command")

    compile_parser = sub.add_parser("compile", help="Compile IR to VM bytecode")
    compile_parser.add_argument("input", help="Input IR file path")
    compile_parser.add_argument("-o", "--output", required=True, help="Output bytecode file")
    compile_parser.add_argument("--functions", required=True,
                                help="Comma-separated list of target function names")
    compile_parser.add_argument("--seed", type=lambda x: bytes.fromhex(x),
                                help="Build seed (hex)")

    mutate_parser = sub.add_parser("mutate", help="Mutate bytecode")
    mutate_parser.add_argument("input", help="Input bytecode file")
    mutate_parser.add_argument("-o", "--output", required=True, help="Output mutated bytecode file")
    mutate_parser.add_argument("--seed", type=lambda x: bytes.fromhex(x), required=True,
                               help="Build seed (hex)")
    mutate_parser.add_argument("--level", type=int, default=3, choices=[1, 2, 3],
                               help="Mutation level (default: 3)")

    run_parser = sub.add_parser("run", help="Run bytecode in VM interpreter")
    run_parser.add_argument("input", help="Bytecode file to execute")
    run_parser.add_argument("--trace", action="store_true", help="Enable instruction tracing")

    args = parser.parse_args(argv)

    if not phase2_enabled:
        print("Advanced Protection is disabled in config. Set shadow_compiler.advanced_protection.enabled to true.", file=sys.stderr)
        return 1

    if args.command == "compile":
        return _cmd_compile(args)
    elif args.command == "mutate":
        return _cmd_mutate(args)
    elif args.command == "run":
        return _cmd_run(args)
    else:
        parser.print_help()
        return 1


def _cmd_compile(args) -> int:
    """
    Compile IR source to encrypted VM bytecode.

    Reads an IR source file, compiles it with irgen.compile, then
    translates each target function to VM bytecode, encrypts the
    bytecode with a key derived from the build seed, and writes
    the result as a JSON container.
    """
    import irgen.compile as ir_compile
    from .bytecode_compiler import compile_to_bytecode, encrypt_bytecode
    from .vm_isa import VMOpcode

    with open(args.input) as f:
        source = f.read()

    module = ir_compile.compile_py_to_ir(source)

    target_functions = [f.strip() for f in args.functions.split(",")]

    opcode_map = {name: idx for idx, name in VMOpcode.LOGICAL_NAMES.items()}

    seed = args.seed or os.urandom(16)
    key = hashlib.sha256(seed).digest()[:32]

    all_bytecode = bytearray()
    for target_func in target_functions:
        func_obj = None
        for func in module.functions:
            if func.name == target_func:
                func_obj = func
                break
        if func_obj is None:
            print(f"Warning: function '{target_func}' not found in IR module", file=sys.stderr)
            continue

        bc = compile_to_bytecode(func_obj, opcode_map, seed)
        all_bytecode.extend(bc)

    encrypted = encrypt_bytecode(all_bytecode, key)

    output = {
        "bytecode": encrypted.hex(),
        "num_functions": len(target_functions),
        "bytecode_size": len(encrypted),
        "seed": seed.hex(),
        "key": key.hex(),
        "functions": target_functions,
    }

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Bytecode written to {args.output} ({len(encrypted)} bytes for {len(target_functions)} function(s))")
    return 0


def _cmd_mutate(args) -> int:
    """
    Apply opcode-level mutation and fusion to existing bytecode.

    Reads a bytecode JSON container, applies mutate_instruction_universe
    from irgen.mutation at the specified level, and writes the result
    as a new JSON container with mutation metadata.
    """
    from irgen.mutation import mutate_instruction_universe

    with open(args.input) as f:
        data = json.load(f)

    bytecode = bytearray(bytes.fromhex(data["bytecode"]))

    mutated_bc, meta = mutate_instruction_universe(bytecode, args.seed, level=args.level)

    output = {
        "bytecode": bytes(mutated_bc).hex(),
        "original_size": len(bytecode),
        "mutated_size": len(mutated_bc),
        "mutation_level": args.level,
        "seed": args.seed.hex(),
        "metadata": {
            "opcode_map": {str(k): v for k, v in meta["opcode_map"].items()},
            "handler_permutations_count": len(meta["handler_permutations"]),
            "fusion_plan": meta["fusion_plan"],
        },
    }

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Mutated bytecode written to {args.output} ({len(mutated_bc)} bytes, level {args.level})")
    return 0


def _cmd_run(args) -> int:
    """
    Execute VM bytecode in the Python interpreter.

    Loads a bytecode JSON container, initializes the VM interpreter
    with 64KB memory and 16 registers, and runs until halt or 1M
    steps. With --trace, prints instruction-level execution info.
    """
    from .interpreter import VMInterpreter

    with open(args.input) as f:
        data = json.load(f)

    bytecode = bytes.fromhex(data["bytecode"])

    state = {
        "regs": [0] * 16,
        "memory": bytearray(65536),
        "stack": [],
        "halted": False,
    }

    vm = VMInterpreter(bytecode, state)

    trace = args.trace

    if trace:
        print("=== VM Trace ===")
        print(f"Starting execution: {len(bytecode)} bytes")
        print()

    steps = 0
    while not state.get("halted", False):
        pc_before = state["regs"][14]
        vm.step()
        steps += 1

        if trace:
            print(f"[{steps:6d}] PC={pc_before:04X}  regs={state['regs'][:8]}   stack={len(state['stack'])}")

        if steps > 1000000:
            print("Max steps reached (1M), halting.")
            state["halted"] = True

    if trace:
        print()
        print(f"=== Halted after {steps} steps ===")
        print(f"Final registers: {state['regs']}")
        print(f"Stack depth: {len(state['stack'])}")

    print(f"VM halted after {steps} steps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
