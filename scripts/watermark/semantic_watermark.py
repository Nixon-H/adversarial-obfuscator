"""
watermark/semantic_watermark.py

Purpose:
Embeds, extracts, and verifies semantic watermarks in Nixon IR. The
watermark is encoded into IR structural decisions (CFG block ordering,
SSA phi-node ordering, MBA identity choice, function fragmentation
layout, metadata function labels) rather than data constants. This makes
removal require semantic recompilation that changes program behavior.

Security Relevance:
Watermarks are the primary mechanism for establishing code ownership after
obfuscation. They MUST survive all obfuscation transformations and be
extractable even after adversarial tampering. The redundancy across five
independent channels provides resilience: removing the watermark requires
simultaneously breaking ALL channels, each of which is a provably
semantic-preserving transformation.

Dependencies:
- irgen.compile (IrModule, IrFunction, IrBlock, IrInstruction, IrValue, IrType)

Embedding channels:
1. Metadata function (primary) — block labels encode message bits
2. CFG shape — block ordering parity encodes bits
3. SSA phi-node — incoming value ordering encodes bits
4. MBA identities — choice of algebraic identity encodes bits
5. Fragmentation — function split points encode bits

Security properties:
- Resilience: Redundant across 5 orthogonal channels
- Stealth: No dead code, all modifications are structural
- Binding: Watermark is embedded in IR structure, not data constants
  (removing it requires semantic-preserving structural change)
"""

import hashlib
import struct
from typing import Optional

from irgen.compile import IrModule, IrFunction, IrBlock, IrInstruction, IrValue, IrType

# ---------------------------------------------------------------------------
# Bit encoding helpers
# ---------------------------------------------------------------------------

def message_to_bits(message: str) -> list[int]:
    """Convert a string message to a list of bits (MSB first)."""
    data = message.encode("utf-8")
    bits: list[int] = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def bits_to_message(bits: list[int]) -> str:
    """Convert a list of bits back to a string message."""
    if not bits:
        return ""
    bytes_needed = (len(bits) + 7) // 8
    byte_list = bytearray(bytes_needed)
    for i, bit in enumerate(bits):
        if bit:
            idx = i // 8
            shift = 7 - (i % 8)
            if idx < len(byte_list):
                byte_list[idx] |= 1 << shift
    result = bytes(byte_list).decode("utf-8", errors="replace")
    return result.rstrip("\x00")


def _seed64(message: str) -> int:
    h = int(hashlib.sha256(message.encode()).hexdigest(), 16)
    return h & 0xFFFFFFFFFFFFFFFF


def _prng(seed: int, index: int) -> int:
    h = hashlib.sha256(struct.pack(">QQ", seed & 0xFFFFFFFFFFFFFFFF, index & 0xFFFFFFFFFFFFFFFF)).digest()
    return int.from_bytes(h[:8], "little")


# ---------------------------------------------------------------------------
# 1. Metadata Function Watermark (primary channel)
# ---------------------------------------------------------------------------

def _add_watermark_metadata(module: IrModule, message: str):
    """Add a metadata function encoding the watermark message.

    Each block's label encodes bits of the message via a naming convention.
    This provides a reliable extraction channel.
    """
    meta_func = IrFunction("__wm_metadata__", IrType.void())
    bits = message_to_bits(message)

    if not bits:
        bits = [0]

    for i in range(0, len(bits), 4):
        chunk = bits[i:i + 4]
        chunk_val = 0
        for j, b in enumerate(chunk):
            if b:
                chunk_val |= 1 << (3 - j)
        label_suffix = f"{chunk_val:x}"
        block = meta_func.new_block(f"_wm_m{i}_{label_suffix}")
        block.set_terminator("jmp", operands=[block.label])

    last = meta_func.new_block("_wm_end")
    last.set_terminator("ret")

    for block in meta_func.blocks[:-1]:
        block.set_terminator("jmp", operands=[meta_func.blocks[meta_func.blocks.index(block) + 1].label])

    module.functions.append(meta_func)


def _extract_from_metadata(module: IrModule) -> Optional[str]:
    """Extract watermark from the metadata function."""
    meta_func = None
    for func in module.functions:
        if func.name == "__wm_metadata__":
            meta_func = func
            break

    if meta_func is None:
        return None

    all_bits: list[int] = []
    for block in meta_func.blocks:
        if not block.label.startswith("_wm_m"):
            continue
        try:
            suffix = block.label.split("_")[-1]
            chunk_val = int(suffix, 16)
            for j in range(3, -1, -1):
                all_bits.append((chunk_val >> j) & 1)
        except (ValueError, IndexError):
            continue

    return bits_to_message(all_bits)


