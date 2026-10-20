"""
verifier/standalone_verifier.py

Purpose:
The main verification engine. Extracts a proof section from a binary,
deserializes the certificate chain, validates hash-chain integrity, and
optionally re-runs SMT validation on each proof.

Security Relevance:
This is the trust anchor for the entire proof-carrying obfuscation system.
The verifier must be simple, auditable, and dependency-minimal to minimize
the chance of bugs that would accept invalid proofs.

Dependencies:
- scripts.certificates.certificate (Certificate, CertificateChain)
- scripts.verifier.binary_reader   (BinaryReader)
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List

from scripts.certificates.certificate import Certificate, CertificateChain
from scripts.verifier.binary_reader import BinaryReader


@dataclass
class VerificationResult:
    passed: bool
    certificates: List[Certificate]
    chain_valid: bool
    errors: List[str]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "num_certificates": len(self.certificates),
            "chain_valid": self.chain_valid,
            "errors": self.errors,
        }


class StandaloneVerifier:
    def __init__(self, re_verify_proofs: bool = False):
        self.reader = BinaryReader()
        self.re_verify_proofs = re_verify_proofs

    def verify(self, binary_path: str) -> VerificationResult:
        errors = []
        try:
            proof_data = self.reader.extract_proof_section(binary_path)
        except ValueError as e:
            return VerificationResult(
                passed=False, certificates=[],
                chain_valid=False, errors=[str(e)],
            )
        try:
            chain_data = json.loads(proof_data.decode("utf-8"))
            if isinstance(chain_data, dict):
                chain = CertificateChain.from_json(json.dumps(chain_data))
            else:
                chain = CertificateChain.from_json(proof_data.decode("utf-8"))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            return VerificationResult(
                passed=False, certificates=[],
                chain_valid=False, errors=[f"Proof deserialization failed: {e}"],
            )
        if not chain.certificates:
            return VerificationResult(
                passed=False, certificates=[],
                chain_valid=False, errors=["Empty certificate chain"],
            )
        chain_valid = chain.validate_chain()
        if not chain_valid:
            errors.append("Hash chain integrity check failed")
        if self.re_verify_proofs:
            for cert in chain.certificates:
                proof = cert.equivalence_proof
                solver_result = proof.get("solver_result", "") if proof else ""
                if not proof:
                    errors.append(
                        f"Certificate for {cert.pass_name} has no proof data"
                    )
                    continue
                formulas = proof.get("formulas")
                if formulas:
                    try:
                        import z3
                        solver = z3.Solver()
                        solver.set("timeout", 30000)
                        for f_str in formulas:
                            parsed = z3.parse_smt2_string(f_str)
                            solver.add(*parsed)
                        result = solver.check()
                        proven = (result == z3.unsat)
                        if not proven:
                            errors.append(
                                f"Certificate for {cert.pass_name} failed SMT re-verification (result: {result})"
                            )
                    except Exception as e:
                        errors.append(
                            f"Certificate for {cert.pass_name} SMT re-verification error: {e}"
                        )
                else:
                    proven = (solver_result == "unsat")
                    if not proven:
                        errors.append(
                            f"Certificate for {cert.pass_name} failed stored proof check"
                        )
        passed = chain_valid and len(errors) == 0
        return VerificationResult(
            passed=passed,
            certificates=chain.certificates,
            chain_valid=chain_valid,
            errors=errors,
        )

    def verify_chain(self, certificates: List[Certificate]) -> bool:
        chain = CertificateChain(certificates=certificates)
        return chain.validate_chain()
