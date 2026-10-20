"""
proofs/jit_reassembly.py

Purpose:
Proves that JIT-reassembled code fragments are semantically equivalent to the
original IR from which they were derived. Uses Z3 SMT to compare IR blocks
before and after reassembly.

Security Relevance:
JIT compilation is a common attack surface — if the reassembled code diverges
from the original IR, an attacker can supply crafted inputs that exploit the
divergence to break out of the obfuscation sandbox. This prover detects such
divergence.

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

from scripts.z3_optional import z3

BITWIDTH = 64


@dataclass
class JITProof:
    """
    JITProof

    What is proven:
    For a given fragment IR and its JIT-compiled IR, that every variable
    definition produces identical values under all inputs.

    Why:
    The JIT compiler may reorder, inline, or specialize instructions. An
    incorrect reassembly silently produces wrong results.

    Assumptions:
    - Both IR snippets use the same 64-bit BitVec semantics.
    - All variables are SSA-like (each defined once).
    - Solver timeout may prevent full verification.

    Limitations:
    - Only verifies straight-line IR blocks; loops, calls, and memory are
      approximated.
    - Proof is at the IR level, not at the native code level — a correct IR
      translation does not guarantee correct code generation.

    Verification Path:
    1. Call prove_fragment(fragment_ir, jit_code).
    2. Assert proof.equivalent == True.
    3. Optionally cross-check by calling prove_reassembly with fragments
       and the original IR.
    """
    pass_name: str
    fragment_ir_hash: str
    jit_code_hash: str
    equivalent: bool
    solver_time_ms: float
    counterexample: Optional[dict] = None
    timestamp: str = ""
    proof_hash: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.proof_hash:
            raw = f"{self.pass_name}:{self.fragment_ir_hash}:{self.jit_code_hash}:{self.equivalent}:{self.solver_time_ms}"
            self.proof_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_certificate_dict(self) -> dict:
        return {
            "pass_name": self.pass_name,
            "input_hash": self.fragment_ir_hash,
            "output_hash": self.jit_code_hash,
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
    """
    Parse a single IR RHS expression string into a Z3 BitVec expression.

    Security note: The tokenizer handles only a fixed set of operators.
    An unrecognized operator raises ValueError, which the callers catch
    and treat as non-equivalent (safe default).
    """
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
    """Rename all %-variables to canonical %v0, %v1, ... form for comparison."""

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
    """Collect all %-variable names that appear on the LHS of an '='."""
    defs: set[str] = set()
    for line in ir_code.split("\n"):
        line = line.strip()
        if "=" in line and "%" in line and not line.startswith("func @"):
            lhs = line.split("=", 1)[0].strip()
            if lhs.startswith("%"):
                defs.add(lhs)
    return defs


def _rename_defs(ir_code: str, suffix: str = "_o") -> str:
    """Append a suffix to every defined variable for disambiguation."""
    defs = _collect_defs(ir_code)
    for v in sorted(defs, key=lambda x: (-len(x), x)):
        ir_code = ir_code.replace(v, v + suffix)
    return ir_code


def _ir_block_to_z3(ir_block: str) -> tuple[z3.BoolRef, list[z3.BitVecRef], Optional[z3.BitVecRef]]:
    """Translate an IR block string into a Z3 formula, input vars, and output var."""

    z3_vars: dict[str, z3.BitVecRef] = {}
    output_var: Optional[z3.BitVecRef] = None
    constraints = []

    lines = [l.strip() for l in ir_block.split("\n") if l.strip()]
    for line in lines:
        if line.startswith("%") and "=" in line:
            parts = line.split("=", 1)
            lhs = parts[0].strip()
            rhs = parts[1].strip()

            if lhs.startswith("%"):
                if lhs not in z3_vars:
                    z3_vars[lhs] = z3.BitVec(lhs, BITWIDTH)

                rhs_expr = _parse_rhs(rhs, z3_vars)
                constraints.append(z3_vars[lhs] == rhs_expr)
        elif "ret" in line and "%" in line:
            ret_parts = line.replace("ret", "").strip()
            if ret_parts.startswith("%"):
                var_name = ret_parts
                if var_name in z3_vars:
                    output_var = z3_vars[var_name]

    formula = z3.And(*constraints) if constraints else z3.BoolVal(True)
    input_vars = [v for v in z3_vars.values() if v is not output_var]
    return formula, input_vars, output_var


class JITReassemblyProver:
    """
    JITReassemblyProver

    What is proven:
    For a fragment IR and its JIT output, every variable produces the same
    value for all inputs. Also proves that reassembling a set of fragments
    yields IR equivalent to the original.

    Why:
    JIT compilation is an integrity-critical pipeline stage. A divergence
    here breaks all downstream proofs.

    Assumptions:
    - IR is in SSA-like form with straight-line blocks.
    - Comparison is at IR level; native codegen is not verified.

    Limitations:
    - No loop/phi modeling across back-edges.
    - prove_reassembly approximates state via variable renaming; may miss
      structural reorderings that preserve semantics.

    Verification Path:
    prove_fragment(ir, jit) -> JITProof.equivalent
    """
    def __init__(self, timeout_ms: int = 30000):
        self.timeout_ms = timeout_ms
        self.proofs: list[JITProof] = []

    def prove_fragment(self, fragment_ir: str, jit_code: str) -> JITProof:
        """
        Prove the JIT output is equivalent to the fragment IR.

        Security-critical path:
        Both IR snippets are canonicalized, renamed with distinct suffixes,
        translated to Z3, then checked for inequality. UNSAT proves equality.
        """

        start = time.time()
        ir_hash = hashlib.sha256(fragment_ir.encode()).hexdigest()[:16]
        jit_hash = hashlib.sha256(jit_code.encode()).hexdigest()[:16]

        try:
            ir_canon = _canonicalize_ir(fragment_ir)
            jit_canon = _canonicalize_ir(jit_code)

            ir_renamed = _rename_defs(ir_canon, "_ir")
            jit_renamed = _rename_defs(jit_canon, "_jit")

            ir_formula, ir_inputs, ir_output = _ir_block_to_z3(ir_renamed)
            jit_formula, jit_inputs, jit_output = _ir_block_to_z3(jit_renamed)
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            proof = JITProof(
                pass_name="jit_fragment",
                fragment_ir_hash=ir_hash,
                jit_code_hash=jit_hash,
                equivalent=False,
                solver_time_ms=elapsed,
                counterexample={"error": str(e)},
            )
            self.proofs.append(proof)
            return proof

        ir_defs = _collect_defs(ir_canon)
        jit_defs = _collect_defs(jit_canon)
        all_defs = ir_defs | jit_defs

        all_inputs = list(set(ir_inputs + jit_inputs))

        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)
        solver.add(ir_formula)
        solver.add(jit_formula)

        if not all_defs:
            elapsed = (time.time() - start) * 1000
            solver_result = solver.check()
            if solver_result == z3.unsat:
                equiv = False
                ce = {"error": "Formulas unsatisfiable (contradictory)"}
            elif solver_result == z3.sat:
                equiv = True
                ce = None
            else:
                equiv = False
                ce = {"error": f"Solver returned {solver_result}"}
            proof = JITProof(
                pass_name="jit_fragment",
                fragment_ir_hash=ir_hash,
                jit_code_hash=jit_hash,
                equivalent=equiv,
                solver_time_ms=elapsed,
                counterexample=ce,
            )
            self.proofs.append(proof)
            return proof

        var_diffs = []
        for v in all_defs:
            var_diffs.append(
                z3.BitVec(v + "_ir", BITWIDTH) != z3.BitVec(v + "_jit", BITWIDTH)
            )

        solver.add(z3.Or(*var_diffs))

        result = solver.check()
        elapsed = (time.time() - start) * 1000

        if result == z3.unsat:
            proof = JITProof(
                pass_name="jit_fragment",
                fragment_ir_hash=ir_hash,
                jit_code_hash=jit_hash,
                equivalent=True,
                solver_time_ms=elapsed,
            )
        elif result == z3.sat:
            m = solver.model()
            ce = {}
            for inp in all_inputs[:5]:
                try:
                    ce[str(inp)] = m.eval(inp, model_completion=True).as_long()
                except (AttributeError, TypeError):
                    ce[str(inp)] = str(m.eval(inp, model_completion=True))
            for v in sorted(all_defs):
                try:
                    ir_val = m.eval(z3.BitVec(v + "_ir", BITWIDTH), model_completion=True)
                    jit_val = m.eval(z3.BitVec(v + "_jit", BITWIDTH), model_completion=True)
                    ce[f"ir_{v}"] = ir_val.as_long()
                    ce[f"jit_{v}"] = jit_val.as_long()
                except (AttributeError, TypeError):
                    pass
            proof = JITProof(
                pass_name="jit_fragment",
                fragment_ir_hash=ir_hash,
                jit_code_hash=jit_hash,
                equivalent=False,
                solver_time_ms=elapsed,
                counterexample=ce,
            )
        else:
            proof = JITProof(
                pass_name="jit_fragment",
                fragment_ir_hash=ir_hash,
                jit_code_hash=jit_hash,
                equivalent=False,
                solver_time_ms=elapsed,
                counterexample={"error": "solver unknown"},
            )

        self.proofs.append(proof)
        return proof

    @staticmethod
    def _build_joint_formula(frag_ir: str, orig_ir: str):
        """Build a single Z3 formula encoding both computations with shared input variables.
        Variables in the original IR get a '_o' suffix for disambiguation.
        NOTE: JIT code verification is IR-level (not native code), which is the correct
        approach since the JIT is generated from IR."""
        joint_vars: dict[str, z3.BitVecRef] = {}
        frag_constraints = []
        orig_constraints = []

        def get_var(name: str) -> z3.BitVecRef:
            if name not in joint_vars:
                joint_vars[name] = z3.BitVec(name, BITWIDTH)
            return joint_vars[name]

        def parse_block(ir_block: str, constraints: list, suffix: str = ""):
            lines = [l.strip() for l in ir_block.split("\n") if l.strip()]
            for line in lines:
                if line.startswith("%") and "=" in line:
                    parts = line.split("=", 1)
                    lhs = parts[0].strip()
                    rhs = parts[1].strip()
                    if lhs.startswith("%"):
                        lhs_renamed = lhs + suffix
                        rhs_renamed = rhs.replace("%", "%" + suffix[1:] if suffix else "%")
                        full_rhs = rhs_renamed
                        lhs_var = get_var(lhs_renamed)
                        rhs_expr = _parse_rhs(full_rhs, joint_vars)
                        constraints.append(lhs_var == rhs_expr)
                elif "ret" in line and "%" in line:
                    pass

        frag_lines = [l.strip() for l in frag_ir.split("\n") if l.strip() and "ret" not in l]
        orig_lines = [l.strip() for l in orig_ir.split("\n") if l.strip() and "ret" not in l]

        orig_defs: set[str] = set()
        for line in orig_lines:
            if line.startswith("%") and "=" in line:
                lhs = line.split("=", 1)[0].strip()
                if lhs.startswith("%"):
                    orig_defs.add(lhs)

        for line in frag_lines:
            if line.startswith("%") and "=" in line:
                parts = line.split("=", 1)
                lhs = parts[0].strip()
                rhs = parts[1].strip()
                lhs_var = get_var(lhs)
                rhs_expr = _parse_rhs(rhs, joint_vars)
                frag_constraints.append(lhs_var == rhs_expr)

        for line in orig_lines:
            if line.startswith("%") and "=" in line:
                parts = line.split("=", 1)
                lhs = parts[0].strip()
                rhs = parts[1].strip()
                lhs_renamed = lhs + "_o"
                rhs_renamed = rhs
                for def_var in sorted(orig_defs, key=len, reverse=True):
                    if def_var in rhs_renamed:
                        rhs_renamed = rhs_renamed.replace(def_var, def_var + "_o")
                lhs_var = get_var(lhs_renamed)
                rhs_expr = _parse_rhs(rhs_renamed, joint_vars)
                orig_constraints.append(lhs_var == rhs_expr)

        return frag_constraints, orig_constraints, joint_vars

    def prove_reassembly(self, fragments: list[str], original_ir: str) -> JITProof:
        """
        Prove that reassembling a list of fragment IRs yields output
        equivalent to the original IR.

        Security-critical path:
        Fragments may be reordered, duplicated, or dropped during
        reassembly. This proof catches omissions or insertions.
        """

        start = time.time()

        combined_frag_hash = hashlib.sha256("|".join(fragments).encode()).hexdigest()[:16]
        orig_hash = hashlib.sha256(original_ir.encode()).hexdigest()[:16]

        try:
            frag_combined = "\n".join(fragments)
            frag_canon = _canonicalize_ir(frag_combined)
            orig_canon = _canonicalize_ir(original_ir)

            frag_constraints, orig_constraints, joint_vars = self._build_joint_formula(
                frag_canon, orig_canon
            )

            frag_formula = z3.And(*frag_constraints) if frag_constraints else z3.BoolVal(True)
            orig_formula = z3.And(*orig_constraints) if orig_constraints else z3.BoolVal(True)

            frag_defs = _collect_defs(frag_canon)
            orig_defs = _collect_defs(orig_canon)
            all_defs = frag_defs | orig_defs

            solver = z3.Solver()
            solver.set("timeout", self.timeout_ms)
            solver.add(frag_formula)
            solver.add(orig_formula)

            if not all_defs:
                elapsed = (time.time() - start) * 1000
                # Fail-closed: no variable definitions means there is
                # nothing to compare — a vacuous True would certify empty
                # IR as "equivalent". Report non-equivalence with the
                # reason instead.
                proof = JITProof(
                    pass_name="jit_reassembly",
                    fragment_ir_hash=combined_frag_hash,
                    jit_code_hash=orig_hash,
                    equivalent=False,
                    solver_time_ms=elapsed,
                    counterexample={"error": "no variable definitions to compare (empty IR?)"},
                )
                self.proofs.append(proof)
                return proof

            # Compare frag output vs orig output (with _o suffix)
            var_diffs = []
            for v in all_defs:
                frag_var_name = v
                orig_var_name = v + "_o"
                if frag_var_name in joint_vars and orig_var_name in joint_vars:
                    var_diffs.append(joint_vars[frag_var_name] != joint_vars[orig_var_name])

            if not var_diffs:
                elapsed = (time.time() - start) * 1000
                # Fail-closed: no comparable output pairs (e.g. disjoint
                # variable namespaces) — certifying True would bless an
                # unchecked reassembly. Report non-equivalence instead.
                proof = JITProof(
                    pass_name="jit_reassembly",
                    fragment_ir_hash=combined_frag_hash,
                    jit_code_hash=orig_hash,
                    equivalent=False,
                    solver_time_ms=elapsed,
                    counterexample={"error": "no comparable variable pairs between fragments and original"},
                )
                self.proofs.append(proof)
                return proof

            solver.add(z3.Or(*var_diffs))

            result = solver.check()
            elapsed = (time.time() - start) * 1000


            if result == z3.unsat:
                proof = JITProof(
                    pass_name="jit_reassembly",
                    fragment_ir_hash=combined_frag_hash,
                    jit_code_hash=orig_hash,
                    equivalent=True,
                    solver_time_ms=elapsed,
                )
            elif result == z3.sat:
                m = solver.model()
                ce = {}
                for v_name in list(joint_vars.keys())[:10]:
                    try:
                        val = m.eval(joint_vars[v_name], model_completion=True)
                        ce[v_name] = val.as_long() if hasattr(val, 'as_long') else str(val)
                    except (AttributeError, TypeError):
                        pass
                proof = JITProof(
                    pass_name="jit_reassembly",
                    fragment_ir_hash=combined_frag_hash,
                    jit_code_hash=orig_hash,
                    equivalent=False,
                    solver_time_ms=elapsed,
                    counterexample=ce,
                )
            else:
                proof = JITProof(
                    pass_name="jit_reassembly",
                    fragment_ir_hash=combined_frag_hash,
                    jit_code_hash=orig_hash,
                    equivalent=False,
                    solver_time_ms=elapsed,
                    counterexample={"error": "solver unknown"},
                )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            proof = JITProof(
                pass_name="jit_reassembly",
                fragment_ir_hash=combined_frag_hash,
                jit_code_hash=orig_hash,
                equivalent=False,
                solver_time_ms=elapsed,
                counterexample={"error": str(e)},
            )

        self.proofs.append(proof)
        return proof
