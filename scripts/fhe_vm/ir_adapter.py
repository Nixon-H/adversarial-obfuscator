"""
ir_adapter.py

Purpose:
Bridge between SSA IR (IrFunction) and FHE circuits (FHECircuit).
Walks the IR's basic blocks and instructions, converting supported
arithmetic operations (add, mul, sub) into circuit gates. Rejects
unsupported operations (calls, control flow, comparisons, etc.)
with clear error messages.

Architectural Role:
Compilation layer for the FHE VM. SSAToFHECircuit.convert_function()
translates an IrFunction into an FHECircuit by mapping IR values to
circuit gates and IR operations to gate operations.

Execution Context:
Called by FHEExecutor when a function is selected for FHE compilation.
is_fhe_compatible() checks prerequisites (single basic block, only
arithmetic ops, max 10 ops) before conversion begins.

Dependencies:
- irgen.compile (IrFunction, IrInstruction, IrValue, IrModule)
- circuit (FHECircuit)
- Standard library (typing)

Security Relevance:
The adapter must faithfully represent the IR function as an FHE
circuit. Any semantic mismatch (wrong operand mapping, missed
instructions, incorrect gate construction) will produce incorrect
encrypted computation results and invalidate the security guarantee.

Maintenance Notes:
- MAX_FHE_OPS = 10 limits circuit depth to prevent noise overflow
  in the BGV scheme. Increase cautiously with larger parameters.
- MEMORY_OPS (alloca/load/store/gep) are scaffolding for parameter
  passing and are mapped to input/output gates.
- UNSUPPORTED_OPS includes all non-arithmetic operations. Calling
  these will raise ValueError from convert_function().
- The _resolve_operand method creates new input gates for unresolved
  values, which may produce incorrect circuits if the value was
  supposed to come from a computation.
"""

from __future__ import annotations
from typing import Optional

from irgen.compile import IrFunction, IrInstruction, IrValue, IrModule
from .circuit import FHECircuit


MAX_FHE_OPS = 10

# Ops that are NOT real arithmetic and should be ignored during
# compatibility checking.  alloca/load/store are compiler scaffolding
# for parameter passing and don't represent real computation.
MEMORY_OPS = {'alloca', 'load', 'store', 'gep'}

UNSUPPORTED_OPS = {
    'call', 'jmp', 'br', 'phi',
    'div', 'mod', 'and', 'or', 'xor', 'shl', 'shr',
    'eq', 'ne', 'lt', 'le', 'gt', 'ge',
    'zext', 'trunc', 'sitofp', 'fptosi', 'bitcast',
    'not', 'ret', 'nop', 'unreachable',
}


def is_fhe_compatible(function: IrFunction) -> tuple[bool, str]:
    """Check if a function is suitable for FHE compilation.

    Returns (compatible, reason).  Compatible means: single basic block,
    only arithmetic ops (add/sub/mul), max 10 ops, no control flow.
    """
    if len(function.blocks) > 1:
        return False, "multiple basic blocks (control flow not supported)"
    if not function.blocks:
        return False, "no basic blocks"
    block = function.blocks[0]
    arithmetic_ops = 0
    for inst in block.instructions:
        op = inst.opcode
        if op in MEMORY_OPS:
            continue
        if op in ('add', 'sub', 'mul'):
            arithmetic_ops += 1
            if arithmetic_ops > MAX_FHE_OPS:
                return False, f"too many arithmetic ops ({arithmetic_ops} > {MAX_FHE_OPS})"
        elif op in UNSUPPORTED_OPS:
            return False, f"unsupported opcode: {op}"
    return True, "compatible"


