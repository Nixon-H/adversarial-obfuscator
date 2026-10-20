from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Callable, Dict, List

from scripts.validation.equivalence import EquivalenceChecker
from scripts.preservation.report import StageResult, PreservationReport


class PreservationEngine:
    def __init__(self):
        self.stages: List[str] = []
        self.results: Dict[str, StageResult] = {}
        self.checker = EquivalenceChecker(timeout_ms=30000)

    def _hash(self, data: Any) -> str:
        raw = str(data)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def check_stage(
        self,
        stage_name: str,
        stage_input: Any,
        stage_output: Any,
        translator_input_to_smt: Callable,
        translator_output_to_smt: Callable,
    ) -> StageResult:
        start = time.time()
        input_hash = self._hash(stage_input)
        output_hash = self._hash(stage_output)

        try:
            orig_formula, orig_state = translator_input_to_smt(stage_input)
            obf_formula, obf_state = translator_output_to_smt(stage_output)

            orig_output = orig_state.get_output_var()
            obf_output = obf_state.get_output_var()
            all_inputs = list(
                set(orig_state.get_input_vars())
                | set(obf_state.get_input_vars())
            )

            check_result = self.checker.check_with_formulas(
                orig_formula, obf_formula,
                orig_output, obf_output,
                all_inputs,
            )
            elapsed = (time.time() - start) * 1000
            result = StageResult(
                stage_name=stage_name,
                passed=check_result.equivalent,
                input_hash=input_hash,
                output_hash=output_hash,
                counterexample=check_result.counterexample,
                duration_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            result = StageResult(
                stage_name=stage_name,
                passed=False,
                input_hash=input_hash,
                output_hash=output_hash,
                counterexample={"error": str(e)},
                duration_ms=elapsed,
            )

        self.stages.append(stage_name)
        self.results[stage_name] = result
        return result

    def run_all(self, pipeline_context: dict) -> PreservationReport:
        stages_run = []
        total_time = 0.0
        stage_fns = pipeline_context.get("stage_fns", [])
        if not stage_fns:
            stage_fns = [
                self._check_llvm_vm_stage,
                self._check_ir_transform_stage,
            ]
        for stage_fn in stage_fns:
            result = stage_fn(pipeline_context)
            stages_run.append(result)
            total_time += result.duration_ms
        all_passed = all(s.passed for s in stages_run)
        return PreservationReport(
            stages=stages_run,
            all_passed=all_passed,
            total_duration_ms=total_time,
        )

    def _check_llvm_vm_stage(self, ctx: dict) -> StageResult:
        from scripts.preservation.stage_llvm_vm import check_llvm_vm
        llvm_ir = ctx.get("llvm_ir", "")
        vm_bytecode = ctx.get("vm_bytecode", b"")
        if not vm_bytecode:
            return StageResult(
                stage_name="llvm_vm", passed=False,
                input_hash=self._hash(llvm_ir), output_hash=self._hash(b""),
                counterexample={"error": "no vm bytecode provided"},
            )
        # Z3 SMT solver is tried first via _check_z3_equivalence inside check_llvm_vm.
        # Test vectors are used as fallback only if Z3 fails or is unavailable.
        logging.info("check_llvm_vm: Z3 SMT equivalence check with test vector fallback")
        return check_llvm_vm(llvm_ir, vm_bytecode)

    def _check_ir_transform_stage(self, ctx: dict) -> StageResult:
        from scripts.validation.smt_validator import SMTValidator
        import ast
        orig_source = ctx.get("original_source", "")
        obf_source = ctx.get("obfuscated_source", "")
        if not orig_source or not obf_source:
            return StageResult(
                stage_name="ir_transform", passed=False,
                input_hash=self._hash(orig_source), output_hash=self._hash(obf_source),
                counterexample={"error": "missing source"},
            )
        try:
            from irgen.compile import compile_py_to_ir
            tree = ast.parse(orig_source)
            ir_module = compile_py_to_ir(obf_source)
            validator = SMTValidator(timeout_ms=30000)
            result = validator.validate(tree, ir_module, "ir_transform")
            return StageResult(
                stage_name="ir_transform",
                passed=result.equivalent,
                input_hash=self._hash(orig_source),
                output_hash=self._hash(obf_source),
                counterexample={"error": result.error} if result.error else None,
            )
        except Exception as e:
            return StageResult(
                stage_name="ir_transform", passed=False,
                input_hash=self._hash(orig_source), output_hash=self._hash(obf_source),
                counterexample={"error": str(e)},
            )
