"""
ephemeral_isa.py

Purpose:
Generates seeded, shuffled opcode and operand maps so each build uses
a different physical encoding for the VM ISA. Provides bytecode remapping,
C-level dispatch table generation, runtime ISA derivation from entropy
seeds, rekeying support, and self-mutating ISA mode selection.

Architectural Role:
Build diversity layer. Ensures that every compilation produces a unique
physical encoding of the same logical VM ISA. Defines the core building
blocks for the ephemeral VM pipeline.

Security Relevance:
- Per-build seeded shuffling of opcode and operand mappings means that
  static analysis of one build does not transfer to another.
- Fisher-Yates shuffle with SHA-256 PRNG ensures the shuffle is
  deterministic from the seed but indistinguishable from random without it.
- runtime_derive_isa() and runtime_collect_entropy() provide the Python
  equivalent of the C runtime ISA derivation, enabling testing and
  validation of the same algorithms used in the final binary.
- vm_rekey_seed() implements the rekeying primitive:
    new_seed = SHA-256(current_seed || epoch || basic_block_hash)
  where bb_hash is a rolling hash of executed bytes. This couples the
  cryptographically-derived ISA to the execution path.
- Self-mutating ISA support: dispatch mode selection (switch/indirect/
  computed_goto), encoding mode selection (fixed/variable/field_shuffle),
  field permutation generation, and handler order shuffling via
  seeded Fisher-Yates.

Threat model: Cross-build comparison, static disassembly, precomputed
dispatch tables, automated deobfuscation tools.

Key design decisions:
- Physical opcode 255 always maps to logical opcode 255 (REKEY). This
  ensures the rekey instruction is always reachable regardless of the
  shuffle.
- field_shuffle encoding permutes operand bytes, requiring the interpreter
  to know the permutation to read operands correctly. The permutation
  is epoch-specific and seed-derived.
"""

from __future__ import annotations
import hashlib
import struct


_OPERAND_VALUE_SIZES = {
    0: 1,  # IMM8
    1: 2,  # IMM16
    2: 4,  # IMM32
    3: 8,  # IMM64
    4: 1,  # REG
    5: 1,  # REG_INDIRECT
    6: 2,  # REL_OFFSET
    7: 4,  # ABS_ADDR
}


_OPCODE_OPERAND_COUNTS: dict[int, int] = {
    0: 0,   # NOP
    1: 2,   # ADD
    2: 2,   # SUB
    3: 2,   # MUL
    4: 2,   # DIV
    5: 2,   # MOD
    6: 2,   # AND
    7: 2,   # OR
    8: 2,   # XOR
    9: 1,   # NOT
    10: 2,  # SHL
    11: 2,  # SHR
    12: 2,  # LOAD
    13: 2,  # STORE
    14: 2,  # MOV
    15: 2,  # LEA
    16: 1,  # JMP
    17: 1,  # JZ
    18: 1,  # JNZ
    19: 1,  # JG
    20: 1,  # JL
    21: 1,  # JGE
    22: 1,  # JLE
    23: -1, # CALL (variable)
    24: -1, # RET  (variable)
    25: 1,  # PUSH
    26: 1,  # POP
    27: 1,  # ENTER
    28: 0,  # LEAVE
    29: 3,  # ENC_LOAD
    30: 3,  # ENC_STORE
    31: 3,  # ENC_ADD
    32: 3,  # ENC_MUL
    33: 3,  # FUSED_LOAD_ADD_STORE
    34: 3,  # FUSED_CMP_JMP
}


def _seeded_shuffle(seed: bytes, n: int) -> list[int]:
    """
    Fisher-Yates shuffle of indices [0..n-1] keyed by SHA-256 PRNG.

    The PRNG state is advanced by SHA-256(state) at each step.
    The Fisher-Yates algorithm produces a uniformly random permutation
    where each of the n! permutations is equally likely (assuming the
    PRNG is indistinguishable from random).

    Security note: If the seed is known, the entire permutation is
    deterministic. The seed must be high-entropy and kept secret.
    """
    indices = list(range(n))
    state = hashlib.sha256(seed).digest()
    for i in range(n - 1, 0, -1):
        state = hashlib.sha256(state).digest()
        j = struct.unpack('<I', state[:4])[0] % (i + 1)
        indices[i], indices[j] = indices[j], indices[i]
    return indices


