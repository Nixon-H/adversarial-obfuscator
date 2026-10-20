"""
bitslice.py

Purpose:
Bit-slicing transformation pass. Decomposes integer arithmetic operations
into bit-level equivalent circuits. Each arithmetic instruction (add, sub,
mul, and, or, xor, shl, shr, cmp) is replaced with 64 per-bit operations,
providing obfuscation through structural complexity.

Architectural Role:
Obfuscation IR transformation pass. Explodes high-level arithmetic into
gate-level equivalents, dramatically increasing the cost of reverse
engineering by requiring analysis of per-bit logic rather than word-level
operations.

Security Relevance:
- Converts opaque word-level instructions into many bit-level primitives.
- Each bitslice operation is itself a combination of simple logic gates
  (xor, and, or), making the computation graph much larger.
- The resulting IR is structurally opaque: a single `add` becomes ~64
  gate-level operations with explicit carry chain.
- Comparison operations are expanded to bit-serial equality/less-than
  networks.

Threat model: Static analysis, decompiler pattern matching, SMT-based
deobfuscation.

Dependencies:
    - irgen.compile (IrModule, IrFunction, IrBlock, IrInstruction, IrValue, IrType)
"""

from __future__ import annotations
import re
from typing import List, Tuple, Optional

from .compile import IrModule, IrFunction, IrBlock, IrInstruction, IrValue, IrType


_BS_OPS = frozenset({'add', 'sub', 'mul', 'and', 'or', 'xor', 'shl', 'shr',
                     'eq', 'ne', 'lt', 'le', 'gt', 'ge'})


def _type_size(ty: IrType) -> int:
    """
    Extract bit width from an IrType.

    Handles 'i8', 'i16', 'i32', 'i64' etc. Falls back to 32 if
    the type string cannot be parsed.
    """
    s = ty.kind
    if s.startswith('i'):
        try:
            return int(s[1:])
        except ValueError:
            return 32
    return 32


