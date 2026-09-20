"""
verifier.py

Purpose:
ZK verifier for state-bound execution. Verifies execution proofs
against claimed states using the sigma protocol verification equation
and enforces replay protection via nonce tracking.

Architectural Role:
High-level verifier for the ZK module. StateBoundVerifier wraps
SigmaVerifier with execution-specific checks: it recomputes state
commitments from claimed states, verifies sigma protocol proofs,
and checks nonce freshness.

Execution Context:
Instantiated with shared group parameters. Called before accepting
a state-bound execution to verify that the prover's execution proof
is valid, the state matches, and the execution has not been replayed.

Dependencies:
- sigma_protocol (GroupParameters, SigmaVerifier, generate_parameters)
- prover (ExecutionProof)
- Standard library (hashlib, time, dataclasses, typing)

Security Relevance:
This is the verification gate for state-bound execution. If the
verifier accepts an invalid proof, an attacker can execute code in
an unauthorized context. If it accepts a replayed proof, an attacker
can reuse an old execution.

# Why this algorithm was chosen:
# Schnorr verification (g^s = t * y^c mod p) is simple and efficient.
# The Fiat-Shamir challenge ensures the proof is bound to the specific
# state commitment.

# Threat addressed:
# Attackers who cannot produce valid proofs for the current state
# cannot execute state-bound functions. Replay attacks are prevented
# by nonce tracking.

# Assumptions:
# - The prover's public key is authentic (not substituted)
# - The state value provided to verify_execution() is correct
# - SHA-256 is collision-resistant for commitment verification

# Failure consequences:
# - Invalid proof accepted: unauthorized execution succeeds
# - Replay not detected: old execution replayed in new context
# - Timing side-channel: nonce status leakage may help attackers

Maintenance Notes:
- Security classification: MEASURED (verification uses standard
  Schnorr verification).
- THEORETICAL: replay protection is memory-bound (tracks used nonces);
  information leaked via timing side-channels could reveal nonce status.
- THEORETICAL: for persistent replay protection across restarts,
  nonces must be persisted to durable storage (currently in-memory set).
- The _compute_combined method hashes (state_commitment || inputs_hash)
  to bind the proof to the specific execution context.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set

from .sigma_protocol import GroupParameters, SigmaVerifier, generate_parameters
from .prover import ExecutionProof
from typing import Dict, Optional, Set

from .sigma_protocol import GroupParameters, SigmaVerifier, generate_parameters
from .prover import ExecutionProof


@dataclass
class VerificationResult:
    """Result of verifying a state-bound execution proof."""
    valid: bool
    state_match: bool
    replay_safe: bool
    latency_ms: float


class StateBoundVerifier:
    """Verifier for state-bound execution proofs.

    Verifies sigma protocol proofs and tracks used nonces to prevent
    replay attacks.

    Security classification: MEASURED
      - Nonce tracking uses an in-memory set (lost on restart)
      - THEORETICAL: for persistent replay protection, nonces must be
        persisted to durable storage
    """

    def __init__(self, group: Optional[GroupParameters] = None):
        if group is None:
            group = generate_parameters(1024)
        self.group = group
        self._verifier = SigmaVerifier(group)
        self._used_nonces: Set[int] = set()
        self._verified_state: Optional[int] = None

    def verify_execution(self, execution_proof: ExecutionProof, state: int) -> VerificationResult:
        """Verify an execution proof against a claimed state.

        Checks:
          1. The sigma protocol proof is valid
          2. The state commitment matches the claimed state
          3. The nonce has not been reused (replay protection)

        Args:
            execution_proof: ExecutionProof from StateBoundProver
            state: the claimed external state

        Returns:
            VerificationResult with individual check results and latency
        """
        start = time.perf_counter()

        combined = self._compute_combined(
            execution_proof.state_commitment,
            execution_proof.inputs_hash,
        )

        proof_valid = self._verifier.verify_state(
            execution_proof.execution_proof, combined
        )

        if proof_valid:
            expected_commitment = self._recompute_commitment(
                state, execution_proof.function_ref,
                execution_proof.public_key
            )
            state_match = (expected_commitment == execution_proof.state_commitment)
        else:
            state_match = False

        replay_safe = execution_proof.nonce not in self._used_nonces

        if proof_valid and state_match and replay_safe:
            self._used_nonces.add(execution_proof.nonce)
            self._verified_state = state

        elapsed = (time.perf_counter() - start) * 1000.0

        overall_valid = proof_valid and state_match and replay_safe

        return VerificationResult(
            valid=overall_valid,
            state_match=state_match,
            replay_safe=replay_safe,
            latency_ms=elapsed,
        )

    def check_replay(self, execution_proof: ExecutionProof) -> bool:
        """Check if a nonce has been reused.

        Args:
            execution_proof: the proof to check

        Returns:
            True if the nonce is fresh (not yet seen)
        """
        return execution_proof.nonce not in self._used_nonces

    def get_state(self) -> Optional[int]:
        return self._verified_state

    def _compute_combined(self, state_commitment: int, inputs_hash: str) -> int:
        h = hashlib.sha256()
        h.update(str(state_commitment).encode())
        h.update(inputs_hash.encode())
        digest = h.digest()
        return int.from_bytes(digest, "big")

    def _recompute_commitment(self, state: int, function_ref: str,
                               public_key: int) -> int:
        h = hashlib.sha256()
        h.update(str(state).encode())
        h.update(function_ref.encode())
        h.update(str(public_key).encode())
        digest = h.digest()
        return int.from_bytes(digest, "big")
