"""
state_isa.py

Purpose:
Implements a state-dependent opcode mapping (Item 84 of the protection
spec). The physical-to-logical opcode mapping rotates based on a rolling
SHA-256 hash of the last N executed instruction IDs. When the hash
crosses configurable thresholds, the mapping shifts.

Architectural Role:
Dynamic ISA obfuscation layer. Provides two classes:
- StateISA: Primary state-dependent opcode mapping with rotation
  based on execution history.
- StateIsaTable: Lightweight runtime lookup variant.

Security Relevance:
State-dependent opcode rotation ensures that even if an attacker
captures the opcode map at one point in execution, the map changes
as execution proceeds. The rotation is driven by the execution history
itself, making it unpredictable without executing the code.

Key design properties:
- History length defaults to 8 instructions.
- Threshold schedule generated from a seed (16 values via SHA-256 PRNG).
- Rotation triggers when the rolling hash exceeds the current threshold.
- The rolling hash is SHA-256 over packed instruction IDs (little-endian).
- The schedule uses a linear congruential generator (LCG) seeded from
  the initial seed: seed_{n+1} = seed_n * 6364136223846793005 + 1442695040888963407.
  This LCG is the same one used by PCG family generators.

Threat model: Static analysis, opcode-map extraction, precomputed
disassembly tables.
"""

import hashlib
import struct
from typing import Optional


class StateISA:
    """
    State-dependent opcode mapping that rotates based on execution history.

    Maintains a sliding window of the last N instruction IDs. A rolling
    SHA-256 hash of this window is compared against threshold values from
    a seeded schedule. When the hash exceeds the threshold, a rotation
    offset is incremented, changing the physical-to-logical mapping.
    """

    def __init__(self, history_len: int = 8, seed: int = 0):
        """
        Initialize the state-dependent ISA with a history window and seed.

        Args:
            history_len: Number of instruction IDs to track in the window.
            seed: Initial seed for the rotation threshold schedule.
        """
        self.history_len = history_len
        self.exec_history: list[int] = []
        self.rotation_schedule = generate_state_rotation_schedule(seed)
        self.current_rotation = 0
        self.base_map = list(range(256))

    def state_isa_lookup(self, physical_opcode: int) -> int:
        """
        Map a physical opcode to a logical opcode based on current ISA state.

        The state is computed as the rolling SHA-256 hash of the execution
        history. If the state exceeds the current threshold, the rotation
        advances. The logical opcode is then:
            rotated = (physical_opcode + current_rotation) & 0xFF
            logical = base_map[rotated]

        Security note: The rotation only advances forward; it never
        rewinds. This ensures monotonic progress through the schedule
        and prevents an attacker from forcing a previous mapping.
        """
        state = self._compute_state()
        threshold = self.rotation_schedule[self.current_rotation % len(self.rotation_schedule)]
        if state > threshold:
            self.current_rotation += 1
        rotated = (physical_opcode + self.current_rotation) & 0xFF
        logical = self.base_map[rotated]
        return logical

    def update_isa_state(self, instruction_id: int) -> bytes:
        """
        Append an instruction ID to the execution history and return the
        current state hash bytes.

        The history is a sliding window: when it exceeds history_len,
        the oldest entry is removed.
        """
        self.exec_history.append(instruction_id & 0xFF)
        if len(self.exec_history) > self.history_len:
            self.exec_history.pop(0)
        return self._compute_state_bytes()

    def _compute_state(self) -> int:
        """
        Compute the rolling state as the first 8 bytes (little-endian) of
        SHA-256 over the packed history bytes.

        Returns 0 if the history is empty (no instructions executed yet).
        """
        if not self.exec_history:
            return 0
        data = struct.pack(f"<{len(self.exec_history)}B", *self.exec_history)
        digest = hashlib.sha256(data).digest()
        return struct.unpack("<Q", digest[:8])[0]

    def _compute_state_bytes(self) -> bytes:
        """
        Compute the full 32-byte SHA-256 state hash.

        Returns 32 zero bytes if the history is empty.
        """
        if not self.exec_history:
            return b"\x00" * 32
        data = struct.pack(f"<{len(self.exec_history)}B", *self.exec_history)
        return hashlib.sha256(data).digest()

    def reset(self):
        """
        Reset the execution history and rotation counter.

        Useful when entering a new execution context or after a TEE
        boundary crossing.
        """
        self.exec_history.clear()
        self.current_rotation = 0


def generate_state_rotation_schedule(seed: int) -> list[int]:
    """
    Generate 16 threshold values for opcode mapping rotation.

    Each threshold is derived from SHA-256(seed || index) and then
    normalized to the range [0x10000000, 0xFFFFFFFF] by OR-ing with
    0x10000000.

    The seed is advanced through an LCG (same constants as PCG family):
        seed_{n+1} = seed_n * 6364136223846793005 + 1442695040888963407

    This ensures that the threshold sequence is deterministic from the
    seed but unpredictable without it.
    """
    rng_seed = seed
    schedule = []
    for i in range(16):
        data = hashlib.sha256(struct.pack("<QQ", rng_seed, i)).digest()
        val = struct.unpack("<Q", data[:8])[0]
        threshold = (val % 0xFFFFFFFF) | 0x10000000
        schedule.append(threshold)
        rng_seed = (rng_seed * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
    return schedule


class StateIsaTable:
    """
    Lightweight state-dependent ISA table for runtime use.

    Similar to StateISA but optimized for in-band use within the VM
    interpreter. Tracks a simpler state vector and provides a single
    lookup() method.
    """

    def __init__(self, history_len: int = 8, seed: int = 0):
        """
        Initialize the runtime state-ISA table.

        Args:
            history_len: Number of instruction IDs to track.
            seed: Seed for the rotation threshold schedule.
        """
        self.history_len = history_len
        self.state: list[int] = []
        self.rotation = 0
        self.schedule = generate_state_rotation_schedule(seed)

    def lookup(self, opcode: int, state_bytes: Optional[bytes] = None) -> int:
        """
        Look up a transformed opcode based on current state.

        If state_bytes is provided, it is used directly as the state
        value. Otherwise, state defaults to 0.

        Security note: The state_bytes parameter allows the caller to
        inject a precomputed state (e.g., from the rolling hash in the
        interpreter), avoiding redundant hashing.
        """
        if state_bytes and len(state_bytes) >= 8:
            state_val = struct.unpack("<Q", state_bytes[:8])[0]
        else:
            state_val = 0
        threshold = self.schedule[self.rotation % len(self.schedule)]
        if state_val > threshold:
            self.rotation += 1
        return (opcode + self.rotation) & 0xFF

    def update_state(self, instruction_id: int) -> bytes:
        """
        Update the state with a new instruction ID and return the
        current state hash bytes.

        Maintains a sliding window and computes SHA-256 over the
        packed history.
        """
        self.state.append(instruction_id & 0xFF)
        if len(self.state) > self.history_len:
            self.state.pop(0)
        if not self.state:
            return b"\x00" * 32
        data = struct.pack(f"<{len(self.state)}B", *self.state)
        return hashlib.sha256(data).digest()
