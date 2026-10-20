"""
validation/equivalence.py

Purpose:
Core SMT equivalence checking engine. Takes two Z3 formulas (original,
obfuscated) and checks whether there exists any input where their outputs
differ. If UNSAT, the two programs are equivalent for all inputs.

Security Relevance:
This is the decision procedure at the heart of the entire proof system.
Every proof — fragment safety, mutation safety, VM correctness, watermark
survivability — ultimately depends on this checker. A bug here mis-certifies
everything.

Dependencies:
- z3 (SMT solver)
"""
from __future__ import annotations

import z3
from dataclasses import dataclass


@dataclass
class CheckResult:
    """
    CheckResult

    What this validates:
    Whether two Z3 expressions/formulas produce identical output for all
    inputs under the given constraints.

    Security impact:
    equivalent=True means the solver proved universal equivalence.
    equivalent=False means a counterexample was found or the solver could
    not decide. The caller MUST treat False as a failed proof, even if it
    is a false negative due to timeout.

    Failure mode:
    If the solver returns 'unknown' (timeout), equivalent=False is returned
    with no counterexample. This is the safe side but causes false alarms.
    """
    equivalent: bool
    counterexample: dict[str, int] | None = None
    model: z3.ModelRef | None = None
    solver_time_ms: float = 0.0


def _bv_to_int(val):
    if z3.is_bv(val):
        try:
            return val.as_long()
        except (AttributeError, TypeError):
            pass
        try:
            s = str(val)
            if s.startswith("0x"):
                return int(s, 16)
            return int(s)
        except (ValueError, TypeError):
            return 0
    try:
        return int(str(val))
    except (ValueError, TypeError):
        return 0


class EquivalenceChecker:
    """
    EquivalenceChecker

    What it validates:
    Two Z3 expressions are equivalent under all inputs, optionally with
    additional context formulas per expression.

    Security impact:
    The checker is the final arbiter of proof validity. Its correctness
    depends on Z3's correctness and the timeout being long enough.

    Failure mode:
    Timeout or solver error yields equivalent=False. The checker does NOT
    distinguish "proven non-equivalent" from "could not decide".
    """
    def __init__(self, timeout_ms: int = 30000):
        self.timeout_ms = timeout_ms

    def check(
        self,
        original_func: z3.ExprRef,
        obfuscated_func: z3.ExprRef,
        inputs: list[z3.BitVecRef],
        original_formula: z3.BoolRef | None = None,
        obfuscated_formula: z3.BoolRef | None = None,
    ) -> CheckResult:
        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)

        if original_formula is not None:
            solver.add(original_formula)
        if obfuscated_formula is not None:
            solver.add(obfuscated_formula)
        solver.add(original_func != obfuscated_func)

        start = __import__("time").time()
        result = solver.check()
        elapsed = (__import__("time").time() - start) * 1000

        if result == z3.unsat:
            return CheckResult(equivalent=True, solver_time_ms=elapsed)
        elif result == z3.sat:
            model = solver.model()
            counterexample = {}
            for inp in inputs:
                val = model.eval(inp, model_completion=True)
                counterexample[str(inp)] = _bv_to_int(val)
            return CheckResult(
                equivalent=False,
                counterexample=counterexample,
                model=model,
                solver_time_ms=elapsed,
            )
        else:
            return CheckResult(equivalent=False, solver_time_ms=elapsed)

    def check_with_formulas(
        self,
        original_formula: z3.BoolRef,
        obfuscated_formula: z3.BoolRef,
        orig_output: z3.BitVecRef | None,
        obf_output: z3.BitVecRef | None,
        inputs: list[z3.BitVecRef],
    ) -> CheckResult:
        if orig_output is None or obf_output is None:
            # No observable output (bare assignments, no return): joint-SAT
            # ("they CAN agree on some input") does NOT prove universal
            # equivalence — x=a+b vs x=a-b agree at b=0 but differ
            # elsewhere. The only sound positive verdict here is
            # syntactically identical canonical forms. Anything else is
            # equivalent=False, never True-from-mere-SAT.
            shared = [v for v in inputs]
            if not shared:
                solver = z3.Solver()
                solver.set("timeout", self.timeout_ms)
                solver.add(original_formula)
                solver.add(obfuscated_formula)
                start = __import__("time").time()
                result = solver.check()
                elapsed = (__import__("time").time() - start) * 1000
                if result == z3.unsat:
                    s1 = z3.Solver(); s1.set("timeout", self.timeout_ms)
                    s1.add(original_formula)
                    s2 = z3.Solver(); s2.set("timeout", self.timeout_ms)
                    s2.add(obfuscated_formula)
                    if s1.check() == z3.sat and s2.check() == z3.sat:
                        # Mutually exclusive but individually satisfiable:
                        # provably DIFFERENT programs.
                        return CheckResult(equivalent=False,
                                           solver_time_ms=elapsed)
                    return CheckResult(equivalent=False, solver_time_ms=elapsed)
                elif result == z3.sat:
                    # Can agree on some input — says NOTHING about all
                    # inputs. NOT equivalence.
                    return CheckResult(equivalent=False, solver_time_ms=elapsed)
                return CheckResult(equivalent=False, solver_time_ms=elapsed)
            solver = z3.Solver()
            solver.set("timeout", self.timeout_ms)
            solver.add(original_formula)
            solver.add(obfuscated_formula)
            if str(original_formula) == str(obfuscated_formula):
                return CheckResult(equivalent=True, solver_time_ms=0)
            # Different canonical forms + no observable output to compare:
            # cannot prove equivalence. Joint-SAT is agreement, not proof.
            return CheckResult(equivalent=False, solver_time_ms=0)

        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)

        solver.add(original_formula)
        solver.add(obfuscated_formula)
        solver.add(orig_output != obf_output)

        start = __import__("time").time()
        result = solver.check()
        elapsed = (__import__("time").time() - start) * 1000

        if result == z3.unsat:
            return CheckResult(equivalent=True, solver_time_ms=elapsed)
        elif result == z3.sat:
            model = solver.model()
            counterexample = {}
            for inp in inputs:
                val = model.eval(inp, model_completion=True)
                counterexample[str(inp)] = _bv_to_int(val)
            if orig_output is not None:
                val = model.eval(orig_output, model_completion=True)
                counterexample["original_output"] = _bv_to_int(val)
            if obf_output is not None:
                val = model.eval(obf_output, model_completion=True)
                counterexample["obfuscated_output"] = _bv_to_int(val)
            return CheckResult(
                equivalent=False,
                counterexample=counterexample,
                model=model,
                solver_time_ms=elapsed,
            )
        else:
            return CheckResult(equivalent=False, solver_time_ms=elapsed)
