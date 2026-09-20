"""
scheme.py

Purpose:
Real leveled BGV-style FHE scheme over polynomial rings R = Z_t[x]/(x^n+1).
Performs actual encryption, decryption, addition, multiplication with
relinearization and noise tracking. Parameters are set small for
research/demonstration.

Architectural Role:
Cryptographic core of the FHE VM. BGVScheme implements the leveled
BGV scheme with:
- Key generation (secret key, public key, relinearization key)
- Encryption (encodes plaintext as polynomial, adds noise)
- Decryption (removes noise, decodes plaintext)
- Homomorphic addition, subtraction, multiplication
- Relinearization after multiplication to keep ciphertext size 2

Execution Context:
Instantiated by FHEExecutor with optional BGVParameters. Key generation
must be called before encryption/decryption. The scheme is stateful:
it tracks noise growth via BGVErrorGrowth.

Dependencies:
- numpy (third-party, polynomial arithmetic)
- Standard library (random, dataclasses, typing)

Security Relevance:
This is a real FHE scheme, not a mock. However, the demonstration
parameters (n=8, q=1073741827) provide negligible security. Production
use requires n >= 4096, q >= 2^120, and secure parameter selection
following HomomorphicEncryption.org security standards.

# Why this algorithm was chosen:
# BGV is a widely-studied leveled FHE scheme supporting arbitrary
# depth with relinearization. It is simpler than CKKS (which handles
# approximate numbers) and more flexible than TFHE (which is
# boolean-circuit oriented).

# Threat addressed:
# An attacker who compromises the execution environment should not
# learn the plaintext values of crown-jewel computations. FHE ensures
# data remains encrypted throughout computation.

# Assumptions:
# - The polynomial ring R = Z_t[x]/(x^n+1) provides the algebraic
#   structure for security (Ring-LWE assumption).
# - The discrete Gaussian noise distribution (sigma=1.0) is sufficient
#   for the chosen parameters.
# - Relinearization keys do not leak the secret key (circular security
#   assumption).

# Failure consequences:
# - Parameter太小导致noise overflow: decryption fails, data lost.
# - Weak parameters: attacker can recover secret key from public key.
# - Incorrect relinearization: ciphertext grows unbounded.

Maintenance Notes:
- The ring multiplication uses naive convolution (O(n^2)). For
  production, use NTT-based multiplication (O(n log n)).
- The _is_prime test is a simple trial division; for production
  parameter selection, use proven-primes from a trusted source.
- BGVErrorGrowth provides a rough estimate of remaining noise budget;
  for precise noise management, implement canonical embedding-based
  noise estimation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

import random

import numpy as np

_sysrand = random.SystemRandom()


@dataclass
class BGVParameters:
    n: int = 8
    t: int = 7
    q: int = 1073741827  # ~2^30 + 3 — prime, large enough to support multi-layer multiplication with relinearization
    sigma: float = 1.0
    relin_base: int = 16

    def __post_init__(self):
        assert self.n > 0 and (self.n & (self.n - 1)) == 0, "n must be a power of 2"
        assert self.t < self.q, "plaintext modulus t must be less than ciphertext modulus q"
        assert self._is_prime(self.q), "q must be prime"
        assert self._is_prime(self.t), "t must be prime"

    @staticmethod
    def _is_prime(x: int) -> bool:
        if x < 2:
            return False
        if x % 2 == 0:
            return x == 2
        i = 3
        while i * i <= x:
            if x % i == 0:
                return False
            i += 2
        return True

    def ring_modulus(self) -> int:
        return self.q

    def plaintext_modulus(self) -> int:
        return self.t

    def poly_degree(self) -> int:
        return self.n


@dataclass
class BGVKeyPair:
    secret_key: np.ndarray
    public_key: tuple[np.ndarray, np.ndarray]
    relin_key: Optional[list[tuple[np.ndarray, np.ndarray]]] = None
    params: BGVParameters = field(default_factory=BGVParameters)


class BGVErrorGrowth:
    def __init__(self, params: BGVParameters):
        self.params = params
        self.noise_budget: float = float(params.q // params.t)
        self.ops_since_reset: int = 0
        self.max_depth: int = self._estimate_max_depth()

    def _relin_noise(self) -> float:
        nf = float(self.params.n)
        sigma = self.params.sigma
        T = float(self.params.relin_base)
        ell = max(1, int(np.ceil(np.log2(float(self.params.q)) / np.log2(T))))
        return nf * sigma * sigma * T * ell

    def _estimate_max_depth(self) -> int:
        qf = float(self.params.q)
        tf = float(self.params.t)
        nf = float(self.params.n)
        budget = qf / tf
        mul_noise = (nf * tf * tf * self.params.sigma * self.params.sigma) + self._relin_noise()
        if mul_noise <= 1:
            return 10
        return max(1, int(budget // mul_noise))

    def record_add(self):
        self.noise_budget -= float(self.params.n)
        self.ops_since_reset += 1

    def record_mul(self):
        tf = float(self.params.t)
        nf = float(self.params.n)
        growth = nf * tf * tf * self.params.sigma * self.params.sigma + self._relin_noise()
        self.noise_budget -= growth
        self.ops_since_reset += 1

    def is_exhausted(self) -> bool:
        return self.noise_budget <= 0

    def remaining_budget(self) -> float:
        return max(0.0, self.noise_budget)

    def __str__(self) -> str:
        return f"BGVErrorGrowth(budget={self.remaining_budget():.1f}, depth={self.max_depth}, ops={self.ops_since_reset})"


class BGVPolynomial:
    @staticmethod
    def random_poly(n: int, q: int, sigma: float = 1.0) -> np.ndarray:
        coeffs = np.array([_sysrand.normalvariate(0, sigma) for _ in range(n)], dtype=np.int64)
        return BGVPolynomial.mod_coeffs(coeffs, q)

    @staticmethod
    def uniform_poly(n: int, q: int) -> np.ndarray:
        coeffs = np.array([_sysrand.randrange(0, q) for _ in range(n)], dtype=np.int64)
        return BGVPolynomial.mod_coeffs(coeffs, q)

    @staticmethod
    def small_poly(n: int, q: int) -> np.ndarray:
        coeffs = np.array([_sysrand.randrange(-1, 2) for _ in range(n)], dtype=np.int64)
        return BGVPolynomial.mod_coeffs(coeffs, q)

    @staticmethod
    def mod_coeffs(coeffs: np.ndarray, q: int) -> np.ndarray:
        return np.mod(coeffs, q).astype(np.int64)

    @staticmethod
    def ring_multiply(a: np.ndarray, b: np.ndarray, q: int) -> np.ndarray:
        n = len(a)
        conv = np.convolve(a, b, mode='full')
        result = np.zeros(n, dtype=np.int64)
        for i in range(len(conv)):
            idx = i % n
            sign = 1 if idx == i else -1
            result[idx] = (result[idx] + sign * int(round(conv[i]))) % q
        return BGVPolynomial.mod_coeffs(result, q)

    @staticmethod
    def ring_multiply_full(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        n = len(a)
        conv = np.convolve(a, b, mode='full')
        result = np.zeros(n, dtype=np.int64)
        for i in range(len(conv)):
            idx = i % n
            sign = 1 if idx == i else -1
            result[idx] = result[idx] + sign * int(round(conv[i]))
        return result

    @staticmethod
    def ring_add(a: np.ndarray, b: np.ndarray, q: int) -> np.ndarray:
        return BGVPolynomial.mod_coeffs(a + b, q)

    @staticmethod
    def ring_sub(a: np.ndarray, b: np.ndarray, q: int) -> np.ndarray:
        return BGVPolynomial.mod_coeffs(a - b, q)

    @staticmethod
    def ring_neg(a: np.ndarray, q: int) -> np.ndarray:
        return BGVPolynomial.mod_coeffs(-a, q)

    @staticmethod
    def encode_int(value: int, t: int, n: int) -> np.ndarray:
        poly = np.zeros(n, dtype=np.int64)
        poly[0] = value % t
        return poly

    @staticmethod
    def decode_int(poly: np.ndarray, t: int) -> int:
        val = int(round(poly[0])) % t
        return val


class BGVScheme:
    def __init__(self, params: Optional[BGVParameters] = None):
        self.params = params or BGVParameters()
        self.keypair: Optional[BGVKeyPair] = None
        self.error_tracker: Optional[BGVErrorGrowth] = None

    def keygen(self) -> BGVKeyPair:
        n = self.params.n
        q = self.params.q
        sk = BGVPolynomial.small_poly(n, q)
        a = BGVPolynomial.uniform_poly(n, q)
        e = BGVPolynomial.random_poly(n, q, self.params.sigma)
        b = BGVPolynomial.ring_sub(BGVPolynomial.ring_neg(
            BGVPolynomial.ring_multiply(a, sk, q), q), e, q)
        pk = (a, b)
        rlk = self._generate_relin_key(sk)
        self.keypair = BGVKeyPair(secret_key=sk, public_key=pk, relin_key=rlk, params=self.params)
        self.error_tracker = BGVErrorGrowth(self.params)
        return self.keypair

    def _generate_relin_key(self, sk: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
        n = self.params.n
        q = self.params.q
        T = self.params.relin_base
        ell = int(np.ceil(np.log2(q) / np.log2(T)))
        sk_sq = BGVPolynomial.ring_multiply(sk, sk, q)
        rlk = []
        for i in range(ell):
            a_i = BGVPolynomial.uniform_poly(n, q)
            e_i = BGVPolynomial.random_poly(n, q, self.params.sigma)
            power = (T ** i) % q
            rhs = BGVPolynomial.ring_add(
                BGVPolynomial.mod_coeffs(sk_sq * power, q),
                e_i, q
            )
            b_i = BGVPolynomial.ring_sub(
                rhs,
                BGVPolynomial.ring_multiply(a_i, sk, q),
                q
            )
            rlk.append((a_i, b_i))
        return rlk

    def encrypt(self, value: int, pk: Optional[tuple[np.ndarray, np.ndarray]] = None) -> tuple[np.ndarray, np.ndarray]:
        if pk is None:
            if self.keypair is None:
                raise ValueError("No keypair available; call keygen() first")
            pk = self.keypair.public_key
        n = self.params.n
        q = self.params.q
        t = self.params.t
        a, b = pk
        m_poly = BGVPolynomial.encode_int(value, t, n)
        u = BGVPolynomial.small_poly(n, q)
        e1 = BGVPolynomial.random_poly(n, q, self.params.sigma)
        e2 = BGVPolynomial.random_poly(n, q, self.params.sigma)
        ct0 = BGVPolynomial.ring_add(
            BGVPolynomial.ring_multiply(b, u, q),
            BGVPolynomial.ring_add(
                BGVPolynomial.mod_coeffs(m_poly * (q // t), q),
                e1, q
            ),
            q
        )
        ct1 = BGVPolynomial.ring_add(
            BGVPolynomial.ring_multiply(a, u, q),
            e2, q
        )
        if self.error_tracker:
            self.error_tracker.ops_since_reset += 1
        return (ct0, ct1)

    def decrypt(self, ciphertext, sk: Optional[np.ndarray] = None) -> int:
        if sk is None:
            if self.keypair is None:
                raise ValueError("No keypair available; call keygen() first")
            sk = self.keypair.secret_key
        q = self.params.q
        t = self.params.t
        if len(ciphertext) == 2:
            ct0, ct1 = ciphertext
            phase = BGVPolynomial.ring_add(
                ct0,
                BGVPolynomial.ring_multiply(ct1, sk, q),
                q
            )
        elif len(ciphertext) == 3:
            ct0, ct1, ct2 = ciphertext
            sk_sq = BGVPolynomial.ring_multiply(sk, sk, q)
            phase = BGVPolynomial.ring_add(
                ct0,
                BGVPolynomial.ring_add(
                    BGVPolynomial.ring_multiply(ct1, sk, q),
                    BGVPolynomial.ring_multiply(ct2, sk_sq, q),
                    q
                ),
                q
            )
        else:
            raise ValueError(f"Invalid ciphertext length: {len(ciphertext)}")
        scaled = np.round(phase.astype(np.float64) * t / q).astype(np.int64) % t
        val = BGVPolynomial.decode_int(scaled, t)
        return val

    def add(self, ct_a: tuple[np.ndarray, np.ndarray],
            ct_b: tuple[np.ndarray, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
        q = self.params.q
        result = (
            BGVPolynomial.ring_add(ct_a[0], ct_b[0], q),
            BGVPolynomial.ring_add(ct_a[1], ct_b[1], q),
        )
        if self.error_tracker:
            self.error_tracker.record_add()
        return result

    def sub(self, ct_a: tuple[np.ndarray, np.ndarray],
            ct_b: tuple[np.ndarray, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
        q = self.params.q
        result = (
            BGVPolynomial.ring_sub(ct_a[0], ct_b[0], q),
            BGVPolynomial.ring_sub(ct_a[1], ct_b[1], q),
        )
        if self.error_tracker:
            self.error_tracker.record_add()
        return result

    def mul(self, ct_a, ct_b):
        q = self.params.q
        t = self.params.t
        ct0_0, ct0_1 = ct_a[:2]
        ct1_0, ct1_1 = ct_b[:2]
        c0_full = BGVPolynomial.ring_multiply_full(ct0_0, ct1_0)
        c1_full = BGVPolynomial.ring_multiply_full(ct0_0, ct1_1) + \
                  BGVPolynomial.ring_multiply_full(ct0_1, ct1_0)
        c2_full = BGVPolynomial.ring_multiply_full(ct0_1, ct1_1)
        delta = q // t
        c0 = BGVPolynomial.mod_coeffs(np.round(c0_full.astype(np.float64) / delta).astype(np.int64), q)
        c1 = BGVPolynomial.mod_coeffs(np.round(c1_full.astype(np.float64) / delta).astype(np.int64), q)
        c2 = BGVPolynomial.mod_coeffs(np.round(c2_full.astype(np.float64) / delta).astype(np.int64), q)
        ct_out = tuple(self._relinearize((c0, c1, c2)))
        if self.error_tracker:
            self.error_tracker.record_mul()
        return ct_out

    def _relinearize(self, ct3: tuple[np.ndarray, np.ndarray, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
        if self.keypair is None or self.keypair.relin_key is None:
            return (ct3[0], ct3[1])
        q = self.params.q
        T = self.params.relin_base
        c0, c1, c2 = ct3
        rlk = self.keypair.relin_key
        ell = len(rlk)
        ct0_new = c0.copy()
        ct1_new = c1.copy()
        temp = c2.copy()
        for i in range(ell):
            c2_i = BGVPolynomial.mod_coeffs(temp, T)
            temp = BGVPolynomial.mod_coeffs((temp - c2_i) // T, q)
            a_i, b_i = rlk[i]
            ct0_new = BGVPolynomial.ring_add(ct0_new, BGVPolynomial.ring_multiply(b_i, c2_i, q), q)
            ct1_new = BGVPolynomial.ring_add(ct1_new, BGVPolynomial.ring_multiply(a_i, c2_i, q), q)
        return (ct0_new, ct1_new)

    def encrypt_array(self, values: list[int]) -> list[tuple[np.ndarray, np.ndarray]]:
        return [self.encrypt(v) for v in values]

    def decrypt_array(self, cts: list[tuple[np.ndarray, np.ndarray]]) -> list[int]:
        return [self.decrypt(ct) for ct in cts]
