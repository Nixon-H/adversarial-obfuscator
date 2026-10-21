"""Tests for the native (IR -> LLVM) lowering path.

Every test here guards a defect that made the native build fail
outright, or silently miscompile:

* ``shr`` was not a known opcode, so the lowering emitted it as a
  COMMENT and its result stayed undefined ("use of undefined value").
* ``gep`` was not a known opcode, and the GEP emitter DROPPED the
  indices -- the address was computed from the base alone.
* A closure constant (``_nx_M`` defined above a nested function)
  resolved to the fallback 0, so ``x & _nx_M`` compiled to ``x & 0``.
* The comparison opcodes (``lt``/``le``/``gt``/``ge``/``ne``) were not
  lowered at all.
* A string constant containing a space was split into several tokens
  by the whitespace tokenizer.
* A float constant in an integer operation is not valid LLVM.
* LLVM requires unnamed values to be numbered consecutively; the
  project's IR numbering has gaps.
"""

import os
import re
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import ast  # noqa: E402

from irgen.compile import IrCompiler, compile_py_to_ir  # noqa: E402
from llvmgen.lower import lower_ir_to_llvm  # noqa: E402

pytestmark = pytest.mark.skipif(
    shutil.which("llc") is None, reason="llc (LLVM) is not installed")


def compile_source(source: str) -> str:
    """Compile Python source to the project's IR text."""
    import ast

    compiler = IrCompiler("test_module")
    module = compiler.compile(ast.parse(source))
    return str(module)


def lower(source: str) -> str:
    """Compile and lower Python source to LLVM IR."""
    return lower_ir_to_llvm(compile_source(source), module_name="test_module")


# --------------------------------------------------------------------------
# The IR generator
# --------------------------------------------------------------------------

def test_closure_constant_keeps_its_value():
    """A constant captured by a nested function must not become 0.

    The mask was silently zeroed, so ``x & _nx_M`` became ``x & 0``.
    """
    source = (
        "def outer():\n"
        "    _nx_M = 4294967295\n"
        "    def inner(_v):\n"
        "        return _v & _nx_M\n"
        "    return inner\n"
    )
    ir = compile_source(source)
    assert "4294967295" in ir
    assert not re.search(r"and i32 %\d+, 0\b", ir), ir


def test_module_constant_keeps_its_value():
    """A module-level constant must not become 0 either."""
    source = (
        "_nx_M = 4294967295\n"
        "def f(_v):\n"
        "    return _v & _nx_M\n"
    )
    ir = compile_source(source)
    assert "4294967295" in ir


def test_shr_is_emitted_not_dropped():
    """The right shift must be a real instruction, not a comment."""
    source = (
        "def f(_v, _n):\n"
        "    return _v >> (32 - _n)\n"
    )
    ir = compile_source(source)
    assert "shr" in ir
    assert "lshr" in lower(source)


def test_comparisons_are_lowered():
    """Every comparison opcode must reach LLVM."""
    for op in ("<", "<=", ">", ">=", "==", "!="):
        source = f"def f(_a, _b):\n    return _a {op} _b\n"
        llvm = lower(source)
        assert "icmp" in llvm, (op, llvm)


# --------------------------------------------------------------------------
# The LLVM lowering
# --------------------------------------------------------------------------

def test_gep_keeps_its_indices():
    """A GEP's index is part of the address and must be emitted."""
    source = (
        "def f(_x, _a):\n"
        "    return _x[_a]\n"
    )
    llvm = lower(source)
    assert "getelementptr" in llvm
    gep = re.search(r"getelementptr i32, ptr [^,\n]+, (i32 %[\w.]+)", llvm)
    assert gep, llvm
    # The index must be a real operand: "getelementptr i32, ptr %p" with
    # no index computes the base address, not the element.
    assert gep.group(1).startswith("i32 %")


def test_string_constant_with_spaces_survives():
    """A quoted constant is ONE token, spaces and commas included."""
    source = (
        "def f():\n"
        "    _s = 'IMPORTANT: read the guide, then run it'\n"
        "    return _s\n"
    )
    llvm = lower(source)
    assert "@.str." in llvm
    assert "IMPORTANT: read the guide" in llvm


