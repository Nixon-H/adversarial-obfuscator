from __future__ import annotations

import hashlib
import re
import time
import z3

from scripts.validation.equivalence import EquivalenceChecker
from scripts.validation.ir_to_smt import IRToSMT
from scripts.preservation.report import StageResult

BITWIDTH = 64


def _strip_comma(s: str) -> str:
    return s.rstrip(",")


def _resolve_val(name: str, z3_vars: dict) -> z3.BitVecRef | None:
    name = _strip_comma(name)
    store_key = name + "_store"
    if store_key in z3_vars:
        return z3_vars[store_key]
    if name in z3_vars:
        return z3_vars[name]
    try:
        clean = name.lstrip("%")
        return z3.BitVecVal(int(clean) & ((1 << BITWIDTH) - 1), BITWIDTH)
    except (ValueError, TypeError):
        pass
    return None


def _parse_llvm_ir_smt(llvm_ir: str) -> tuple[z3.BoolRef, list[z3.BitVecRef], z3.BitVecRef | None]:
    z3_vars: dict[str, z3.BitVecRef] = {}
    output_var: z3.BitVecRef | None = None
    constraints: list[z3.BoolRef] = []
    param_names: list[str] = []

    func_match = re.search(r'define\s+\S+\s+@(\w+)\s*\(([^)]*)\)', llvm_ir)
    if not func_match:
        raise ValueError("could not parse LLVM IR: no function definition")

    params_str = func_match.group(2)
    if params_str.strip():
        for p in params_str.split(","):
            p = p.strip()
            m = re.match(r'\S+\s+%([\w.-]+)', p)
            if m:
                name = m.group(1)
                var = z3.BitVec(name, BITWIDTH)
                z3_vars["%" + name] = var
                param_names.append(name)

    body_match = re.search(r'define\s+\S+\s+@\w+\s*\([^)]*\)\s*\{([^}]+)\}', llvm_ir, re.DOTALL)
    if not body_match:
        raise ValueError("could not parse LLVM IR: no function definition")

    body = body_match.group(1)
    lines = []
    for line in body.split("\n"):
        line = line.strip()
        if not line or line.endswith(":"):
            continue
        lines.append(line)

    alloca_set: set[str] = set()

    for line in lines:
        result_name = None
        eq_idx = line.find(" = ")
        if eq_idx >= 0:
            maybe_result = line[:eq_idx].strip()
            if maybe_result.startswith("%"):
                result_name = maybe_result
                line = line[eq_idx + 3:].strip()

        parts = line.split()
        if not parts:
            continue
        opcode = parts[0]

        if opcode == "ret":
            if len(parts) >= 3:
                val = _resolve_val(parts[2], z3_vars)
                if val is not None:
                    output_var = val

        elif opcode == "alloca" and result_name:
            alloca_set.add(result_name)

        elif opcode == "store" and len(parts) >= 5:
            val_name = _strip_comma(parts[2])
            ptr_name = parts[4]
            val = _resolve_val(val_name, z3_vars)
            if val is not None and ptr_name in alloca_set:
                z3_vars[ptr_name + "_store"] = val

        elif opcode == "load" and result_name and len(parts) >= 4:
            ptr_name = parts[3]
            store_key = ptr_name + "_store"
            if store_key in z3_vars:
                z3_vars[result_name] = z3_vars[store_key]
            elif ptr_name in alloca_set:
                z3_vars[result_name] = z3.BitVec(result_name.lstrip("%"), BITWIDTH)

        elif opcode in ("add", "sub", "mul", "udiv", "sdiv", "and", "or",
                        "xor", "shl", "lshr", "ashr", "srem", "urem"):
            if len(parts) >= 4:
                lhs = _resolve_val(parts[2], z3_vars)
                rhs = _resolve_val(parts[3], z3_vars)
                if lhs is not None and rhs is not None and result_name:
                    if opcode == "add":
                        val = lhs + rhs
                    elif opcode == "sub":
                        val = lhs - rhs
                    elif opcode == "mul":
                        val = lhs * rhs
                    elif opcode == "and":
                        val = lhs & rhs
                    elif opcode == "or":
                        val = lhs | rhs
                    elif opcode == "xor":
                        val = lhs ^ rhs
                    elif opcode == "shl":
                        val = lhs << rhs
                    elif opcode == "lshr":
                        val = z3.LShR(lhs, rhs)
                    elif opcode == "ashr":
                        val = lhs >> rhs
                    elif opcode == "udiv":
                        val = z3.BVUDiv(lhs, rhs)
                    elif opcode == "sdiv":
                        val = z3.BVSDiv(lhs, rhs)
                    elif opcode == "srem":
                        val = z3.SRem(lhs, rhs)
                    elif opcode == "urem":
                        val = z3.BVURem(lhs, rhs)
                    else:
                        val = lhs
                    z3_vars[result_name] = val

        elif opcode == "icmp" and len(parts) >= 5:
            predicate = parts[1]
            lhs = _resolve_val(parts[3], z3_vars)
            rhs = _resolve_val(parts[4], z3_vars)
            if lhs is not None and rhs is not None and result_name:
                if predicate == "eq":
                    cond = (lhs == rhs)
                elif predicate == "ne":
                    cond = (lhs != rhs)
                elif predicate in ("slt", "ult"):
                    cond = lhs < rhs
                elif predicate in ("sle", "ule"):
                    cond = lhs <= rhs
                elif predicate in ("sgt", "ugt"):
                    cond = lhs > rhs
                elif predicate in ("sge", "uge"):
                    cond = lhs >= rhs
                else:
                    cond = (lhs == rhs)
                z3_vars[result_name] = z3.If(cond, z3.BitVecVal(1, BITWIDTH), z3.BitVecVal(0, BITWIDTH))

        elif opcode == "select" and len(parts) >= 5:
            cond = _resolve_val(parts[1], z3_vars)
            tval = _resolve_val(parts[3], z3_vars)
            fval = _resolve_val(parts[4], z3_vars)
            if cond is not None and tval is not None and fval is not None and result_name:
                z3_vars[result_name] = z3.If(cond != 0, tval, fval)

        elif opcode == "zext" and len(parts) >= 3:
            val = _resolve_val(parts[2], z3_vars)
            if val is not None and result_name:
                z3_vars[result_name] = val

    input_vars = [v for k, v in z3_vars.items()
                  if k.startswith("%") and not re.match(r'^%\d+$', k)]
    if not input_vars:
        input_vars = [v for k, v in z3_vars.items() if k.startswith("%")]
    final_formula = z3.And(*constraints) if constraints else z3.BoolVal(True)

    return final_formula, input_vars, output_var


