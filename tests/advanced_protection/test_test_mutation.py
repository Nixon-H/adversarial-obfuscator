import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestMutation:
    def test_generate_opcode_map_structure(self, monkeypatch):
        from irgen.mutation import generate_opcode_map
        monkeypatch.setattr("irgen.mutation._phase2_enabled", lambda: True)
        omap = generate_opcode_map(b"seed", 256)
        assert len(omap) >= 29
        for k in range(29):
            assert k in omap
            assert 0 <= omap[k] < 256

    def test_generate_opcode_map_deterministic(self, monkeypatch):
        from irgen.mutation import generate_opcode_map
        monkeypatch.setattr("irgen.mutation._phase2_enabled", lambda: True)
        m1 = generate_opcode_map(b"fixed_seed", 256)
        m2 = generate_opcode_map(b"fixed_seed", 256)
        assert m1 == m2

    def test_generate_opcode_map_different_seed(self, monkeypatch):
        from irgen.mutation import generate_opcode_map
        monkeypatch.setattr("irgen.mutation._phase2_enabled", lambda: True)
        m1 = generate_opcode_map(b"seed_a", 256)
        m2 = generate_opcode_map(b"seed_b", 256)
        assert m1 != m2

    def test_remap_bytecode_empty(self, monkeypatch):
        from irgen.mutation import remap_bytecode
        monkeypatch.setattr("irgen.mutation._phase2_enabled", lambda: True)
        omap = {i: i for i in range(256)}
        assert remap_bytecode(bytearray(), omap) == bytearray()

    def test_remap_bytecode_identity(self, monkeypatch):
        from irgen.mutation import remap_bytecode
        monkeypatch.setattr("irgen.mutation._phase2_enabled", lambda: True)
        bc = bytearray([1, 2, 3])
        omap = {i: i for i in range(256)}
        assert remap_bytecode(bc, omap) == bc

    def test_remap_bytecode_remapped(self, monkeypatch):
        from irgen.mutation import remap_bytecode
        monkeypatch.setattr("irgen.mutation._phase2_enabled", lambda: True)
        # Boundary-aware: opcode bytes are remapped, operand bytes are copied
        # verbatim. MOV (14) has 3 operand bytes, RET (24) has none.
        bc = bytearray([14, 0xAA, 0xBB, 0xCC, 24])
        omap = {14: 99, 24: 77}
        result = remap_bytecode(bc, omap)
        assert result == bytearray([99, 0xAA, 0xBB, 0xCC, 77]), list(result)

    def test_remap_bytecode_operands_not_corrupted(self, monkeypatch):
        """Regression: the old byte-at-a-time remap mapped operand bytes too,
        corrupting every instruction after the first."""
        from irgen.mutation import remap_bytecode
        monkeypatch.setattr("irgen.mutation._phase2_enabled", lambda: True)
        bc = bytearray([0x0e, 0x01, 0x34, 0x12, 0x01, 0x01, 0x02, 0x18])
        omap = {0x0e: 0x3a, 0x01: 0xf8, 0x18: 0x51}
        result = remap_bytecode(bc, omap)
        assert list(result) == [0x3a, 0x01, 0x34, 0x12, 0xf8, 0x01, 0x02, 0x51]

    def test_permute_handler_length_preserved(self, monkeypatch):
        from irgen.mutation import permute_handler
        monkeypatch.setattr("irgen.mutation._phase2_enabled", lambda: True)
        ops = ["load_x", "compute_x", "store_x", "advance_pc_x"]
        result = permute_handler(ops, b"seed")
        assert len(result) == len(ops)
        assert set(result) == set(ops)

    def test_permute_handler_deterministic(self, monkeypatch):
        from irgen.mutation import permute_handler
        monkeypatch.setattr("irgen.mutation._phase2_enabled", lambda: True)
        ops = ["load_a", "compute_b", "store_c"]
        r1 = permute_handler(ops, b"seed")
        r2 = permute_handler(ops, b"seed")
        assert r1 == r2

    def test_generate_handler_variants(self, monkeypatch):
        from irgen.mutation import generate_handler_variants
        monkeypatch.setattr("irgen.mutation._phase2_enabled", lambda: True)
        template = ["load_x", "compute_x", "store_x"]
        variants = generate_handler_variants(template, 3, b"seed")
        assert len(variants) == 3
        assert all(len(v) == 3 for v in variants)

    def test_generate_fusion_plan_structure(self, monkeypatch):
        from irgen.mutation import generate_fusion_plan
        monkeypatch.setattr("irgen.mutation._phase2_enabled", lambda: True)
        plan = generate_fusion_plan(b"seed")
        assert isinstance(plan, list)
        for entry in plan:
            assert "type" in entry

    def test_generate_fusion_plan_with_custom_ops(self, monkeypatch):
        from irgen.mutation import generate_fusion_plan
        monkeypatch.setattr("irgen.mutation._phase2_enabled", lambda: True)
        ops = [("LOAD", "ADD"), ("CMP", "JMP")]
        plan = generate_fusion_plan(b"seed", ops)
        assert len(plan) >= 1

    def test_mutate_instruction_universe_level1(self, monkeypatch):
        from irgen.mutation import mutate_instruction_universe
        monkeypatch.setattr("irgen.mutation._phase2_enabled", lambda: True)
        bc = bytearray([1, 2, 3])
        result, meta = mutate_instruction_universe(bc, b"seed", level=1)
        assert meta["level"] == 1
        assert "opcode_map" in meta

    def test_levels_2_and_3_are_real_executable_mutations(self, monkeypatch):
        from irgen.mutation import mutate_instruction_universe
        from vm.interpreter import VMInterpreter
        monkeypatch.setattr("irgen.mutation._phase2_enabled", lambda: True)
        original = bytearray([14, 1, 7, 0, 24])  # MOV r1, 7; RET
        outputs = []
        for level in (1, 2, 3):
            mutated, meta = mutate_instruction_universe(original, b"seed", level=level)
            outputs.append(bytes(mutated))
            state = VMInterpreter(bytes(mutated), opcode_map=meta["opcode_map"]).run()
            assert state["regs"][1] == 7
            assert meta["unsupported_transforms"] == ["wire_fusion", "wire_splitting"]
        assert len(set(outputs)) == 3

    def test_fusion_plan_fails_closed_instead_of_noop(self, monkeypatch):
        from irgen.mutation import apply_fusion_plan
        import pytest
        monkeypatch.setattr("irgen.mutation._phase2_enabled", lambda: True)
        with pytest.raises(NotImplementedError):
            apply_fusion_plan(bytearray([0]), [{"type": "fuse"}], {})