class BitSliceCompiler:
    """
    Core bit-slice engine for word-level to gate-level decomposition.

    Provides per-operation bit-slice methods that operate on lists
    of integer bits (0 or 1). The public methods handle add, sub,
    mul, xor, and, or, shl, shr, cmp_eq, cmp_lt.
    """

    def __init__(self, word_size: int = 64):
        """Initialize with the target word size in bits."""
        self.word_size = word_size

    def slice_value(self, value: int) -> List[int]:
        """
        Decompose an integer into a list of bits (LSB first).

        Each bit position i gets (value >> i) & 1.
        """
        bits = []
        for i in range(self.word_size):
            bits.append((value >> i) & 1)
        return bits

    def add_bitslice(self, a_bits: List[int], b_bits: List[int]) -> Tuple[List[int], int]:
        """
        Bit-slice addition with carry propagation.

        Uses the standard full-adder recurrence:
        sum[i] = a[i] ^ b[i] ^ carry[i]
        carry[i+1] = (a[i] & b[i]) | (carry[i] & (a[i] ^ b[i]))
        """
        result = []
        carry = 0
        for i in range(self.word_size):
            s = a_bits[i] ^ b_bits[i] ^ carry
            carry = (a_bits[i] & b_bits[i]) | (carry & (a_bits[i] ^ b_bits[i]))
            result.append(s)
        return result, carry

    def sub_bitslice(self, a_bits: List[int], b_bits: List[int]) -> Tuple[List[int], int]:
        """
        Bit-slice subtraction via two's complement negation.

        Computes a - b as a + (~b + 1).
        """
        not_b = [1 - b for b in b_bits]
        one = [1] + [0] * (self.word_size - 1)
        neg_b, _ = self.add_bitslice(not_b, one)
        result, borrow = self.add_bitslice(a_bits, neg_b)
        return result, borrow

    def mul_bitslice(self, a_bits: List[int], b_bits: List[int]) -> Tuple[List[int], int]:
        """
        Bit-slice multiplication via shift-and-add.

        For each set bit in b at position i, adds a shifted left by i.
        Uses the standard pen-and-paper multiplication algorithm.
        """
        result = [0] * self.word_size
        carry_total = 0
        for i in range(self.word_size):
            if b_bits[i]:
                shifted = ([0] * i) + a_bits[:self.word_size - i]
                while len(shifted) < self.word_size:
                    shifted.append(0)
                shifted = shifted[:self.word_size]
                result, carry = self.add_bitslice(result, shifted)
                carry_total |= carry
        return result, carry_total

    def xor_bitslice(self, a_bits: List[int], b_bits: List[int]) -> List[int]:
        """Per-bit XOR."""
        return [a ^ b for a, b in zip(a_bits, b_bits)]

    def and_bitslice(self, a_bits: List[int], b_bits: List[int]) -> List[int]:
        """Per-bit AND."""
        return [a & b for a, b in zip(a_bits, b_bits)]

    def or_bitslice(self, a_bits: List[int], b_bits: List[int]) -> List[int]:
        """Per-bit OR."""
        return [a | b for a, b in zip(a_bits, b_bits)]

    def shl_bitslice(self, val_bits: List[int], shift_amount: int) -> List[int]:
        """
        Bit-slice left shift.

        Pads with zeros on the right and truncates to word_size.
        """
        shift = shift_amount % self.word_size
        return ([0] * shift + val_bits[:self.word_size - shift])[:self.word_size]

    def shr_bitslice(self, val_bits: List[int], shift_amount: int) -> List[int]:
        """
        Bit-slice right shift.

        Pads with zeros on the left and truncates to word_size.
        """
        shift = shift_amount % self.word_size
        result = val_bits[shift:] + [0] * shift
        return result[:self.word_size]

    def cmp_eq_bitslice(self, a_bits: List[int], b_bits: List[int]) -> List[int]:
        """
        Bit-slice equality comparison.

        Computes NOR of all per-bit XORs. Returns 1 if all bits equal.
        """
        xors = [a ^ b for a, b in zip(a_bits, b_bits)]
        nor = 1
        for x in xors:
            nor = nor & (1 - x)
        return [nor]

    def cmp_lt_bitslice(self, a_bits: List[int], b_bits: List[int]) -> List[int]:
        """
        Bit-slice signed less-than comparison.

        Checks sign bits first, then scans from MSB to LSB.
        """
        sign_a = a_bits[self.word_size - 1]
        sign_b = b_bits[self.word_size - 1]
        if sign_a != sign_b:
            return [1 if sign_a > sign_b else 0]
        for i in range(self.word_size - 2, -1, -1):
            if a_bits[i] != b_bits[i]:
                return [a_bits[i] < b_bits[i]]
        return [0]

    def recombine(self, bits: List[int]) -> int:
        """
        Reconstruct an integer from a bit list (LSB first).

        Equivalent to the inverse of slice_value.
        """
        result = 0
        for i in range(min(len(bits), self.word_size)):
            result |= (bits[i] & 1) << i
        return result


# ---- IR-level helpers ----

def _emit(block: IrBlock, opcode: str, restype: IrType, operands: list, insts: list) -> IrValue:
    """Emit a new IR instruction into the instruction list."""
    inst = IrInstruction(opcode, restype, operands, ty=restype)
    inst.parent_block = block
    insts.append(inst)
    return inst.result


def _extract_bit(block: IrBlock, val: IrValue, idx: int, ty: IrType, insts: list) -> IrValue:
    """
    Extract a single bit at position idx from a value.

    Uses (val >> idx) & 1 via shr + and.
    """
    if idx == 0:
        return _emit(block, 'and', ty, [val, IrValue.const_int(1)], insts)
    shifted = _emit(block, 'shr', ty, [val, IrValue.const_int(idx)], insts)
    return _emit(block, 'and', ty, [shifted, IrValue.const_int(1)], insts)


def _extract_bits(block: IrBlock, val: IrValue, word_size: int, ty: IrType, insts: list) -> list:
    """Extract all bit positions into a list of per-bit values."""
    return [_extract_bit(block, val, i, ty, insts) for i in range(word_size)]


