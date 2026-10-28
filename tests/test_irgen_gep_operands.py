"""A gep with a missing operand must fail where it is produced.

A build once emitted `i32 ` as a GEP index, which llc reported far away as
"expected value token" -- and llvmgen deleted the temp .ll, so the evidence
went with it. Two rounds were spent finding that. Both ends now refuse with
a message that names the instruction: the lowering (llvmgen/lower.py) and
the generator (irgen/compile.py) -- this file covers the generator.
"""

import pytest

from irgen.compile import IrInstruction


def test_gep_with_empty_index_is_rejected():
    ins = IrInstruction("gep", operands=["%p", ""])
    with pytest.raises(ValueError, match="missing operand"):
        str(ins)


def test_gep_with_missing_operand_is_rejected():
    ins = IrInstruction("gep", operands=["%p"])
    with pytest.raises(ValueError, match="missing operand"):
        str(ins)


def test_well_formed_gep_still_renders():
    ins = IrInstruction("gep", operands=["%p", "0"])
    assert "gep ptr %p, i32 0" in str(ins)
