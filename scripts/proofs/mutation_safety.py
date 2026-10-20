"""
proofs/mutation_safety.py

Purpose:
Proves that an IR mutation (applied by an obfuscation pass) produces
semantically equivalent code. Mutation sequences are chained so that a
pipeline of many small mutations can be proven as a whole.

Security Relevance:
If a mutation changes program semantics even slightly, an attacker can
leverage the difference for oracle-guided deobfuscation. This prover
catches semantic drift.

Dependencies:
- z3 (BitVec solver)
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import z3

BITWIDTH = 64


@dataclass
class MutationProof:
    """
    MutationProof

    What is proven:
    For a pair of IR strings (original, mutated), that every variable
    definition produces identical values over all 64-bit inputs.

    Why:
    Obfuscation mutations must preserve semantics. Without proof, the
    transformation pipeline is operating on trust.

    Assumptions:
    - IR is a sequence of SSA-like %-variable assignments.
    - All values are BitVec(64); floating point and memory are abstracted.

    Limitations:
    - Only verifies straight-line IR; loops require fixed-point reasoning.
    - Mutation sequences are verified step-by-step; the chain proof
      aggregates per-step results and fails fast on the first divergence.

    Verification Path:
    prove_mutation(original, mutated) -> proof.equivalent
    prove_mutation_sequence(original, [m1, m2, ...]) -> proof.equivalent
    """
    pass_name: str
    original_hash: str
    mutated_hash: str
    equivalent: bool
    solver_time_ms: float
    counterexample: Optional[dict] = None
    timestamp: str = ""
    proof_hash: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.proof_hash:
            raw = f"{self.pass_name}:{self.original_hash}:{self.mutated_hash}:{self.equivalent}:{self.solver_time_ms}"
            self.proof_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_certificate_dict(self) -> dict:
        return {
            "pass_name": self.pass_name,
            "input_hash": self.original_hash,
            "output_hash": self.mutated_hash,
            "equivalence_proof": {
                "equivalent": self.equivalent,
                "solver_time_ms": self.solver_time_ms,
                "counterexample": self.counterexample,
            },
            "duration_ms": self.solver_time_ms,
            "timestamp": self.timestamp,
            "validated": self.equivalent,
        }


_RHS_TOKEN_RE = re.compile(
    r'%[a-zA-Z_]\w*'
    r'|0x[0-9a-fA-F]+'
    r'|-?\d+'
    r'|<<|>>|//'
    r'|[+\-*/%^&|~()]'
)


def _parse_rhs(rhs: str, z3_vars: dict) -> z3.BitVecRef:
    tokens = _RHS_TOKEN_RE.findall(rhs)
    if not tokens:
        raise ValueError(f"empty RHS expression: {rhs!r}")

    def _val(tok: str) -> z3.BitVecRef:
        if tok.startswith("%"):
            if tok not in z3_vars:
                z3_vars[tok] = z3.BitVec(tok, BITWIDTH)
            return z3_vars[tok]
        base = 16 if tok.startswith("0x") else 10
        return z3.BitVecVal(int(tok, base), BITWIDTH)

    idx = 0
    negated = False
    if tokens[idx] == "~":
        negated = True
        idx += 1
    if idx >= len(tokens):
        raise ValueError(f"incomplete expression after unary operator in: {rhs!r}")

    expr = _val(tokens[idx])
    if negated:
        expr = ~expr
    idx += 1

    while idx < len(tokens):
        op = tokens[idx]
        idx += 1
        if idx >= len(tokens):
            raise ValueError(f"trailing operator {op!r} in: {rhs!r}")
        rhs_val = _val(tokens[idx])
        idx += 1

        if op == "+":
            expr = expr + rhs_val
        elif op == "-":
            expr = expr - rhs_val
        elif op == "*":
            expr = expr * rhs_val
        elif op == "//":
            expr = z3.UDiv(expr, rhs_val)
        elif op == "%":
            expr = z3.URem(expr, rhs_val)
        elif op == "^":
            expr = expr ^ rhs_val
        elif op == "&":
            expr = expr & rhs_val
        elif op == "|":
            expr = expr | rhs_val
        elif op == "<<":
            expr = expr << rhs_val
        elif op == ">>":
            expr = z3.LShR(expr, rhs_val)
        else:
            raise ValueError(f"unknown operator {op!r} in: {rhs!r}")

    return expr


def _canonicalize_ir(ir_code: str) -> str:
    mapping: dict[str, int] = {}
    counter = [0]

    def _repl(m: re.Match) -> str:
        v = m.group(0)
        if v not in mapping:
            mapping[v] = counter[0]
            counter[0] += 1
        return f"%v{mapping[v]}"

    return re.sub(r'%[a-zA-Z_]\w*', _repl, ir_code)


def _collect_defs(ir_code: str) -> set[str]:
    defs: set[str] = set()
    for line in ir_code.split("\n"):
        line = line.strip()
        if "=" in line and "%" in line and not line.startswith("func @"):
            lhs = line.split("=", 1)[0].strip()
            if lhs.startswith("%"):
                defs.add(lhs)
    return defs


def _rename_defs(ir_code: str, suffix: str = "_o") -> str:
    defs = _collect_defs(ir_code)
    for v in sorted(defs, key=lambda x: (-len(x), x)):
        ir_code = ir_code.replace(v, v + suffix)
    return ir_code


def _formula_from_ir(ir_code: str) -> tuple[z3.BoolRef, list[z3.BitVecRef], Optional[z3.BitVecRef]]:
    lines = [l.strip() for l in ir_code.split("\n") if l.strip() and not l.strip().startswith(";")]
    z3_vars: dict[str, z3.BitVecRef] = {}
    output_var: Optional[z3.BitVecRef] = None
    constraints = []

    for line in lines:
        if line.startswith("func @"):
            continue
        if "=" in line and "->" not in line:
            parts = line.split("=", 1)
            lhs = parts[0].strip()
            rhs = parts[1].strip()

            if lhs.startswith("%"):
                var_name = lhs
                if var_name not in z3_vars:
                    z3_vars[var_name] = z3.BitVec(var_name, BITWIDTH)

                rhs_expr = _parse_rhs(rhs, z3_vars)
                constraints.append(z3_vars[var_name] == rhs_expr)
        elif "ret" in line and "%" in line:
            ret_parts = line.replace("ret", "").strip()
            if ret_parts.startswith("%"):
                var_name = ret_parts
                if var_name in z3_vars:
                    output_var = z3_vars[var_name]

    formula = z3.And(*constraints) if constraints else z3.BoolVal(True)
    input_vars = [v for v in z3_vars.values()]
    return formula, input_vars, output_var


class MutationSafetyProver:
    """
    MutationSafetyProver

    What is proven:
    For any IR mutation, all outputs match for all inputs (BitVec 64).

    Why:
    Each mutation pass transforms IR in-place. Without this prover, a
    buggy pass introduces silent semantic drift.

    Assumptions:
    - IR variables are uniquely named within a block.
    - Mutations are applied in sequence; ordering matters.

    Limitations:
    - No support for indirect branches, calls, or exception handling.
    - Solver timeout may miss divergences.

    Verification Path:
    prove_mutation -> MutationProof.equivalent
    prove_mutation_sequence -> MutationProof.equivalent (chain)
    """
    def __init__(self, timeout_ms: int = 30000):
        self.timeout_ms = timeout_ms
        self.proofs: list[MutationProof] = []
        self.stats = {"total": 0, "equivalent": 0, "nonequivalent": 0, "total_time_ms": 0.0}

    def prove_mutation(self, original: str, mutated: str) -> MutationProof:
        """
        Prove that a single mutation preserves semantics.

        Security-critical path:
        Canonicalize and rename both IRs with disambiguating suffixes,
        translate to Z3, then search for a model where any output differs.
        UNSAT = equivalent for all inputs.
        """

        start = time.time()
        orig_hash = hashlib.sha256(original.encode()).hexdigest()[:16]
        mut_hash = hashlib.sha256(mutated.encode()).hexdigest()[:16]

        try:
            orig_canon = _canonicalize_ir(original)
            mut_canon = _canonicalize_ir(mutated)

            orig_renamed = _rename_defs(orig_canon, "_o")
            mut_renamed = _rename_defs(mut_canon, "_m")

            orig_formula, orig_inputs, orig_output = _formula_from_ir(orig_renamed)
            mut_formula, mut_inputs, mut_output = _formula_from_ir(mut_renamed)
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            self.stats["total"] += 1
            self.stats["total_time_ms"] += elapsed
            proof = MutationProof(
                pass_name="mutation_safety",
                original_hash=orig_hash,
                mutated_hash=mut_hash,
                equivalent=False,
                solver_time_ms=elapsed,
                counterexample={"error": str(e)},
            )
            self.proofs.append(proof)
            return proof

        orig_defs = _collect_defs(orig_canon)
        mut_defs = _collect_defs(mut_canon)
        all_defs = orig_defs | mut_defs

        all_inputs = list(set(orig_inputs + mut_inputs))

        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)
        solver.add(orig_formula)
        solver.add(mut_formula)

        if not all_defs:
            elapsed = (time.time() - start) * 1000
            fwd = z3.Solver()
            fwd.set("timeout", self.timeout_ms)
            fwd.add(orig_formula)
            fwd.add(mut_formula)
            result_fwd = fwd.check()
            elapsed2 = (time.time() - start) * 1000
            if result_fwd == z3.unsat:
                self.stats["total"] += 1
                self.stats["total_time_ms"] += elapsed2
                proof = MutationProof(
                    pass_name="mutation_safety",
                    original_hash=orig_hash,
                    mutated_hash=mut_hash,
                    equivalent=False,
                    solver_time_ms=elapsed2,
                    counterexample={"error": "formulas together unsatisfiable"},
                )
                self.proofs.append(proof)
                return proof
            self.stats["total"] += 1
            self.stats["total_time_ms"] += elapsed2
            proof = MutationProof(
                pass_name="mutation_safety",
                original_hash=orig_hash,
                mutated_hash=mut_hash,
                equivalent=True,
                solver_time_ms=elapsed2,
            )
            self.proofs.append(proof)
            return proof

        var_diffs = []
        for v in all_defs:
            var_diffs.append(
                z3.BitVec(v + "_o", BITWIDTH) != z3.BitVec(v + "_m", BITWIDTH)
            )

        solver.add(z3.Or(*var_diffs))

        result = solver.check()
        elapsed = (time.time() - start) * 1000

        self.stats["total"] += 1
        self.stats["total_time_ms"] += elapsed

        if result == z3.unsat:
            self.stats["equivalent"] += 1
            proof = MutationProof(
                pass_name="mutation_safety",
                original_hash=orig_hash,
                mutated_hash=mut_hash,
                equivalent=True,
                solver_time_ms=elapsed,
            )
        elif result == z3.sat:
            self.stats["nonequivalent"] += 1
            m = solver.model()
            ce = {}
            for inp in all_inputs[:5]:
                try:
                    ce[str(inp)] = m.eval(inp, model_completion=True).as_long()
                except (AttributeError, TypeError):
                    ce[str(inp)] = str(m.eval(inp, model_completion=True))
            for v in sorted(all_defs):
                try:
                    orig_val = m.eval(z3.BitVec(v + "_o", BITWIDTH), model_completion=True)
                    mut_val = m.eval(z3.BitVec(v + "_m", BITWIDTH), model_completion=True)
                    ce[f"orig_{v}"] = orig_val.as_long()
                    ce[f"mut_{v}"] = mut_val.as_long()
                except (AttributeError, TypeError):
                    pass
            proof = MutationProof(
                pass_name="mutation_safety",
                original_hash=orig_hash,
                mutated_hash=mut_hash,
                equivalent=False,
                solver_time_ms=elapsed,
                counterexample=ce,
            )
        else:
            self.stats["nonequivalent"] += 1
            proof = MutationProof(
                pass_name="mutation_safety",
                original_hash=orig_hash,
                mutated_hash=mut_hash,
                equivalent=False,
                solver_time_ms=elapsed,
                counterexample={"error": "solver unknown"},
            )

        self.proofs.append(proof)
        return proof

    def prove_mutation_sequence(self, original: str, mutations: list[str]) -> MutationProof:
        """
        Prove that a pipeline of mutations preserves semantics end-to-end.

        Fails fast: stops at the first non-equivalent mutation and returns
        a failing proof with the counterexample from that step.
        """

        if not mutations:
            # Vacuous truth: zero mutations = zero semantic change.
            # equivalent=True with identical hashes (fail-open would hide
            # nothing here — there is literally nothing to verify).
            orig_hash = hashlib.sha256(original.encode()).hexdigest()[:16]
            return MutationProof(
                pass_name="mutation_sequence",
                original_hash=orig_hash,
                mutated_hash=orig_hash,
                equivalent=True,
                solver_time_ms=0.0,
                counterexample=None,
            )

        current = original
        for mutation in mutations:
            proof = self.prove_mutation(current, mutation)
            if not proof.equivalent:
                mut_hash = hashlib.sha256(mutation.encode()).hexdigest()[:16]
                return MutationProof(
                    pass_name="mutation_sequence",
                    original_hash=hashlib.sha256(original.encode()).hexdigest()[:16],
                    mutated_hash=mut_hash,
                    equivalent=False,
                    solver_time_ms=proof.solver_time_ms,
                    counterexample=proof.counterexample,
                )
            current = mutation

        orig_hash = hashlib.sha256(original.encode()).hexdigest()[:16]
        final_hash = hashlib.sha256(mutations[-1].encode()).hexdigest()[:16]
        total_time = sum(p.solver_time_ms for p in self.proofs[-len(mutations):])
        return MutationProof(
            pass_name="mutation_sequence",
            original_hash=orig_hash,
            mutated_hash=final_hash,
            equivalent=True,
            solver_time_ms=total_time,
        )

    def get_stats(self) -> dict:
        return dict(self.stats)
