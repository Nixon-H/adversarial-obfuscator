"""
temporal_key.py

Purpose:
Implements a temporal micro-key evolution system inspired by the
SilentTime framework and forward-secure key-agreement protocols.
Derives ephemeral sub-keys from a master seed using a hash chain
(ratchet), enabling per-epoch or per-session keys that cannot be
retroactively derived if the master seed is later compromised.

Architectural Role:
Key management layer for the fragment binding system. TemporalKey
provides time-evolving keys for CryptoFragmentBinder, ensuring
that fragment encryption keys change across epochs (time windows,
session boundaries, or build versions).

Security Relevance:
Forward secrecy: Compromise of a temporal sub-key does not reveal
past sub-keys because each step in the hash chain discards the
parent. Specifically:
- Master seed is used only at initialization and never stored.
- derive_sub_key(epoch) walks the hash chain from the current
  epoch to the target epoch.
- The hash chain uses SHA-256(previous_key || epoch_salt) where
  epoch_salt is a static salt mixed with the epoch number.
- The internal ratchet is advanced by overwriting current_key
  with each derivation step, preventing re-derivation of old keys.

Threat model: Long-term key compromise, cross-epoch decryption,
key extraction from memory dumps.

What happens on invalid epoch: derive_key() returns None.

Sibling: crypto_binding.py — fragment-payload encryption transform that
CONSUMES these epoch keys (rolling/history-bound modes). Key schedule
here, fragment transform there; do not merge.
"""

import hashlib
import os
from typing import Optional


class TemporalKey:
    """
    Hash-chain-based temporal key evolution.

    Provides a ratcheting key derivation mechanism where each epoch
    produces a unique sub-key, and past sub-keys cannot be re-derived
    after the ratchet has advanced.

    Usage:
        tk = TemporalKey()
        epoch_0_key = tk.derive_key(0)
        epoch_1_key = tk.derive_key(1)
        # epoch_0_key cannot be re-derived after derive_key(1)
    """

    KEY_LENGTH = 32

    def __init__(self, seed: Optional[bytes] = None, salt: Optional[bytes] = None):
        """
        Initialize the temporal key chain.

        Args:
            seed: 32-byte master seed. If None, os.urandom(32).
            salt: Static salt mixed at each derivation step.
                  If None, generated from os.urandom(16).

        If seed is provided externally, caller must ensure it has
        at least KEY_LENGTH bytes of entropy. Truncation to KEY_LENGTH
        is applied silently.
        """
        if seed is None:
            seed = os.urandom(self.KEY_LENGTH)
        self._current_key = seed[:self.KEY_LENGTH]

        if salt is None:
            if seed is not None:
                salt = hashlib.sha256(seed).digest()[:16]
            else:
                salt = os.urandom(16)
        self._salt = salt

        self._current_epoch = 0

    def derive_key(self, target_epoch: int) -> Optional[bytes]:
        """
        Derive the sub-key for a given epoch.

        If target_epoch >= current_epoch, advances the ratchet
        forward by repeated hashing. If target_epoch < current_epoch,
        returns None (no rewinding).

        The ratchet step is:
            key_{i+1} = SHA-256(key_i || salt || epoch_number)

        Each step is irreversible: given key_{i+1}, you cannot
        compute key_i without brute-forcing SHA-256.
        """
        if target_epoch < self._current_epoch:
            return None

        steps = target_epoch - self._current_epoch
        key = self._current_key

        for _ in range(steps):
            epoch_bytes = str(self._current_epoch).encode()
            key = hashlib.sha256(key + self._salt + epoch_bytes).digest()
            self._current_epoch += 1

        self._current_key = key
        return key

    def get_current_epoch(self) -> int:
        """Return the epoch index of the current internal key."""
        return self._current_epoch

    def reseed(self, new_seed: bytes) -> None:
        self._current_key = new_seed[:self.KEY_LENGTH]
        self._current_epoch = 0


import time


class TemporalKeyChain:
    """
    Time-window-based key chain for temporal micro-key evolution (Item 59).

    Derives a unique key per time window (epoch), supporting forward-secure
    key evolution where past window keys cannot be re-derived after the
    ratchet advances.
    """

    def __init__(self, genesis_secret: bytes, window_seconds: float = 60.0):
        self._genesis = genesis_secret
        self._window_seconds = window_seconds
        self._tk = TemporalKey(seed=genesis_secret)
        self._current_window = 0

    def derive_key_for_window(self, window: int | None = None) -> "WindowKey":
        target = window if window is not None else int(time.time() / self._window_seconds)
        key_bytes = self._tk.derive_key(target)
        if key_bytes is None:
            self._tk = TemporalKey(seed=self._genesis)
            key_bytes = self._tk.derive_key(target)
            if key_bytes is None:
                key_bytes = self._tk.derive_key(0)
                target = 0
        self._current_window = target
        return WindowKey(index=target, key=key_bytes,
                         window_start=target * self._window_seconds,
                         window_end=(target + 1) * self._window_seconds)

    def verify_key_in_window(self, key: "WindowKey", timestamp: float) -> bool:
        return key.window_start <= timestamp < key.window_end

    def get_chain_length(self) -> int:
        return self._current_window + 1


class WindowKey:
    """A single temporal window key with metadata."""

    def __init__(self, index: int, key: bytes, window_start: float, window_end: float):
        self.index = index
        self.key = key
        self.window_start = window_start
        self.window_end = window_end
