"""
validation/ir_to_smt.py

Purpose:
Translates Nixon IR module objects into Z3 BitVec formulas. Handles basic
arithmetic/logic instructions, comparisons, phi nodes, memory (load/store),
block terminators (jmp/br/ret), and control-flow dispatch via a state
variable.

Security Relevance:
This is the bridge between the IR representation and the SMT proof system.
If the translation is incorrect, the IR-level proofs (mutation, fragment,
VM correctness) are meaningless. The translator must faithfully model IR
semantics.

Dependencies:
- z3 (BitVec solver)
"""
from __future__ import annotations
from scripts.z3_optional import z3

BITWIDTH = 64


class IRToSMT:
    """
    Translates IR modules into Z3 formulas for equivalence checking.

    What it validates:
    - Each instruction maps to a Z3 BitVec constraint on register state.
    - Control flow is encoded via a block-index state variable.
    - Phi nodes approximate merge semantics via ITE.

    Security impact:
    If an IR instruction is not handled (opcode missing), it silently
    returns None and is NOT encoded. The resulting formula is weaker than
    the actual IR semantics, potentially enabling false equivalence proofs.

    Failure mode:
    Unsupported opcodes produce no constraints -> may certify incorrect
    transformations. Keep _translate_instruction's opcode list current.
    """
    def __init__(self):
        self.z3_vars: dict[str, z3.BitVecRef] = {}
        self.z3_registers: dict[int, z3.BitVecRef] = {}
        self._output_var: z3.BitVecRef | None = None
        self._func_inputs: list[z3.BitVecRef] = []
        self._memory: dict[int, z3.BitVecRef] = {}
        self._alloca_count = 0
        self._param_reg_ids: set[int] = set()

    def _bv(self, name: str) -> z3.BitVecRef:
        return z3.BitVec(name, BITWIDTH)

    def _ensure_param(self, name: str) -> z3.BitVecRef:
        if name not in self.z3_vars:
            self.z3_vars[name] = self._bv(name)
        return self.z3_vars[name]

    def _make_state_var(self) -> z3.BitVecRef:
        return self._bv("__state__")

    def translate(self, module) -> z3.BoolRef:
        constraints = []
        for func in module.functions:
            result = self._translate_function(func)
            if result is not None:
                constraints.append(result)
        return z3.And(*constraints) if constraints else z3.BoolVal(True)

    def _translate_function(self, func) -> z3.BoolRef | None:
        self.z3_registers = {}
        self._output_var = None
        self._memory = {}
        self._alloca_count = 0
        self._param_reg_ids = set()

        param_name_to_var = {}
        for idx, (pname, ptype) in enumerate(func.params):
            pname_clean = pname.lstrip("%")
            var = self._ensure_param(pname_clean)
            self._func_inputs.append(var)
            param_name_to_var[pname_clean] = var

        if func.entry_block:
            for inst in func.entry_block.instructions:
                if inst.opcode == 'store' and len(inst.operands) >= 1:
                    operand = inst.operands[0]
                    if hasattr(operand, 'id') and hasattr(operand, 'name'):
                        op_name = str(operand).lstrip("%").split()[0]
                        if op_name in param_name_to_var:
                            self.z3_registers[operand.id] = param_name_to_var[op_name]
                            self._param_reg_ids.add(operand.id)

        state_var = self._make_state_var()

        block_labels_map: dict[str, int] = {}
        for i, block in enumerate(func.blocks):
            block_labels_map[block.label] = i

        block_smts = []
        for i, block in enumerate(func.blocks):
            block_formula = self._translate_block(block, block_labels_map, state_var)
            block_smts.append((i, block_formula))

        dispatch = []
        entry_state = z3.BitVecVal(block_labels_map.get(func.entry_block.label if func.entry_block else "entry", 0), BITWIDTH)
        for i, (bidx, formula) in enumerate(block_smts):
            guard = (state_var == z3.BitVecVal(bidx, BITWIDTH))
            masked_formula = z3.If(guard, formula, z3.BoolVal(True))
            dispatch.append(masked_formula)

        dispatch.append(state_var == entry_state)
        return z3.And(*dispatch)

    def _get_param_ir_value(self, func, param_idx):
        if func.entry_block and func.entry_block.instructions:
            for inst in func.entry_block.instructions:
                if inst.opcode == 'store' and len(inst.operands) >= 1:
                    op = inst.operands[0]
                    if hasattr(op, 'result') and op.result is not None:
                        return op.result
        return None

    def _translate_block(self, block, block_labels_map: dict[str, int], state_var: z3.BitVecRef) -> z3.BoolRef:
        constraints = []
        for inst in block.instructions:
            result = self._translate_instruction(inst)
            if result is not None:
                constraints.append(result)

        if block.terminator:
            term_result = self._translate_terminator(block.terminator, block_labels_map, state_var, block.label)
            if term_result is not None:
                constraints.append(term_result)

        return z3.And(*constraints) if constraints else z3.BoolVal(True)

    def _get_ir_value(self, operand) -> z3.BitVecRef:
        op_str = str(operand)
        if hasattr(operand, 'id') and isinstance(operand.id, int):
            rid = operand.id
            if rid in self.z3_registers:
                return self.z3_registers[rid]
            try:
                val = int(op_str)
                return z3.BitVecVal(val & ((1 << BITWIDTH) - 1), BITWIDTH)
            except (ValueError, TypeError):
                fresh = self._bv(f"reg_{rid}")
                self.z3_registers[rid] = fresh
                return fresh
        if hasattr(operand, 'result') and operand.result is not None:
            rid = operand.result.id
            if rid in self.z3_registers:
                return self.z3_registers[rid]
            try:
                val = int(str(operand.result))
                return z3.BitVecVal(val & ((1 << BITWIDTH) - 1), BITWIDTH)
            except (ValueError, TypeError):
                fresh = self._bv(f"reg_{rid}")
                self.z3_registers[rid] = fresh
                return fresh
        if isinstance(operand, int):
            return z3.BitVecVal(operand & ((1 << BITWIDTH) - 1), BITWIDTH)
        try:
            val = int(op_str)
            return z3.BitVecVal(val & ((1 << BITWIDTH) - 1), BITWIDTH)
        except (ValueError, TypeError):
            pass
        return self._bv(f"op_{op_str}")

    def _translate_instruction(self, inst) -> z3.BoolRef | None:
        if inst.opcode in ('add', 'sub', 'mul', 'and', 'or', 'xor', 'shl', 'shr', 'div', 'mod'):
            if len(inst.operands) >= 2:
                lhs = self._get_ir_value(inst.operands[0])
                rhs = self._get_ir_value(inst.operands[1])
                if inst.result is not None:
                    rid = inst.result.id
                    if inst.opcode == 'add':
                        val = lhs + rhs
                    elif inst.opcode == 'sub':
                        val = lhs - rhs
                    elif inst.opcode == 'mul':
                        val = lhs * rhs
                    elif inst.opcode == 'and':
                        val = lhs & rhs
                    elif inst.opcode == 'or':
                        val = lhs | rhs
                    elif inst.opcode == 'xor':
                        val = lhs ^ rhs
                    elif inst.opcode == 'shl':
                        val = lhs << rhs
                    elif inst.opcode == 'shr':
                        val = z3.LShR(lhs, rhs)
                    elif inst.opcode == 'div':
                        val = z3.BVSDiv(lhs, rhs)
                    elif inst.opcode == 'mod':
                        val = z3.SRem(lhs, rhs)
                    else:
                        val = lhs
                    self.z3_registers[rid] = val
                    return z3.BoolVal(True)
        elif inst.opcode in ('eq', 'ne', 'lt', 'le', 'gt', 'ge'):
            if len(inst.operands) >= 2:
                lhs = self._get_ir_value(inst.operands[0])
                rhs = self._get_ir_value(inst.operands[1])
                if inst.result is not None:
                    rid = inst.result.id
                    if inst.opcode == 'eq':
                        cond = (lhs == rhs)
                    elif inst.opcode == 'ne':
                        cond = (lhs != rhs)
                    elif inst.opcode == 'lt':
                        cond = lhs < rhs
                    elif inst.opcode == 'le':
                        cond = lhs <= rhs
                    elif inst.opcode == 'gt':
                        cond = lhs > rhs
                    elif inst.opcode == 'ge':
                        cond = lhs >= rhs
                    else:
                        cond = (lhs == rhs)
                    result_bv = z3.If(cond, z3.BitVecVal(1, BITWIDTH), z3.BitVecVal(0, BITWIDTH))
                    self.z3_registers[rid] = result_bv
                    return z3.BoolVal(True)
        elif inst.opcode == 'phi':
            if inst.result is not None and len(inst.operands) >= 2:
                rid = inst.result.id
                candidates = []
                for i in range(0, len(inst.operands) - 1, 2):
                    val_operand = inst.operands[i]
                    val = self._get_ir_value(val_operand)
                    candidates.append(val)
                if candidates:
                    result = candidates[0]
                    for i, c in enumerate(candidates[1:], start=1):
                        block_guard = z3.BoolVal(f"_phi_guard_{rid}_{i}")
                        result = z3.If(block_guard, c, result)
                    self.z3_registers[rid] = result
                    return z3.BoolVal(True)
        elif inst.opcode == 'zext':
            if inst.operands and inst.result is not None:
                val = self._get_ir_value(inst.operands[0])
                rid = inst.result.id
                self.z3_registers[rid] = val
                return z3.BoolVal(True)
        elif inst.opcode == 'load':
            if inst.result is not None and inst.operands:
                rid = inst.result.id
                ptr = self._get_ir_value(inst.operands[0])
                ptr_key = hash(str(ptr))
                if ptr_key in self._memory:
                    self.z3_registers[rid] = self._memory[ptr_key]
                else:
                    fresh = self._bv(f"load_{rid}")
                    self.z3_registers[rid] = fresh
                return None
        elif inst.opcode == 'alloca':
            if inst.result is not None:
                rid = inst.result.id
                self._alloca_count += 1
                ptr = self._bv(f"alloca_{rid}")
                self.z3_registers[rid] = ptr
            return None
        elif inst.opcode == 'store':
            if len(inst.operands) >= 2:
                val = self._get_ir_value(inst.operands[0])
                ptr = self._get_ir_value(inst.operands[1])
                ptr_key = hash(str(ptr))
                self._memory[ptr_key] = val
            return None
        elif inst.opcode == 'call':
            return None
        elif inst.opcode == 'nop':
            return None
        raise NotImplementedError(f"Unsupported IR opcode: {inst.opcode if hasattr(inst, 'opcode') else 'unknown'}")

    def _translate_terminator(self, term, block_labels_map: dict[str, int],
                               state_var: z3.BitVecRef, current_label: str) -> z3.BoolRef | None:
        if term.opcode == 'ret':
            if term.operands:
                val = self._get_ir_value(term.operands[1]) if len(term.operands) >= 2 else None
                if val is not None:
                    self._output_var = val
            return None
        elif term.opcode == 'jmp':
            target_label = term.operands[0] if term.operands else None
            if target_label and target_label in block_labels_map:
                next_state = z3.BitVecVal(block_labels_map[target_label], BITWIDTH)
                return state_var == next_state
            return None
        elif term.opcode == 'br':
            if len(term.operands) >= 3:
                cond = self._get_ir_value(term.operands[0])
                true_label = term.operands[1]
                false_label = term.operands[2]
                cond_bool = (cond != 0)
                true_state = z3.BitVecVal(block_labels_map.get(true_label, 0), BITWIDTH)
                false_state = z3.BitVecVal(block_labels_map.get(false_label, 0), BITWIDTH)
                return state_var == z3.If(cond_bool, true_state, false_state)
        return None

    def get_output_var(self) -> z3.BitVecRef | None:
        return self._output_var

    def get_input_vars(self) -> list[z3.BitVecRef]:
        return self._func_inputs


def ir_to_smt_formula(module) -> tuple[z3.BoolRef, IRToSMT]:
    translator = IRToSMT()
    formula = translator.translate(module)
    return formula, translator