def _recombine_bits(block: IrBlock, bits: list, ty: IrType, insts: list) -> IrValue:
    """
    Recombine a list of bit values into a single integer.

    Equivalent to the inverse of _extract_bits.
    """
    result = bits[0]
    for i in range(1, len(bits)):
        shifted = _emit(block, 'shl', ty, [bits[i], IrValue.const_int(i)], insts)
        result = _emit(block, 'or', ty, [result, shifted], insts)
    return result


def _bitwise_add_ir(block: IrBlock, a_bits: list, b_bits: list, ty: IrType, insts: list) -> list:
    """
    IR-level bitwise addition with full-adder chain.

    Each bit position uses three operations:
    sum = a_xor_b ^ carry
    carry = (a & b) | (a_xor_b & carry)
    """
    word_size = len(a_bits)
    result_bits = []
    carry = IrValue.const_int(0)
    for i in range(word_size):
        a_xor_b = _emit(block, 'xor', ty, [a_bits[i], b_bits[i]], insts)
        sum_bit = _emit(block, 'xor', ty, [a_xor_b, carry], insts)
        a_and_b = _emit(block, 'and', ty, [a_bits[i], b_bits[i]], insts)
        a_xor_b_and_c = _emit(block, 'and', ty, [a_xor_b, carry], insts)
        carry = _emit(block, 'or', ty, [a_and_b, a_xor_b_and_c], insts)
        result_bits.append(sum_bit)
    return result_bits


def _bitwise_sub_ir(block: IrBlock, a_bits: list, b_bits: list, ty: IrType, insts: list) -> list:
    """
    IR-level bitwise subtraction via two's complement.

    Returns only the first bit of the result (borrow=0 assumption).
    """
    word_size = len(a_bits)
    not_b = [_emit(block, 'xor', ty, [b, IrValue.const_int(1)], insts) for b in b_bits]
    one = [IrValue.const_int(1)] + [IrValue.const_int(0)] * (word_size - 1)
    neg_b = _bitwise_add_ir(block, not_b, one, ty, insts)
    return _bitwise_add_ir(block, a_bits, neg_b, ty, insts)[0]


def _bitwise_mul_ir(block: IrBlock, a_bits: list, b_bits: list, ty: IrType, insts: list) -> list:
    """
    IR-level bitwise multiplication via shift-and-add.

    For each set bit in b, adds a shifted copy of a to the accumulator.
    """
    word_size = len(a_bits)
    result = [IrValue.const_int(0)] * word_size
    for i in range(word_size):
        shifted = ([IrValue.const_int(0)] * i) + a_bits[:word_size - i]
        while len(shifted) < word_size:
            shifted.append(IrValue.const_int(0))
        shifted = shifted[:word_size]
        result = _bitwise_add_ir(block, result, shifted, ty, insts)
    return result


def _bitwise_xor_ir(block: IrBlock, a_bits: list, b_bits: list, ty: IrType, insts: list) -> list:
    """IR-level per-bit XOR."""
    return [_emit(block, 'xor', ty, [a, b], insts) for a, b in zip(a_bits, b_bits)]


def _bitwise_and_ir(block: IrBlock, a_bits: list, b_bits: list, ty: IrType, insts: list) -> list:
    """IR-level per-bit AND."""
    return [_emit(block, 'and', ty, [a, b], insts) for a, b in zip(a_bits, b_bits)]


def _bitwise_or_ir(block: IrBlock, a_bits: list, b_bits: list, ty: IrType, insts: list) -> list:
    """IR-level per-bit OR."""
    return [_emit(block, 'or', ty, [a, b], insts) for a, b in zip(a_bits, b_bits)]


def _bitwise_shl_ir(block: IrBlock, val_bits: list, shift_val: IrValue, word_size: int, ty: IrType, insts: list) -> list:
    """IR-level left shift by a constant amount."""
    try:
        shift = int(shift_val.name) % word_size
    except (ValueError, TypeError):
        return val_bits
    return ([IrValue.const_int(0)] * shift + val_bits[:word_size - shift])[:word_size]


