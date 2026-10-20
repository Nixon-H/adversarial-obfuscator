"""
validation/smt_validator.py

Purpose:
Cross-validates AST-level (source) semantics against IR-level (compiled)
semantics. Translates both to Z3 and checks equivalence. This is the
primary validation gate for the compilation pipeline: if the AST and IR
disagree, the compiler is wrong.

Security Relevance:
This validator connects source-level proofs to IR-level proofs. If the
AST-to-IR translation is incorrect, all downstream IR proofs are working
on the wrong semantics. This validator detects such translation bugs.

Dependencies:
- scripts.validation.ast_to_smt   (AST -> Z3)
- scripts.validation.ir_to_smt    (IR -> Z3)
- scripts.validation.equivalence  (Z3 equivalence check)
"""
from __future__ import annotations

import ast
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from scripts.validation.ast_to_smt import ASTToSMT
from scripts.validation.ir_to_smt import IRToSMT
from scripts.validation.equivalence import EquivalenceChecker, CheckResult

if TYPE_CHECKING:  # pragma: no cover - typing only
    from irgen.compile import IrModule


@dataclass
class ValidationResult:
    """
    ValidationResult

    What this validates:
    Whether an AST function and its compiled IR form produce identical
    outputs for all inputs.

    Security impact:
    If equivalent=False, the compilation pipeline introduced a semantic
    change. This must be treated as a pipeline bug and investigated.

    Failure mode:
    equivalent=False with an error string indicates a translation failure
    (parse error, unsupported construct, solver exception).
    """
    function_name: str
    equivalent: bool
    check_result: CheckResult | None = None
    error: str | None = None
    duration_ms: float = 0.0


class SMTValidator:
    def __init__(self, timeout_ms: int = 30000):
        self.timeout_ms = timeout_ms
        self.checker = EquivalenceChecker(timeout_ms=timeout_ms)

    def validate(
        self,
        original_ast: ast.AST,
        obfuscated_ir: "IrModule",
        function_name: str | None = None,
    ) -> ValidationResult:
        start = time.time()

        try:
            orig_translator = ASTToSMT()
            orig_formula = orig_translator.translate(original_ast)
            orig_output = orig_translator.get_output_var()

            ir_translator = IRToSMT()
            obf_formula = ir_translator.translate(obfuscated_ir)
            obf_output = ir_translator.get_output_var()

            all_inputs = list(
                set(orig_translator.get_input_vars()) |
                set(ir_translator.get_input_vars())
            )

            check_result = self.checker.check_with_formulas(
                orig_formula, obf_formula,
                orig_output, obf_output,
                all_inputs,
            )

            duration_ms = (time.time() - start) * 1000

            return ValidationResult(
                function_name=function_name or "<module>",
                equivalent=check_result.equivalent,
                check_result=check_result,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            logging.warning(f"SMT validation failed for {function_name or '<module>'}: {e}")
            return ValidationResult(
                function_name=function_name or "<module>",
                equivalent=False,
                error=str(e),
                duration_ms=duration_ms,
            )

    def validate_source_vs_ir(
        self,
        source_code: str,
        ir_module: "IrModule",
        function_name: str | None = None,
    ) -> ValidationResult:
        tree = ast.parse(source_code)
        return self.validate(tree, ir_module, function_name)