def generate_ephemeral_opcode_map(
    build_seed: bytes,
    num_opcodes: int = 256,
) -> dict[int, int]:
    """
    Generate a seeded, shuffled opcode mapping.

    The seed is SHA-256(b"opcode:" + build_seed). The shuffle produces
    a bijection over [0..num_opcodes). Returns {logical: physical}.

    num_opcodes=256 covers the full byte range. Fewer opcodes may be
    used for testing.
    """
    seed = b"opcode:" + build_seed
    shuffled = _seeded_shuffle(seed, num_opcodes)
    return {i: shuffled[i] for i in range(num_opcodes)}


def generate_ephemeral_operand_map(
    build_seed: bytes,
    num_operand_types: int = 8,
) -> dict[int, int]:
    """
    Generate a seeded, shuffled operand type mapping.

    The seed is SHA-256(b"operand:" + build_seed). Returns
    {logical_type: physical_type}.

    num_operand_types=8 covers the full VMOperand range (0-7).
    """
    seed = b"operand:" + build_seed
    shuffled = _seeded_shuffle(seed, num_operand_types)
    return {i: shuffled[i] for i in range(num_operand_types)}


def _read_operand_entry(
    bytecode: bytes,
    pos: int,
    operand_map: dict[int, int] | None,
    reverse: bool = False,
) -> tuple[int, bytearray]:
    """
    Read and optionally remap a single operand entry from bytecode.

    An operand entry consists of a type byte followed by value bytes
    (size determined by _OPERAND_VALUE_SIZES). If operand_map is
    provided, the type byte is remapped (or inverse-remapped if
    reverse=True).

    Returns (new_position, entry_bytes) where entry_bytes includes
    the type byte and value bytes.
    """
    typ = bytecode[pos]
    phys_typ = operand_map.get(typ, typ) if operand_map else typ
    logical_typ = phys_typ if reverse else typ
    val_size = _OPERAND_VALUE_SIZES.get(logical_typ, 1)
    end = pos + 1 + val_size
    if end > len(bytecode):
        end = len(bytecode)
        val_size = end - pos - 1
    buf = bytearray([phys_typ & 0xFF])
    buf.extend(bytecode[pos + 1:end])
    return end, buf


def remap_bytecode(
    bytecode: bytes,
    opcode_map: dict[int, int],
    operand_map: dict[int, int] | None = None,
    *,
    reverse: bool = False,
) -> bytes:
    """
    Remap bytecode opcodes and operands from logical to physical (or
    physical to logical if reverse=True).

    Iterates through the bytecode, mapping each opcode byte through
    opcode_map, then reading and remapping each operand based on the
    operand count from _OPCODE_OPERAND_COUNTS.

    For variable-length instructions (count=-1, like CALL/RET), reads
    operands until the end of the bytecode if operand_map is provided,
    or copies the remainder verbatim if not.

    Security note: This is used build-time to transform bytecode from
    logical encoding to physical encoding. The reverse transform is
    used by the runtime ISA derivation.
    """
    buf = bytearray()
    i = 0
    while i < len(bytecode):
        raw_byte = bytecode[i]
        mapped_byte = opcode_map.get(raw_byte, raw_byte)
        buf.append(mapped_byte & 0xFF)
        i += 1

        logical_op = raw_byte if raw_byte in _OPCODE_OPERAND_COUNTS else mapped_byte
        if logical_op not in _OPCODE_OPERAND_COUNTS:
            logical_op = 0
        num_operands = _OPCODE_OPERAND_COUNTS.get(logical_op, 0)

        if num_operands >= 0:
            for _ in range(num_operands):
                if i >= len(bytecode):
                    break
                i, entry = _read_operand_entry(bytecode, i, operand_map, reverse)
                buf.extend(entry)
        else:
            if operand_map is not None:
                while i < len(bytecode):
                    if i >= len(bytecode):
                        break
                    i, entry = _read_operand_entry(bytecode, i, operand_map, reverse)
                    buf.extend(entry)
            else:
                buf.extend(bytecode[i:])
                i = len(bytecode)

    return bytes(buf)