def test_values_are_numbered_consecutively():
    """LLVM requires unnamed values to be numbered 0, 1, 2, ..."""
    source = (
        "def f(_v, _n):\n"
        "    _a = _v + _n\n"
        "    _b = _a * 3\n"
        "    _c = _b - 1\n"
        "    return _c\n"
    )
    llvm = lower(source)
    body = llvm.split("define", 1)[1]
    numbers = [int(m) for m in re.findall(r"^\s+%(?!_gepbase)(\d+) = ", body,
                                          re.MULTILINE)]
    assert numbers == list(range(len(numbers))), numbers


def test_unknown_instruction_is_an_error_not_a_comment():
    """An unlowerable instruction must fail loudly.

    It used to be emitted as a COMMENT, which left its result
    undefined while later instructions still used it.
    """
    from llvmgen.lower import _emit_instruction

    with pytest.raises(ValueError):
        _emit_instruction({"opcode": "frobnicate", "raw": "frobnicate i32 %1"})


def test_float_operation_is_valid_llvm():
    """A float constant must produce a valid floating-point operation."""
    source = (
        "def f(_v):\n"
        "    return _v * 0.001\n"
    )
    llvm = lower(source)
    assert "fmul double" in llvm


def test_boolop_has_a_phi_with_one_entry_per_predecessor():
    """``a and b`` must produce a phi, with the right short-circuit value.

    The old implementation left the short-circuit block without a
    terminator and branched to an empty block, so the module did not
    verify.
    """
    source = "def f(a, b):\n    return a and b\n"
    llvm = lower(source)
    assert "phi i1" in llvm
    # "and": when the left side is false the result is false.
    assert re.search(r"phi i1 \[0, %\w+\]", llvm), llvm

    source = "def f(a, b):\n    return a or b\n"
    llvm = lower(source)
    # "or": when the left side is true the result is true.
    assert re.search(r"phi i1 \[1, %\w+\]", llvm), llvm


def test_phi_survives_the_optimizer():
    """The dead-code pass must not delete a value a phi reads.

    A phi's operands are (value, label) PAIRS; treating them as plain
    values made the producer look unused, and the phi was left
    pointing at nothing.
    """
    from irgen.optimize import optimize

    compiler = IrCompiler("test_module")
    module = compiler.compile(ast.parse("def f(a, b):\n    return a and b\n"))
    optimized = optimize(module, level=2)
    text = str(optimized)
    assert "phi i1" in text, text
    # Every value the phi names must still be defined.
    for m in re.finditer(r"phi i1 \[([^,\]]+), label (\w+)\]", text):
        value = m.group(1).strip()
        assert f"{value} =" in text, (value, text)


def test_a_call_with_no_arguments_is_still_a_call():
    """A call with no arguments must keep its parentheses.

    Without them the lowering could not tell the callee from the
    argument list.
    """
    source = "def f():\n    return globals()\n"
    ir = compile_source(source)
    assert "call i32 @globals()" in ir
    llvm = lower(source)
    assert "call i32 @globals()" in llvm


def test_a_string_argument_is_not_swallowed_by_the_callee():
    """``call i32 @f("x")`` is a call to f with one string argument."""
    source = "def f():\n    return __import__('hashlib')\n"
    llvm = lower(source)
    assert "@__import__" in llvm
    assert 'declare i32 @__import__(ptr)' in llvm, llvm


def test_try_body_is_not_dropped():
    """A try block's body must be compiled.

    The statement used to be skipped entirely, so the variables it
    bound were never defined.
    """
    source = (
        "def f():\n"
        "    try:\n"
        "        _v = 42\n"
        "    except Exception:\n"
        "        _v = 0\n"
        "    return _v\n"
    )
    ir = compile_source(source)
    assert "42" in ir


