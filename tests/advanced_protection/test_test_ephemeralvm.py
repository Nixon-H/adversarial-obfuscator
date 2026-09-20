import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestEphemeralVM:

    def test_ephemeral_opcode_map_is_bijection(self):
        from vm.ephemeral_isa import generate_ephemeral_opcode_map
        omap = generate_ephemeral_opcode_map(b"cicd-seed-2026", num_opcodes=256)
        assert len(omap) == 256
        values = set(omap.values())
        assert len(values) == 256
        assert min(values) == 0
        assert max(values) == 255

    def test_ephemeral_opcode_map_deterministic(self):
        from vm.ephemeral_isa import generate_ephemeral_opcode_map
        seed = b"build-42"
        m1 = generate_ephemeral_opcode_map(seed, 256)
        m2 = generate_ephemeral_opcode_map(seed, 256)
        assert m1 == m2

    def test_ephemeral_opcode_map_different_seeds(self):
        from vm.ephemeral_isa import generate_ephemeral_opcode_map
        m1 = generate_ephemeral_opcode_map(b"seed-a", 256)
        m2 = generate_ephemeral_opcode_map(b"seed-b", 256)
        assert m1 != m2

    def test_remap_bytecode_roundtrip(self):
        from vm.ephemeral_isa import generate_ephemeral_opcode_map, remap_bytecode
        from vm.vm_isa import VMInstruction, VMOpcode, VMOperand
        seed = b"test-build-roundtrip"
        omap = generate_ephemeral_opcode_map(seed, 256)

        inst = VMInstruction(VMOpcode.ADD, [
            (VMOperand.REG, 1),
            (VMOperand.REG, 2),
        ])
        original = bytes(inst.encode())

        remapped = remap_bytecode(original, omap)
        assert remapped != original
        assert len(remapped) == len(original)

        inverse = {v: k for k, v in omap.items()}
        restored = remap_bytecode(remapped, inverse)
        assert restored == original

    def test_remap_bytecode_roundtrip_multi_inst(self):
        from vm.ephemeral_isa import generate_ephemeral_opcode_map, remap_bytecode
        from vm.vm_isa import VMInstruction, VMOpcode, VMOperand
        seed = b"multi-inst-roundtrip"
        omap = generate_ephemeral_opcode_map(seed, 256)

        insts = [
            VMInstruction(VMOpcode.NOP),
            VMInstruction(VMOpcode.MOV, [(VMOperand.REG, 1), (VMOperand.IMM16, 42)]),
            VMInstruction(VMOpcode.ADD, [(VMOperand.REG, 1), (VMOperand.REG, 2)]),
            VMInstruction(VMOpcode.JMP, [(VMOperand.ABS_ADDR, 0x1000)]),
            VMInstruction(VMOpcode.PUSH, [(VMOperand.REG, 3)]),
            VMInstruction(VMOpcode.POP, [(VMOperand.REG, 4)]),
        ]
        original = bytes(b''.join(bytes(inst.encode()) for inst in insts))

        remapped = remap_bytecode(original, omap)
        assert remapped != original
        assert len(remapped) == len(original)

        inverse = {v: k for k, v in omap.items()}
        restored = remap_bytecode(remapped, inverse)
        assert restored == original

    def test_operand_map_generation_and_remapping(self):
        from vm.ephemeral_isa import (
            generate_ephemeral_opcode_map,
            generate_ephemeral_operand_map,
            remap_bytecode,
        )
        from vm.vm_isa import VMInstruction, VMOpcode, VMOperand
        seed = b"operand-test"
        omap = generate_ephemeral_opcode_map(seed, 256)
        opmap = generate_ephemeral_operand_map(seed, 8)

        assert len(opmap) == 8
        values = set(opmap.values())
        assert len(values) == 8
        assert min(values) == 0
        assert max(values) == 7

        inst = VMInstruction(VMOpcode.ADD, [
            (VMOperand.REG, 1),
            (VMOperand.REG, 2),
        ])
        original = bytes(inst.encode())

        remapped = remap_bytecode(original, omap, opmap)
        assert remapped != original
        assert len(remapped) == len(original)

        inverse_op = {v: k for k, v in omap.items()}
        inverse_operand = {v: k for k, v in opmap.items()}
        restored = remap_bytecode(remapped, inverse_op, inverse_operand, reverse=True)
        assert restored == original

    def test_interpreter_dispatch_table_generation(self):
        from vm.ephemeral_isa import (
            generate_ephemeral_opcode_map,
            generate_interpreter_dispatch_table,
        )
        seed = b"dispatch-table-test"
        omap = generate_ephemeral_opcode_map(seed, 256)
        table = generate_interpreter_dispatch_table(omap, seed)

        assert isinstance(table, bytes)
        assert len(table) == 256

        key = 42  # default XOR key when no seed kwarg
        for logical, physical in omap.items():
            assert table[physical] == ((logical ^ key) & 0xFF)

        assert len(set(table)) == 256  # all logical values appear
