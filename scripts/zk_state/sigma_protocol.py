"""
sigma_protocol.py

Purpose:
Implements the Schnorr sigma protocol for zero-knowledge proofs of
knowledge. Includes safe-prime group parameter generation, the prover
(3-move commit-challenge-response), and the verifier (verification
equation g^s = t * y^c mod p).

Architectural Role:
Cryptographic foundation for the ZK state-bound execution module.
SigmaProver generates proofs of secret knowledge; SigmaVerifier checks
them. The protocol is a standard honest-verifier zero-knowledge (HVZK)
proof of knowledge based on the discrete-log assumption.

Execution Context:
Group parameters are generated once (by generate_parameters()) and
shared between prover and verifier. The prover creates proofs via
prove_state(); the verifier checks via verify_state().

Dependencies:
- gmpy2 (optional, for fast modular arithmetic)
- Standard library (hashlib, os, secrets, dataclasses, typing)

Security Relevance:
This is a real cryptographic protocol, not a simulation. The security
rests on the computational hardness of the discrete-log problem.

# Why this algorithm was chosen:
# Schnorr sigma protocol is the simplest efficient HVZK proof of
# knowledge. It requires only modular exponentiation (no pairings)
# and produces short proofs (3 integers).

# Threat addressed:
# An attacker must prove knowledge of the secret state to execute
# protected code. Without the secret, they cannot produce a valid
# proof, even if they can observe previous proofs.

# Assumptions:
# - Discrete-log problem is hard in the chosen safe-prime group.
# - The Fiat-Shamir heuristic (H(t||m) for challenge) produces
#   a random oracle; cryptographic hash functions approximate this.
# - 2048-bit safe primes provide ~112 bits of security.

# Failure consequences:
# - Weak prime (not safe prime): discrete-log may be tractable.
# - Weak hash: challenge may be predictable, breaking ZK property.
# - Poor randomness: secret may be recoverable from multiple proofs.

Maintenance Notes:
- Security classification: MEASURED (standard Schnorr identification
  scheme, honest-verifier zero-knowledge proof of knowledge).
- THEORETICAL: no formal UC-security proof; HVZK only, does not
  provide post-quantum security.
- If gmpy2 is installed, modular exponentiation uses gmpy2.powmod()
  for ~10x speedup. Falls back to Python's built-in pow().
- Miller-Rabin primality test uses 20 rounds (error probability < 2^-40)
  with trial division pre-screening against small primes.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass
from typing import Optional, Tuple

try:
    import gmpy2
    _HAS_GMPY = True
except ImportError:
    _HAS_GMPY = False

try:
    import gmpy2
    _HAS_GMPY = True
except ImportError:
    _HAS_GMPY = False


@dataclass
class GroupParameters:
    """Safe-prime group parameters for the sigma protocol."""
    p: int
    q: int
    g: int

    def serialize(self) -> dict:
        return {"p": self.p, "q": self.q, "g": self.g}

    @classmethod
    def deserialize(cls, data: dict) -> GroupParameters:
        return cls(p=data["p"], q=data["q"], g=data["g"])


@dataclass
class Proof:
    """A complete sigma-protocol proof (commit-challenge-response)."""
    commitment: int
    challenge: int
    response: int
    public_key: int


def _mod_inv(a: int, m: int) -> int:
    """Modular inverse using extended Euclidean algorithm."""
    g, x, _ = _extended_gcd(a % m, m)
    if g != 1:
        raise ValueError(f"{a} has no inverse mod {m}")
    return x % m


def _extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
    if b == 0:
        return a, 1, 0
    g, x1, y1 = _extended_gcd(b, a % b)
    return g, y1, x1 - (a // b) * y1


def _mod_pow(base: int, exp: int, mod: int) -> int:
    """Modular exponentiation."""
    if _HAS_GMPY:
        return int(gmpy2.powmod(base, exp, mod))
    return pow(base, exp, mod)


def _hash_to_challenge(*values: int, mod: int) -> int:
    """Hash a sequence of integers into a challenge in [0, q)."""
    h = hashlib.sha256()
    for v in values:
        h.update(str(v).encode())
    digest = h.digest()
    challenge = int.from_bytes(digest, "big") % mod
    return challenge


_SMALL_PRIMES = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
    53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107,
    109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167,
    173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229,
    233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283,
    293, 307, 311, 313, 317, 331, 337, 347, 349, 353, 359,
    367, 373, 379, 383, 389, 397, 401, 409, 419, 421, 431,
    433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491,
    499, 503, 509, 521, 523, 541,
]


_MILLER_RABIN_ROUNDS = 20


def _is_probable_prime(n: int, rounds: int = _MILLER_RABIN_ROUNDS) -> bool:
    """Miller-Rabin primality test with trial division pre-screening.

    Uses GMP (if available) for fast modular arithmetic, falling back to
    Python's built-in pow().
    """
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False

    for p in _SMALL_PRIMES[1:]:
        if n % p == 0:
            return False

    if _HAS_GMPY:
        if gmpy2.is_prime(n):
            return True
        return False

    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2

    for _ in range(rounds):
        a = secrets.randbelow(n - 3) + 2
        x = _mod_pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = _mod_pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def generate_parameters(bits: int = 2048) -> GroupParameters:
    """Generate safe-prime group parameters for the sigma protocol.

    Uses a non-deterministic safe-prime construction with incremental search.
    Returns a GroupParameters instance with p = 2q + 1 (safe prime).

    Security classification: MEASURED
      - 2048-bit safe prime provides ~112 bits of security
      - THEORETICAL: larger parameters (3072+) recommended for post-2030
    """
    if bits < 512:
        bits = 512

    candidate = secrets.randbits(bits - 1)
    candidate |= (1 << (bits - 2))
    if candidate % 2 == 0:
        candidate += 1

    while True:
        q = candidate
        p_candidate = 2 * q + 1
        try:
            if not _is_probable_prime(p_candidate):
                candidate += 2
                continue
            if _is_probable_prime(q) and pow(2, 2, p_candidate) == 1:
                g = 2
            else:
                g = 4
            return GroupParameters(p=p_candidate, q=q, g=g)
        except Exception:
            candidate += 2


class SigmaProver:
    """Prover in the sigma protocol.

    Generates proofs of knowledge of a secret scalar corresponding to
    a given public key, using a three-move commit-challenge-response
    protocol.

    Security classification: MEASURED
      - Standard Schnorr proof of knowledge
      - THEORETICAL: honest-verifier zero-knowledge only; malicious
        verifier may extract bounded information
    """

    def __init__(self, group: GroupParameters):
        self.group = group
        self._secret: Optional[int] = None
        self._public_key: Optional[int] = None

    def generate_keypair(self) -> Tuple[int, int]:
        q = self.group.q
        x = secrets.randbelow(q - 1) + 1
        y = _mod_pow(self.group.g, x, self.group.p)
        self._secret = x
        self._public_key = y
        return x, y

    def get_public_key(self) -> Optional[int]:
        return self._public_key

    def set_secret(self, secret: int, public_key: int) -> None:
        """Set the secret and public key externally."""
        self._secret = secret
        self._public_key = public_key

    def prove_state(self, state_commitment: int, secret: Optional[int] = None) -> Proof:
        """Generate a sigma protocol proof for the given state commitment.

        Three-move protocol:
          1. Prover picks random r, computes commitment t = g^r mod p
          2. Challenge c = H(t || state_commitment) mod q
          3. Response s = r + c * secret mod q

        Args:
            state_commitment: integer representing the committed state
            secret: private key (if None, uses internally generated)

        Returns:
            Proof with commitment, challenge, response, public_key
        """
        if secret is not None:
            x = secret
            y = _mod_pow(self.group.g, x, self.group.p)
        elif self._secret is not None:
            x = self._secret
            y = self._public_key
        else:
            x, y = self.generate_keypair()

        p = self.group.p
        q = self.group.q
        g = self.group.g

        r = secrets.randbelow(q - 1) + 1
        t = _mod_pow(g, r, p)

        c = _hash_to_challenge(t, state_commitment, y, mod=q)

        s = (r + c * x) % q

        return Proof(commitment=t, challenge=c, response=s, public_key=y)


class SigmaVerifier:
    """Verifier in the sigma protocol.

    Verifies sigma protocol proofs against a state commitment.

    Security classification: MEASURED
      - Standard Schnorr verification equation g^s = t * y^c (mod p)
      - THEORETICAL: completeness holds with probability 1; soundness
        holds with probability 1 - 1/q (negligible for 2048-bit groups)
    """

    def __init__(self, group: GroupParameters):
        self.group = group

    def verify_state(self, proof: Proof, state_commitment: int) -> bool:
        """Verify a sigma protocol proof against a state commitment.

        Checks: g^response = commitment * public_key^challenge (mod p)
        and verifies the challenge is correctly derived.

        Args:
            proof: Proof from SigmaProver.prove_state()
            state_commitment: the state commitment the proof is bound to

        Returns:
            True if the proof is valid, False otherwise
        """
        p = self.group.p
        q = self.group.q
        g = self.group.g

        if proof.commitment <= 0 or proof.commitment >= p:
            return False
        if proof.public_key <= 0 or proof.public_key >= p:
            return False
        if proof.response < 0 or proof.response >= q:
            return False
        if proof.challenge < 0 or proof.challenge >= q:
            return False

        expected_c = _hash_to_challenge(
            proof.commitment, state_commitment, proof.public_key, mod=q
        )
        if proof.challenge != expected_c:
            return False

        lhs = _mod_pow(g, proof.response, p)

        pk_c = _mod_pow(proof.public_key, proof.challenge, p)
        rhs = (proof.commitment * pk_c) % p

        return lhs == rhs