def generate_interpreter_dispatch_table(
    opcode_map: dict[int, int],
    build_seed: bytes,
    seed: int | None = None,
) -> bytes:
    """
    Generate a C dispatch table for the ephemeral interpreter.

    The table is 256 bytes. Each physical opcode slot contains the
    logical opcode XOR'ed with a key byte derived from the build seed.
    The key is (seed & 0xFF) or 42 if seed is None.

    Security note: The XOR obfuscation is minimal. An attacker with
    access to the binary can extract the table and XOR each entry
    with the key to recover the logical opcodes. The primary value
    is preventing simple byte-level pattern matching.
    """
    key = (seed & 0xFF) if seed is not None else 42
    table = bytearray(256)
    for logical, physical in opcode_map.items():
        if 0 <= physical < 256:
            table[physical] = (logical ^ key) & 0xFF
    return bytes(table)


def runtime_derive_isa(entropy_seed: bytes) -> list[int]:
    """
    Derive a 256-entry opcode mapping from a 32-byte entropy seed.

    This is the Python equivalent of vm_derive_isa() in vm_stub.c.
    Uses Fisher-Yates shuffle keyed by SHA-256 PRNG. Physical opcode
    255 always maps to logical 255 (REKEY) to ensure the rekey
    instruction is always accessible.

    Security note: The shuffle is deterministic from the entropy seed.
    The seed must be derived from a secure source at runtime (see
    runtime_collect_entropy).
    """
    mapping = list(range(256))
    state = entropy_seed
    for i in range(254, 0, -1):
        state = hashlib.sha256(state).digest()
        j = state[0] % (i + 1)
        mapping[i], mapping[j] = mapping[j], mapping[i]
    mapping[255] = 255
    return mapping


def runtime_collect_entropy() -> bytes:
    """
    Collect system entropy (32 bytes) for runtime ISA seed derivation.

    Python equivalent of the C runtime entropy collector. Sources:
    - /proc/self/maps (memory layout)
    - /proc/self/status (process state)
    - time.time_ns() and time.monotonic_ns()
    - os.getpid()
    - socket.gethostname()
    - os.urandom(32) (cryptographic entropy)

    All sources are fed into a SHA-256 context for a 32-byte digest.

    Security note: The /proc entries are adversary-readable in some
    configurations. os.urandom(32) provides the cryptographic entropy;
    the other sources add variability beyond what urandom alone provides.
    """
    import os
    import time
    import socket

    ctx = hashlib.sha256()

    try:
        with open("/proc/self/maps", "rb") as f:
            ctx.update(f.read(4096))
    except (IOError, OSError):
        pass

    try:
        with open("/proc/self/status", "rb") as f:
            ctx.update(f.read(4096))
    except (IOError, OSError):
        pass

    ctx.update(struct.pack('<QQ', time.time_ns(), time.monotonic_ns()))
    ctx.update(struct.pack('<I', os.getpid()))
    try:
        ctx.update(socket.gethostname().encode())
    except OSError:
        pass
    ctx.update(os.urandom(32))

    return ctx.digest()


def vm_rekey_seed(current_seed: bytes, epoch: int, bb_hash: int) -> bytes:
    """
    Derive a new entropy seed for a VM rekey operation.

    new_seed = SHA-256(current_seed || epoch (32-bit LE) || bb_hash (64-bit LE))

    The bb_hash parameter is a rolling hash of all executed bytes since
    the last rekey. This ties the new ISA to the specific execution path,
    making it impossible to precompute the post-rekey state without
    executing the same path.

    Security note: If current_seed is compromised, an attacker can
    compute future seeds for known (epoch, bb_hash) pairs. The bb_hash
    provides path-dependent protection, but the seed must be protected.
    """
    ctx = hashlib.sha256()
    ctx.update(current_seed)
    ctx.update(struct.pack('<I', epoch))
    ctx.update(struct.pack('<Q', bb_hash))
    return ctx.digest()


# ── Self-Mutating Runtime ISA support ─────────────────────────────────


DISPATCH_MODES = ["switch", "indirect", "computed_goto"]
ENCODING_MODES = ["fixed", "variable", "field_shuffle"]