def test_module_level_binding_is_visible_in_a_function():
    """A module-level dict must not become the integer 0."""
    source = (
        "_CHECKS = {'a': 1}\n"
        "def f():\n"
        "    return _CHECKS\n"
    )
    ir = compile_source(source)
    assert "call i32 @dict(" in ir, ir


def test_imported_module_gets_a_handle():
    """An imported module is an opaque handle, not a zero."""
    source = (
        "import hashlib as _h\n"
        "def f(_x):\n"
        "    return _h.sha256(_x)\n"
    )
    ir = compile_source(source)
    assert "global i32 @__nx_mod_hashlib" in ir, ir
    assert "load i32, ptr @__nx_mod_hashlib" in ir, ir


def test_strict_mode_reports_a_name_the_ir_cannot_represent():
    """A name the IR cannot represent is an error, not a silent zero."""
    from irgen.compile import UnresolvedNameError

    source = (
        "def f():\n"
        "    return some_name_that_does_not_exist\n"
    )
    with pytest.raises(UnresolvedNameError):
        compile_py_to_ir(source, strict=True)
    # Without strict mode it still compiles, and the name is recorded.
    compiler = IrCompiler("t")
    compiler.compile(ast.parse(source))
    assert "some_name_that_does_not_exist" in compiler.unresolved


# --------------------------------------------------------------------------
# End to end: the object file must assemble
# --------------------------------------------------------------------------

def test_llvm_output_assembles(tmp_path):
    """The lowered IR must pass llc and produce an object file."""
    source = (
        "def _nx_rl(_v, _n):\n"
        "    _nx_M = 4294967295\n"
        "    return ((_v << _n) & _nx_M) | (_v >> (32 - _n))\n"
        "def _nx_qr(_x, _a, _b, _c, _d):\n"
        "    _x[_a] = (_x[_a] + _x[_b]) & 4294967295\n"
        "    _x[_d] ^= _x[_a]\n"
        "    _x[_d] = _nx_rl(_x[_d], 16)\n"
        "    return _x[_c]\n"
        "def main():\n"
        "    _msg = 'IMPORTANT: native path works'\n"
        "    _x = [0, 0, 0, 0]\n"
        "    _nx_qr(_x, 0, 1, 2, 3)\n"
        "    return _x[2]\n"
    )
    llvm = lower(source)
    ll_path = tmp_path / "module.ll"
    ll_path.write_text(llvm, encoding="utf-8")
    result = subprocess.run(
        ["llc", str(ll_path), "-filetype=obj", "-o", str(tmp_path / "out.o")],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    obj = tmp_path / "out.o"
    assert obj.exists() and obj.stat().st_size > 0
    with open(obj, "rb") as f:
        assert f.read(4) == b"\x7fELF"


def test_ollvm_passes_produce_a_verifiable_module(tmp_path):
    """The OLLVM passes must not break the module.

    A control-flow pass that adds a branch gives the target block a
    new predecessor, and LLVM requires a phi to have one entry per
    predecessor.  The new entry needs a value that DOMINATES the
    block, or llc rejects the module ("Instruction does not dominate
    all uses").
    """
    from llvmgen.passes import apply_all

    source = (
        "def f(a, b):\n"
        "    if a and b:\n"
        "        return a + b\n"
        "    return a - b\n"
        "def g(x):\n"
        "    return x * 3\n"
    )
    llvm = lower(source)
    obfuscated = apply_all(llvm, ["bcf", "fla", "sub"])
    ll_path = tmp_path / "obf.ll"
    ll_path.write_text(obfuscated, encoding="utf-8")
    result = subprocess.run(
        ["llc", str(ll_path), "-filetype=obj", "-o", str(tmp_path / "obf.o")],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr


def test_none_is_a_value_the_ir_can_store():
    """None must be storable in the IR's i32 slots.

    It used to be a pointer-typed "null", which is not a valid i32
    value ("null must be a pointer type").
    """
    source = (
        "def f():\n"
        "    _v = None\n"
        "    return _v\n"
    )
    llvm = lower(source)
    assert "null" not in llvm, llvm
