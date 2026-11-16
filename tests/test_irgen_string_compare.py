"""Comparisons must not put a string literal or a wrong type into `icmp`.

Two defects lived here:

* ``x == "literal"`` emitted ``eq i32 %x, "literal"``.  LLVM has no bare
  string value, so the whole llvmgen stage died with "string literal used
  as a value" -- for every payload, because the obfuscator injects
  ``__name__ == "__main__"`` into every module.
* ``a is not b`` forced ``ptr`` on the operands, emitting
  ``icmp ne ptr %i32handle, ...`` which llc rejects with "defined with
  type 'i32' but expected 'ptr'".

Both are pinned here at the IR-text level, which is where they surfaced.
"""
import sys
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from irgen.compile import compile_py_to_ir  # noqa: E402


def _ir(source):
    module = compile_py_to_ir(source)
    return module.to_text() if hasattr(module, "to_text") else str(module)


def test_string_literal_comparison_emits_a_runtime_call():
    ir = _ir('name = "x"\nflag = name == "__main__"\n')
    assert "__builtin_str_eq" in ir
    # The literal must never appear as an icmp operand.
    for line in ir.splitlines():
        if "icmp" in line:
            assert '"' not in line, f"string literal in icmp: {line.strip()}"


def test_string_literal_not_equal_negates_the_helper():
    ir = _ir('name = "x"\nflag = name != "__main__"\n')
    assert "__builtin_str_eq" in ir
    for line in ir.splitlines():
        if "icmp" in line:
            assert '"' not in line, f"string literal in icmp: {line.strip()}"


def test_two_string_literals_still_fold():
    """Both sides constant is decidable at compile time -- no call needed."""
    ir = _ir('flag = "__main__" == "__main__"\n')
    assert "__builtin_str_eq" not in ir


def test_is_not_does_not_force_pointer_type():
    ir = _ir("a = 1\nb = 2\nflag = a is not b\n")
    for line in ir.splitlines():
        if "icmp" in line:
            assert "icmp ne ptr" not in line, (
                f"`is not` forced ptr on an i32 operand: {line.strip()}")


def test_is_does_not_force_pointer_type():
    ir = _ir("a = 1\nb = 2\nflag = a is b\n")
    for line in ir.splitlines():
        if "icmp" in line:
            assert "icmp eq ptr" not in line, (
                f"`is` forced ptr on an i32 operand: {line.strip()}")


def test_module_guard_lowers_without_a_string_operand():
    """The exact shape the obfuscator injects into every payload."""
    ir = _ir('if __name__ == "__main__":\n    x = 1\n')
    for line in ir.splitlines():
        if "icmp" in line:
            assert '"' not in line, f"string literal in icmp: {line.strip()}"
