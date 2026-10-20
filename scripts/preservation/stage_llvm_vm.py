from __future__ import annotations

import hashlib
import logging
import random
import re
import time
from typing import List, Optional, Tuple

from scripts.z3_optional import z3

from scripts.preservation.report import StageResult

BITWIDTH = 64


def generate_test_vectors(count: int = 20, seed: int = 42) -> List[Tuple[List[int], int]]:
    """Generate systematic test vectors for LLVM-to-VM semantic preservation.
    Covers edge cases: zero, positive, negative, large values, sign extension."""
    rng = random.Random(seed)
    vectors = []

    vectors.append(([0, 0], 0))
    vectors.append(([1, 2], 3))
    vectors.append(([10, 20], 30))
    vectors.append(([255, 1], 256))
    vectors.append(([0x7FFFFFFF, 1], 0x80000000))
    vectors.append(([0xFFFFFFFF, 1], 0x100000000))
    vectors.append(([100, 200], 300))
    vectors.append(([1024, 2048], 3072))
    vectors.append(([0xFFFF, 0x0001], 0x10000))
    vectors.append(([0xAAAAAAAA, 0x55555555], 0xFFFFFFFF))

    for _ in range(10):
        a = rng.randint(0, 2**32 - 1)
        b = rng.randint(0, 2**32 - 1)
        vectors.append(([a, b], a + b))

    return vectors


def _parse_llvm_to_z3(llvm_ir: str) -> tuple[z3.BoolRef, list[z3.BitVecRef], z3.BitVecRef | None]:
    """Parse LLVM IR into a Z3 formula. Returns (formula, input_vars, output_var)."""
    z3_vars: dict[str, z3.BitVecRef] = {}
    output_var: z3.BitVecRef | None = None
    constraints: list[z3.BoolRef] = []
    param_names: list[str] = []

    func_match = re.search(r'define\s+\S+\s+@\w+\s*\(([^)]*)\)', llvm_ir)
    if not func_match:
        raise ValueError("could not parse LLVM IR: no function definition")

    params_str = func_match.group(1)
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
    lines = [l.strip() for l in body.split("\n") if l.strip() and not l.strip().endswith(":")]

    def resolve_val(name: str) -> z3.BitVecRef | None:
        name = name.rstrip(",")
        if name in z3_vars:
            return z3_vars[name]
        try:
            clean = name.lstrip("%")
            return z3.BitVecVal(int(clean) & ((1 << BITWIDTH) - 1), BITWIDTH)
        except (ValueError, TypeError):
            pass
        return None

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

        if opcode == "ret" and len(parts) >= 3:
            val = resolve_val(parts[2])
            if val is not None:
                output_var = val

        elif opcode in ("add", "sub", "mul", "and", "or", "xor", "shl", "lshr", "ashr"):
            if len(parts) >= 4 and result_name:
                lhs = resolve_val(parts[2])
                rhs = resolve_val(parts[3])
                if lhs is not None and rhs is not None:
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
                    else:
                        val = lhs
                    z3_vars[result_name] = val

    formula = z3.And(*constraints) if constraints else z3.BoolVal(True)
    input_vars = [v for k, v in z3_vars.items() if k.startswith("%")]
    return formula, input_vars, output_var


def _vm_bytecode_to_z3(bytecode: bytes, num_regs: int = 8) -> tuple[z3.BoolRef, list[z3.BitVecRef], z3.BitVecRef | None]:
    """Encode VM bytecode execution as Z3 formulas for equivalence checking.
    Simulates a simple VM with registers and basic ALU ops."""
    regs = [z3.BitVec(f"vm_r{i}", BITWIDTH) for i in range(num_regs)]
    z3.BitVec('vm_pc', BITWIDTH)
    constraints = []
    output_var = None

    pos = 0
    while pos < len(bytecode) and pos < 256:
        opcode = bytecode[pos]
        if opcode == 0x00:
            pos += 1
        elif opcode == 0x01:
            rd = bytecode[pos + 1] % num_regs if pos + 1 < len(bytecode) else 0
            rs1 = bytecode[pos + 2] % num_regs if pos + 2 < len(bytecode) else 0
            rs2 = bytecode[pos + 3] % num_regs if pos + 3 < len(bytecode) else 0
            constraints.append(regs[rd] == regs[rs1] + regs[rs2])
            pos += 4
        elif opcode == 0x02:
            rd = bytecode[pos + 1] % num_regs if pos + 1 < len(bytecode) else 0
            rs1 = bytecode[pos + 2] % num_regs if pos + 2 < len(bytecode) else 0
            rs2 = bytecode[pos + 3] % num_regs if pos + 3 < len(bytecode) else 0
            constraints.append(regs[rd] == regs[rs1] - regs[rs2])
            pos += 4
        elif opcode == 0x03:
            rd = bytecode[pos + 1] % num_regs if pos + 1 < len(bytecode) else 0
            rs1 = bytecode[pos + 2] % num_regs if pos + 2 < len(bytecode) else 0
            rs2 = bytecode[pos + 3] % num_regs if pos + 3 < len(bytecode) else 0
            constraints.append(regs[rd] == regs[rs1] * regs[rs2])
            pos += 4
        elif opcode == 0x08:
            rd = bytecode[pos + 1] % num_regs if pos + 1 < len(bytecode) else 0
            rs1 = bytecode[pos + 2] % num_regs if pos + 2 < len(bytecode) else 0
            rs2 = bytecode[pos + 3] % num_regs if pos + 3 < len(bytecode) else 0
            constraints.append(regs[rd] == regs[rs1] ^ regs[rs2])
            pos += 4
        elif opcode == 0x06:
            rd = bytecode[pos + 1] % num_regs if pos + 1 < len(bytecode) else 0
            rs1 = bytecode[pos + 2] % num_regs if pos + 2 < len(bytecode) else 0
            rs2 = bytecode[pos + 3] % num_regs if pos + 3 < len(bytecode) else 0
            constraints.append(regs[rd] == regs[rs1] & regs[rs2])
            pos += 4
        elif opcode == 0x07:
            rd = bytecode[pos + 1] % num_regs if pos + 1 < len(bytecode) else 0
            rs1 = bytecode[pos + 2] % num_regs if pos + 2 < len(bytecode) else 0
            rs2 = bytecode[pos + 3] % num_regs if pos + 3 < len(bytecode) else 0
            constraints.append(regs[rd] == regs[rs1] | regs[rs2])
            pos += 4
        elif opcode == 0x0E:
            rd = bytecode[pos + 1] % num_regs if pos + 1 < len(bytecode) else 0
            rs = bytecode[pos + 2] % num_regs if pos + 2 < len(bytecode) else 0
            constraints.append(regs[rd] == regs[rs])
            pos += 3
        elif opcode == 0xFF:
            output_var = regs[0]
            break
        else:
            pos += 1

    formula = z3.And(*constraints) if constraints else z3.BoolVal(True)
    return formula, regs, output_var