def _seeded_choice(seed: bytes, options: list) -> int:
    """
    Deterministically select an index from a list of options using a seed.

    Returns the index (not the value). The selection uses the first
    4 bytes of SHA-256(seed) as the random value.
    """
    h = hashlib.sha256(seed).digest()
    idx = struct.unpack('<I', h[:4])[0] % len(options)
    return idx


def select_dispatch_mode(seed: bytes, epoch: int = 0) -> str:
    """
    Select a dispatch mode (switch, indirect, computed_goto) based on
    SHA-256(seed || epoch || "dispatch").

    The choice is deterministic from the seed and epoch, but varies
    across epochs. The three modes provide increasing levels of
    indirection:
    - switch: direct lookup (fastest, easiest to reverse).
    - indirect: lookup through shuffled dispatch table.
    - computed_goto: compute handler index from opcode and epoch.
    """
    ctx = hashlib.sha256(seed)
    ctx.update(struct.pack('<I', epoch))
    ctx.update(b"dispatch")
    derived = ctx.digest()
    idx = _seeded_choice(derived, DISPATCH_MODES)
    return DISPATCH_MODES[idx]


def select_encoding_mode(seed: bytes, epoch: int = 0) -> str:
    """
    Select an encoding mode (fixed, variable, field_shuffle) based on
    SHA-256(seed || epoch || "encoding").

    The three modes:
    - fixed: opcode byte + fixed-width operand bytes (fast, easy to parse).
    - variable: length-prefixed instruction (harder to parse statically).
    - field_shuffle: opcode + permuted operand bytes (requires permutation).
    """
    ctx = hashlib.sha256(seed)
    ctx.update(struct.pack('<I', epoch))
    ctx.update(b"encoding")
    derived = ctx.digest()
    idx = _seeded_choice(derived, ENCODING_MODES)
    return ENCODING_MODES[idx]


def generate_field_permutation(seed: bytes, num_bytes: int = 16) -> list[int]:
    """
    Generate a permutation of indices [0..num_bytes) for field shuffle encoding.

    Uses Fisher-Yates keyed by SHA-256 PRNG (same as _seeded_shuffle).
    The permutation determines how operand bytes are scrambled before
    emission and unshuffled before consumption.
    """
    perm = list(range(num_bytes))
    state = seed
    for i in range(num_bytes - 1, 0, -1):
        state = hashlib.sha256(state).digest()
        j = state[0] % (i + 1)
        perm[i], perm[j] = perm[j], perm[i]
    return perm


def shuffle_handler_order(seed: bytes, handlers: list) -> list:
    """
    Shuffle a list of handler entries using Fisher-Yates keyed by seed.

    Used to vary the order in which handlers appear in the dispatch
    table, making the binary layout unpredictable.
    """
    shuffled = list(handlers)
    n = len(shuffled)
    state = seed
    for i in range(n - 1, 0, -1):
        state = hashlib.sha256(state).digest()
        j = state[0] % (i + 1)
        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
    return shuffled


OPCODE_OPERAND_BYTES: dict[int, int] = {
    0: 0,   # NOP
    1: 2,   # ADD  (dst, src)
    2: 2,   # SUB
    3: 2,   # MUL
    4: 2,   # DIV
    5: 2,   # MOD
    6: 2,   # AND
    7: 2,   # OR
    8: 2,   # XOR
    9: 1,   # NOT
    10: 2,  # SHL
    11: 2,  # SHR
    12: 2,  # LOAD
    13: 2,  # STORE
    14: 3,  # MOV  (dst, lo, hi)
    15: 2,  # LEA
    16: 4,  # JMP
    17: 4,  # JZ
    18: 4,  # JNZ
    19: 4,  # JG
    20: 4,  # JL
    21: 4,  # JGE
    22: 4,  # JLE
    23: 4,  # CALL
    24: 0,  # RET
    25: 1,  # PUSH
    26: 1,  # POP
    27: 3,  # ENTER (reg, lo, hi)
    28: 0,  # LEAVE
    29: 3,  # ENC_LOAD (dst, addr, key)
    30: 3,  # ENC_STORE
    31: 3,  # ENC_ADD  (dst, src, key_byte)
    32: 3,  # ENC_MUL
    33: 3,  # FUSED_LOAD_ADD_STORE
    34: 9,  # FUSED_CMP_JMP (reg, u32, u32)
    255: 0, # REKEY
}