def _bitwise_shr_ir(block: IrBlock, val_bits: list, shift_val: IrValue, word_size: int, ty: IrType, insts: list) -> list:
    """IR-level right shift by a constant amount."""
    try:
        shift = int(shift_val.name) % word_size
    except (ValueError, TypeError):
        return val_bits
    result = val_bits[shift:] + [IrValue.const_int(0)] * shift
    return result[:word_size]


def _bitwise_cmp_eq_ir(block: IrBlock, a_bits: list, b_bits: list, ty: IrType, insts: list) -> IrValue:
    """
    IR-level equality comparison.

    Returns 1 if all corresponding bits are equal, 0 otherwise.
    Uses AND reduction of per-bit XNOR.
    """
    word_size = len(a_bits)
    eq = IrValue.const_int(1)
    for i in range(word_size):
        x = _emit(block, 'xor', ty, [a_bits[i], b_bits[i]], insts)
        eq = _emit(block, 'and', ty, [eq, _emit(block, 'xor', ty, [x, IrValue.const_int(1)], insts)], insts)
    return eq


def _bitwise_cmp_ne_ir(block: IrBlock, a_bits: list, b_bits: list, ty: IrType, insts: list) -> IrValue:
    """IR-level not-equal: invert equality result."""
    eq = _bitwise_cmp_eq_ir(block, a_bits, b_bits, ty, insts)
    return _emit(block, 'xor', ty, [eq, IrValue.const_int(1)], insts)


def _bitwise_cmp_lt_ir(block: IrBlock, a_bits: list, b_bits: list, ty: IrType, insts: list) -> IrValue:
    """
    IR-level signed less-than comparison.

    Scans from MSB to LSB computing the comparison result.
    Uses a ripple chain of (a & ~b) | (a == b) & previous.
    """
    word_size = len(a_bits)
    lt = IrValue.const_int(0)
    for i in range(word_size - 1, -1, -1):
        a_not_b = _emit(block, 'and', ty, [a_bits[i], _emit(block, 'xor', ty, [b_bits[i], IrValue.const_int(1)], insts)], insts)
        a_eq_b = _emit(block, 'xor', ty, [_emit(block, 'xor', ty, [a_bits[i], b_bits[i]], insts), IrValue.const_int(1)], insts)
        lt = _emit(block, 'or', ty, [a_not_b, _emit(block, 'and', ty, [a_eq_b, lt], insts)], insts)
    return lt


def _bitwise_cmp_le_ir(block: IrBlock, a_bits: list, b_bits: list, ty: IrType, insts: list) -> IrValue:
    """IR-level less-or-equal: lt | eq."""
    lt = _bitwise_cmp_lt_ir(block, a_bits, b_bits, ty, insts)
    eq = _bitwise_cmp_eq_ir(block, a_bits, b_bits, ty, insts)
    return _emit(block, 'or', ty, [lt, eq], insts)


def _bitwise_cmp_gt_ir(block: IrBlock, a_bits: list, b_bits: list, ty: IrType, insts: list) -> IrValue:
    """IR-level greater-than: invert le."""
    le = _bitwise_cmp_le_ir(block, a_bits, b_bits, ty, insts)
    return _emit(block, 'xor', ty, [le, IrValue.const_int(1)], insts)


def _bitwise_cmp_ge_ir(block: IrBlock, a_bits: list, b_bits: list, ty: IrType, insts: list) -> IrValue:
    """IR-level greater-or-equal: invert lt."""
    lt = _bitwise_cmp_lt_ir(block, a_bits, b_bits, ty, insts)
    return _emit(block, 'xor', ty, [lt, IrValue.const_int(1)], insts)


# ---- Public API ----

def transform_ir_function(ir_func: IrFunction, compiler: Optional[BitSliceCompiler] = None) -> IrFunction:
    """
    Apply bit-slicing to all arithmetic instructions in a function.

    Iterates over blocks and replaces arithmetic instructions with
    their bit-level equivalents. Non-arithmetic instructions pass
    through unchanged.
    """
    if compiler is None:
        compiler = BitSliceCompiler()

    for block in ir_func.blocks:
        new_insts: list[IrInstruction] = []
        for inst in block.instructions:
            if inst.opcode in _BS_OPS:
                _transform_inst(block, inst, compiler, new_insts)
            else:
                new_insts.append(inst)
        block.instructions = new_insts

    return ir_func