def check_ir_llvm(
    ir_module,
    llvm_ir: str,
    timeout_ms: int = 30000,
) -> StageResult:
    start = time.time()
    input_hash = hashlib.sha256(str(ir_module).encode()).hexdigest()
    output_hash = hashlib.sha256(llvm_ir.encode("utf-8")).hexdigest()

    try:
        ir_translator = IRToSMT()
        ir_formula = ir_translator.translate(ir_module)
        ir_output = ir_translator.get_output_var()
        ir_inputs = ir_translator.get_input_vars()

        llvm_formula, llvm_inputs, llvm_output = _parse_llvm_ir_smt(llvm_ir)

        all_inputs = list(set(ir_inputs) | set(llvm_inputs))

        checker = EquivalenceChecker(timeout_ms=timeout_ms)
        check_result = checker.check_with_formulas(
            ir_formula, llvm_formula,
            ir_output, llvm_output,
            all_inputs,
        )
        elapsed = (time.time() - start) * 1000

        return StageResult(
            stage_name="ir_llvm",
            passed=check_result.equivalent,
            input_hash=input_hash,
            output_hash=output_hash,
            counterexample=check_result.counterexample,
            duration_ms=elapsed,
        )
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return StageResult(
            stage_name="ir_llvm",
            passed=False,
            input_hash=input_hash,
            output_hash=output_hash,
            counterexample={"error": str(e)},
            duration_ms=elapsed,
        )