class SSAToFHECircuit:
    def __init__(self):
        self.circuit: Optional[FHECircuit] = None
        self._value_map: dict[int, int] = {}
        self._param_indices: dict[str, int] = {}
        self._slot_to_param: dict[int, str] = {}
        self._param_to_gate: dict[int, int] = {}

    def convert_function(self, function: IrFunction) -> FHECircuit:
        compatible, reason = is_fhe_compatible(function)
        if not compatible:
            raise ValueError(f"Function {function.name} not FHE-compatible: {reason}")
        self.circuit = FHECircuit(function.name)
        self._value_map = {}
        self._param_indices = {}
        self._slot_to_param = {}
        self._param_to_gate = {}
        param_index = 0
        for param_name, _ in function.params:
            self._param_indices[param_name] = param_index
            param_index += 1
        block = function.blocks[0]
        for inst in block.instructions:
            self._convert_instruction(inst)
        for inst in function.blocks[0].instructions:
            if inst.opcode == 'ret':
                if inst.operands and len(inst.operands) >= 2:
                    val = inst.operands[1]
                    if isinstance(val, IrValue) and val.id in self._value_map:
                        self.circuit.set_output(self._value_map[val.id])
                break
        output_gates = list(self.circuit.gates.keys())
        for gid in output_gates:
            gate = self.circuit.gates[gid]
            if gate.gate_type == 'output':
                return self.circuit
        if self.circuit.output_gate is None and block.instructions:
            last_inst = block.instructions[-1]
            if last_inst.result and last_inst.result.id in self._value_map:
                self.circuit.set_output(self._value_map[last_inst.result.id])
        return self.circuit

    def _convert_instruction(self, inst: IrInstruction):
        op = inst.opcode
        if op == 'add':
            self._convert_binary('add', inst)
        elif op == 'sub':
            self._convert_binary('sub', inst)
        elif op == 'mul':
            self._convert_binary('mul', inst)
        elif op == 'store':
            if len(inst.operands) >= 2:
                val_op = inst.operands[0]
                ptr_op = inst.operands[1]
                if isinstance(val_op, IrValue) and isinstance(ptr_op, IrValue):
                    name = (val_op.name or '').lstrip('%')
                    if name in self._param_indices:
                        self._slot_to_param[ptr_op.id] = name
        elif op == 'load':
            if inst.result and len(inst.operands) >= 1:
                ptr_op = inst.operands[0]
                if isinstance(ptr_op, IrValue) and ptr_op.id in self._slot_to_param:
                    param_name = self._slot_to_param[ptr_op.id]
                    param_idx = self._param_indices[param_name]
                    if param_idx in self._param_to_gate:
                        self._value_map[inst.result.id] = self._param_to_gate[param_idx]
                    else:
                        gid = self.circuit.new_gate('input')
                        self._param_to_gate[param_idx] = gid
                        self._value_map[inst.result.id] = gid
                elif isinstance(ptr_op, IrValue):
                    gid = self.circuit.new_gate('input')
                    self._value_map[inst.result.id] = gid
        elif op in ('alloca', 'gep', 'nop'):
            pass
        elif op == 'ret':
            pass
        elif op == 'call':
            self._convert_call(inst)
        elif op in UNSUPPORTED_OPS:
            pass
        else:
            if inst.result and self._is_constant_inst(inst):
                val = self._constant_value(inst)
                gid = self.circuit.new_gate('const', value=val)
                if inst.result:
                    self._value_map[inst.result.id] = gid

    def _convert_binary(self, gate_type: str, inst: IrInstruction):
        if not inst.result or len(inst.operands) < 2:
            return
        lhs = self._resolve_operand(inst.operands[0])
        rhs = self._resolve_operand(inst.operands[1])
        gid = self.circuit.new_gate(gate_type, operands=[lhs, rhs])
        self._value_map[inst.result.id] = gid

    def _convert_call(self, inst: IrInstruction):
        raise NotImplementedError("call instructions are not yet supported by FHE-VM")

    def _resolve_operand(self, op) -> int:
        if isinstance(op, IrValue):
            if op.id in self._value_map:
                return self._value_map[op.id]
            if op.name and self._is_numeric_str(op.name):
                val = int(op.name) % self._get_t_modulus()
                gid = self.circuit.new_gate('const', value=val)
                self._value_map[op.id] = gid
                return gid
            gid = self.circuit.new_gate('input')
            self._value_map[op.id] = gid
            return gid
        if isinstance(op, str):
            gid = self.circuit.new_gate('input')
            return gid
        gid = self.circuit.new_gate('input')
        return gid

    def _is_constant_inst(self, inst: IrInstruction) -> bool:
        try:
            if inst.opcode == 'add':
                return all(self._is_numeric_str(str(o)) for o in inst.operands)
            return inst.is_constant()
        except Exception:
            return False

    def _constant_value(self, inst: IrInstruction) -> int:
        try:
            vals = []
            for o in inst.operands:
                if isinstance(o, IrValue) and self._is_numeric_str(o.name):
                    vals.append(int(o.name))
                elif isinstance(o, IrValue):
                    vals.append(0)
                else:
                    vals.append(0)
            if inst.opcode == 'add':
                return sum(vals) % self._get_t_modulus()
            elif inst.opcode == 'sub':
                return (vals[0] - vals[1]) % self._get_t_modulus()
            elif inst.opcode == 'mul':
                result = 1
                for v in vals:
                    result *= v
                return result % self._get_t_modulus()
            return vals[0] if vals else 0
        except (ValueError, IndexError):
            return 0

    def _get_t_modulus(self) -> int:
        try:
            from .scheme import BGVParameters
            return BGVParameters().t
        except ImportError:
            return 17

    @staticmethod
    def _is_numeric_str(s: str) -> bool:
        try:
            int(s)
            return True
        except (ValueError, TypeError):
            return False
