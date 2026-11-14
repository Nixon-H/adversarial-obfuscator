"""Semantic fixes in the Python-to-IR compiler.

`assert`/`raise` used to be dropped (a failed licence check fell through),
`while ... else` dropped the else clause, and chained comparisons compared
the previous boolean result instead of the previous comparator.
"""
from irgen.compile import compile_py_to_ir


def _func(src):
    return compile_py_to_ir(src).functions[0]


def _terminators(func):
    return {b.label: (b.terminator.opcode if b.terminator else None)
            for b in func.blocks}


def test_raise_is_unreachable():
    func = _func("def f():\n    raise ValueError('no')\n")
    assert "unreachable" in _terminators(func).values()


def test_assert_has_a_trap_block():
    func = _func("def f():\n    assert 0\n    return 1\n")
    assert "unreachable" in _terminators(func).values()


def test_while_else_is_not_dropped():
    func = _func(
        "def f():\n"
        "    x = 0\n"
        "    while False:\n"
        "        x = 1\n"
        "    else:\n"
        "        x = 2\n"
        "    return x\n")
    # The header's false edge must point at the else block, not straight
    # at the after block; the else block must contain the x = 2 store.
    header = next(b for b in func.blocks
                  if b.terminator and b.terminator.opcode == "br")
    false_label = header.terminator.operands[2]
    else_block = next(b for b in func.blocks if b.label == false_label)
    assert any(getattr(i, "opcode", "") == "store" for i in else_block.instructions)


def test_break_skips_while_else():
    func = _func(
        "def f():\n"
        "    x = 0\n"
        "    while True:\n"
        "        break\n"
        "    else:\n"
        "        x = 2\n"
        "    return x\n")
    header = next(b for b in func.blocks
                  if b.terminator and b.terminator.opcode == "br")
    else_label = header.terminator.operands[2]
    # The break terminator must target a different block than the else.
    break_block = next(b for b in func.blocks
                       if b.terminator and b.terminator.opcode == "jmp"
                       and b.label != header.label)
    assert break_block.terminator.operands[0] != else_label


def test_chained_comparison_uses_the_previous_comparator():
    func = _func("def f(a, b, c):\n    return a < b < c\n")
    lts = [i for b in func.blocks for i in b.instructions
           if getattr(i, "opcode", "") == "lt"]
    assert len(lts) == 2
    first_result = lts[0].result.name
    # The second comparison must not consume the first boolean result.
    assert all(getattr(o, "name", None) != first_result
               for o in lts[1].operands)
    # Both results are combined with an AND.
    assert any(getattr(i, "opcode", "") == "and"
               for b in func.blocks for i in b.instructions)
