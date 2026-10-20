import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestInterpreter:
    def test_vm_interpreter_init_sets_state_default(self):
        from vm.interpreter import VMInterpreter
        vm = VMInterpreter(b"\x00", opcode_map={i: i for i in range(256)})
        assert not vm.state.get("halted", True)
        assert len(vm.state["regs"]) == 16

    def test_vm_interpreter_init_sets_state(self, monkeypatch):
        from vm.interpreter import VMInterpreter
        monkeypatch.setattr("vm.interpreter._phase2_enabled", lambda: True)
        vm = VMInterpreter(b"\x00", opcode_map={i: i for i in range(256)})
        assert not vm.state.get("halted", True)
        assert len(vm.state["regs"]) == 16
        assert len(vm.state["memory"]) == 65536

    def test_vm_nop_does_not_halt(self, monkeypatch):
        from vm.interpreter import VMInterpreter
        from vm.vm_isa import VMOpcode
        monkeypatch.setattr("vm.interpreter._phase2_enabled", lambda: True)
        bc = bytearray([VMOpcode.NOP])
        vm = VMInterpreter(bytes(bc), opcode_map={i: i for i in range(256)})
        vm.step()
        assert not vm.state["halted"]

    def _make_flat_bc(self, opcode, *args):
        bc = bytearray([opcode])
        bc.extend(args)
        return bc

    def test_vm_add(self, monkeypatch):
        from vm.interpreter import VMInterpreter
        from vm.vm_isa import VMOpcode
        monkeypatch.setattr("vm.interpreter._phase2_enabled", lambda: True)
        state = {"regs": [0] * 16, "memory": bytearray(65536), "stack": [], "halted": False}
        state["regs"][1] = 3
        state["regs"][2] = 4
        bc = self._make_flat_bc(VMOpcode.ADD, 1, 2)
        vm = VMInterpreter(bytes(bc), state=state, opcode_map={i: i for i in range(256)})
        vm.step()
        assert state["regs"][1] == 7

    def test_vm_mov(self, monkeypatch):
        from vm.interpreter import VMInterpreter
        from vm.vm_isa import VMOpcode
        monkeypatch.setattr("vm.interpreter._phase2_enabled", lambda: True)
        state = {"regs": [0] * 16, "memory": bytearray(65536), "stack": [], "halted": False}
        bc = self._make_flat_bc(VMOpcode.MOV, 1, 42, 0)
        vm = VMInterpreter(bytes(bc), state=state, opcode_map={i: i for i in range(256)})
        vm.step()
        assert state["regs"][1] == 42

    def test_vm_jmp(self, monkeypatch):
        from vm.interpreter import VMInterpreter
        from vm.vm_isa import VMOpcode
        monkeypatch.setattr("vm.interpreter._phase2_enabled", lambda: True)
        state = {"regs": [0] * 16, "memory": bytearray(65536), "stack": [], "halted": False}
        target = 100
        bc = self._make_flat_bc(VMOpcode.JMP, target & 0xFF, (target >> 8) & 0xFF,
                                (target >> 16) & 0xFF, (target >> 24) & 0xFF)
        vm = VMInterpreter(bytes(bc), state=state, opcode_map={i: i for i in range(256)})
        vm.step()
        assert state["regs"][14] == 100

    def test_vm_push_pop(self, monkeypatch):
        from vm.interpreter import VMInterpreter
        from vm.vm_isa import VMOpcode
        monkeypatch.setattr("vm.interpreter._phase2_enabled", lambda: True)
        state = {"regs": [0] * 16, "memory": bytearray(65536), "stack": [], "halted": False}
        state["regs"][1] = 99
        push_bc = self._make_flat_bc(VMOpcode.PUSH, 1)
        pop_bc = self._make_flat_bc(VMOpcode.POP, 2)
        vm = VMInterpreter(bytes(push_bc + pop_bc), state=state, opcode_map={i: i for i in range(256)})
        vm.step()
        vm.step()
        assert state["regs"][2] == 99

    def test_vm_div_by_zero_halts(self, monkeypatch):
        from vm.interpreter import VMInterpreter
        from vm.vm_isa import VMOpcode
        monkeypatch.setattr("vm.interpreter._phase2_enabled", lambda: True)
        state = {"regs": [0] * 16, "memory": bytearray(65536), "stack": [], "halted": False}
        state["regs"][1] = 10
        state["regs"][2] = 0
        bc = self._make_flat_bc(VMOpcode.DIV, 1, 2)
        vm = VMInterpreter(bytes(bc), state=state, opcode_map={i: i for i in range(256)})
        vm.step()
        assert state["halted"]

    def test_vm_run(self, monkeypatch):
        from vm.interpreter import VMInterpreter
        from vm.vm_isa import VMOpcode
        monkeypatch.setattr("vm.interpreter._phase2_enabled", lambda: True)
        bc = self._make_flat_bc(VMOpcode.NOP)
        vm = VMInterpreter(bytes(bc), opcode_map={i: i for i in range(256)})
        result = vm.run(max_steps=10)
        assert "regs" in result

    def test_vm_enc_add(self, monkeypatch):
        from vm.interpreter import VMInterpreter
        from vm.vm_isa import VMOpcode
        monkeypatch.setattr("vm.interpreter._phase2_enabled", lambda: True)
        state = {"regs": [0] * 16, "memory": bytearray(65536), "stack": [], "halted": False}
        key = 0xAB
        plain_a = 10
        plain_b = 20
        state["regs"][1] = plain_a ^ key
        state["regs"][2] = plain_b ^ key
        bc = self._make_flat_bc(VMOpcode.ENC_ADD, 1, 2, key)
        vm = VMInterpreter(bytes(bc), state=state, opcode_map={i: i for i in range(256)})
        vm.step()
        result = state["regs"][1] ^ key
        assert result == (plain_a + plain_b) & 0xFFFFFFFFFFFFFFFF

    def test_vm_step_halts_on_unknown_opcode(self, monkeypatch):
        from vm.interpreter import VMInterpreter
        monkeypatch.setattr("vm.interpreter._phase2_enabled", lambda: True)
        bc = bytearray([0xFF, 0x00])
        vm = VMInterpreter(bytes(bc), opcode_map={i: i for i in range(256)})
        result = vm.step()
        assert result is False
        assert vm.state["halted"]