def apply_field_shuffle(data: bytes, perm: list[int]) -> bytes:
    """
    Apply a field permutation to operand bytes: result[i] = data[perm[i]].

    This scrambles the byte order of operand data according to the
    permutation. The permutation must match what generate_field_permutation
    produced for the same seed/epoch.
    """
    n = len(data)
    result = bytearray(n)
    for i in range(n):
        src_idx = perm[i] if i < len(perm) else i
        result[i] = data[src_idx % n] if src_idx < n else data[i]
    return bytes(result)


def apply_field_unshuffle(data: bytes, perm: list[int]) -> bytes:
    """
    Apply the inverse of a field permutation: result[perm[i]] = data[i].

    This restores the original byte order after apply_field_shuffle.
    The permutation must be the same one used for the forward transform.
    """
    n = len(data)
    result = bytearray(n)
    for i in range(n):
        src_idx = perm[i] if i < len(perm) else i
        if src_idx < n:
            result[src_idx] = data[i]
        else:
            result[i] = data[i]
    return bytes(result)


def encode_instruction(
    opcode: int,
    operands: bytes,
    encoding_mode: str,
    field_perm: list[int] | None = None,
) -> bytes:
    """
    Encode a single instruction in the specified encoding mode.

    Modes:
    - fixed: [opcode_byte][operand_bytes]
    - variable: [total_length][opcode_byte][operand_bytes]
    - field_shuffle: [opcode_byte][shuffled_operand_bytes]

    The field_perm is required for field_shuffle mode to determine
    the byte permutation.
    """
    if encoding_mode == "fixed":
        return bytes([opcode]) + operands
    elif encoding_mode == "variable":
        total_len = 1 + 1 + len(operands)
        return bytes([total_len, opcode]) + operands
    elif encoding_mode == "field_shuffle":
        shuffled = apply_field_shuffle(operands, field_perm or list(range(len(operands))))
        return bytes([opcode]) + shuffled
    return bytes([opcode]) + operands


def decode_instruction_length(
    bytecode: bytes,
    pc: int,
    encoding_mode: str,
    logical_opcode: int,
    field_perm: list[int] | None = None,
) -> tuple[int, bytes]:
    """
    Decode an instruction at PC and return (bytes_consumed, operand_bytes).

    Modes:
    - fixed: opcode at pc, n_op operand bytes from OPCODE_OPERAND_BYTES.
    - variable: length byte at pc, opcode at pc+1, operands follow.
    - field_shuffle: opcode at pc, then read n_op permuted operand bytes
      and unshuffle them.

    The logical_opcode is used to look up the expected operand byte count
    from OPCODE_OPERAND_BYTES.
    """
    if pc >= len(bytecode):
        return 0, b""

    if encoding_mode == "fixed":
        opcode = bytecode[pc]
        n_op = OPCODE_OPERAND_BYTES.get(logical_opcode, 0)
        end = pc + 1 + n_op
        consumed = min(end, len(bytecode)) - pc
        operand_data = bytecode[pc + 1:pc + 1 + n_op] if n_op > 0 else b""
        return consumed, operand_data

    elif encoding_mode == "variable":
        if pc + 1 >= len(bytecode):
            return 1, b""
        total_len = bytecode[pc]
        if total_len < 2:
            return 1, b""
        end = pc + total_len
        cap_end = min(end, len(bytecode))
        op_start = pc + 2
        operand_data = bytecode[op_start:cap_end] if op_start < cap_end else b""
        return cap_end - pc, operand_data

    elif encoding_mode == "field_shuffle":
        n_op = OPCODE_OPERAND_BYTES.get(logical_opcode, 0)
        if pc + 1 + n_op > len(bytecode):
            n_op = len(bytecode) - pc - 1
            if n_op < 0:
                return 1, b""
        shuffled = bytecode[pc + 1:pc + 1 + n_op]
        if field_perm and n_op > 0:
            unshuffled = apply_field_unshuffle(bytes(shuffled), field_perm)
        else:
            unshuffled = bytes(shuffled)
        return 1 + n_op, unshuffled

    return 1 + len(bytecode) - pc - 1, bytecode[pc + 1:]