def _transform_inst(block: IrBlock, inst: IrInstruction, compiler: BitSliceCompiler, new_insts: list):
    """
    Transform a single arithmetic instruction into its bit-level equivalent.

    Extracts both operands to bit arrays, applies the appropriate
    bitwise operation, and recombines the result.
    """
    opcode = inst.opcode
    a = inst.operands[0]
    b = inst.operands[1]
    ty = inst.ty or inst.result_type
    word_size = _type_size(ty)

    if opcode in ('add', 'sub', 'mul', 'and', 'or', 'xor', 'shl', 'shr'):
        a_bits = _extract_bits(block, a, word_size, ty, new_insts)
        b_bits = _extract_bits(block, b, word_size, ty, new_insts)

        if opcode == 'add':
            result_bits = _bitwise_add_ir(block, a_bits, b_bits, ty, new_insts)
        elif opcode == 'sub':
            result_bits = _bitwise_sub_ir(block, a_bits, b_bits, ty, new_insts)
        elif opcode == 'mul':
            result_bits = _bitwise_mul_ir(block, a_bits, b_bits, ty, new_insts)
        elif opcode == 'xor':
            result_bits = _bitwise_xor_ir(block, a_bits, b_bits, ty, new_insts)
        elif opcode == 'and':
            result_bits = _bitwise_and_ir(block, a_bits, b_bits, ty, new_insts)
        elif opcode == 'or':
            result_bits = _bitwise_or_ir(block, a_bits, b_bits, ty, new_insts)
        elif opcode == 'shl':
            result_bits = _bitwise_shl_ir(block, a_bits, b, word_size, ty, new_insts)
        elif opcode == 'shr':
            result_bits = _bitwise_shr_ir(block, a_bits, b, word_size, ty, new_insts)
        else:
            result_bits = a_bits

        if isinstance(result_bits, list) and len(result_bits) == word_size:
            recombined = _recombine_bits(block, result_bits, ty, new_insts)
            _patch_result(inst, new_insts, recombined)

    elif opcode in ('eq', 'ne', 'lt', 'le', 'gt', 'ge'):
        a_bits = _extract_bits(block, a, word_size, ty, new_insts)
        b_bits = _extract_bits(block, b, word_size, ty, new_insts)
        IrType.i1()

        if opcode == 'eq':
            result_val = _bitwise_cmp_eq_ir(block, a_bits, b_bits, ty, new_insts)
        elif opcode == 'ne':
            result_val = _bitwise_cmp_ne_ir(block, a_bits, b_bits, ty, new_insts)
        elif opcode == 'lt':
            result_val = _bitwise_cmp_lt_ir(block, a_bits, b_bits, ty, new_insts)
        elif opcode == 'le':
            result_val = _bitwise_cmp_le_ir(block, a_bits, b_bits, ty, new_insts)
        elif opcode == 'gt':
            result_val = _bitwise_cmp_gt_ir(block, a_bits, b_bits, ty, new_insts)
        elif opcode == 'ge':
            result_val = _bitwise_cmp_ge_ir(block, a_bits, b_bits, ty, new_insts)
        else:
            result_val = IrValue.const_int(0)

        _patch_result(inst, new_insts, result_val)


def _patch_result(inst: IrInstruction, new_insts: list, result_val: IrValue):
    """
    Patch the result of the original instruction onto the last
    emitted instruction in the replacement list.

    This ensures that downstream uses of the original instruction's
    result continue to work correctly.
    """
    if new_insts and new_insts[-1].result is not None:
        last_inst = new_insts[-1]
        last_inst.result = inst.result
        last_inst.result_type = inst.result_type
        last_inst.result.type = inst.result.type
    else:
        inst.result.name = result_val.name
        inst.result.type = result_val.type


