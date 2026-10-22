"""A string literal cannot be lowered to LLVM as a comparison operand.

``irgen`` emits a comparison against a string literal for the very
common ``__name__ == "__main__"`` — ``%926 = eq ptr "__main__", %925``.
LLVM has no bare string value, so this reached ``llc`` and died with
"expected value token", which names neither the string nor the cause.

These tests pin three things:

* the failure names the cause, at the lowering layer where it happens;
* the PARSER still accepts the IR, because the ROP compiler parses the
  same module and rejecting in the parser turned a recoverable stage
  failure into a hard one;
* the tempting "fix" is not taken — interning the literal as
  ``@.str.N`` and comparing pointers would be silently wrong, because
  nothing interns strings and this IR models a string as an i32 handle.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from llvmgen.lower import NixonIRParser, lower_ir_to_llvm  # noqa: E402

IR_WITH_STRING_COMPARE = """
module @m
  func @f() -> i32 {
    entry:
      %925 = add i32 1, 2
      %926 = eq ptr "__main__", %925
      ret i32 0
  }
"""

IR_WITH_STRING_CALL = """
module @m
  func @f() -> i32 {
    entry:
      %1 = call i32 @g("hello")
      ret i32 %1
  }
"""

IR_INTEGER_COMPARE = """
module @m
  func @f() -> i32 {
    entry:
      %1 = add i32 1, 2
      %2 = eq i32 %1, 3
      ret i32 0
  }
"""


class TestStringOperandLowering:
    def test_parser_accepts_a_string_comparison(self):
        """The ROP compiler and the VM path must still read this IR.

        Rejecting in the parser broke
        test_adversarial_seal_integrity's end-to-end build, which
        reaches phase_rop_compile before the LLVM codegen stage.
        """
        module = NixonIRParser(IR_WITH_STRING_COMPARE).parse()
        assert module["functions"], "the parser must still accept valid IR"

    def test_lowering_rejects_a_string_comparison_loudly(self):
        with pytest.raises(Exception) as e:
            lower_ir_to_llvm(IR_WITH_STRING_COMPARE)
        assert "string literal" in str(e.value), \
            f"the failure must name the cause, got: {str(e.value)!r}"

    def test_rejection_names_the_string(self):
        with pytest.raises(Exception) as e:
            lower_ir_to_llvm(IR_WITH_STRING_COMPARE)
        assert "__main__" in str(e.value)

    def test_rejection_does_not_intern_the_literal(self):
        """Pointer comparison would be silently wrong: guard the fix."""
        with pytest.raises(Exception) as e:
            lower_ir_to_llvm(IR_WITH_STRING_COMPARE)
        assert "@.str" not in str(e.value) or "silently" in str(e.value)

    def test_string_as_call_argument_still_lowers(self):
        """Call arguments legitimately become @.str.N — do not reject those."""
        out = lower_ir_to_llvm(IR_WITH_STRING_CALL)
        assert "@.str.0" in out, "a string call argument must intern as @.str.N"

    def test_integer_comparison_still_lowers(self):
        out = lower_ir_to_llvm(IR_INTEGER_COMPARE)
        assert "icmp eq i32" in out
