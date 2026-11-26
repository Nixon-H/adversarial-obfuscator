"""End-to-end regression tests for vm/bytecode_compiler.py.

The compiler previously (a) emitted md5(label)[:4] as jump targets while the
VM's PC is a byte offset -- every branch halted instantly; (b) compiled all
six comparisons to a single XOR; (c) dropped ret values; (d) desynced
load/store operand order; (e) allocated every alloca at address 0; and
(f) could allocate reserved registers FLAGS=13/PC=14/SP=15.
"""
import ctypes
import shutil
import subprocess
import tempfile

import pytest

import irgen.compile as ir_compile
from irgen.compile import IrBlock, IrFunction, IrType, IrValue
from vm.bytecode_compiler import compile_to_bytecode
from vm.interpreter import VMInterpreter


def _run(src, fname, seed=bytes(range(16))):
    fn = next(f for f in ir_compile.compile_py_to_ir(src).functions if f.name == fname)
    bc = compile_to_bytecode(fn, None, seed)
    r = VMInterpreter(bytes(bc)).run(max_steps=100000)
    assert r.get("halted", False)
    return r


def test_branch_taken_and_not_taken():
    src = "def f(x):\n    if x > 0:\n        return 1\n    return 2\n"
    # x is never stored (no calling convention), so memory[0] == 0 -> else path
    assert _run(src, "f")["regs"][1] == 2


def test_arithmetic_and_return_value():
    assert _run("def g():\n    return (3 + 4) * 2\n", "g")["regs"][1] == 14


def test_multiple_allocas_do_not_collide():
    src = "def h():\n    a = 5\n    b = 7\n    return a * b - 3\n"
    assert _run(src, "h")["regs"][1] == 32


def test_comparison_results():
    # Each comparison opcode must produce a real 0/1 result register.
    from vm.bytecode_compiler import _translate_instruction, _Rng
    from vm.vm_isa import VMOpcode
    from irgen.compile import IrValue, IrType

    class _Inst:
        def __init__(self, op, ops, res):
            self.opcode = op
            self.operands = ops
            self.result = res

    rng = _Rng(b"0" * 16)
    res = IrValue(IrType.i1(), "r")
    a, b = IrValue(IrType.i32(), "3"), IrValue(IrType.i32(), "7")
    for op in ("eq", "ne", "lt", "le", "gt", "ge"):
        insts = _translate_instruction(_Inst(op, [a, b], res), None, rng)
        ops_used = [i.opcode for i in insts]
        assert VMOpcode.CMP in ops_used, (op, ops_used)


def test_comparison_return_values_execute_correctly():
    cases = {
        "3 == 7": 0,
        "3 != 7": 1,
        "3 < 7": 1,
        "3 <= 7": 1,
        "3 > 7": 0,
        "3 >= 7": 0,
        "7 == 7": 1,
        "7 != 7": 0,
        "7 < 3": 0,
        "7 <= 3": 0,
        "7 > 3": 1,
        "7 >= 3": 1,
    }
    for expression, expected in cases.items():
        src = "def f():\n    return %s\n" % expression
        assert _run(src, "f")["regs"][1] == expected, expression


def test_computed_return_value_is_not_truncated_to_one_byte():
    assert _run("def f():\n    return 150 + 150\n", "f")["regs"][1] == 300


def _int_type(bits):
    return {1: IrType.i1, 8: IrType.i8, 16: IrType.i16, 32: IrType.i32, 64: IrType.i64}[bits]()


def _run_integer_binary(bits, opcode, lhs, rhs):
    IrValue.reset_counter()
    func = IrFunction("integer_parity", _int_type(bits))
    block = IrBlock("entry")
    func.blocks.append(block)
    a = IrValue(_int_type(bits), str(lhs))
    b = IrValue(_int_type(bits), str(rhs))
    result = block._make(opcode, _int_type(bits), [a, b])
    block.set_terminator("ret", operands=[_int_type(bits), result.result])
    bytecode = compile_to_bytecode(func, seed=b"integer-parity")
    state = VMInterpreter(bytes(bytecode)).run(max_steps=10000)
    assert state["halted"]
    return state["regs"][1]


def _execute_llvm_integer(bits, body):
    clang = shutil.which("clang")
    if clang is None:
        pytest.skip("clang is required for executed LLVM parity tests")
    source = f"define i{bits} @vm_parity() {{\nentry:\n{body}\n}}\n"
    # Use the system temp directory: the old hardcoded /tmp/opencode path does
    # not exist in CI containers or on most developer machines.
    with tempfile.TemporaryDirectory(prefix="vm-parity-") as directory:
        library = f"{directory}/parity.so"
        subprocess.run(
            [clang, "-shared", "-fPIC", "-x", "ir", "-", "-o", library],
            input=source, text=True, capture_output=True, check=True, timeout=20,
        )
        shared = ctypes.CDLL(library)
        function = shared.vm_parity
        function.restype = ctypes.c_uint32 if bits <= 32 else ctypes.c_uint64
        function.argtypes = []
        return function()


@pytest.mark.parametrize("bits,opcode,lhs,rhs,llvm_body", [
    (32, "add", 70000, 1, "  %r = add i32 70000, 1\n  ret i32 %r"),
    (32, "add", -1, 1, "  %r = add i32 -1, 1\n  ret i32 %r"),
    (32, "add", 2147483647, 1, "  %r = add i32 2147483647, 1\n  ret i32 %r"),
    (64, "add", 4294967296, -1, "  %r = add i64 4294967296, -1\n  ret i64 %r"),
    (64, "add", -1, 1, "  %r = add i64 -1, 1\n  ret i64 %r"),
])
def test_integer_constants_match_executed_llvm(bits, opcode, lhs, rhs, llvm_body):
    expected = _execute_llvm_integer(bits, llvm_body)
    actual = _run_integer_binary(bits, opcode, lhs, rhs)
    assert actual == expected


@pytest.mark.parametrize("opcode,lhs,rhs,predicate", [
    ("lt", -1, 1, "slt"),
    ("lt", 70000, -1, "slt"),
    ("gt", -1, -2, "sgt"),
    ("ge", 2147483647, -1, "sge"),
])
def test_signed_comparisons_match_executed_llvm(opcode, lhs, rhs, predicate):
    llvm_body = (
        f"  %c = icmp {predicate} i32 {lhs}, {rhs}\n"
        "  %r = zext i1 %c to i32\n  ret i32 %r"
    )
    expected = _execute_llvm_integer(32, llvm_body)
    IrValue.reset_counter()
    func = IrFunction("comparison_parity", IrType.i32())
    block = IrBlock("entry")
    func.blocks.append(block)
    a = IrValue(IrType.i32(), str(lhs))
    b = IrValue(IrType.i32(), str(rhs))
    comparison = block._make(opcode, IrType.i1(), [a, b])
    widened = block._make("zext", IrType.i32(), [comparison.result])
    block.set_terminator("ret", operands=[IrType.i32(), widened.result])
    state = VMInterpreter(bytes(compile_to_bytecode(func, seed=b"comparison-parity"))).run(max_steps=10000)
    assert state["halted"]
    assert state["regs"][1] == expected
