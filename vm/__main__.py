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

    compile_parser = sub.add_parser("compile", help="Compile Python source to VM bytecode")
    compile_parser.add_argument("input", help="Input Python source file path")
    compile_parser.add_argument("-o", "--output", required=True, help="Output bytecode file")
    compile_parser.add_argument("--functions", required=True,
                                help="Comma-separated list of target function names")
    compile_parser.add_argument("--seed", type=lambda x: bytes.fromhex(x),
                                help="Build seed (hex)")
    compile_parser.add_argument("--key-out", default=None,
                                help="Path to write the derived key to (0600). Either --seed "
                                     "or --key-out is required so the key remains recoverable. "
                                     "The seed is never persisted.")

    mutate_parser = sub.add_parser("mutate", help="Mutate bytecode")
    mutate_parser.add_argument("input", help="Input bytecode file")
    mutate_parser.add_argument("-o", "--output", required=True, help="Output mutated bytecode file")
    mutate_parser.add_argument("--seed", type=lambda x: bytes.fromhex(x), required=True,
                               help="Build seed (hex)")
    mutate_parser.add_argument("--level", type=int, default=3, choices=[1, 2, 3],
                               help="Mutation level (default: 3)")
    mutate_parser.add_argument("--key", default=None, help="Decryption key (hex) for the input container")
    mutate_parser.add_argument("--key-file", default=None,
                               help="File holding key=<hex> (or legacy seed=<hex>)")

    run_parser = sub.add_parser("run", help="Run bytecode in VM interpreter")
    run_parser.add_argument("input", help="Bytecode file to execute")
    run_parser.add_argument("--trace", action="store_true", help="Enable instruction tracing")
    run_parser.add_argument("--key", default=None, help="Decryption key (hex) for the container")
    run_parser.add_argument("--key-file", default=None,
                            help="File holding key=<hex> (or legacy seed=<hex>); "
                                 "defaults to <input>.key when present")

    args = parser.parse_args(argv)

    if not phase2_enabled:
        print("Advanced Protection is disabled in config. Set shadow_compiler.advanced_protection.enabled to true.", file=sys.stderr)
        return 1

    from .bytecode_compiler import BytecodeAuthenticationError
    try:
        if args.command == "compile":
            return _cmd_compile(args)
        elif args.command == "mutate":
            return _cmd_mutate(args)
        elif args.command == "run":
            return _cmd_run(args)
    except BytecodeAuthenticationError as exc:
        print(f"VM bytecode authentication failed: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


def _cmd_compile(args) -> int:
    """
    Compile IR source to encrypted VM bytecode.

    Reads a Python source file, lowers it to IR with irgen.compile, then
    translates each target function to VM bytecode, encrypts the
    bytecode with a key derived from the build seed, and writes
    the result as a JSON container.
    """
    import irgen.compile as ir_compile
    from .bytecode_compiler import compile_to_bytecode, encrypt_bytecode
    from .vm_isa import VMOpcode

    if args.seed is not None and not args.seed:
        raise SystemExit("--seed must not be empty")
    if not args.seed and not args.key_out:
        raise SystemExit(
            "vm compile requires --seed or --key-out so the encryption key remains recoverable")

    with open(args.input) as f:
        source = f.read()

    if source.lstrip().startswith("module @") or "\nfunc @" in source:
        raise SystemExit(
            "vm compile expects Python source, not lowered IR text; "
            "compile the Python file directly (or use python -m irgen for IR)")
    module = ir_compile.compile_py_to_ir(source)

    target_functions = [f.strip() for f in args.functions.split(",") if f.strip()]
    if not target_functions:
        raise SystemExit("--functions must name at least one function")
    if len(set(target_functions)) != len(target_functions):
        raise SystemExit("--functions contains duplicate target names")

    opcode_map = {name: idx for idx, name in VMOpcode.LOGICAL_NAMES.items()}

    seed = args.seed or os.urandom(16)
    key = hashlib.sha256(seed).digest()[:32]

    all_bytecode = bytearray()
    function_offsets = {}
    for target_func in target_functions:
        func_obj = next((func for func in module.functions
                         if func.name == target_func), None)
        if func_obj is None:
            raise SystemExit(f"function '{target_func}' not found in IR module")

        function_offsets[target_func] = len(all_bytecode)
        bc = compile_to_bytecode(func_obj, opcode_map, seed)
        all_bytecode.extend(bc)

    encrypted = encrypt_bytecode(all_bytecode, key)

    # Key material is NOT written into the container, and the seed is never
    # persisted: seed -> key means co-locating either with the ciphertext is
    # a self-contained break. The derived key is written only when the
    # operator passes --key-out; otherwise the operator must retain --seed.
    if getattr(args, "key_out", None):
        # os.open returns a raw fd, which is not a context manager.
        fd = os.open(args.key_out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.fchmod(fd, 0o600)
            os.write(fd, ("key=%s\n" % key.hex()).encode())
            os.fsync(fd)
        finally:
            os.close(fd)
        print(f"key written to {args.key_out} (0600) - distribute separately, never beside the ciphertext")
    else:
        print("no --key-out given: key material was not persisted; pass --key/--key-file to `vm run`")

    output = {
        "bytecode": encrypted.hex(),
        "encrypted": True,
        "num_functions": len(target_functions),
        "bytecode_size": len(encrypted),
        "functions": target_functions,
        "function_offsets": function_offsets,
    }

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Bytecode written to {args.output} ({len(encrypted)} bytes for {len(target_functions)} function(s))")
    return 0


def _read_key_file(path: str) -> bytes:
    """Parse a key sidecar: `key=<hex>` directly, or legacy `seed=<hex>`
    (key = sha256(seed)[:32], matching _cmd_compile's derivation)."""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("key="):
                return bytes.fromhex(line[4:])
            if line.startswith("seed="):
                return hashlib.sha256(bytes.fromhex(line[5:])).digest()[:32]
    raise SystemExit(f"no key= or seed= line found in {path}")


def _load_container_key(args, input_path: str, key_required: bool = True):
    """Resolve the container key from --key, --key-file, or <input>.key."""
    if getattr(args, "key", None):
        return bytes.fromhex(args.key)
    explicit = getattr(args, "key_file", None)
    key_file = explicit or (input_path + ".key")
    if os.path.exists(key_file):
        return _read_key_file(key_file)
    if explicit:
        raise SystemExit(f"key file not found: {explicit}")
    if key_required:
        raise SystemExit(
            "container is encrypted; pass --key <hex> or --key-file <path> "
            "(default <input>.key is absent)")
    return None


def _cmd_mutate(args) -> int:
    """
    Apply opcode-level mutation and fusion to existing bytecode.

    Reads a bytecode JSON container, DECRYPTS it, applies
    mutate_instruction_universe from irgen.mutation at the specified level,
    re-encrypts, and writes the result as a new JSON container.
    """
    from irgen.mutation import mutate_instruction_universe
    from .bytecode_compiler import decrypt_bytecode, encrypt_bytecode

    with open(args.input) as f:
        data = json.load(f)

    ciphertext = bytes.fromhex(data["bytecode"])
    if data.get("encrypted", True):
        key = _load_container_key(args, args.input)
        bytecode = decrypt_bytecode(ciphertext, key)
    else:
        bytecode = bytearray(ciphertext)

    mutated_bc, meta = mutate_instruction_universe(bytecode, args.seed, level=args.level)
    if "function_offsets" in data and len(mutated_bc) != len(bytecode):
        raise SystemExit(
            "mutation changed bytecode length; function offsets would no longer be valid")

    # Re-encrypt so the output container has the same protection as the input.
    if data.get("encrypted", True):
        key = _load_container_key(args, args.input)
        out_ciphertext = encrypt_bytecode(mutated_bc, key)
    else:
        out_ciphertext = bytes(mutated_bc)

    output = {
        "bytecode": out_ciphertext.hex(),
        "encrypted": data.get("encrypted", True),
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
    for field in ("functions", "function_offsets"):
        if field in data:
            output[field] = data[field]

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
    from .bytecode_compiler import decrypt_bytecode

    with open(args.input) as f:
        data = json.load(f)

    ciphertext = bytes.fromhex(data["bytecode"])
    if data.get("encrypted", True):
        # The compile step stores ENCRYPTED bytecode; running the raw
        # ciphertext can never work. Decrypt with the out-of-band key first.
        key = _load_container_key(args, args.input)
        bytecode = decrypt_bytecode(ciphertext, key)
    else:
        bytecode = ciphertext

    raw_opcode_map = (data.get("metadata") or {}).get("opcode_map")
    opcode_map = None
    if raw_opcode_map is not None:
        if not isinstance(raw_opcode_map, dict):
            raise SystemExit("invalid opcode_map metadata: expected an object")
        try:
            opcode_map = {int(k): int(v) for k, v in raw_opcode_map.items()}
        except (TypeError, ValueError) as exc:
            raise SystemExit(f"invalid opcode_map metadata: {exc}") from exc
        if any(not (0 <= k <= 255 and 0 <= v <= 255) for k, v in opcode_map.items()):
            raise SystemExit("invalid opcode_map metadata: keys and values must be 0..255")
        if len(set(opcode_map.values())) != len(opcode_map):
            raise SystemExit("invalid opcode_map metadata: physical opcodes must be unique")

    raw_offsets = data.get("function_offsets")
    entries: list[tuple[str | None, int]] = []
    if raw_offsets is not None:
        if not isinstance(raw_offsets, dict):
            raise SystemExit("invalid function_offsets metadata: expected an object")
        try:
            offsets = {str(k): int(v) for k, v in raw_offsets.items()}
        except (TypeError, ValueError) as exc:
            raise SystemExit(f"invalid function_offsets metadata: {exc}") from exc
        functions = data.get("functions")
        if not isinstance(functions, list) or set(functions) != set(offsets):
            raise SystemExit("function_offsets does not match the container function list")
        if any(offset < 0 or offset >= len(bytecode) for offset in offsets.values()):
            raise SystemExit("function offset lies outside the bytecode")
        entries = [(name, offsets[name]) for name in functions]
    else:
        entries = [(None, 0)]

    trace = args.trace
    if trace:
        print("=== VM Trace ===")
        print(f"Starting execution: {len(bytecode)} bytes")
        print()

    total_steps = 0
    failed = False
    for function_name, start_offset in entries:
        state = {
            "regs": [0] * 16,
            "memory": bytearray(65536),
            "stack": [],
            "halted": False,
        }
        state["regs"][14] = start_offset
        vm = VMInterpreter(bytecode, state, opcode_map=opcode_map)
        if trace and function_name is not None:
            print(f"--- Function {function_name} @ byte {start_offset} ---")

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
                failed = True
                break

        total_steps += steps
        if function_name is not None:
            print(f"Function {function_name}: result={state['regs'][1]}")
        if trace:
            print(f"=== Halted after {steps} steps ===")
            print(f"Final registers: {state['regs']}")
            print(f"Stack depth: {len(state['stack'])}")
            print()

    print(f"VM halted after {total_steps} steps")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
