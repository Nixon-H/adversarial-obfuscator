"""
validation/mba_validator.py

Purpose:
Validates that a Mixed Boolean-Arithmetic (MBA) expression replacement
preserves semantics. Wraps AST-to-Z3 translation and equivalence checking
into a simple boolean API.

Security Relevance:
MBA substitution is a core obfuscation primitive. If an MBA identity is
wrong, the code computes a different value. This validator catches
incorrect identities before they reach production.

Dependencies:
- scripts.validation.ast_to_smt   (AST -> Z3)
- scripts.validation.equivalence  (Z3 equivalence check)
"""
from __future__ import annotations

import ast
import time

from scripts.validation.ast_to_smt import ASTToSMT
from scripts.validation.equivalence import EquivalenceChecker


class MBAValidator:
    """
    MBAValidator

    What it validates:
    That an MBA replacement AST node computes the same function as the
    original AST node for all integer inputs.

    Security impact:
    Validates the core obfuscation primitive. An MBA identity that passes
    validation is provably equivalent; one that fails must be rejected.

    Failure mode:
    - Returns False for any non-equivalent replacement (correct rejection).
    - Also returns False on solver error/timeout (safe false negative).
    """
    def __init__(self, timeout_ms: int = 30000):
        self.stats = {
            "attempted": 0,
            "passed": 0,
            "failed": 0,
            "total_time_ms": 0.0,
        }
        self.checker = EquivalenceChecker(timeout_ms=timeout_ms)

    def validate(
        self,
        original: ast.AST,
        replacement: ast.AST,
    ) -> bool:
        self.stats["attempted"] += 1
        start = time.time()

        try:
            orig_translator = ASTToSMT()
            orig_formula = orig_translator.translate(original)
            orig_output = orig_translator.get_output_var()

            repl_translator = ASTToSMT()
            repl_formula = repl_translator.translate(replacement)
            repl_output = repl_translator.get_output_var()

            all_inputs = list(
                set(orig_translator.get_input_vars())
                | set(repl_translator.get_input_vars())
            )

            check_result = self.checker.check_with_formulas(
                orig_formula, repl_formula,
                orig_output, repl_output,
                all_inputs,
            )

            elapsed = (time.time() - start) * 1000
            self.stats["total_time_ms"] += elapsed

            if check_result.equivalent:
                self.stats["passed"] += 1
                return True
            else:
                self.stats["failed"] += 1
                return False

        except Exception as _e:
            import traceback
            elapsed = (time.time() - start) * 1000
            self.stats["total_time_ms"] += elapsed
            self.stats["failed"] += 1
            print(f"[MBAValidator] Validation error: {_e}")
            traceback.print_exc()
            return False

    def validate_expressions(
        self,
        original_expr: ast.AST,
        replacement_expr: ast.AST,
    ) -> bool:
        orig_ret = ast.Return(value=original_expr)
        repl_ret = ast.Return(value=replacement_expr)
        var_names = sorted(set(
            node.id for node in ast.walk(original_expr)
            if isinstance(node, ast.Name)
        ))
        if not var_names:
            var_names = ["a", "b"]
        orig_args = [ast.arg(arg=v) for v in var_names]
        repl_args = [ast.arg(arg=v) for v in var_names]
        orig_func = ast.FunctionDef(
            name="f", args=ast.arguments(
                posonlyargs=[], args=orig_args,
                kwonlyargs=[], kw_defaults=[], defaults=[],
            ),
            body=[orig_ret], decorator_list=[], returns=None,
        )
        repl_func = ast.FunctionDef(
            name="f", args=ast.arguments(
                posonlyargs=[], args=repl_args,
                kwonlyargs=[], kw_defaults=[], defaults=[],
            ),
            body=[repl_ret], decorator_list=[], returns=None,
        )
        return self.validate(orig_func, repl_func)

    def log_stats(self):
        avg_time = (
            self.stats["total_time_ms"] / self.stats["attempted"]
            if self.stats["attempted"] > 0 else 0.0
        )
        print("MBA Validation Stats:")
        print(f"  Attempted: {self.stats['attempted']}")
        print(f"  Passed:    {self.stats['passed']}")
        print(f"  Failed:    {self.stats['failed']}")
        print(f"  Avg time:  {avg_time:.2f} ms")
