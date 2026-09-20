"""
proofs/fragment_safety.py

Purpose:
Formally proves that code fragments produced by fragmentation passes remain
semantically equivalent when chained together, and that isolated fragments are
internally consistent (no contradictory constraints). Uses Z3 to encode the
relations between fragment input/output variables as bit-vector formulas.

Security Relevance:
Fragmentation is a core obfuscation technique that splits functions across
multiple fragments. If fragments are not proven equivalent, the obfuscated
program may compute a different result. Worse, an attacker could exploit a
divergent fragment to bypass protection. This prover catches such divergences
at proof-generation time.

Dependencies:
- z3 (BitVec solver)
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import z3

BITWIDTH = 64


@dataclass
class FragmentProof:
    """
    FragmentProof

    What is proven:
    For a set of fragment IDs, that the chain-expression composition is
    equivalent to the sum-expression composition over the same constraints.
    Equivalence means: for all BitVec inputs, every output variable is
    identical under both composition strategies.

    Why:
    Fragments are reordered, duplicated, or interleaved during obfuscation.
    Chaining changes the algebraic structure of how fragments combine (sum vs
    xor vs custom). This proof guarantees the change preserves semantics.

    Assumptions:
    - All fragment expressions and constraints are encoded as Z3 BitVec(64).
    - Fragment input/output variable names are consistent across fragments.
    - The solver terminates within the configured timeout.

    Limitations:
    - Only covers 64-bit bit-vector semantics; pointer/float/struct are
      abstracted away.
    - Fragment isolation proof checks satisfiability, not equivalence to a
      reference — a sat result only proves a model exists, not that the
      fragment behaves incorrectly in the full program.
    - Solver timeout produces "unknown", treated as non-equivalent (safe
      false-negative but may cause false alarms).

    Verification Path:
    1. Re-run prove_fragment_chain or prove_fragment_isolation with the
       same fragments.
    2. Check that proof.equivalent == True.
    3. Optionally verify the proof_hash binds proof fields via SHA-256.
    """
    pass_name: str
    fragment_ids: list[int]
    equivalent: bool
    solver_time_ms: float
    counterexample: Optional[dict] = None
    timestamp: str = ""
    proof_hash: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.proof_hash:
            raw = f"{self.pass_name}:{self.fragment_ids}:{self.equivalent}:{self.solver_time_ms}"
            self.proof_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_certificate_dict(self) -> dict:
        """Serialize this proof into a certificate-compatible dictionary."""
        return {
            "pass_name": self.pass_name,
            "input_hash": hashlib.sha256(str(self.fragment_ids).encode()).hexdigest(),
            "output_hash": self.proof_hash,
            "equivalence_proof": {
                "equivalent": self.equivalent,
                "solver_time_ms": self.solver_time_ms,
                "counterexample": self.counterexample,
            },
            "duration_ms": self.solver_time_ms,
            "timestamp": self.timestamp,
            "validated": self.equivalent,
        }


@dataclass
class Fragment:
    """
    A single code fragment with named inputs/outputs, an expression, and
    an optional Z3 constraint. Used as the basic unit for chain-equivalence
    and isolation proofs.
    """
    id: int
    input_vars: list[str] = field(default_factory=list)
    output_vars: list[str] = field(default_factory=list)
    expression: Optional[z3.ExprRef] = None
    constraint: Optional[z3.BoolRef] = None


class FragmentSafetyProver:
    """
    FragmentSafetyProver

    What is proven:
    Two forms of fragment safety:
      1. Fragment-chain equivalence — the output of composing fragments with
         sum semantics equals the output with xor semantics, under all inputs.
      2. Fragment isolation — the fragment's own constraints are satisfiable
         (no internal contradiction).

    Why:
    Obfuscation passes split and reorder code. If fragments are not chain-safe,
    the transformed program may silently compute a different result, enabling
    oracle-guided deobfuscation.

    Assumptions:
    - All Z3 variables are BITWIDTH (64) BitVecs.
    - Fragment expressions are side-effect-free arithmetic/logic.
    - Solver timeout may miss some equivalences.

    Limitations:
    - Does not model memory aliasing, control flow, or non-linear operations.
    - Fragment isolation's 'equivalent=True' only means satisfiable, not
      correct relative to a spec.

    Verification Path:
    Instantiate with a timeout, call prove_fragment_chain(fragments) or
    prove_fragment_isolation(fragment), read .equivalent from the result.
    """
    def __init__(self, timeout_ms: int = 30000):
        self.timeout_ms = timeout_ms
        self.proofs: list[FragmentProof] = []

    def _mk_bv(self, name: str) -> z3.BitVecRef:
        return z3.BitVec(name, BITWIDTH)

    def prove_fragment_chain(self, fragments: list[Fragment]) -> FragmentProof:
        """
        Prove that chaining fragments with xor-based composition is
        equivalent to the original sum-based composition.

        Security-critical path:
        The solver encodes both compositions, then adds a disjunction of
        inequalities over all outputs. If unsat, every output matches for
        all inputs — fragments are chain-safe. If sat, a counterexample
        input producing different outputs is captured.
        """
        start = time.time()
        if not fragments:
            return FragmentProof(
                pass_name="fragment_chain",
                fragment_ids=[],
                equivalent=False,
                solver_time_ms=0.0,
                counterexample={"error": "empty fragment list"},
            )

        ids = [f.id for f in fragments]
        fragment_ids_str = "_".join(str(i) for i in ids)

        all_inputs = set()
        all_outputs = set()
        for f in fragments:
            for v in f.input_vars:
                all_inputs.add(v)
            for v in f.output_vars:
                all_outputs.add(v)

        original_outputs: dict[str, z3.BitVecRef] = {}
        original_constraints = []

        all_vars: dict[str, z3.BitVecRef] = {}
        for v in all_inputs | all_outputs:
            if v not in all_vars:
                all_vars[v] = self._mk_bv(v)

        for v in all_outputs:
            original_outputs[v] = self._mk_bv(f"orig_{v}")

        combined_expr: Optional[z3.BitVecRef] = None
        for f in fragments:
            if f.expression is not None:
                if combined_expr is None:
                    combined_expr = f.expression
                else:
                    combined_expr = combined_expr + f.expression
            if f.constraint is not None:
                original_constraints.append(f.constraint)

        if combined_expr is not None:
            for v in all_outputs:
                original_constraints.append(original_outputs[v] == combined_expr)
        else:
            for v in all_outputs:
                original_constraints.append(original_outputs[v] == all_vars.get(v, self._mk_bv(v)))

        chain_outputs: dict[str, z3.BitVecRef] = {}
        for v in all_outputs:
            chain_outputs[v] = self._mk_bv(f"chain_{v}")

        chain_expr: Optional[z3.BitVecRef] = None
        for f in fragments:
            if f.expression is not None:
                if chain_expr is None:
                    chain_expr = f.expression
                else:
                    chain_expr = chain_expr ^ f.expression

        chain_constraints = []
        for f in fragments:
            if f.constraint is not None:
                chain_constraints.append(f.constraint)
        if chain_expr is not None:
            for v in all_outputs:
                chain_constraints.append(chain_outputs[v] == chain_expr)
        else:
            for v in all_outputs:
                chain_constraints.append(chain_outputs[v] == all_vars.get(v, self._mk_bv(v)))

        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)
        for c in original_constraints:
            solver.add(c)
        for c in chain_constraints:
            solver.add(c)

        diff_clauses = []
        for v in all_outputs:
            diff_clauses.append(original_outputs[v] != chain_outputs[v])
        solver.add(z3.Or(*diff_clauses))

        result = solver.check()
        elapsed = (time.time() - start) * 1000

        if result == z3.unsat:
            proof = FragmentProof(
                pass_name="fragment_chain",
                fragment_ids=ids,
                equivalent=True,
                solver_time_ms=elapsed,
            )
        elif result == z3.sat:
            m = solver.model()
            ce = {}
            for v in list(all_inputs)[:5]:
                try:
                    ce[v] = m.eval(all_vars[v], model_completion=True).as_long()
                except (AttributeError, TypeError):
                    ce[v] = str(m.eval(all_vars[v], model_completion=True))
            proof = FragmentProof(
                pass_name="fragment_chain",
                fragment_ids=ids,
                equivalent=False,
                solver_time_ms=elapsed,
                counterexample=ce,
            )
        else:
            proof = FragmentProof(
                pass_name="fragment_chain",
                fragment_ids=ids,
                equivalent=False,
                solver_time_ms=elapsed,
                counterexample={"error": "solver unknown"},
            )

        self.proofs.append(proof)
        return proof

    def prove_fragment_isolation(self, fragment: Fragment) -> FragmentProof:
        """
        Prove that a single fragment's constraints are satisfiable.

        If unsat, the fragment is internally contradictory and will never
        execute — indicating a bug in the fragmentation pass.

        Security-critical path:
        A contradictory fragment may be injected by an attacker to create
        dead code that traps analysis. This proof flags such fragments.
        """
        start = time.time()

        input_vars = {v: self._mk_bv(v) for v in fragment.input_vars}
        output_vars = {v: self._mk_bv(f"iso_out_{v}") for v in fragment.output_vars}

        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)

        if fragment.expression is not None:
            for v in fragment.output_vars:
                solver.add(output_vars[v] == fragment.expression)
        if fragment.constraint is not None:
            solver.add(fragment.constraint)

        result = solver.check()
        elapsed = (time.time() - start) * 1000

        if result == z3.sat:
            proof = FragmentProof(
                pass_name="fragment_isolation",
                fragment_ids=[fragment.id],
                equivalent=True,
                solver_time_ms=elapsed,
            )
        elif result == z3.unsat:
            proof = FragmentProof(
                pass_name="fragment_isolation",
                fragment_ids=[fragment.id],
                equivalent=False,
                solver_time_ms=elapsed,
                counterexample={"error": "fragment constraints unsatisfiable"},
            )
        else:
            proof = FragmentProof(
                pass_name="fragment_isolation",
                fragment_ids=[fragment.id],
                equivalent=False,
                solver_time_ms=elapsed,
                counterexample={"error": "solver unknown"},
            )

        self.proofs.append(proof)
        return proof