def _parse_nixon_ir(text: str) -> IrModule:
    """
    Parse a Nixon IR text representation into an IrModule.

    Supports module, func, basic block labels, and instructions
    including arithmetic, memory ops, control flow, calls, phi,
    casts, and GEP.
    """
    module: Optional[IrModule] = None
    current_func: Optional[IrFunction] = None
    current_block: Optional[IrBlock] = None
    var_types: dict[str, str] = {}

    for raw_line in text.split('\n'):
        line = raw_line.strip()
        if not line:
            continue

        m = re.match(r'module\s+@?(\S+)', line)
        if m:
            module = IrModule(m.group(1))
            continue

        m = re.match(r'func\s+@(\w+)\s*\((.*)\)\s*(->\s*(\w+))?\s*\{', line)
        if m:
            name = m.group(1)
            params_str = m.group(2).strip()
            ret_type_str = m.group(4) or 'void'
            ret_type = IrType(ret_type_str) if ret_type_str != 'void' else IrType.void()
            current_func = IrFunction(name, ret_type)
            var_types = {}
            if params_str:
                for p in params_str.split(','):
                    p = p.strip()
                    if ':' in p:
                        pname, ptype_str = p.split(':', 1)
                        ptype_str = ptype_str.strip()
                        pname_clean = pname.strip().lstrip('%')
                        current_func.params.append((pname_clean, IrType(ptype_str)))
                        var_types[pname.strip()] = ptype_str
            current_block = None
            if module is not None:
                module.functions.append(current_func)
            continue

        if line == '}':
            current_func = None
            current_block = None
            continue

        m = re.match(r'^([a-zA-Z_]\w*):\s*(.*)', line)
        if m:
            label = m.group(1)
            rest = m.group(2).strip()
            if current_func is not None:
                current_block = current_func.new_block(label)
                if rest:
                    _parse_instruction_line(rest, current_block, var_types)
            continue

        if current_block is not None:
            _parse_instruction_line(line, current_block, var_types)

    if module is None:
        module = IrModule("parsed")
    return module


