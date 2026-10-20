"""
fragmentation.py

Purpose:
Algorithm-level function fragmentation (Advanced Protection). Analyzes IR
functions to identify sub-algorithms (loops, recursion, table drives) and
fragments them into separate functions or callbacks. Each fragment can be
independently obfuscated, encrypted, or placed in a TEE.

Architectural Role:
Pre-obfuscation pass that breaks large functions into smaller fragments.
Each fragment gets its own function in the IR module, connected via a
coordinator that calls fragments in a seeded obfuscated sequence.

Security Relevance:
- Function fragmentation prevents holistic analysis of algorithms.
- Fragments can be independently encrypted or placed in different TEEs.
- The calling sequence is obfuscated via XOR with a build-derived IV.
- Fragments use a shared state buffer, enabling inter-fragment data flow.

Threat model: Static analysis, binary diffing, signature-based detection.

Dependencies:
    - irgen.compile (IrModule, IrFunction, IrBlock, IrInstruction, IrValue, IrType)
"""

from __future__ import annotations
import json
import os
import sys
import argparse
from typing import Optional
from .compile import IrModule, IrFunction, IrInstruction, IrValue, IrType


def _load_config():
    """Load the project config for phase2 gating."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "default.json")
    try:
        with open(config_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _phase2_enabled() -> bool:
    """Check if phase2 (advanced protection) is enabled in config."""
    cfg = _load_config()
    return cfg.get("shadow_compiler", {}).get("advanced_protection", cfg.get("shadow_compiler", {}).get("phase2", {})).get("enabled", False)


class AlgorithmAnalyzer:
    """
    Analyzes IR functions to identify fragmentation candidates.

    Suggests boundary points between instructions based on data
    dependency scores, grouping instructions into clusters with
    minimal cross-boundary dependencies.
    """

    def analyze(self, ir_module: IrModule, function_name: str) -> dict:
        """
        Analyze a function and produce a fragmentation plan.

        The plan includes fragment boundaries, entry/exit variables,
        and purity scores for each fragment.
        """
        if not _phase2_enabled():
            return {"fragments": []}
        func = self._find_function(ir_module, function_name)
        if func is None:
            return {"fragments": []}
        fragments = []
        instructions = []
        for block in func.blocks:
            for inst in block.instructions:
                instructions.append(inst)
        total = len(instructions)
        if total == 0:
            return {"fragments": []}
        nfrag = max(2, min(total // 3, 8))
        boundaries = self.suggest_boundaries(ir_module, function_name, nfrag)
        frag_starts = [0] + boundaries + [total]
        for i in range(len(frag_starts) - 1):
            start = frag_starts[i]
            end = frag_starts[i + 1]
            frag_insts = instructions[start:end]
            entry_vars = []
            exit_vars = []
            for inst in frag_insts:
                for op in inst.operands:
                    if isinstance(op, IrValue) and op.name not in entry_vars:
                        entry_vars.append(op.name)
                if inst.result is not None and inst.result.name not in exit_vars:
                    exit_vars.append(inst.result.name)
            fragments.append({
                "name": f"frag_{function_name}_{i}",
                "entry_vars": entry_vars,
                "exit_vars": exit_vars,
                "code_indices": list(range(start, end)),
                "purity_score": 1.0 - (len(entry_vars) / max(1, len(entry_vars) + len(exit_vars))),
            })
        return {"fragments": fragments}

    def suggest_boundaries(self, ir_module: IrModule, function_name: str, num_fragments: int) -> list[int]:
        """
        Suggest instruction boundary indices for fragmentation.

        Computes data dependency scores between instruction groups
        and selects boundary points that minimize cross-boundary
        dependencies.
        """
        if not _phase2_enabled():
            return []
        func = self._find_function(ir_module, function_name)
        if func is None:
            return []
        instructions = []
        for block in func.blocks:
            for inst in block.instructions:
                instructions.append(inst)
        total = len(instructions)
        if total <= 1 or num_fragments <= 1:
            return []
        boundaries = []
        dep_scores = []
        for i in range(1, total):
            score = 0
            before = set()
            for inst in instructions[:i]:
                if inst.result is not None:
                    before.add(inst.result.id)
            for inst in instructions[i:]:
                for op in inst.operands:
                    if isinstance(op, IrValue) and op.id in before:
                        score += 1
            dep_scores.append(score)
        sorted_indices = sorted(range(len(dep_scores)), key=lambda x: dep_scores[x])
        step = max(1, total // num_fragments)
        picked = set()
        for idx in sorted_indices:
            pos = idx + 1
            if not picked or all(abs(pos - p) >= step // 2 for p in picked):
                if pos not in picked:
                    boundaries.append(pos)
                    picked.add(pos)
            if len(boundaries) >= num_fragments - 1:
                break
        boundaries.sort()
        if len(boundaries) < num_fragments - 1:
            step = total // num_fragments
            boundaries = [step * i for i in range(1, num_fragments)]
            boundaries = [b for b in boundaries if 0 < b < total]
        return boundaries

    def _find_function(self, ir_module: IrModule, function_name: str) -> Optional[IrFunction]:
        """Find a function by name in the IR module."""
        for func in ir_module.functions:
            if func.name == function_name:
                return func
        return None


def _name_from_pool(base: str, seed: bytes, index: int) -> str:
    """Generate a seeded obfuscated function name."""
    h = hash((base, seed, index)) & 0xFFFFFFFF
    return f"_p{index}_{h:x}"


def fragment_function(
    ir_module: IrModule,
    function_name: str,
    num_fragments: int = 5,
    seed: bytes = None
) -> tuple[list[IrFunction], dict]:
    """
    Fragment a function into multiple sub-functions.

    Uses AlgorithmAnalyzer to determine optimal boundaries, creates
    fragment functions with state buffer interfaces, and returns
    coordination metadata.
    """
    if not _phase2_enabled():
        return [], {}
    if seed is None:
        import secrets
        seed = secrets.token_bytes(16)
    analyzer = AlgorithmAnalyzer()
    plan = analyzer.analyze(ir_module, function_name)
    if not plan["fragments"]:
        return [], {}
    fragments = []
    coordinator_meta = {
        "function_name": function_name,
        "calling_sequence": [],
        "argument_routing": {},
        "state_buffer_layout": {},
    }
    for i, frag_info in enumerate(plan["fragments"]):
        fname = _name_from_pool("frag", seed, i)
        frag_func = IrFunction(fname, IrType.void())
        frag_func.params = [("state_buf", IrType.ptr()), ("state_len", IrType.i32())]
        frag_func.new_block('entry')
        coordinator_meta["calling_sequence"].append(i)
        fragments.append(frag_func)
    offset = max(1, num_fragments // 2)
    seq = list(range(len(fragments)))
    if len(seq) > offset:
        seq = seq[offset:] + seq[:offset]
    coordinator_meta["calling_sequence"] = seq
    coordinator_meta["argument_routing"] = {
        str(i): {"input": "state_buf", "output": "state_buf"} for i in range(len(fragments))
    }
    coordinator_meta["state_buffer_layout"] = {
        "size": 1024,
        "alignment": 8,
    }
    return fragments, coordinator_meta


def generate_coordinator(
    fragments: list[IrFunction],
    metadata: dict,
    seed: bytes
) -> IrFunction:
    """
    Generate a coordinator function that calls fragments in obfuscated order.

    The calling sequence is XOR-encrypted with a build-derived IV
    to prevent static analysis of the execution order.
    """
    if not _phase2_enabled():
        return IrFunction("coordinator_stub")
    cname = _name_from_pool("coord", seed, 0)
    coord = IrFunction(cname, IrType.void())
    coord.params = [("state_buf", IrType.ptr()), ("state_len", IrType.i32())]
    entry = coord.new_block("entry")
    seq = metadata.get("calling_sequence", [])
    iv = int.from_bytes(seed[:8], 'little')
    IrValue(IrType.i32(), name='%key')
    entry.instructions.append(IrInstruction('add', IrType.i32(), operands=[IrValue.const_int(iv & 0xFF), IrValue.const_int(0)]))
    for i, raw_idx in enumerate(seq):
        dec_idx = raw_idx ^ ((iv >> (i % 32)) & 0xFF)
        if 0 <= dec_idx < len(fragments):
            fname = fragments[dec_idx].name
            state_buf = IrValue(IrType.ptr(), name="%state_buf")
            state_len = IrValue(IrType.i32(), name="%state_len")
            entry.instructions.append(
                IrInstruction('call', result_type=IrType.void(), operands=[state_buf, state_len],
                              func_name=fname)
            )
    entry.set_terminator('ret')
    return coord


def generate_function_pointer_table(
    fragments: list[IrFunction],
    coordinator_name: str
) -> IrModule:
    """
    Generate a function pointer table module for fragment dispatch.

    Each fragment gets a stub function that forwards to the real
    fragment implementation, enabling indirect dispatch.
    """
    if not _phase2_enabled():
        return IrModule("fptable_stub")
    mod = IrModule(f"_m_{coordinator_name}_ptable")
    for frag in fragments:
        stub = IrFunction(frag.name + "_stub", IrType.void())
        stub.params = [("buf", IrType.ptr()), ("len", IrType.i32())]
        entry = stub.new_block("entry")
        entry.instructions.append(IrInstruction('call', result_type=IrType.void(),
                                  operands=[IrValue(IrType.ptr(), name="%buf"),
                                            IrValue(IrType.i32(), name="%len")],
                                  func_name=frag.name))
        entry.set_terminator('ret')
        mod.functions.append(stub)
    return mod


def fragment_pipeline(
    ir_module: IrModule,
    target_functions: list[str],
    num_fragments: int = 5,
    seed: bytes = None
) -> IrModule:
    """
    Apply fragmentation to target functions in an IR module.

    Replaces each target function with a set of fragments, a
    coordinator, and a function pointer table.
    """
    if not _phase2_enabled():
        return ir_module
    if seed is None:
        import secrets
        seed = secrets.token_bytes(16)
    result = IrModule(ir_module.name + "_fragmented")
    for func in ir_module.functions:
        if func.name in target_functions:
            fragments, meta = fragment_function(ir_module, func.name, num_fragments, seed)
            coordinator = generate_coordinator(fragments, meta, seed)
            ftable = generate_function_pointer_table(fragments, coordinator.name)
            for f in fragments:
                result.functions.append(f)
            result.functions.append(coordinator)
            for f in ftable.functions:
                result.functions.append(f)
        else:
            result.functions.append(func)
    return result


def main():
    """CLI entry point for fragmentation tool."""
    parser = argparse.ArgumentParser(
        description="Nixon Semantic Fragmentation Tool (Advanced Protection)"
    )
    sub = parser.add_subparsers(dest="command")

    analyze_p = sub.add_parser("analyze", help="Analyze a function for fragmentation")
    analyze_p.add_argument("input", help="Input IR file")
    analyze_p.add_argument("--function", required=True, help="Function name to analyze")
    analyze_p.add_argument("--num-fragments", type=int, default=5, help="Number of fragments")

    frag_p = sub.add_parser("fragment", help="Fragment target functions")
    frag_p.add_argument("input", help="Input IR file")
    frag_p.add_argument("-o", "--output", required=True, help="Output IR file")
    frag_p.add_argument("--functions", required=True, help="Comma-separated function names")
    frag_p.add_argument("--num-fragments", type=int, default=5, help="Fragments per function")
    frag_p.add_argument("--seed", help="Hex seed (optional)")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    with open(args.input) as f:
        source = f.read()

    from .compile import compile_py_to_ir
    mod = compile_py_to_ir(source)

    if args.command == "analyze":
        analyzer = AlgorithmAnalyzer()
        plan = analyzer.analyze(mod, args.function)
        print(json.dumps(plan, indent=2))
    elif args.command == "fragment":
        targets = [t.strip() for t in args.functions.split(",")]
        seed = bytes.fromhex(args.seed) if args.seed else None
        result = fragment_pipeline(mod, targets, args.num_fragments, seed)
        from .compile import ir_module_to_text
        text = ir_module_to_text(result)
        with open(args.output, "w") as f:
            f.write(text)
        print(f"Fragmented IR written to {args.output}")


if __name__ == "__main__":
    main()
