"""Brute-force correctness tests for the bit-slice arithmetic circuits.

The IR-level helpers emit a gate network instead of computing a value, so the
only way to check them is to evaluate the emitted instructions. These tests do
that for every operand pair in a small word size, which is exhaustive enough to
catch carry-chain, gating and sign-handling mistakes.
"""

import itertools

import pytest

from irgen.bitslice import (
    BitSliceCompiler,
    _bitwise_add_ir,
    _bitwise_cmp_eq_ir,
    _bitwise_cmp_lt_ir,
    _bitwise_mul_ir,
    _bitwise_sub_ir,
    _extract_bits,
    _recombine_bits,
)
from irgen.compile import IrBlock, IrType, IrValue

BITS = 6
MASK = (1 << BITS) - 1


def _eval(insts, env):
    """Evaluate a flat list of IR instructions over integer values."""
    for inst in insts:
        args = [env[o.name] if o.name in env else int(o.name)
                for o in inst.operands]
        op = inst.opcode
        if op == 'xor':
            val = args[0] ^ args[1]
        elif op == 'and':
            val = args[0] & args[1]
        elif op == 'or':
            val = args[0] | args[1]
        elif op == 'add':
            val = args[0] + args[1]
        elif op == 'sub':
            val = args[0] - args[1]
        elif op == 'mul':
            val = args[0] * args[1]
        elif op == 'shl':
            val = args[0] << args[1]
        elif op == 'shr':
            val = args[0] >> args[1]
        else:
            raise AssertionError(f'unexpected opcode {op}')
        env[inst.result.name] = val & MASK
    return env


def _bits_of(value):
    return [(value >> i) & 1 for i in range(BITS)]


def _run_binary(helper, a, b):
    block = IrBlock('entry')
    insts = []
    ty = IrType(f'i{BITS}')
    a_val = IrValue(ty, 'a')
    b_val = IrValue(ty, 'b')
    a_bits = _extract_bits(block, a_val, BITS, ty, insts)
    b_bits = _extract_bits(block, b_val, BITS, ty, insts)
    result_bits = helper(block, a_bits, b_bits, ty, insts)
    recombined = _recombine_bits(block, result_bits, ty, insts)
    env = _eval(insts, {'a': a, 'b': b})
    return env[recombined.name]


def _run_cmp(helper, a, b):
    block = IrBlock('entry')
    insts = []
    ty = IrType(f'i{BITS}')
    a_val = IrValue(ty, 'a')
    b_val = IrValue(ty, 'b')
    a_bits = _extract_bits(block, a_val, BITS, ty, insts)
    b_bits = _extract_bits(block, b_val, BITS, ty, insts)
    result = helper(block, a_bits, b_bits, ty, insts)
    env = _eval(insts, {'a': a, 'b': b})
    return env[result.name]


def _signed(value):
    return value - (1 << BITS) if value >> (BITS - 1) else value


@pytest.mark.parametrize('a,b', itertools.product(range(1 << BITS), repeat=2))
def test_add_matches_python(a, b):
    assert _run_binary(_bitwise_add_ir, a, b) == (a + b) & MASK


@pytest.mark.parametrize('a,b', itertools.product(range(1 << BITS), repeat=2))
def test_sub_matches_python(a, b):
    assert _run_binary(_bitwise_sub_ir, a, b) == (a - b) & MASK


@pytest.mark.parametrize('a,b', itertools.product(range(1 << BITS), repeat=2))
def test_mul_matches_python(a, b):
    assert _run_binary(_bitwise_mul_ir, a, b) == (a * b) & MASK


@pytest.mark.parametrize('a,b', itertools.product(range(1 << BITS), repeat=2))
def test_cmp_eq_matches_python(a, b):
    assert _run_cmp(_bitwise_cmp_eq_ir, a, b) == int(a == b)


@pytest.mark.parametrize('a,b', itertools.product(range(1 << BITS), repeat=2))
def test_cmp_lt_matches_signed_python(a, b):
    assert _run_cmp(_bitwise_cmp_lt_ir, a, b) == int(_signed(a) < _signed(b))


@pytest.mark.parametrize('a,b', itertools.product(range(1 << BITS), repeat=2))
def test_compiler_class_agrees_with_ir(a, b):
    """The pure-Python slicer and the IR emitter must agree."""
    compiler = BitSliceCompiler(word_size=BITS)
    a_bits = compiler.slice_value(a)
    b_bits = compiler.slice_value(b)

    assert compiler.recombine(compiler.add_bitslice(a_bits, b_bits)[0]) == (a + b) & MASK
    assert compiler.recombine(compiler.sub_bitslice(a_bits, b_bits)[0]) == (a - b) & MASK
    assert compiler.recombine(compiler.mul_bitslice(a_bits, b_bits)[0]) == (a * b) & MASK
    assert compiler.cmp_eq_bitslice(a_bits, b_bits)[0] == int(a == b)
    assert compiler.cmp_lt_bitslice(a_bits, b_bits)[0] == int(_signed(a) < _signed(b))
