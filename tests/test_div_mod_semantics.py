"""Python integer semantics must survive both execution engines.

The IR is compiled from Python, so ``//`` floors toward -inf, ``%`` follows
the divisor's sign, and ``>>`` is arithmetic.  Two defects made the obfuscated
program compute different numbers from the original:

* the VM implemented C semantics (truncating division, dividend-sign
  remainder);
* the native lowering emitted ``udiv``/``lshr`` (and, at another point,
  truncating ``sdiv``/``srem``) for the same instructions.

Both are fixed in ``vm/interpreter.py`` and ``llvmgen/lower.py``.  These tests
are executed, not textual: the VM runs the compiled bytecode and the native
path is compiled with clang and run, then both are compared with Python for
every sign combination.
"""
import ast
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from irgen.compile import IrCompiler  # noqa: E402
from llvmgen.lower import lower_ir_to_llvm  # noqa: E402
from vm.bytecode_compiler import compile_to_bytecode  # noqa: E402
from vm.interpreter import VMInterpreter  # noqa: E402

# (expression, Python's answer).  All four sign combinations for // and %,
# plus shifts whose sign bit is set (where lshr and ashr disagree).
CASES = [
    ("-7 // 2", -4),
    ("7 // -2", -4),
    ("-7 // -2", 3),
    ("7 // 2", 3),
    ("-7 % 2", 1),
    ("7 % -2", -1),
    ("-7 % -2", -1),
    ("7 % 2", 1),
    ("-7 >> 1", -4),
    ("-1 >> 3", -1),
    ("7 >> 1", 3),
]

SEED = bytes(range(16))
MASK32 = 0xFFFFFFFF


def _compile(expr):
    source = f"def f():\n    return {expr}\n"
    module = IrCompiler("divmod_semantics").compile(ast.parse(source))
    function = next(f for f in module.functions if f.name == "f")
    return module, function


def _vm_result(expr):
    _module, function = _compile(expr)
    bytecode = compile_to_bytecode(function, None, SEED)
    state = VMInterpreter(bytes(bytecode)).run(max_steps=100000)
    assert state.get("halted"), expr
    return state["regs"][1]


def _native_result(expr, tmp_path):
    module, _function = _compile(expr)
    llvm_ir = lower_ir_to_llvm(str(module), module_name="divmod_semantics")
    # The constants must not hide the arithmetic: at this point we are
    # checking the lowering, not LLVM's constant folding.
    if ">>" in expr:
        assert "ashr" in llvm_ir, llvm_ir
        assert "lshr" not in llvm_ir, llvm_ir
    if "//" in expr:
        assert "sdiv" in llvm_ir, llvm_ir
        assert "udiv" not in llvm_ir, llvm_ir
    if "%" in expr:
        assert "srem" in llvm_ir, llvm_ir
        assert "select i1" in llvm_ir, llvm_ir
    driver = tmp_path / "driver.c"
    driver.write_text(
        "#include <stdint.h>\n"
        "#include <stdio.h>\n"
        "extern int32_t f(void);\n"
        "int main(void) { printf(\"%u\\n\", (uint32_t)f()); return 0; }\n"
    )
    module_path = tmp_path / "module.ll"
    module_path.write_text(llvm_ir)
    binary = tmp_path / "program"
    build = subprocess.run(
        ["clang", "-O0", str(module_path), str(driver), "-o", str(binary)],
        capture_output=True, text=True, timeout=120,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    return int(run.stdout.strip())


@pytest.mark.parametrize("expr,expected", CASES)
def test_vm_matches_python(expr, expected):
    assert _vm_result(expr) == expected & MASK32, expr


@pytest.mark.skipif(shutil.which("clang") is None, reason="clang is not installed")
@pytest.mark.parametrize("expr,expected", CASES)
def test_native_matches_python(expr, expected, tmp_path):
    assert _native_result(expr, tmp_path) == expected & MASK32, expr


@pytest.mark.skipif(shutil.which("clang") is None, reason="clang is not installed")
def test_native_and_vm_agree_on_every_case(tmp_path):
    for expr, _expected in CASES:
        assert _native_result(expr, tmp_path) == _vm_result(expr), expr
