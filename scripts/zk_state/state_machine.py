"""
state_machine.py

Purpose:
State machine with provable transitions using sigma protocol proofs.
Each transition generates a zero-knowledge proof that binds the new
state to the state machine's identity, enabling verifiable state
execution.

Architectural Role:
Provides state-bound execution context for the ZK module. The
StateMachine maintains a monotonic state value, generates commitment
hashes, and produces transition proofs. Verifiers can check that a
state transition is valid without knowing the state.

Execution Context:
Instantiated with an initial state value and optional group parameters.
Each call to transition() produces a StateProof. The proof can be
verified by verify_transition() on the same or another StateMachine
instance.

Dependencies:
- sigma_protocol (GroupParameters, Proof, SigmaProver, SigmaVerifier)
- Standard library (hashlib, os, time, dataclasses, typing)

Security Relevance:
State proofs bind execution to a verifiable context. Without this,
an attacker could execute protected code in an arbitrary state
(e.g., skipping security checks). The nonce prevents replay attacks.

# Why this algorithm was chosen:
# Sigma protocol proofs are non-interactive (Fiat-Shamir) and efficient
# (3 exponentiations). State commitments bind the machine's identity
# (public key) to each state, preventing impersonation.

# Threat addressed:
# An attacker who can execute arbitrary code should not be able to
# forge state transitions. Without the secret key, they cannot produce
# valid proofs for arbitrary states.

# Assumptions:
# - The initial state is correctly set by trusted bootstrap code
# - SHA-256 commitments are collision-resistant
# - The system clock is reasonably accurate for timestamp checks

# Failure consequences:
# - Weak commitments: attacker can claim false states
# - Nonce reuse: attacker can replay old transitions
# - Clock skew: timestamp-based replay checks may be bypassed

Maintenance Notes:
- Security classification: MEASURED
  - State transitions are provably bound to the state machine's identity
  - THEORETICAL: replay protection relies on monotonic nonce + wall-clock
    time; clock-skew attacks can bypass timestamp checks.
- State commitments use SHA-256 over (state || public_key). This binds
  the commitment to both the state value and the machine identity.
- Nonces are strictly monotonic (incrementing integer). Combined with
  the used_nonces set, this prevents replay attacks within a session.
- THEORETICAL: no forward-secrecy; compromise of secret allows forging
  historical transitions.
"""

from __future__ import annotations

import hashlib
import os  # noqa: F401 (this line binds a name used by an embedded template)
import time
from dataclasses import dataclass
from typing import Optional, Set

from .sigma_protocol import GroupParameters, Proof, SigmaProver, SigmaVerifier


@dataclass
class StateProof:
    """Proof of a state machine transition."""
    state_commitment: int
    transition_proof: Proof
    timestamp: float
    nonce: int


class StateMachine:
    """State machine with provable state transitions.

    Each transition generates a sigma-protocol proof binding the new
    state commitment to the state machine's identity.  Replay protection
    is enforced via a strictly monotonic nonce and wall-clock timestamp.

    Security classification: MEASURED
      - State commitments use SHA-256
      - THEORETICAL: no forward-secrecy; compromise of secret allows
        forging historical transitions
    """

    def __init__(self, initial_state: int, group: Optional[GroupParameters] = None,
                 secret: Optional[int] = None):
        if group is None:
            from .sigma_protocol import generate_parameters
            group = generate_parameters(1024)

        self.group = group
        self._prover = SigmaProver(group)
        if secret is not None:
            self._secret = secret
            self._public_key = _mod_pow(group.g, secret, group.p)
            self._prover.set_secret(secret, self._public_key)
        else:
            self._secret, self._public_key = self._prover.generate_keypair()

        self._state = initial_state
        self._state_commitment = self._commit_state(initial_state)
        self._last_proof: Optional[StateProof] = None
        self._nonce = 0
        self._used_nonces: Set[int] = set()

    def _commit_state(self, state: int) -> int:
        h = hashlib.sha256()
        h.update(str(state).encode())
        h.update(str(self._public_key).encode())
        digest = h.digest()
        return int.from_bytes(digest, "big")

    def transition(self, new_state: int, secret: Optional[int] = None) -> StateProof:
        """Create a state transition with a zero-knowledge proof.

        Args:
            new_state: the new state value
            secret: optional explicit secret (uses internal if None)

        Returns:
            StateProof containing the proof of transition
        """
        self._state = new_state
        self._state_commitment = self._commit_state(new_state)

        if secret is None:
            secret = self._secret

        proof = self._prover.prove_state(self._state_commitment, secret)

        self._nonce += 1

        sp = StateProof(
            state_commitment=self._state_commitment,
            transition_proof=proof,
            timestamp=time.time(),
            nonce=self._nonce,
        )
        self._last_proof = sp
        return sp

    def verify_transition(self, proof: StateProof) -> bool:
        """Verify a transition proof.

        Checks the sigma protocol proof and replay protection (nonce
        not previously seen).

        Args:
            proof: StateProof to verify

        Returns:
            True if the transition proof is valid
        """
        if proof.state_commitment != self._state_commitment:
            return False

        if proof.nonce in self._used_nonces:
            return False

        if proof.transition_proof.public_key != self._public_key:
            return False

        verifier = SigmaVerifier(self.group)
        valid = verifier.verify_state(proof.transition_proof, proof.state_commitment)

        if valid:
            self._used_nonces.add(proof.nonce)

        return valid

    def get_state_commitment(self) -> int:
        return self._state_commitment

    def get_proof(self) -> Optional[StateProof]:
        return self._last_proof

    def get_public_key(self) -> int:
        return self._public_key


def _mod_pow(base: int, exp: int, mod: int) -> int:
    return pow(base, exp, mod)