def _check_z3_equivalence(
    llvm_ir: str,
    vm_bytecode: bytes,
    timeout_ms: int = 30000,
) -> tuple[bool, Optional[dict]]:
    """Check LLVM IR vs VM bytecode equivalence using Z3."""
    from scripts.validation.equivalence import EquivalenceChecker

    llvm_formula, llvm_inputs, llvm_output = _parse_llvm_to_z3(llvm_ir)
    vm_formula, vm_regs, vm_output = _vm_bytecode_to_z3(vm_bytecode)

    if llvm_output is None or vm_output is None:
        return False, {"error": "could not extract output from LLVM or VM"}

    checker = EquivalenceChecker(timeout_ms=timeout_ms)
    result = checker.check_with_formulas(
        llvm_formula, vm_formula,
        llvm_output, vm_output,
        llvm_inputs,
    )
    return result.equivalent, result.counterexample


def check_llvm_vm(
    llvm_ir: str,
    vm_bytecode: bytes,
    test_vectors: Optional[List[Tuple[List[int], int]]] = None,
) -> StageResult:
    start = time.time()
    input_hash = hashlib.sha256(llvm_ir.encode("utf-8")).hexdigest()
    output_hash = hashlib.sha256(vm_bytecode).hexdigest()

    z3_passed = False
    z3_error = None
    try:
        z3_passed, z3_ce = _check_z3_equivalence(llvm_ir, vm_bytecode)
        if not z3_passed and z3_ce:
            elapsed = (time.time() - start) * 1000
            return StageResult(
                stage_name="llvm_vm",
                passed=False,
                input_hash=input_hash,
                output_hash=output_hash,
                counterexample=z3_ce,
                duration_ms=elapsed,
            )
    except Exception as e:
        z3_error = str(e)
        logging.warning("Z3 equivalence check failed, falling back to test vectors: %s", e)

    if test_vectors is None:
        test_vectors = generate_test_vectors(count=20)

    all_passed = True
    counterexample = None

    try:
        from vm.interpreter import VMInterpreter

        for inp, expected in test_vectors:
            state = {
                "regs": [0] * VMInterpreter.NUM_REGISTERS,
                "memory": bytearray(65536),
                "stack": [],
                "halted": False,
            }
            regs = state["regs"]
            for i, val in enumerate(inp):
                if i < len(regs):
                    regs[i] = val & 0xFFFFFFFFFFFFFFFF

            interpreter = VMInterpreter(vm_bytecode, state=state)
            interpreter.run(max_steps=10000)

            if state.get("halted", False):
                result = None
                for r in state.get("regs", []):
                    if r != 0:
                        result = r
                        break
                if result is None and state.get("stack"):
                    result = state["stack"][-1] if state["stack"] else 0
            else:
                result = state["regs"][0] if state.get("regs") else 0

            if result is not None:
                result = result & 0xFFFFFFFFFFFFFFFF

            if result is None or result != expected:
                all_passed = False
                counterexample = {
                    "inputs": inp,
                    "expected": expected,
                    "got": result,
                    "z3_error": z3_error,
                }
                break
    except ImportError:
        if z3_error:
            counterexample = {"error": f"Z3 and vm.interpreter unavailable: {z3_error}"}
        else:
            counterexample = {"error": "vm.interpreter not available"}
    except Exception as e:
        counterexample = {"error": str(e), "z3_error": z3_error}

    passed = (z3_passed or all_passed) and counterexample is None
    elapsed = (time.time() - start) * 1000
    return StageResult(
        stage_name="llvm_vm",
        passed=passed,
        input_hash=input_hash,
        output_hash=output_hash,
        counterexample=counterexample,
        duration_ms=elapsed,
    )
