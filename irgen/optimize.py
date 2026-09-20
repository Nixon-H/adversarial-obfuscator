"""
optimize.py

Purpose:
IR optimization passes. Applies constant folding, dead code elimination,
basic block merging, and store-to-load forwarding to reduce and simplify
IR before code generation.

Architectural Role:
Cleanup pass applied after obfuscation transforms. Removes trivially
dead code, folds constant expressions, merges empty blocks, and forwards
store values to subsequent loads. This reduces the IR size and improves
downstream code generation quality.

Security Relevance:
- Constant folding eliminates obvious constants that leak information
  about algorithm structure.
- Dead code elimination removes unreachable blocks that could serve
  as analysis anchors.
- Block merging reduces the CFG complexity that attackers can use for
  structural fingerprinting.
- Optimization is applied both before and after obfuscation passes.

Dependencies:
    - irgen.compile (IrModule, IrFunction, IrBlock, IrInstruction, IrValue, IrType)
"""

from __future__ import annotations
from typing import Optional

from .compile import IrModule, IrFunction, IrBlock, IrInstruction, IrValue, IrType


def optimize(module: IrModule, level: int = 2) -> IrModule:
    """
    Apply optimization passes to an IR module.

    Level 1: constant folding + dead code elimination.
    Level 2: adds basic block merging + store-to-load forwarding.

    Iterates until fixpoint (no changes) or 10 iterations.
    """
    if level < 1:
        return module

    for _ in range(10):
        before = _module_hash(module)
        module = _constant_folding(module)
        module = _dead_code_elimination(module)
        if level >= 2:
            module = _basic_block_merging(module)
            module = _store_to_load_forwarding(module)
        module = _dead_code_elimination(module)
        if _module_hash(module) == before:
            break

    return module


def _module_hash(module: IrModule) -> int:
    """Compute a hash of the module for fixpoint detection."""
    return hash(str(module))


def _constant_folding(module: IrModule) -> IrModule:
    """
    Fold constant expressions into their results.

    For each instruction that is a constant (all operands are literal),
    evaluates the expression at compile time and replaces the result
    with the folded constant. The original instruction is replaced
    with a NOP.
    """
    for func in module.functions:
        for block in func.blocks:
            for inst in block.instructions:
                if inst.is_constant():
                    folded = _fold_instruction(inst)
                    if folded is not None and inst.result is not None:
                        inst.result.name = folded.name
                        inst.result.type = folded.type
                        inst.opcode = 'nop'
                        inst.result_type = None
            block.instructions = [i for i in block.instructions if i.opcode != 'nop']
    return module


def _fold_instruction(inst: IrInstruction) -> Optional[IrValue]:
    """
    Attempt to fold a constant instruction.

    Evaluates the operation at compile time. Returns a constant
    IrValue if successful, None otherwise.
    """
    try:
        vals = []
        for op in inst.operands:
            if isinstance(op, IrValue):
                if op.name.lstrip('-').isdigit():
                    vals.append(int(op.name))
                elif op.name in ('true', '1'):
                    vals.append(True)
                elif op.name in ('false', '0'):
                    vals.append(False)
                else:
                    return None
            elif isinstance(op, IrType):
                continue
            else:
                try:
                    int(str(op))
                    vals.append(int(str(op)))
                except (ValueError, TypeError):
                    return None

        result = None
        type_ = inst.result_type

        if inst.opcode == 'add' and len(vals) >= 2:
            result = vals[0] + vals[1]
        elif inst.opcode == 'sub' and len(vals) >= 2:
            result = vals[0] - vals[1]
        elif inst.opcode == 'mul' and len(vals) >= 2:
            result = vals[0] * vals[1]
        elif inst.opcode == 'div' and len(vals) >= 2 and vals[1] != 0:
            result = vals[0] // vals[1]
        elif inst.opcode == 'mod' and len(vals) >= 2 and vals[1] != 0:
            result = vals[0] % vals[1]
        elif inst.opcode == 'and' and len(vals) >= 2:
            result = vals[0] & vals[1]
        elif inst.opcode == 'or' and len(vals) >= 2:
            result = vals[0] | vals[1]
        elif inst.opcode == 'xor' and len(vals) >= 2:
            result = vals[0] ^ vals[1]
        elif inst.opcode == 'shl' and len(vals) >= 2:
            result = vals[0] << vals[1]
        elif inst.opcode == 'shr' and len(vals) >= 2:
            result = vals[0] >> vals[1]
        elif inst.opcode == 'eq' and len(vals) >= 2:
            result = 1 if vals[0] == vals[1] else 0
        elif inst.opcode == 'ne' and len(vals) >= 2:
            result = 1 if vals[0] != vals[1] else 0
        elif inst.opcode == 'lt' and len(vals) >= 2:
            result = 1 if vals[0] < vals[1] else 0
        elif inst.opcode == 'le' and len(vals) >= 2:
            result = 1 if vals[0] <= vals[1] else 0
        elif inst.opcode == 'gt' and len(vals) >= 2:
            result = 1 if vals[0] > vals[1] else 0
        elif inst.opcode == 'ge' and len(vals) >= 2:
            result = 1 if vals[0] >= vals[1] else 0
        elif inst.opcode == 'zext' and len(vals) >= 1:
            result = vals[0]
        elif inst.opcode == 'trunc' and len(vals) >= 1:
            result = vals[0] & 1

        if result is not None:
            if type_ and type_.kind == 'i1':
                return IrValue.const_bool(bool(result))
            return IrValue.const_int(int(result))
    except (ValueError, TypeError, ZeroDivisionError):
        pass
    return None