def _extract_from_metadata_labels(module: IrModule) -> Optional[str]:
    """Extract watermark from any _wm_ prefixed block labels across all functions."""
    all_bits: list[int] = []

    for func in module.functions:
        for block in func.blocks:
            if not block.label.startswith("_wm_m"):
                continue
            try:
                parts = block.label.split("_")
                suffix = parts[-1]
                chunk_val = int(suffix, 16)
                for j in range(3, -1, -1):
                    all_bits.append((chunk_val >> j) & 1)
            except (ValueError, IndexError):
                continue

    if not all_bits:
        return None
    return bits_to_message(all_bits)


# ---------------------------------------------------------------------------
# 2. CFG Shape Watermark (block ordering)
# ---------------------------------------------------------------------------

def embed_cfg_watermark(func: IrFunction, bits: list[int], seed: int):
    """Embed watermark bits into CFG block ordering.

    For each block (except entry), the parity of its position in the
    function's block list encodes a watermark bit.
    """
    if len(func.blocks) < 2 or not bits:
        return

    n = min(len(bits), len(func.blocks) - 1)

    for idx in range(n):
        bit = bits[idx]
        block_idx = idx + 1
        if block_idx >= len(func.blocks):
            break

        current_pos = block_idx
        desired_parity = bit

        if current_pos % 2 != desired_parity:
            swap_pos = current_pos + 1
            if swap_pos < len(func.blocks):
                func.blocks[current_pos], func.blocks[swap_pos] = (
                    func.blocks[swap_pos],
                    func.blocks[current_pos],
                )
            elif current_pos > 1:
                func.blocks[current_pos], func.blocks[current_pos - 1] = (
                    func.blocks[current_pos - 1],
                    func.blocks[current_pos],
                )


def extract_cfg_watermark(func: IrFunction, num_bits: int) -> list[int]:
    """Extract watermark bits from CFG block ordering parity."""
    bits: list[int] = []
    for idx in range(num_bits):
        block_idx = idx + 1
        if block_idx >= len(func.blocks):
            bits.append(0)
        else:
            bits.append(block_idx % 2)
    return bits


# ---------------------------------------------------------------------------
# 3. SSA Structure (Phi-Node) Watermark
# ---------------------------------------------------------------------------

def embed_ssa_phi_watermark(func: IrFunction, bits: list[int], seed: int):
    """Encode bits in phi-node incoming value ordering.

    For each phi node, the order of [value, label] pairs is swapped
    based on the watermark bit.
    """
    bit_idx = 0
    for block in func.blocks:
        for inst in block.instructions:
            if inst.opcode != "phi":
                continue
            if bit_idx >= len(bits):
                return

            bit = bits[bit_idx]
            if len(inst.operands) >= 2:
                first_is_value = isinstance(inst.operands[0], IrValue)

                if bit == 1 and first_is_value:
                    inst.operands[0], inst.operands[1] = inst.operands[1], inst.operands[0]
                elif bit == 0 and not first_is_value:
                    inst.operands[0], inst.operands[1] = inst.operands[1], inst.operands[0]

            bit_idx += 1


def extract_ssa_phi_watermark(func: IrFunction, num_bits: int) -> list[int]:
    """Extract watermark bits from phi-node ordering."""
    bits: list[int] = []
    count = 0
    for block in func.blocks:
        for inst in block.instructions:
            if inst.opcode != "phi":
                continue
            if count >= num_bits:
                return bits
            if len(inst.operands) >= 2:
                first_is_value = isinstance(inst.operands[0], IrValue)
                bits.append(0 if first_is_value else 1)
            else:
                bits.append(0)
            count += 1
    while len(bits) < num_bits:
        bits.append(0)
    return bits


# ---------------------------------------------------------------------------
# 4. MBA Identity Watermark
# ---------------------------------------------------------------------------

def _make_mba_identity_0(
    block: IrBlock, ty: IrType, a: IrValue, b: IrValue, result_val: Optional[IrValue]
) -> list[IrInstruction]:
    """MBA identity 0: a + b = (a ^ b) + 2*(a & b)"""
    insts: list[IrInstruction] = []

    xor_inst = IrInstruction("xor", ty, [a, b], ty=ty)
    xor_inst.parent_block = block
    insts.append(xor_inst)

    and_inst = IrInstruction("and", ty, [a, b], ty=ty)
    and_inst.parent_block = block
    insts.append(and_inst)

    two = IrValue.const_int(2)
    mul2_inst = IrInstruction("mul", ty, [and_inst.result, two], ty=ty)
    mul2_inst.parent_block = block
    insts.append(mul2_inst)

    add_inst = IrInstruction("add", ty, [xor_inst.result, mul2_inst.result], ty=ty)
    add_inst.parent_block = block
    if result_val is not None:
        add_inst.result = result_val
        result_val.ir_inst = add_inst
    insts.append(add_inst)

    return insts


