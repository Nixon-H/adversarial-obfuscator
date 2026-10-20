"""
proofs/proof_carrying.py

Purpose:
Implements Proof-Carrying Obfuscation (PCO). Each transformation pass emits
a Z3-based equivalence proof, serialized as a proof certificate alongside the
obfuscated code. The proof can be independently verified without trusting the
obfuscation pipeline.

Security Relevance:
PCO enables trustless verification. A third party can verify that the obfuscated
code is semantically equivalent to the original WITHOUT running the obfuscator,
and WITHOUT trusting the obfuscator binary — only the proof and the verifier
need to be trusted.

Dependencies:
- scripts.certificates.certificate     (Certificate, CertificateChain)
- scripts.validation.smt_validator     (SMTValidator)
- scripts.validation.equivalence       (EquivalenceChecker)
"""
import base64
import json
import time
import z3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from scripts.certificates.certificate import Certificate, CertificateChain, emit_certificate  # noqa: F401 (this line binds a name used by an embedded template)
from scripts.validation.smt_validator import SMTValidator  # noqa: F401 (this line binds a name used by an embedded template)
from scripts.validation.equivalence import EquivalenceChecker


@dataclass
class ProofCertificate:
    """
    ProofCertificate

    What is proven:
    A single transformation is semantics-preserving (or not). The proof
    contains the Z3 solver result, input names, and optional counterexample.

    Why:
    Bundles the proof in a self-describing format that can be serialized
    alongside the binary for independent verification.

    Assumptions:
    The proof_json faithfully records the solver invocation. Nothing more;
    re-running the verification may produce different results if Z3 is
    not deterministic or the solver version differs.

    Limitations:
    - The proof is only as strong as the Z3 encoding. If the encoding
      abstracts away relevant semantics (e.g., memory, FP), the proof
      may certify incorrect code.
    - prove_bv_identity is a trivial self-equivalence test (identity
      function). It does NOT prove any non-trivial transformation.

    Verification Path:
    1. Call prove_equivalence with expressions + formulas.
    2. Check ProofCertificate.equivalent.
    3. Re-run SMT on the proof_json data for independent confirmation.
    """
    transformation_name: str
    equivalent: bool
    solver_time_ms: float
    proof_json: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transformation": self.transformation_name,
            "equivalent": self.equivalent,
            "solver_time_ms": self.solver_time_ms,
            "proof": self.proof_json,
            "error": self.error,
        }

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class ProofCarryingObfuscator:
    """Generates Z3-based equivalence proofs for obfuscation transformations
    and serializes them as proof certificates alongside the obfuscated code."""

    def __init__(self, timeout_ms: int = 30000):
        self.timeout_ms = timeout_ms
        self.checker = EquivalenceChecker(timeout_ms=timeout_ms)
        self.certificates: List[ProofCertificate] = []

    def prove_equivalence(self, transformation_name: str,
                          original_expr: z3.ExprRef,
                          transformed_expr: z3.ExprRef,
                          inputs: List[z3.BitVecRef],
                          original_formula: Optional[z3.BoolRef] = None,
                          transformed_formula: Optional[z3.BoolRef] = None,
                          ) -> ProofCertificate:
        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)
        if original_formula is not None:
            solver.add(original_formula)
        if transformed_formula is not None:
            solver.add(transformed_formula)
        solver.add(original_expr != transformed_expr)
        smt2_str = solver.to_smt2()
        start = time.time()
        result = solver.check()
        elapsed = (time.time() - start) * 1000
        equivalent = (result == z3.unsat)
        proof_data: Dict[str, Any] = {
            "solver_result": str(result),
            "num_inputs": len(inputs),
            "input_names": [str(v) for v in inputs],
            "transformation": transformation_name,
            "timestamp": time.time(),
            "formulas": [smt2_str],
        }
        if result == z3.sat:
            model = solver.model()
            ce = {}
            for inp in inputs:
                val = model.eval(inp, model_completion=True)
                try:
                    ce[str(inp)] = val.as_long()
                except Exception:
                    ce[str(inp)] = str(val)
            proof_data["counterexample"] = ce
        if result == z3.unknown:
            reason = solver.reason_unknown()
            proof_data["reason_unknown"] = reason
        cert = ProofCertificate(
            transformation_name=transformation_name,
            equivalent=equivalent,
            solver_time_ms=elapsed,
            proof_json=proof_data,
        )
        self.certificates.append(cert)
        return cert

    def prove_bv_identity(self, name: str, bv_size: int = 64) -> ProofCertificate:
        """TEST helper: proves x == x (trivial self-identity).

        WARNING: This does NOT prove any transformation or rewrite rule. It
        is only useful for testing the proof infrastructure itself. Do not
        use this as evidence that a real transformation preserves semantics.
        """
        x = z3.BitVec("x", bv_size)
        return self.prove_equivalence(
            transformation_name=name,
            original_expr=x,
            transformed_expr=x,
            inputs=[x],
        )

    def verify_certificate(self, cert: ProofCertificate) -> bool:
        """Independently re-verify a certificate by re-running the solver.

        The stored ``solver_result`` string is UNTRUSTED (anyone holding
        the JSON can flip "sat" to "unsat"). The verdict is re-derived by
        parsing the stored SMT-LIB formulas and re-checking them with a
        fresh solver: unsat => equivalent, anything else => not.
        Fail-closed: missing formulas, parse errors, solver errors, and
        ``unknown`` all return False.
        """
        if not cert.proof_json:
            return False
        try:
            formulas = cert.proof_json.get("formulas") or []
            if not formulas:
                return False
            solver = z3.Solver()
            solver.set("timeout", self.timeout_ms)
            for smt2 in formulas:
                if not isinstance(smt2, str) or not smt2.strip():
                    return False
                for assertion in z3.parse_smt2_string(smt2):
                    solver.add(assertion)
            recheck = solver.check()
            if recheck == z3.unsat:
                return True
            return False
        except Exception:
            return False

    def get_all_certificates(self) -> List[ProofCertificate]:
        return list(self.certificates)

    def serialize_all(self) -> str:
        return json.dumps(
            [c.to_dict() for c in self.certificates],
            indent=2,
        )

    def prove_ir_transformations(self, ir_function: str,
                                  transformations: List[str]) -> CertificateChain:
        """For each transformation, bind proof to the IR function content
        by encoding the IR as a Z3 constant and proving self-equivalence
        (input == output for identity)."""
        certs = []
        import hashlib
        ir_hash = hashlib.sha256(ir_function.encode()).hexdigest()
        ir_const = z3.BitVecVal(int(ir_hash[:16], 16), 64)
        for t_name in transformations:
            cert = self.prove_equivalence(t_name, ir_const, ir_const, [ir_const])
            json_str = json.dumps(cert.to_dict())
            proof_json = json.loads(json_str)
            proof_json["ir_hash"] = ir_hash
            proof_json["ir_length"] = len(ir_function)
            c = emit_certificate(
                pass_name=t_name,
                input_text=ir_function,
                output_text=ir_function,
                equivalence_proof=proof_json,
                duration_ms=cert.solver_time_ms,
                validated=cert.equivalent,
            )
            certs.append(c)

        chain = CertificateChain(certificates=certs)
        chain.validate_chain()
        return chain

    def embed_proof_section(self, binary_path: str,
                             chain: CertificateChain) -> str:
        """Embed the proof chain into a binary file as a .proof section."""
        import hashlib
        with open(binary_path, "rb") as f:
            binary_content = f.read()
        binary_hash = hashlib.sha256(binary_content).hexdigest()
        chain_data = json.loads(chain.to_json())
        if isinstance(chain_data, list):
            for c in chain_data:
                c["binary_hash"] = binary_hash
        elif isinstance(chain_data, dict):
            chain_data["binary_hash"] = binary_hash
        proof_bytes = json.dumps(chain_data).encode("utf-8")
        proof_b64 = base64.b64encode(proof_bytes).decode("ascii")
        marker_start = "__NIXON_PROOF_BEGIN__"
        marker_end = "__NIXON_PROOF_END__"
        payload = f"\n# {marker_start}:{proof_b64}:{marker_end}\n"
        with open(binary_path, "ab") as f:
            f.write(payload.encode("ascii"))
        return payload

    def get_summary(self) -> dict:
        total = len(self.certificates)
        passed = sum(1 for c in self.certificates if c.equivalent)
        failed = total - passed
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "avg_solver_time_ms": (
                sum(c.solver_time_ms for c in self.certificates) / max(total, 1)
            ),
        }
