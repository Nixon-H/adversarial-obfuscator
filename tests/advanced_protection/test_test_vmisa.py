import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestVmIsa:
    def test_vm_opcode_constants(self):
        from vm.vm_isa import VMOpcode
        assert VMOpcode.NOP == 0
        assert VMOpcode.ADD == 1
        assert VMOpcode.SUB == 2
        assert VMOpcode.LOGICAL_NAMES[0] == "NOP"
        assert VMOpcode.LOGICAL_NAMES[34] == "FUSED_CMP_JMP"

    def test_vm_operand_constants(self):
        from vm.vm_isa import VMOperand
        assert VMOperand.IMM8 == 0
        assert VMOperand.REG == 4

    def test_vm_properties(self):
        from vm.vm_isa import VM_PROPERTIES
        assert VM_PROPERTIES["num_registers"] == 16
        assert VM_PROPERTIES["encoding"] == "variable-width"

    def test_vm_instruction_init(self):
        from vm.vm_isa import VMInstruction, VMOpcode
        inst = VMInstruction(VMOpcode.ADD, [(4, 1), (4, 2)])
        assert inst.opcode == 1
        assert len(inst.operands) == 2

    def test_vm_instruction_repr(self):
        from vm.vm_isa import VMInstruction, VMOpcode
        inst = VMInstruction(VMOpcode.NOP)
        r = repr(inst)
        assert "NOP" in r

    def test_vm_instruction_byte_length(self):
        from vm.vm_isa import VMInstruction, VMOpcode
        inst = VMInstruction(VMOpcode.NOP)
        assert inst.byte_length() == 1

    def test_vm_instruction_byte_length_with_operands(self):
        from vm.vm_isa import VMInstruction, VMOpcode, VMOperand
        inst = VMInstruction(VMOpcode.ADD, [(VMOperand.REG, 1), (VMOperand.REG, 2)])
        assert inst.byte_length() >= 3

    def test_vm_instruction_encode(self):
        from vm.vm_isa import VMInstruction, VMOpcode, VMOperand
        inst = VMInstruction(VMOpcode.JMP, [(VMOperand.ABS_ADDR, 0x1234)])
        encoded = inst.encode()
        assert len(encoded) >= 5
        assert encoded[0] == VMOpcode.JMP

    def test_vm_instruction_encode_with_opcode_map(self):
        from vm.vm_isa import VMInstruction, VMOpcode, VMOperand
        inst = VMInstruction(VMOpcode.ADD, [(VMOperand.REG, 1)])
        omap = {VMOpcode.ADD: 0xAB}
        encoded = inst.encode(omap)
        assert encoded[0] == 0xAB

    def test_vm_instruction_encode_imm_variants(self):
        from vm.vm_isa import VMInstruction, VMOpcode, VMOperand
        inst = VMInstruction(VMOpcode.MOV, [
            (VMOperand.IMM8, 0xFF),
            (VMOperand.IMM16, 0xFFFF),
            (VMOperand.IMM32, 0xDEADBEEF),
        ])
        encoded = inst.encode()
        assert len(encoded) > 5
