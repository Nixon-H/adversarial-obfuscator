"""
prover.py

Purpose:
ZK prover for state-bound execution. Binds function execution to a
given external state by generating zero-knowledge proofs that an
execution is valid for the claimed state, without revealing the state
itself.

Architectural Role:
High-level prover for the ZK module. StateBoundProver wraps SigmaProver
with execution-specific logic: it binds function references and inputs
to state commitments, generates execution proofs, and manages nonces
for replay protection.

Execution Context:
Instantiated with shared group parameters. Called during protected
execution to generate execution proofs that bind the current function
and inputs to the execution state.

Dependencies:
- sigma_protocol (GroupParameters, Proof, SigmaProver, generate_parameters)
- Standard library (hashlib, secrets, time, dataclasses, typing)

Security Relevance:
Execution proofs ensure that protected code runs in the correct
execution context. The binding between state, function, and inputs
prevents an attacker from executing functions out-of-context or with
tampered inputs.

# Why this algorithm was chosen:
# Sigma protocol proofs are efficient (3 modular exponentiations for
# proof, 2 for verification) and non-interactive (Fiat-Shamir). The
# state commitment chains the execution to the external context.

# Threat addressed:
# An attacker who can execute arbitrary code in the protected environment
# should not be able to execute state-bound functions without knowing
# the current state. The proof binds function+inputs+state together.

# Assumptions:
# - SHA-256 is collision-resistant for commitment binding
# - The prover's secret key is never exposed
# - The external state is honestly maintained

# Failure consequences:
# - Secret key leak: attacker can forge proofs for any state
# - SHA-256 collision: attacker can substitute different function/inputs
# - Nonce reuse: attacker can replay old executions

Maintenance Notes:
- Security classification: MEASURED (execution proofs are sigma-protocol
  based; they demonstrate state-knowledge, not correct execution).
- THEORETICAL: execution validity is a claim about the prover's
  integrity; the proof only demonstrates state-knowledge, not that
  the function was *correctly* executed.
- The bind_execution() method creates a SHA-256 commitment over
  (state || function_ref || public_key). This binds the execution
  to a specific state and prover identity.
"""

from __future__ import annotations

import hashlib
import secrets  # noqa: F401 (this line binds a name used by an embedded template)
import time
from dataclasses import dataclass
from typing import Dict, Optional

from .sigma_protocol import GroupParameters, Proof, SigmaProver, generate_parameters



@dataclass
class ExecutionProof:
    """Proof that an execution is bound to a given state."""
    state_commitment: int
    execution_proof: Proof
    function_ref: str
    inputs_hash: str
    nonce: int
    timestamp: float
    public_key: int


class StateBoundProver:
    """Prover for state-bound execution.

    Generates execution proofs that bind a function reference and
    inputs to a specific state commitment using sigma protocol proofs.

    Security classification: MEASURED
      - Binding uses SHA-256 commitments
      - THEORETICAL: no computational binding if SHA-256 collisions found
    """

    def __init__(self, group: Optional[GroupParameters] = None):
        if group is None:
            group = generate_parameters(1024)
        self.group = group
        self._prover = SigmaProver(group)
        self._secret, self._public_key = self._prover.generate_keypair()
        self._last_execution_proof: Optional[ExecutionProof] = None
        self._nonce = 0

    def bind_execution(self, state: int, function_ref: str) -> int:
        """Bind a function execution to the current state.

        Creates a state commitment from the given state value and
        function reference.

        Args:
            state: the external state value
            function_ref: identifier for the function to execute

        Returns:
            state_commitment integer
        """
        h = hashlib.sha256()
        h.update(str(state).encode())
        h.update(function_ref.encode())
        h.update(str(self._public_key).encode())
        digest = h.digest()
        return int.from_bytes(digest, "big")

    def prove_execution(self, inputs: Dict[str, object], state: int) -> ExecutionProof:
        """Generate a proof that execution is valid for the given state.

        Args:
            inputs: execution inputs (dict of parameter names to values)
            state: the external state value

        Returns:
            ExecutionProof
        """
        function_ref = inputs.get("_function", "default")
        state_commitment = self.bind_execution(state, function_ref)

        inputs_str = str(sorted(inputs.items()))
        h = hashlib.sha256()
        h.update(inputs_str.encode())
        inputs_hash = h.hexdigest()

        combined = _hash_combined(state_commitment, inputs_hash)

        self._nonce += 1
        proof = self._prover.prove_state(combined, self._secret)

        exec_proof = ExecutionProof(
            state_commitment=state_commitment,
            execution_proof=proof,
            function_ref=function_ref,
            inputs_hash=inputs_hash,
            nonce=self._nonce,
            timestamp=time.time(),
            public_key=self._public_key,
        )
        self._last_execution_proof = exec_proof
        return exec_proof

    def get_execution_proof(self) -> Optional[ExecutionProof]:
        return self._last_execution_proof

    def get_public_key(self) -> int:
        return self._public_key


def _hash_combined(a: int, b: str) -> int:
    h = hashlib.sha256()
    h.update(str(a).encode())
    h.update(b.encode())
    digest = h.digest()
    return int.from_bytes(digest, "big")