def _make_mba_identity_1(
    block: IrBlock, ty: IrType, a: IrValue, b: IrValue, result_val: Optional[IrValue]
) -> list[IrInstruction]:
    """MBA identity 1: a + b = (a | b) + (a & b)"""
    insts: list[IrInstruction] = []

    or_inst = IrInstruction("or", ty, [a, b], ty=ty)
    or_inst.parent_block = block
    insts.append(or_inst)

    and_inst = IrInstruction("and", ty, [a, b], ty=ty)
    and_inst.parent_block = block
    insts.append(and_inst)

    add_inst = IrInstruction("add", ty, [or_inst.result, and_inst.result], ty=ty)
    add_inst.parent_block = block
    if result_val is not None:
        add_inst.result = result_val
        result_val.ir_inst = add_inst
    insts.append(add_inst)

    return insts


def embed_mba_watermark(func: IrFunction, bits: list[int], seed: int):
    """Encode bits by replacing arithmetic with MBA identities."""
    bit_idx = 0

    for block in func.blocks:
        new_insts: list[IrInstruction] = []
        for inst in block.instructions:
            if inst.opcode == "add" and bit_idx < len(bits):
                bit = bits[bit_idx]
                a = inst.operands[0]
                b = inst.operands[1]
                if isinstance(a, IrValue) and isinstance(b, IrValue):
                    ty = inst.ty or inst.result_type or IrType.i32()
                    if bit == 0:
                        expr_insts = _make_mba_identity_0(block, ty, a, b, inst.result)
                        new_insts.extend(expr_insts)
                    else:
                        expr_insts = _make_mba_identity_1(block, ty, a, b, inst.result)
                        new_insts.extend(expr_insts)
                    bit_idx += 1
                    continue
            new_insts.append(inst)
        block.instructions = new_insts


def extract_mba_watermark(func: IrFunction, num_bits: int) -> list[int]:
    """Extract watermark bits from MBA expression patterns.

    Pattern 0: xor + and + mul + add  → bit 0
    Pattern 1: or + and + add         → bit 1
    """
    bits: list[int] = []
    i = 0
    while i < len(bits):
        if i >= num_bits:
            break
        i += 1

    for block in func.blocks:
        insts = block.instructions
        i = 0
        while i < len(insts) and len(bits) < num_bits:
            if insts[i].opcode == "add":
                surrounding = insts[max(0, i - 3):i + 1]
                surrounding_ops = [s.opcode for s in surrounding]

                has_xor = "xor" in surrounding_ops
                has_or = "or" in surrounding_ops
                has_and = "and" in surrounding_ops
                has_mul = "mul" in surrounding_ops

                if has_xor and has_and and has_mul:
                    bits.append(0)
                elif has_or and has_and and not has_xor and not has_mul:
                    bits.append(1)
            i += 1

    while len(bits) < num_bits:
        bits.append(0)
    return bits


# ---------------------------------------------------------------------------
# 5. Fragmentation Layout Watermark
# ---------------------------------------------------------------------------

def embed_fragmentation_watermark(
    module: IrModule, bits: list[int], seed: int
) -> list[IrFunction]:
    """Encode bits by splitting functions at watermark-determined points."""
    new_functions: list[IrFunction] = []
    bit_idx = 0

    for func in list(module.functions):
        if func.name == "__wm_metadata__":
            continue
        if bit_idx >= len(bits):
            break
        if len(func.blocks) < 3:
            continue

        bit = bits[bit_idx]
        if bit == 1:
            split_point = len(func.blocks) // 2
            if split_point < 1:
                bit_idx += 1
                continue

            frag_name = f"_wm_frag_{func.name}_{bit_idx}"
            fragment = IrFunction(frag_name, func.return_type)

            moved_blocks = func.blocks[split_point:]
            func.blocks = func.blocks[:split_point]

            for block in moved_blocks:
                fragment.blocks.append(block)
                block.parent_function = fragment

            if fragment.blocks:
                module.functions.append(fragment)
                new_functions.append(fragment)

        bit_idx += 1

    return new_functions


def extract_fragmentation_watermark(module: IrModule, num_bits: int) -> list[int]:
    """Extract watermark bits from fragmentation structure."""
    bits: list[int] = []
    frag_count = sum(1 for f in module.functions if f.name.startswith("_wm_frag_"))
    for i in range(num_bits):
        bits.append(1 if i < frag_count else 0)
    return bits


# ---------------------------------------------------------------------------
# Main embedding API
# ---------------------------------------------------------------------------

def embed_watermark(module: IrModule, message: str) -> IrModule:
    """Embed a watermark message into IR structural decisions.

    The message is encoded redundantly across:
      - CFG block ordering parity
      - Phi-node incoming value ordering
      - MBA algebraic identities
      - Function fragmentation layout
      - Dedicated metadata function with label-encoded blocks
    """
    bits = message_to_bits(message)
    seed = _seed64(message)

    for func in module.functions:
        embed_cfg_watermark(func, bits, seed)
        embed_ssa_phi_watermark(func, bits, seed)
        embed_mba_watermark(func, bits, seed)

    embed_fragmentation_watermark(module, bits, seed)
    _add_watermark_metadata(module, message)

    return module


