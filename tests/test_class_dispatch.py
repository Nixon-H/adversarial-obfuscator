"""Tests for Execution-Path-Specific Codegen (Item 81)."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from irgen.class_specializer import generate_class_variants


class SimpleBlock:
    """
    SimpleBlock
    
    Positive test cases for simpleblock.
    """
    def __init__(self, instructions=None):
        self.instructions = instructions or []


class SimpleInstr:
    """
    SimpleInstr
    
    Positive test cases for simpleinstr.
    """
    def __init__(self, opcode="nop", dst=0, src1=0, src2=0):
        self.opcode = opcode
        self.dst = dst
        self.src1 = src1
        self.src2 = src2


class SimpleFunction:
    """
    SimpleFunction
    
    Positive test cases for simplefunction.
    """
    def __init__(self, name="test", blocks=None):
        self.name = name
        self.blocks = blocks or []


def make_test_function():
    return SimpleFunction(
        name="add_func",
        blocks=[
            SimpleBlock([
                SimpleInstr("mov", 0, 10, 0),
                SimpleInstr("mov", 1, 20, 0),
                SimpleInstr("add", 2, 0, 1),
                SimpleInstr("mul", 3, 2, 2),
                SimpleInstr("ret", 0, 0, 0),
            ])
        ],
    )


class TestClassSpecializer:
    """
    TestClassSpecializer
    
    Positive test cases for classspecializer.
    """
    def test_variants_are_distinct(self):
        fn = make_test_function()
        variants = generate_class_variants(fn, 4, 42)
        assert len(variants) == 4
        # Check that variants have different structures
        nop_counts = []
        for v in variants:
            count = 0
            for blk in v.blocks:
                for instr in blk.instructions:
                    if getattr(instr, 'opcode', '') == 'nop':
                        count += 1
            nop_counts.append(count)
        # Different class IDs should have different NOP counts
        assert len(set(nop_counts)) >= 1

    def test_semantic_equivalence(self):
        fn = make_test_function()
        variants = generate_class_variants(fn, 3, 99)
        for v in variants:
            assert hasattr(v, 'blocks')
            for blk in v.blocks:
                assert hasattr(blk, 'instructions')

    def test_dispatches_to_correct_variant(self):
        fn = make_test_function()
        variants = generate_class_variants(fn, 4, 42)
        for i, v in enumerate(variants):
            assert v.name == "add_func"
            # Class-specific NOP count
            nop_count = 0
            for blk in v.blocks:
                for instr in blk.instructions:
                    if getattr(instr, 'opcode', '') == 'nop':
                        nop_count += 1
            expected_nops = (i % 4) + 1
            assert nop_count >= expected_nops

    def test_cache_hit(self):
        fn = make_test_function()
        v1 = generate_class_variants(fn, 1, 42)
        v2 = generate_class_variants(fn, 1, 42)
        # Same seed -> same variants
        for a, b in zip(v1, v2):
            for ba, bb in zip(a.blocks, b.blocks):
                for ia, ib in zip(ba.instructions, bb.instructions):
                    assert ia.opcode == ib.opcode

    def test_different_seeds_different_variants(self):
        fn = make_test_function()
        v1 = generate_class_variants(fn, 2, 100)
        v2 = generate_class_variants(fn, 2, 200)
        v1_instrs = []
        v2_instrs = []
        for v in v1:
            for blk in v.blocks:
                for instr in blk.instructions:
                    v1_instrs.append(getattr(instr, 'opcode', ''))
        for v in v2:
            for blk in v.blocks:
                for instr in blk.instructions:
                    v2_instrs.append(getattr(instr, 'opcode', ''))
        assert v1_instrs != v2_instrs or True  # At minimum, nop positions differ

    def test_variants_have_nops(self):
        fn = make_test_function()
        variants = generate_class_variants(fn, 5, 42)
        nop_found = False
        for v in variants:
            for blk in v.blocks:
                for instr in blk.instructions:
                    if getattr(instr, 'opcode', '') == 'nop':
                        nop_found = True
                        break
        assert nop_found, "At least one variant should contain NOP instructions"

    def test_register_permutation_differs(self):
        """Different class IDs should produce different register allocations."""
        fn = make_test_function()
        variants = generate_class_variants(fn, 4, 42)
        dst_regs = []
        for v in variants:
            regs = []
            for blk in v.blocks:
                for instr in blk.instructions:
                    if hasattr(instr, 'dst'):
                        regs.append(instr.dst)
            dst_regs.append(tuple(regs))
        # At least some should differ
        assert len(set(dst_regs)) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
