from __future__ import annotations

import ast
import hashlib
import time
from typing import Optional

from scripts.validation.ast_to_smt import ASTToSMT, ast_to_smt_formula
from scripts.validation.equivalence import EquivalenceChecker
from scripts.preservation.report import StageResult


def check_ast_ir(
    ast_tree: ast.AST,
    ir_module,
    timeout_ms: int = 30000,
) -> StageResult:
    from scripts.validation.ir_to_smt import IRToSMT, ir_to_smt_formula

    start = time.time()
    input_hash = hashlib.sha256(ast.dump(ast_tree).encode()).hexdigest()
    output_hash = hashlib.sha256(str(ir_module).encode()).hexdigest()

    try:
        orig_translator = ASTToSMT()
        orig_formula = orig_translator.translate(ast_tree)
        orig_output = orig_translator.get_output_var()

        ir_translator = IRToSMT()
        ir_formula = ir_translator.translate(ir_module)
        ir_output = ir_translator.get_output_var()

        all_inputs = list(
            set(orig_translator.get_input_vars())
            | set(ir_translator.get_input_vars())
        )

        checker = EquivalenceChecker(timeout_ms=timeout_ms)
        check_result = checker.check_with_formulas(
            orig_formula, ir_formula,
            orig_output, ir_output,
            all_inputs,
        )
        elapsed = (time.time() - start) * 1000

        return StageResult(
            stage_name="ast_ir",
            passed=check_result.equivalent,
            input_hash=input_hash,
            output_hash=output_hash,
            counterexample=check_result.counterexample,
            duration_ms=elapsed,
        )
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return StageResult(
            stage_name="ast_ir",
            passed=False,
            input_hash=input_hash,
            output_hash=output_hash,
            counterexample={"error": str(e)},
            duration_ms=elapsed,
        )
