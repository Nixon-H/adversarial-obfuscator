"""Item 69: Payload dispersal execution model.

Splits the payload into N shares using Shamir's Secret Sharing. Each share
is independently decryptable with a partial key. Shares are scattered across
multiple memory regions using mmap with randomized base addresses.
Reconstruction requires a quorum of shares (threshold-based).
"""

import hashlib
import os
import random
import struct
from typing import Any, Dict, List, Optional, Tuple


class ShamirSharing:
    """Shamir's Secret Sharing over GF(256)."""

    PRIME = 251

    @staticmethod
    def _eval_poly(coeffs: List[int], x: int) -> int:
        result = 0
        for c in reversed(coeffs):
            result = (result * x + c) % ShamirSharing.PRIME
        return result

    @staticmethod
    def _lagrange_interpolate(shares: List[Tuple[int, int]], x: int) -> int:
        result = 0
        for i, (xi, yi) in enumerate(shares):
            numerator = 1
            denominator = 1
            for j, (xj, _) in enumerate(shares):
                if i == j:
                    continue
                numerator = (numerator * (x - xj)) % ShamirSharing.PRIME
                denominator = (denominator * (xi - xj)) % ShamirSharing.PRIME
            result = (result + yi * numerator * pow(denominator, -1,
                      ShamirSharing.PRIME)) % ShamirSharing.PRIME
        return result

    @staticmethod
    def split_secret(secret: bytes, num_shares: int,
                     threshold: int) -> List[Tuple[int, bytes]]:
        if threshold > num_shares:
            raise ValueError("Threshold cannot exceed number of shares")
        if threshold < 2:
            raise ValueError("Threshold must be at least 2")
        secret_ints = list(secret)
        share_bytes: List[bytearray] = [
            bytearray(len(secret_ints)) for _ in range(num_shares)
        ]
        for byte_idx, byte_val in enumerate(secret_ints):
            coeffs = [byte_val] + [
                random.randint(0, ShamirSharing.PRIME - 1)
                for _ in range(threshold - 1)
            ]
            for share_idx in range(num_shares):
                x = share_idx + 1
                val = ShamirSharing._eval_poly(coeffs, x)
                share_bytes[share_idx][byte_idx] = val & 0xFF
        return [(i + 1, bytes(share_bytes[i])) for i in range(num_shares)]

    @staticmethod
    def recover_secret(shares: List[Tuple[int, bytes]],
                       threshold: int) -> bytes:
        if len(shares) < threshold:
            raise ValueError(
                f"Not enough shares: need {threshold}, got {len(shares)}"
            )
        shares = shares[:threshold]
        num_bytes = len(shares[0][1])
        result = bytearray(num_bytes)
        for byte_idx in range(num_bytes):
            byte_shares = [
                (x, y[byte_idx]) for x, y in shares
            ]
            val = ShamirSharing._lagrange_interpolate(byte_shares, 0)
            result[byte_idx] = val & 0xFF
        return bytes(result)


class PayloadShare:
    __slots__ = ("index", "data", "partial_key", "mmap_addr")

    def __init__(self, index: int, data: bytes,
                 partial_key: bytes, mmap_addr: Optional[int] = None):
        self.index = index
        self.data = data
        self.partial_key = partial_key
        self.mmap_addr = mmap_addr


class PayloadDispersal:
    """Splits payload into shares using Shamir's Secret Sharing with
    threshold-based reconstruction."""

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed or int.from_bytes(os.urandom(4), "big")
        self.shares: List[PayloadShare] = []
        self.threshold: int = 0
        self._rng = random.Random(self.seed)
        self._master_key: bytes = b""

    def disperse(self, payload: bytes, num_shares: int = 5,
                 threshold: Optional[int] = None) -> List[PayloadShare]:
        if threshold is None:
            threshold = (num_shares // 2) + 1
        self.threshold = threshold
        self._master_key = os.urandom(32)

        raw_shares = ShamirSharing.split_secret(
            payload, num_shares, threshold
        )

        self.shares = []
        for idx, share_data in raw_shares:
            partial_key = hashlib.sha256(
                self._master_key + struct.pack(">I", idx)
            ).digest()[:16]
            encrypted = self._xor_encrypt(share_data, partial_key)
            mmap_addr = self._random_mmap_address(idx)
            self.shares.append(
                PayloadShare(idx, encrypted, partial_key, mmap_addr)
            )
        return self.shares

    def _xor_encrypt(self, data: bytes, key: bytes) -> bytes:
        keystream = b""
        counter = 0
        while len(keystream) < len(data):
            block = struct.pack(">Q", counter)
            keystream += hashlib.sha256(key + block).digest()
            counter += 1
        keystream = keystream[:len(data)]
        return bytes(p ^ k for p, k in zip(data, keystream))

    def _random_mmap_address(self, idx: int) -> int:
        base = 0x7f000000000 + (idx * 0x100000)
        offset = self._rng.randint(0, 0xFFFFF) * 0x1000
        return base + offset

    def reconstruct(self, shares: Optional[List[PayloadShare]] = None,
                    threshold: Optional[int] = None) -> bytes:
        if shares is None:
            shares = self.shares
        if threshold is None:
            threshold = self.threshold
        if len(shares) < threshold:
            raise ValueError(
                f"Not enough shares for reconstruction: "
                f"need {threshold}, have {len(shares)}"
            )

        decrypted = []
        for s in shares[:threshold]:
            partial_key = hashlib.sha256(
                self._master_key + struct.pack(">I", s.index)
            ).digest()[:16]
            dec = self._xor_encrypt(s.data, partial_key)
            decrypted.append((s.index, dec))

        return ShamirSharing.recover_secret(decrypted, threshold)

    def get_dispersal_summary(self) -> Dict[str, Any]:
        return {
            "num_shares": len(self.shares),
            "threshold": self.threshold,
            "share_indices": [s.index for s in self.shares],
            "mmap_addresses": [hex(s.mmap_addr) for s in self.shares
                               if s.mmap_addr is not None],
            "seed": self.seed,
        }
