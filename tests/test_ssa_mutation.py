"""Tests for build-time SSA Mutation (Item 83)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestSsaMutation:
    """
    TestSsaMutation
    
    Positive test cases for ssamutation.
    """
    def test_generate_variants_produces_correct_count(self):
        from irgen.ssa_mutation import generate_ssa_variants
        ir = [
            {"opcode": "add", "operands": ["%a", "%b"]},
            {"opcode": "mul", "operands": ["%c", "%d"]},
            {"opcode": "store", "operands": ["%a", "%r"]},
        ]
        variants = generate_ssa_variants("test_fn", ir, 4)
        assert len(variants) == 4, f"Expected 4 variants, got {len(variants)}"

    def test_variants_are_distinct(self):
        from irgen.ssa_mutation import generate_ssa_variants
        ir = [
            {"opcode": "add", "operands": ["%a", "%b"]},
            {"opcode": "mul", "operands": ["%c", "%d"]},
            {"opcode": "sub", "operands": ["%e", "%f"]},
        ]
        variants = generate_ssa_variants("distinct_fn", ir, 6)
        inst_reprs = set()
        for v in variants:
            ops = tuple(tuple(i.get("operands", [])) for i in v["instructions"])
            inst_reprs.add(ops)
        assert len(inst_reprs) >= 2, "Should produce at least 2 distinct operand orderings"

    def test_preserves_semantics(self):
        from irgen.ssa_mutation import generate_ssa_variants
        ir = [
            {"opcode": "add", "operands": ["%a", "%b"]},
            {"opcode": "add", "operands": ["%c", "%d"]},
            {"opcode": "store", "operands": ["%r", "%s"]},
        ]
        variants = generate_ssa_variants("sem_test", ir, 4)
        for v in variants:
            commutative_count = sum(
                1 for i in v["instructions"]
                if i["opcode"] in {"add", "mul", "and", "or", "xor", "eq", "ne"}
                and len(i.get("operands", [])) >= 2
            )
            assert commutative_count >= 2, "Should preserve commutative operations"

    def test_deterministic_given_same_name(self):
        from irgen.ssa_mutation import generate_ssa_variants
        ir = [
            {"opcode": "add", "operands": ["%a", "%b"]},
            {"opcode": "mul", "operands": ["%c", "%d"]},
        ]
        v1 = generate_ssa_variants("det_test", ir, 3)
        v2 = generate_ssa_variants("det_test", ir, 3)
        assert v1 == v2, "Same function name should produce identical variants"

    def test_different_names_different_variants(self):
        from irgen.ssa_mutation import generate_ssa_variants
        ir = [
            {"opcode": "add", "operands": ["%a", "%b"]},
            {"opcode": "mul", "operands": ["%c", "%d"]},
            {"opcode": "add", "operands": ["%e", "%f"]},
            {"opcode": "sub", "operands": ["%g", "%h"]},
            {"opcode": "xor", "operands": ["%i", "%j"]},
            {"opcode": "or", "operands": ["%k", "%l"]},
            {"opcode": "store", "operands": ["%m", "%n"]},
        ]
        v1 = generate_ssa_variants("func_alpha", ir, 16)
        v2 = generate_ssa_variants("func_beta", ir, 16)
        v1_repr = [tuple(tuple(i.get("operands", [])) for i in v["instructions"]) for v in v1]
        v2_repr = [tuple(tuple(i.get("operands", [])) for i in v["instructions"]) for v in v2]
        assert v1_repr != v2_repr, "Different function names should produce different variant sets"

    def test_generate_config_produces_all_functions(self):
        from irgen.ssa_mutation import generate_ssa_mutation_config
        funcs = {
            "f1": [{"opcode": "add", "operands": ["%a", "%b"]}],
            "f2": [{"opcode": "mul", "operands": ["%c", "%d"]}],
        }
        config = generate_ssa_mutation_config(funcs, 3)
        assert set(config.keys()) == {"f1", "f2"}
        assert config["f1"]["num_variants"] == 3
        assert config["f2"]["num_variants"] == 3

    def test_phi_positions_generated(self):
        from irgen.ssa_mutation import generate_ssa_variants
        ir = [
            {"opcode": "add", "operands": ["%a", "%b"]},
            {"opcode": "sub", "operands": ["%c", "%d"]},
            {"opcode": "mul", "operands": ["%e", "%f"]},
            {"opcode": "store", "operands": ["%r", "%s"]},
        ]
        variants = generate_ssa_variants("phi_test", ir, 4)
        for v in variants:
            assert "phi_positions" in v
            assert len(v["phi_positions"]) > 0, "Each variant should have at least one phi position"