def _dead_code_elimination(module: IrModule) -> IrModule:
    """
    Remove instructions whose results are never used.

    An instruction is dead if its result value has no users in the
    function and the instruction is not a store, call, alloca, or
    load (which have side effects). Iterates to fixpoint.
    """
    for func in module.functions:
        changed = True
        while changed:
            changed = False
            used_values: set[int] = set()

            for block in func.blocks:
                for inst in block.instructions:
                    if inst.opcode in ('store', 'call', 'alloca'):
                        for op in inst.operands:
                            if isinstance(op, IrValue):
                                used_values.add(op.id)
                    elif inst.opcode == 'ret':
                        for op in inst.operands:
                            if isinstance(op, IrValue):
                                used_values.add(op.id)
                    elif inst.result is not None:
                        for op in inst.operands:
                            if isinstance(op, IrValue):
                                used_values.add(op.id)
                    elif inst.opcode == 'jmp':
                        pass
                    elif inst.opcode == 'br':
                        for op in inst.operands:
                            if isinstance(op, IrValue):
                                used_values.add(op.id)

                if block.terminator:
                    for op in block.terminator.operands:
                        if isinstance(op, IrValue):
                            used_values.add(op.id)

            for block in func.blocks:
                new_insts = []
                for inst in block.instructions:
                    keep = True
                    if inst.result is not None and inst.result.id not in used_values:
                        if inst.opcode not in ('call', 'store', 'alloca', 'load'):
                            keep = False
                    if keep:
                        new_insts.append(inst)
                    else:
                        changed = True
                block.instructions = new_insts
    return module


def _basic_block_merging(module: IrModule) -> IrModule:
    """
    Merge adjacent basic blocks when one has a single successor
    and the other has a single predecessor.

    A block ending with 'jmp' to the next block can be merged by
    appending its instructions and copying the terminator.
    """
    for func in module.functions:
        if len(func.blocks) < 2:
            continue
        merged = True
        while merged:
            merged = False
            i = 0
            while i < len(func.blocks) - 1:
                current = func.blocks[i]
                next_block = func.blocks[i + 1]

                if _can_merge(current, next_block):
                    successors = _get_successors(current)
                    if len(successors) == 1 and successors[0] == next_block.label:
                        predecessors = _get_predecessors(func, next_block)
                        if len(predecessors) == 1 and predecessors[0] == current.label:
                            current.instructions.extend(next_block.instructions)
                            current.terminator = next_block.terminator
                            if current.terminator:
                                current.terminator.parent_block = current
                            func.blocks.pop(i + 1)
                            merged = True
                            continue
                i += 1
    return module


def _can_merge(block: IrBlock, next_block: IrBlock) -> bool:
    """Check if two blocks can be merged (current ends with 'jmp')."""
    if block.terminator is None or next_block.terminator is None:
        return False
    return block.terminator.opcode == 'jmp'


def _get_successors(block: IrBlock) -> list[str]:
    """Get successor block labels for a given block."""
    if block.terminator is None:
        return []
    if block.terminator.opcode == 'jmp':
        return [block.terminator.operands[0]]
    if block.terminator.opcode == 'br' and len(block.terminator.operands) >= 3:
        return [block.terminator.operands[1], block.terminator.operands[2]]
    return []


def _get_predecessors(func: IrFunction, block: IrBlock) -> list[str]:
    """
    Get predecessor block labels for a given block.

    Scans all blocks in the function for terminators that reference
    this block's label.
    """
    preds = []
    for b in func.blocks:
        if b is block:
            continue
        succs = _get_successors(b)
        if block.label in succs:
            preds.append(b.label)
    return preds


def _store_to_load_forwarding(module: IrModule) -> IrModule:
    """
    Forward stored values to subsequent loads from the same pointer.

    When a store is followed by a load from the same pointer (with
    no intervening store to the same pointer), the load result is
    replaced with the stored value and the load is removed.
    """
    for func in module.functions:
        for block in func.blocks:
            i = 0
            while i < len(block.instructions):
                inst = block.instructions[i]
                if inst.opcode == 'store':
                    store_val = None
                    store_ptr = None
                    seen_val = False
                    for op in inst.operands:
                        if isinstance(op, IrValue):
                            if not seen_val:
                                store_val = op
                                seen_val = True
                            else:
                                store_ptr = op
                                break

                    if store_val is not None and store_ptr is not None:
                        j = i + 1
                        while j < len(block.instructions):
                            next_inst = block.instructions[j]
                            if next_inst.opcode == 'load':
                                load_ptr = next_inst.operands[0] if next_inst.operands else None
                                if load_ptr is not None and load_ptr.id == store_ptr.id:
                                    _replace_all_uses(block, func, next_inst.result, store_val)
                                    block.instructions.pop(j)
                                    continue
                            elif next_inst.opcode == 'store':
                                next_store_val = next_inst.operands[1] if len(next_inst.operands) > 1 else None
                                if next_store_val is not None and next_store_val.id == store_ptr.id:
                                    break
                            j += 1
                i += 1
    return module


def _replace_all_uses(block: IrBlock, func: IrFunction, old_val: IrValue, new_val: IrValue):
    """
    Replace all uses of old_val with new_val in the function.

    Updates operands in all instructions and terminators across
    all blocks.
    """
    for b in func.blocks:
        for inst in b.instructions:
            for k, op in enumerate(inst.operands):
                if isinstance(op, IrValue) and op.id == old_val.id:
                    inst.operands[k] = new_val
        if b.terminator:
            for k, op in enumerate(b.terminator.operands):
                if isinstance(op, IrValue) and op.id == old_val.id:
                    b.terminator.operands[k] = new_val