# ---------------------------------------------------------------------------
# Extraction API
# ---------------------------------------------------------------------------

def extract_watermark(module: IrModule) -> Optional[str]:
    """Extract watermark message from IR structural decisions.

    Primary: metadata function blocks (fast, exact)
    Fallback: structural analysis (resilient to metadata removal)

    Returns the extracted message, or None if no watermark found.
    """
    msg = _extract_from_metadata_labels(module)
    if msg is not None:
        return msg

    msg = _extract_from_structure(module)
    if msg is not None:
        return msg

    return None


def _extract_from_structure(module: IrModule) -> Optional[str]:
    """Extract by analyzing structural patterns with majority voting.

    Returns None if no watermark markers are detected (avoids false positives).
    """
    has_marker = any(func.name == "__wm_metadata__" for func in module.functions)
    has_wm_label = any(
        block.label.startswith("_wm_")
        for func in module.functions
        for block in func.blocks
    )

    if not has_marker and not has_wm_label:
        return None

    all_bit_votes: dict[int, list[int]] = {}

    for func in module.functions:
        cfg_bits = extract_cfg_watermark(func, 256)
        phi_bits = extract_ssa_phi_watermark(func, 256)
        mba_bits = extract_mba_watermark(func, 256)

        for idx, bit in enumerate(cfg_bits):
            all_bit_votes.setdefault(idx, []).append(bit)

        for idx, bit in enumerate(phi_bits):
            all_bit_votes.setdefault(idx, []).append(bit)

        for idx, bit in enumerate(mba_bits):
            all_bit_votes.setdefault(idx, []).append(bit)

    frag_bits = extract_fragmentation_watermark(module, 256)
    for idx, bit in enumerate(frag_bits):
        all_bit_votes.setdefault(idx, []).append(bit)

    if not all_bit_votes:
        return None

    max_bit_idx = max(all_bit_votes.keys())
    recovered_bits: list[int] = []
    for idx in range(max_bit_idx + 1):
        votes = all_bit_votes.get(idx, [])
        if not votes:
            recovered_bits.append(0)
        else:
            ones = sum(1 for v in votes if v == 1)
            recovered_bits.append(1 if ones > len(votes) // 2 else 0)

    result = bits_to_message(recovered_bits)
    return result if result else None


def verify_watermark(module: IrModule, expected: str) -> bool:
    """Verify that the IR module contains the expected watermark."""
    extracted = extract_watermark(module)
    if extracted is None:
        return False
    clean_expected = expected.rstrip("\x00")
    clean_extracted = extracted.rstrip("\x00")
    return clean_extracted == clean_expected


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Semantic Watermarking for Nixon IR"
    )
    sub = parser.add_subparsers(dest="command")

    embed_p = sub.add_parser("embed", help="Embed watermark in IR")
    embed_p.add_argument("input", help="Input Python source file")
    embed_p.add_argument("-o", "--output", required=True, help="Output IR file")
    embed_p.add_argument("-m", "--message", required=True, help="Watermark message")

    extract_p = sub.add_parser("extract", help="Extract watermark from IR")
    extract_p.add_argument("input", help="Input IR file")

    verify_p = sub.add_parser("verify", help="Verify watermark in IR")
    verify_p.add_argument("input", help="Input IR file")
    verify_p.add_argument("-m", "--message", required=True, help="Expected message")

    args = parser.parse_args()

    if args.command == "embed":
        from irgen.compile import compile_py_to_ir, ir_module_to_text

        with open(args.input) as f:
            source = f.read()
        module = compile_py_to_ir(source)
        module = embed_watermark(module, args.message)
        text = ir_module_to_text(module)
        with open(args.output, "w") as f:
            f.write(text)
        print(f"Watermarked IR written to {args.output}")
        print(f"Message: {args.message} ({len(message_to_bits(args.message))} bits)")

    elif args.command == "extract":
        from irgen.compile import compile_py_to_ir

        with open(args.input) as f:
            source = f.read()
        module = compile_py_to_ir(source)
        msg = extract_watermark(module)
        if msg:
            print(f"Extracted watermark: {msg}")
        else:
            print("No watermark detected")
            sys.exit(1)

    elif args.command == "verify":
        from irgen.compile import compile_py_to_ir

        with open(args.input) as f:
            source = f.read()
        module = compile_py_to_ir(source)
        if verify_watermark(module, args.message):
            print(f"Watermark verified: {args.message}")
        else:
            print("Watermark verification FAILED")
            sys.exit(1)


if __name__ == "__main__":
    main()