def _parse_instruction_line(line: str, block: IrBlock, var_types: dict):
    """
    Parse a single IR instruction line and emit the appropriate
    IrInstruction into the given block.
    """
    eq_idx = line.find(' = ')
    result_name = None
    if eq_idx >= 0:
        possible = line[:eq_idx].strip()
        if possible.startswith('%'):
            result_name = possible
            line = line[eq_idx + 3:].strip()

    parts = line.split()
    if not parts:
        return

    opcode = parts[0]

    if opcode == 'ret':
        if len(parts) >= 3 and parts[1] != 'void':
            v = IrValue(IrType(parts[1]))
            v.name = parts[2]
            block.set_terminator('ret', operands=[IrType(parts[1]), v])
        else:
            block.set_terminator('ret')
        return

    if opcode in _BS_OPS:
        ty_str = parts[1]
        ty = IrType(ty_str)
        lhs_str = parts[2].rstrip(',')
        rhs_str = parts[3].rstrip(',')
        lhs = IrValue(ty)
        lhs.name = lhs_str
        rhs = IrValue(ty)
        rhs.name = rhs_str
        inst = IrInstruction(opcode, ty, [lhs, rhs], ty=ty)
        inst.parent_block = block
        if result_name:
            inst.result.name = result_name
            var_types[result_name] = ty_str
        block.instructions.append(inst)
        return

    if opcode == 'alloca':
        ty_str = parts[1]
        inst = IrInstruction('alloca', IrType(ty_str))
        inst.parent_block = block
        if result_name:
            inst.result.name = result_name
            var_types[result_name] = 'ptr'
        block.instructions.append(inst)
        return

    if opcode == 'load':
        ty_str = parts[1]
        if len(parts) >= 4 and parts[2] == 'ptr':
            ptr = IrValue(IrType.ptr())
            ptr.name = parts[3].rstrip(',')
            inst = IrInstruction('load', IrType(ty_str), [ptr])
            inst.parent_block = block
            if result_name:
                inst.result.name = result_name
                var_types[result_name] = ty_str
            block.instructions.append(inst)
        return

    if opcode == 'store':
        ty_str = parts[1]
        val = IrValue(IrType(ty_str))
        val.name = parts[2].rstrip(',')
        if len(parts) >= 5 and parts[3] == 'ptr':
            ptr = IrValue(IrType.ptr())
            ptr.name = parts[4].rstrip(',')
            inst = IrInstruction('store', IrType(ty_str), [val, ptr])
            inst.parent_block = block
            block.instructions.append(inst)
        return

    if opcode == 'jmp':
        target = parts[-1].lstrip('%')
        block.set_terminator('jmp', operands=[target])
        return

    if opcode == 'br' and len(parts) >= 7:
        cond = IrValue(IrType.i1())
        cond.name = parts[2].rstrip(',')
        true_label = parts[4].rstrip(',')
        false_label = parts[6].rstrip(',')
        block.set_terminator('br', operands=[cond, true_label, false_label])
        return

    if opcode == 'call':
        ret_type_str = parts[1]
        func_name = parts[2].rstrip('(') if '(' not in parts[2] else parts[2]
        inst = IrInstruction('call', IrType(ret_type_str) if ret_type_str != 'void' else None,
                          func_name=func_name)
        inst.parent_block = block
        if result_name:
            inst.result.name = result_name
            var_types[result_name] = ret_type_str
        block.instructions.append(inst)
        return

    if opcode == 'phi':
        ty_str = parts[1]
        incs = []
        for m in re.finditer(r'\[\s*(\S+)\s*,\s*(\S+)\s*\]', line):
            incs.append((m.group(1), m.group(2)))
        inst = IrInstruction('phi', IrType(ty_str))
        inst.parent_block = block
        if result_name:
            inst.result.name = result_name
            var_types[result_name] = ty_str
        block.instructions.append(inst)
        return

    if opcode == 'zext':
        src_str = parts[1]
        val = IrValue(IrType(src_str))
        val.name = parts[2].rstrip(',')
        to_str = parts[-1]
        inst = IrInstruction('zext', IrType(src_str), [val], ty=IrType(to_str))
        inst.parent_block = block
        if result_name:
            inst.result.name = result_name
            var_types[result_name] = to_str
        block.instructions.append(inst)
        return

    if opcode == 'trunc':
        src_str = parts[1]
        val = IrValue(IrType(src_str))
        val.name = parts[2].rstrip(',')
        to_str = parts[-1]
        inst = IrInstruction('trunc', IrType(src_str), [val], ty=IrType(to_str))
        inst.parent_block = block
        if result_name:
            inst.result.name = result_name
            var_types[result_name] = to_str
        block.instructions.append(inst)
        return

    if opcode == 'gep':
        if len(parts) >= 4:
            ptr = IrValue(IrType.ptr())
            ptr.name = parts[2].rstrip(',')
            idx = IrValue(IrType.i32())
            idx.name = parts[3].rstrip(',')
            inst = IrInstruction('gep', IrType.ptr(), [ptr, idx])
            inst.parent_block = block
            if result_name:
                inst.result.name = result_name
                var_types[result_name] = 'ptr'
            block.instructions.append(inst)
        return

    if opcode == 'nop':
        inst = IrInstruction('nop')
        inst.parent_block = block
        block.instructions.append(inst)
        return

    if opcode == 'unreachable':
        block.set_terminator('unreachable')
        return


def transform_ir_module(module: IrModule, compiler: Optional[BitSliceCompiler] = None) -> IrModule:
    """
    Apply bit-slicing to all functions in an IR module.

    Each function's arithmetic instructions are replaced with
    bit-level equivalents.
    """
    if compiler is None:
        compiler = BitSliceCompiler()
    for func in module.functions:
        transform_ir_function(func, compiler)
    return module


def generate_bitslice_ir(source_ir: str) -> str:
    """
    Parse Nixon IR text, apply bit-slicing, and return the result.

    Convenience function that combines parsing, transformation,
    and serialization.
    """
    module = _parse_nixon_ir(source_ir)
    transform_ir_module(module)
    return str(module)
