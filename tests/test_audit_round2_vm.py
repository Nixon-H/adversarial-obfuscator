"""Regression tests for the VM encoding contract.

The compiler, the Python interpreter and the generated C interpreter all have
to agree on the wire format. These tests pin that agreement: a compiled
function must execute to the expected result, and a remap must not shift
instruction boundaries.
"""

import pytest

from irgen.compile import IrBlock, IrFunction, IrType, IrValue
from vm.bytecode_compiler import compile_to_bytecode
from vm.ephemeral_isa import (
    generate_ephemeral_opcode_map,
    generate_interpreter_dispatch_table,
    remap_bytecode,
)
from vm.interpreter import VMInterpreter
from vm.vm_isa import VMInstruction, VMOperand, VMOpcode


def _state(regs=None):
    state = {"regs": [0] * 16, "memory": bytearray(65536),
             "stack": [], "halted": False}
    for idx, val in (regs or {}).items():
        state["regs"][idx] = val
    return state


def _add_function():
    func = IrFunction('add2', IrType.i32())
    block = IrBlock('entry')
    func.blocks.append(block)
    a = IrValue(IrType.i32(), '%a')
    b = IrValue(IrType.i32(), '%b')
    result = block._make('add', IrType.i32(), [a, b])
    block.set_terminator('ret', operands=[result.result])
    return func


def test_compiled_add_executes():
    bytecode = compile_to_bytecode(_add_function(), {}, b'\x00' * 32)
    vm = VMInterpreter(bytes(bytecode), state=_state({1: 20, 2: 22}))
    out = vm.run()
    assert out["regs"][1] == 42


def test_encode_has_no_operand_type_tags():
    """ADD reg1, reg2 must be three bytes: opcode, reg, reg."""
    encoded = bytes(VMInstruction(VMOpcode.ADD, [
        (VMOperand.REG, 1), (VMOperand.REG, 2)]).encode())
    assert encoded == bytes([VMOpcode.ADD, 1, 2])


def test_byte_length_matches_encode():
    insts = [
        VMInstruction(VMOpcode.ADD, [(VMOperand.REG, 1), (VMOperand.REG, 2)]),
        VMInstruction(VMOpcode.MOV, [(VMOperand.REG, 1), (VMOperand.IMM8, 7),
                                     (VMOperand.IMM8, 0)]),
        VMInstruction(VMOpcode.JMP, [(VMOperand.ABS_ADDR, 0x1000)]),
        VMInstruction(VMOpcode.RET),
        VMInstruction(VMOpcode.FUSED_CMP_JMP, [(VMOperand.REG, 1),
                                               (VMOperand.ABS_ADDR, 4),
                                               (VMOperand.ABS_ADDR, 8)]),
    ]
    for inst in insts:
        assert inst.byte_length() == len(inst.encode()), inst


def test_remap_keeps_call_and_ret_intact():
    """CALL used to swallow the rest of the stream, truncating the program."""
    insts = [
        VMInstruction(VMOpcode.CALL, [(VMOperand.ABS_ADDR, 0x40)]),
        VMInstruction(VMOpcode.ADD, [(VMOperand.REG, 1), (VMOperand.REG, 2)]),
        VMInstruction(VMOpcode.RET),
    ]
    original = b''.join(bytes(i.encode()) for i in insts)
    omap = generate_ephemeral_opcode_map(b'call-ret-seed', 256)

    remapped = remap_bytecode(original, omap)
    assert len(remapped) == len(original)

    inverse = {v: k for k, v in omap.items()}
    assert remap_bytecode(remapped, inverse) == original


def test_remapped_program_still_executes():
    bytecode = bytes(compile_to_bytecode(_add_function(), {}, b'\x00' * 32))
    omap = generate_ephemeral_opcode_map(b'exec-seed', 256)
    remapped = remap_bytecode(bytecode, omap)

    vm = VMInterpreter(remapped, state=_state({1: 5, 2: 37}), opcode_map=omap)
    out = vm.run()
    assert out["regs"][1] == 42


def test_dispatch_table_is_deobfuscated_in_generated_c():
    from vm import generate_ephemeral_interpreter_source

    omap = generate_ephemeral_opcode_map(b'dispatch-seed', 256)
    table = generate_interpreter_dispatch_table(omap, b'dispatch-seed', seed=0x5A)
    source = generate_ephemeral_interpreter_source(table, omap, dispatch_key=0x5A)

    assert '#define VM_DISPATCH_KEY 0x5A' in source
    assert 'VM_DISPATCH_TABLE[phys_opcode] ^ VM_DISPATCH_KEY' in source


@pytest.mark.parametrize('opcode,width', [
    (VMOpcode.MOV, 3),
    (VMOpcode.LEA, 2),
    (VMOpcode.CALL, 4),
    (VMOpcode.RET, 0),
    (VMOpcode.FUSED_CMP_JMP, 9),
])
def test_operand_widths_match_interpreter(opcode, width):
    from vm.ephemeral_isa import _OPCODE_OPERAND_BYTES

    assert _OPCODE_OPERAND_BYTES[opcode] == width


def test_string_constant_encoding_is_deterministic():
    """A salted hash() made the same string encode differently per run."""
    import random
    from vm.bytecode_compiler import _materialize

    out1, out2 = [], []
    _materialize("hello", random.Random(1), out1)
    _materialize("hello", random.Random(1), out2)
    assert bytes(out1[0].encode()) == bytes(out2[0].encode())
