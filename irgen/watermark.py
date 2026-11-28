"""
watermark.py

Purpose:
Advanced Protection — IR-Level Watermarking. Embeds customer/build
identifiers into IR control flow graphs using dead-block topology
patterns that survive obfuscation. Uses BCH error-correcting codes
for robustness against bit destruction during compilation.

Architectural Role:
Post-obfuscation marking pass. Inserts watermark blocks into the IR
control flow graph that encode a bit string derived from customer and
build IDs. Watermarks survive LLVM lowering and linking because they
are structurally valid dead code.

Security Relevance:
- Enables forensic tracing of leaked binaries back to the customer.
- Error correction via BCH(255, 20) codes provides resilience against
  compilation-induced bit changes.
- Two watermark patterns: P1 (bit=1) uses dead block with opaque-false
  predicate and realistic code; P0 (bit=0) uses opaque-true predicate
  and constant return.
- Watermark bits are deterministically placed using BLAKE2b-based
  position selection.
- Detection works on lifted IR from compiled binaries via basic block
  pattern analysis.

Threat model: Binary redistribution, forensic linking, code theft attribution.

Dependencies:
    - irgen.compile (IrModule, IrFunction, IrBlock, IrInstruction, IrValue, IrType)
"""

import hashlib
import json
import os
import random
import re
import struct
from typing import Any, Optional

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "default.json"
)
_PHASE2_ENABLED = True
try:
    with open(_CONFIG_PATH) as _f:
        _cfg = json.load(_f)
    _PHASE2_ENABLED = bool(
        _cfg.get("shadow_compiler", {})
        .get("advanced_protection", _cfg.get("shadow_compiler", {}).get("phase2", {}))
        .get("enabled", False)
    )
except Exception:
    pass

from .compile import IrModule, IrFunction, IrBlock, IrInstruction, IrValue, IrType


def _phase2_enabled() -> bool:
    """Check if phase2 (advanced protection) is enabled."""
    return _PHASE2_ENABLED


# ---------------------------------------------------------------------------
# BCH Error-Correcting Code
# ---------------------------------------------------------------------------

class _GF:
    """GF(2^8) with primitive polynomial x^8+x^4+x^3+x^2+1 (0x11D)."""

    def __init__(self):
        """Build log and antilog tables for GF(2^8) arithmetic."""
        self.m = 8
        self.n = 255
        self.poly = 0x11D
        self.log = [0] * 256
        self.alog = [0] * 255
        val = 1
        for i in range(255):
            self.alog[i] = val
            self.log[val] = i
            val <<= 1
            if val & 0x100:
                val ^= self.poly
            val &= 0xFF

    def mul(self, a: int, b: int) -> int:
        """Multiply two elements in GF(2^8)."""
        if a == 0 or b == 0:
            return 0
        return self.alog[(self.log[a] + self.log[b]) % 255]

    def div(self, a: int, b: int) -> int:
        """Divide two elements in GF(2^8)."""
        if a == 0:
            return 0
        if b == 0:
            raise ZeroDivisionError("division by zero in GF(2^8)")
        return self.alog[(self.log[a] - self.log[b]) % 255]

    def inv(self, a: int) -> int:
        """Multiplicative inverse in GF(2^8)."""
        if a == 0:
            return 0
        return self.alog[(255 - self.log[a]) % 255]

    def pow(self, a: int, n: int) -> int:
        """Exponentiation in GF(2^8)."""
        if a == 0:
            return 0
        if n == 0:
            return 1
        return self.alog[(self.log[a] * n) % 255]

    def add(self, a: int, b: int) -> int:
        """Addition in GF(2^8) is XOR."""
        return a ^ b

    def sub(self, a: int, b: int) -> int:
        """Subtraction in GF(2^8) is XOR."""
        return a ^ b

    def eval_poly(self, coeffs: list[int], x: int) -> int:
        """Evaluate a polynomial at point x using Horner's method."""
        r = 0
        for c in reversed(coeffs):
            r = self.mul(r, x) ^ c
        return r


_gf = _GF()


class _Poly:
    """Polynomial over GF(2^8). coeffs[0] = constant term."""

    def __init__(self, coeffs: Optional[list[int]] = None):
        """Initialize with coefficient list (LSB = constant term)."""
        self.coeffs = list(coeffs) if coeffs else [0]
        self._trim()

    def _trim(self):
        """Remove leading zero coefficients."""
        while len(self.coeffs) > 1 and self.coeffs[-1] == 0:
            self.coeffs.pop()

    def deg(self) -> int:
        """Return the degree of the polynomial."""
        return len(self.coeffs) - 1

    def __add__(self, other: "_Poly") -> "_Poly":
        """Polynomial addition (XOR of coefficients)."""
        n = max(len(self.coeffs), len(other.coeffs))
        result = [0] * n
        for i in range(len(self.coeffs)):
            result[i] ^= self.coeffs[i]
        for i in range(len(other.coeffs)):
            result[i] ^= other.coeffs[i]
        return _Poly(result)

    def __sub__(self, other: "_Poly") -> "_Poly":
        """Polynomial subtraction (same as addition in GF(2))."""
        return self.__add__(other)

    def __mul__(self, other: "_Poly") -> "_Poly":
        """Polynomial multiplication."""
        result = [0] * (len(self.coeffs) + len(other.coeffs) - 1)
        for i, a in enumerate(self.coeffs):
            if a == 0:
                continue
            for j, b in enumerate(other.coeffs):
                if b == 0:
                    continue
                result[i + j] ^= _gf.mul(a, b)
        return _Poly(result)

    def __mod__(self, other: "_Poly") -> "_Poly":
        """Polynomial modulo (long division)."""
        r = _Poly(list(self.coeffs))
        while r.deg() >= other.deg():
            shift = r.deg() - other.deg()
            leading = _gf.div(r.coeffs[-1], other.coeffs[-1])
            sub_coeffs = [0] * (shift + 1)
            sub_coeffs[-1] = leading
            sub = _Poly(sub_coeffs) * other
            r = r + sub
        return r

    def __truediv__(self, other: "_Poly") -> "_Poly":
        """Polynomial division."""
        if other.deg() == 0 and other.coeffs[0] == 0:
            raise ZeroDivisionError
        q = _Poly([0])
        r = _Poly(list(self.coeffs))
        while r.deg() >= other.deg() and not (r.deg() == 0 and r.coeffs[0] == 0):
            shift = r.deg() - other.deg()
            leading = _gf.div(r.coeffs[-1], other.coeffs[-1])
            term = [0] * (shift + 1)
            term[-1] = leading
            term_poly = _Poly(term)
            q = q + term_poly
            r = r + term_poly * other
        return q

    def eval(self, x: int) -> int:
        """Evaluate the polynomial at point x."""
        return _gf.eval_poly(self.coeffs, x)

    def copy(self) -> "_Poly":
        """Create a deep copy."""
        return _Poly(list(self.coeffs))


class BCHCode:
    """
    BCH error-correcting code for watermark robustness.

    Encodes data into an error-corrected codeword that can recover
    from bit destruction during compilation and linking. Uses
    BCH(n=255, t=20) with an automatically computed generator
    polynomial.

    The encoding adds parity bits that allow correction of up to
    t bit errors in the codeword.
    """

    def __init__(self, n: int = 255, t: int = 20):
        """
        Initialize BCH code with block length and error correction capability.

        n: Codeword length (default 255 for GF(2^8)).
        t: Number of correctable errors (default 20).
        """
        self.n = n
        self.t = t
        self.gf = _gf
        self.g = self._compute_generator()
        self.k = (n - self.g.deg()) // 8 * 8
        if self.k <= 0:
            self.k = 8

    def _cyclotomic_coset(self, i: int) -> list[int]:
        """
        Compute the cyclotomic coset of i modulo n.

        Cosets group exponents that share the same minimal polynomial.
        """
        coset: list[int] = []
        current = i
        while current not in coset:
            coset.append(current)
            current = (current * 2) % self.n
        return sorted(coset)

    def _minimal_poly(self, i: int) -> _Poly:
        """
        Compute the minimal polynomial for exponent i.

        The minimal polynomial is the product of (x - alpha^c)
        for each c in the cyclotomic coset of i.
        """
        coset = self._cyclotomic_coset(i)
        result = _Poly([1])
        for c in coset:
            factor = _Poly([_gf.alog[c], 1])
            result = result * factor
        return result

    def _compute_generator(self) -> _Poly:
        """
        Compute the BCH generator polynomial.

        The generator is the LCM of minimal polynomials for
        exponents 1, 3, 5, ..., 2t-1. Distinct cyclotomic cosets yield
        distinct irreducible minimal polynomials, which are coprime, so
        multiplying each coset's polynomial ONCE (dedup by coset) gives
        exactly the LCM. The old code multiplied every exponent's minimal
        polynomial, so colliding cosets (e.g. 9 and 33 mod 255) were
        multiplied twice and g no longer divided x^n - 1 -- encode/decode
        failed even with zero errors.
        """
        g = _Poly([1])
        seen_cosets = set()
        for i in range(1, 2 * self.t + 1, 2):
            coset = tuple(self._cyclotomic_coset(i))
            if coset in seen_cosets:
                continue
            seen_cosets.add(coset)
            m = self._minimal_poly(i)
            g = g * m
        return g

    def encode(self, data: bytes, codeword_bits: int = 255) -> bytes:
        """
        Encode data with BCH error correction.

        Pads the data to k bits, computes the systematic codeword
        by dividing x^(n-k) * m(x) by g(x), and returns the
        codeword as bytes.

        Args:
            data: Input bytes to encode.
            codeword_bits: Length of codeword in bits.

        Returns:
            BCH-encoded codeword bytes.
        """
        if not data:
            return b""

        data_bit_count = len(data) * 8
        max_data_bits = self.k
        if data_bit_count > max_data_bits:
            raise ValueError(
                f"data exceeds BCH capacity of {max_data_bits // 8} bytes")

        bits: list[int] = []
        for byte in data:
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)

        bits = bits[: self.k]
        while len(bits) < self.k:
            bits.append(0)

        m_poly = _Poly([0])
        for i, b in enumerate(bits):
            if b:
                m_poly = m_poly + _Poly([0] * (len(bits) - 1 - i) + [1])

        # m_poly.coeffs must be exactly k long: bit i lives at power k-1-i,
        # so leading zero bits would otherwise shift the whole message down
        # and misalign the codeword (roundtrip failed even at zero errors).
        mc = list(m_poly.coeffs)
        if len(mc) < self.k:
            mc += [0] * (self.k - len(mc))
        padded = _Poly([0] * (self.n - self.k) + mc)
        rem = padded % self.g
        codeword = padded + rem

        codeword_bytes = bytearray((codeword_bits + 7) // 8)
        for i, c in enumerate(codeword.coeffs):
            if c:
                byte_idx = i // 8
                bit_idx = 7 - (i % 8)
                if byte_idx < len(codeword_bytes):
                    codeword_bytes[byte_idx] |= 1 << bit_idx

        return bytes(codeword_bytes)

    def decode(
        self, codeword: bytes, data_bits: int
    ) -> bytes:
        """
        Decode and correct errors in a BCH codeword.

        Uses the Berlekamp-Massey algorithm for error-locator
        polynomial and Chien search for finding error positions.

        Args:
            codeword: The received codeword bytes.
            data_bits: Number of data bits to extract.

        Returns:
            Corrected data bytes.
        """
        if not 0 <= data_bits <= self.k:
            raise ValueError("data_bits exceeds BCH capacity")
        if len(codeword) * 8 < self.n:
            raise ValueError("truncated BCH codeword")

        bits: list[int] = []
        for byte in codeword:
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)
        bits = bits[: self.n]

        def compute_syndromes() -> list[int]:
            return [
                self.gf.eval_poly(bits, _gf.alog[i])
                for i in range(1, 2 * self.t + 1)
            ]

        syndromes = compute_syndromes()
        if any(s != 0 for s in syndromes):
            err_loc = self._berlekamp_massey(syndromes)
            degree = err_loc.deg()
            error_positions = self._chien_search(err_loc)
            if (degree <= 0 or degree > self.t
                    or len(error_positions) != degree
                    or len(error_positions) > self.t
                    or any(pos >= self.n for pos in error_positions)):
                raise ValueError("uncorrectable BCH codeword")
            for pos in error_positions:
                bits[pos] ^= 1
            # A locator with the right degree is not enough: reject a word
            # unless every syndrome is zero after correction.
            if any(s != 0 for s in compute_syndromes()):
                raise ValueError("uncorrectable BCH codeword")

        result_bytes = bytearray((data_bits + 7) // 8)
        for i in range(data_bits):
            src_idx = self.n - 1 - i
            if src_idx < len(bits) and bits[src_idx]:
                byte_idx = i // 8
                bit_idx = 7 - (i % 8)
                if byte_idx < len(result_bytes):
                    result_bytes[byte_idx] |= 1 << bit_idx
        return bytes(result_bytes)

    def _berlekamp_massey(
        self, syndromes: list[int]
    ) -> _Poly:
        """
        Berlekamp-Massey algorithm for finding the error-locator
        polynomial from syndrome values.
        """
        Lambda = _Poly([1])
        B = _Poly([1])
        L = 0
        m = 1
        b = 1  # previous non-zero discrepancy

        for r in range(1, len(syndromes) + 1):
            d = syndromes[r - 1]
            for i in range(1, L + 1):
                if i < len(Lambda.coeffs):
                    d ^= _gf.mul(
                        Lambda.coeffs[i], syndromes[r - 1 - i]
                    )

            if d == 0:
                m += 1
            else:
                T = Lambda.copy()
                shift_poly = _Poly([0] * m + B.coeffs)
                # scale by d / b (NOT d alone -- the old code used inv(d)
                # and never tracked b, so the locator was wrong whenever
                # errors were present).
                scale = _gf.mul(_gf.inv(b), d)
                scaled_shift = _Poly(
                    [_gf.mul(scale, c) for c in shift_poly.coeffs]
                )
                Lambda = Lambda + scaled_shift

                if 2 * L <= r:
                    B = T
                    L = r - L
                    b = d
                    m = 1
                else:
                    m += 1

        return Lambda

    def _chien_search(self, Lambda: _Poly) -> list[int]:
        """
        Chien search: evaluate the error-locator polynomial at
        every non-zero element of GF(2^8) to find error positions.
        """
        positions: list[int] = []
        for k in range(self.n):
            # Error at bit position k (power k) puts a locator root at
            # x = alpha^(-k); evaluate at alog[(-k) mod n].
            power = (-k) % self.n
            if Lambda.eval(_gf.alog[power]) == 0:
                positions.append(k)
        return positions


# ---------------------------------------------------------------------------
# Watermark Generator
# ---------------------------------------------------------------------------

def generate_watermark(
    customer_id: bytes,
    build_id: bytes,
    error_correct: bool = True,
) -> tuple[bytes, dict[str, Any]]:
    """
    Generate watermark bit string from customer and build identifiers.

    Combines identifiers via BLAKE2b, then optionally applies BCH
    error correction to produce a robust watermark.

    Returns:
        (watermark_bytes, metadata) where metadata contains:
        - bits: the raw bit string
        - encoded: error-corrected version
        - patterns: which IR block patterns to use per bit
    """
    if not _PHASE2_ENABLED:
        raise RuntimeError("Advanced Protection must be enabled for watermark generation")

    combined = hashlib.blake2b(
        customer_id + build_id, digest_size=32
    ).digest()
    bch = BCHCode(n=255, t=20)
    payload = combined[: bch.k // 8]

    raw_bits: list[int] = []
    for byte in payload:
        for i in range(7, -1, -1):
            raw_bits.append((byte >> i) & 1)

    if error_correct:
        encoded = bch.encode(payload)
    else:
        encoded = payload
    encoded_bits: list[int] = []
    for byte in encoded:
        for i in range(7, -1, -1):
            encoded_bits.append((byte >> i) & 1)
    if error_correct:
        encoded_bits = encoded_bits[:bch.n]

    patterns: dict[int, str] = {}
    rand = random.Random(hashlib.blake2b(build_id).digest())
    for i in range(len(encoded_bits)):
        patterns[i] = f"pat_{rand.randint(0, 0xFFFF):04x}"

    metadata: dict[str, Any] = {
        "bits": raw_bits,
        "encoded": encoded_bits,
        "patterns": patterns,
        "bch_used": error_correct,
        "bit_count": len(encoded_bits),
        "data_bits": len(payload) * 8,
        "capacity_bytes": bch.k // 8,
        "build_seed": build_id.hex(),
    }

    return encoded, metadata


# ---------------------------------------------------------------------------
# Opaque Predicate Helpers
# ---------------------------------------------------------------------------

def _make_opaque_predicate(
    block: IrBlock,
    always_true: bool,
    rand: random.Random,
) -> IrInstruction:
    """
    Insert an opaque predicate that always evaluates to the desired
    truth value.

    Uses MBA expressions with random constants so the predicate is
    hard to analyze statically.
    """
    a_val = rand.randint(1, 1000)
    b_val = rand.randint(1, 1000)

    const_a = IrValue.const_int(a_val)
    const_b = IrValue.const_int(b_val)

    cmp = block.eq(IrType.i32(), const_a, const_b)

    # (a == b) OR (a != b) is always true; ANDing the same complementary
    # pair is always false.  The previous false predicate computed
    # ``(cmp != 0) xor 1``, which is true exactly when cmp is false -- the
    # opposite of its contract for the unequal random constants normally
    # generated here.
    neq = block.ne(IrType.i32(), const_a, const_b)
    if always_true:
        return block.or_(IrType.i1(), cmp.result, neq.result)
    return block.and_(IrType.i1(), cmp.result, neq.result)


_DEFAULT_BUILD_SEED = bytes(16)
_WATERMARK_LABEL_RE = re.compile(
    r"^_wm_([0-9a-f]{16})_([01])_(\d+)_([01])_([0-9a-f]{8})$")


def _coerce_build_seed(value: Any) -> bytes:
    if value is None:
        return _DEFAULT_BUILD_SEED
    if isinstance(value, bytes):
        return value
    if isinstance(value, (bytearray, memoryview)):
        return bytes(value)
    if isinstance(value, str):
        return value.encode()
    return str(value).encode()


def _watermark_sequence_id(func_name: str, seed: bytes, bch_used: bool) -> str:
    digest = hashlib.blake2b(b"nixon-ir-watermark-v1", digest_size=8)
    digest.update(seed)
    digest.update(b"\0")
    digest.update(func_name.encode())
    digest.update(b"\1" if bch_used else b"\0")
    return digest.hexdigest()


def _watermark_marker_tag(sequence_id: str, seed: bytes, index: int,
                          bit: int, bch_used: bool) -> str:
    digest = hashlib.blake2b(b"nixon-ir-watermark-bit-v1", digest_size=4)
    digest.update(seed)
    digest.update(bytes.fromhex(sequence_id))
    digest.update(index.to_bytes(4, "big"))
    digest.update(bytes((bit, 1 if bch_used else 0)))
    return digest.hexdigest()


def _make_watermark_block(
    func: IrFunction,
    pattern_type: str,
    bit_val: int,
    rand: random.Random,
    label: Optional[str] = None,
) -> IrBlock:
    """
    Create a watermark block with the specified pattern.

    Pattern P1 (bit=1): dead block with opaque-false predicate,
    contains realistic code (arithmetic + memory ops).
    Pattern P0 (bit=0): dead block with opaque-true predicate,
    returns constant.

    Both patterns are structurally valid but unreachable at runtime.
    """
    block = func.new_block(
        label=label or f"_wm_{pattern_type}_{bit_val}_{rand.randint(0, 0xFFFF):04x}")

    local_var = block.alloca(IrType.i32())
    const_zero = IrValue.const_int(0)
    block.store(IrType.i32(), const_zero, local_var.result)

    const_val = IrValue.const_int(rand.randint(0, 0xFFFFFF))
    block.store(IrType.i32(), const_val, local_var.result)

    loaded = block.load(IrType.i32(), local_var.result)

    if bit_val == 1:
        x_val = IrValue.const_int(rand.randint(1, 100))
        y_val = IrValue.const_int(rand.randint(1, 100))
        block.add(IrType.i32(), loaded.result, x_val)
        block.sub(IrType.i32(), loaded.result, y_val)
        block.mul(IrType.i32(), x_val, y_val)
        predicate = _make_opaque_predicate(block, False, rand)
    else:
        # No arithmetic here: the detector classifies a block as bit=1 by the
        # presence of add/sub/mul/div, so a P0 block that added anything
        # would decode as a 1.
        predicate = _make_opaque_predicate(block, True, rand)

    pred_cond = predicate.result

    dead_block = func.new_block(label=f"_wm_dead_{rand.randint(0, 0xFFFF):04x}")
    dead_val = IrValue.const_int(rand.randint(0, 0xFFFFFF))
    # The IR's ret format is `ret <type> <value>`; dropping the type
    # operand made IrInstruction.__str__ raise IndexError.
    dead_block.set_terminator("ret", operands=[IrType.i32(), dead_val])

    # Both targets start out dead. The embedder repoints the taken edge at
    # the block that follows the watermark block once it knows the position;
    # branching to block.label here made the block its own successor.
    block.set_terminator(
        "br",
        operands=[
            pred_cond,
            dead_block.label,
            dead_block.label,
        ],
    )

    return block


# ---------------------------------------------------------------------------
# Watermark Embedder
# ---------------------------------------------------------------------------

def embed_watermark(
    ir_module: IrModule,
    watermark: bytes,
    metadata: dict[str, Any],
) -> IrModule:
    """
    Embed watermark into IR control flow graph.

    For each bit in watermark:
    - 1: insert basic block with pattern P1 (dead block, opaque-false,
         realistic code).
    - 0: insert basic block with pattern P0 (dead block, opaque-true,
         constant return).

    Blocks are inserted at positions determined by BLAKE2b hashing
    of the bit index and build seed.
    """
    if not _PHASE2_ENABLED:
        return ir_module

    encoded_bits = list(metadata.get("encoded", []))
    if not encoded_bits:
        for byte in watermark:
            for i in range(7, -1, -1):
                encoded_bits.append((byte >> i) & 1)
    if any(bit not in (0, 1) for bit in encoded_bits):
        raise ValueError("watermark bits must be 0 or 1")

    # One canonical sequence per module.  Repeating the payload in every
    # function made detection concatenate duplicate watermarks.
    func = next((candidate for candidate in ir_module.functions
                 if candidate.blocks), None)
    if func is None or not encoded_bits:
        return ir_module

    patterns = metadata.get("patterns", {})
    build_seed = _coerce_build_seed(metadata.get("build_seed"))
    bch_used = bool(metadata.get("bch_used", False))
    sequence_id = _watermark_sequence_id(func.name, build_seed, bch_used)
    build_seed_val = hashlib.sha256(build_seed).digest()

    rand = random.Random(
        hashlib.blake2b(build_seed_val + watermark).digest()
    )

    for bit_idx, bit_val in enumerate(encoded_bits):
        pattern_key = patterns.get(bit_idx, f"bit_{bit_idx}")
        tag = _watermark_marker_tag(
            sequence_id, build_seed, bit_idx, bit_val, bch_used)
        label = f"_wm_{sequence_id}_{int(bch_used)}_{bit_idx}_{bit_val}_{tag}"
        _make_watermark_block(func, pattern_key, bit_val, rand, label=label)

        insert_pos = (
            int.from_bytes(
                hashlib.blake2b(
                    struct.pack(">I", bit_idx) + build_seed_val,
                    digest_size=4,
                ).digest(),
                "little",
            )
            % len(func.blocks)
        )

        if insert_pos < len(func.blocks):
            last = func.blocks.pop()
            func.blocks.insert(insert_pos, last)
            # Point the taken edge at the block that now follows, so the
            # watermark block is not its own successor.
            if insert_pos + 1 < len(func.blocks):
                target = func.blocks[insert_pos + 1].label
            else:
                target = func.blocks[0].label
            term = last.terminator
            if term is not None and term.opcode == "br" and len(term.operands) >= 3:
                term.operands[1] = target

    return ir_module


# ---------------------------------------------------------------------------
# Watermark Detector
# ---------------------------------------------------------------------------

def detect_watermark(
    ir_module: IrModule, build_seed: bytes
) -> Optional[bytes]:
    """
    Detect watermark in an IR module.

    Recovers the bit string by analyzing block topology patterns.
    Looks for blocks with _wm_ prefix and analyzes their internal
    structure to classify as P1 (bit=1, has arithmetic) or P0
    (bit=0, no arithmetic).

    Returns recovered watermark bytes, or None if insufficient
    watermark blocks are found.
    """
    if not _PHASE2_ENABLED:
        return None

    seed = _coerce_build_seed(build_seed)
    candidates: list[tuple[int, str, bool, int, int]] = []
    for func_index, func in enumerate(ir_module.functions):
        expected_sequences = {
            bch_used: _watermark_sequence_id(func.name, seed, bch_used)
            for bch_used in (False, True)
        }
        for block in func.blocks:
            match = _WATERMARK_LABEL_RE.match(block.label)
            if not match:
                continue
            sequence_id, ecc_text, index_text, bit_text, tag = match.groups()
            bch_used = ecc_text == "1"
            index, bit = int(index_text), int(bit_text)
            if sequence_id != expected_sequences[bch_used]:
                continue
            if tag != _watermark_marker_tag(
                    sequence_id, seed, index, bit, bch_used):
                continue
            if not (block.terminator and block.terminator.opcode == "br"
                    and len(block.terminator.operands) >= 3):
                continue
            has_alloca = any(inst.opcode == "alloca" for inst in block.instructions)
            has_load = any(inst.opcode == "load" for inst in block.instructions)
            has_arithmetic = any(
                inst.opcode in ("add", "sub", "mul", "div")
                for inst in block.instructions)
            if not (has_alloca and has_load) or int(has_arithmetic) != bit:
                continue
            candidates.append((func_index, sequence_id, bch_used, index, bit))

    if not candidates:
        return None
    sequences = {(func_index, sequence_id, bch_used)
                 for func_index, sequence_id, bch_used, _index, _bit in candidates}
    # Duplicate payloads or mixed watermark generations are ambiguous rather
    # than a longer canonical sequence.
    if len(sequences) != 1:
        return None

    candidates.sort(key=lambda item: item[3])
    indices = [item[3] for item in candidates]
    if indices != list(range(len(candidates))):
        return None
    recovered_bits = [item[4] for item in candidates]
    bch_used = candidates[0][2]
    if not bch_used and len(recovered_bits) % 8:
        return None

    codeword = bytearray((len(recovered_bits) + 7) // 8)
    for i, bit in enumerate(recovered_bits):
        if bit:
            codeword[i // 8] |= 1 << (7 - (i % 8))
    if bch_used:
        bch = BCHCode(n=255, t=20)
        if len(recovered_bits) != bch.n:
            raise ValueError("invalid BCH watermark length")
        return bch.decode(bytes(codeword), bch.k)
    return bytes(codeword)


# ---------------------------------------------------------------------------
# Binary Watermark Detector
# ---------------------------------------------------------------------------

def detect_watermark_from_binary(
    binary_path: str, build_seed: bytes
) -> Optional[bytes]:
    """Detect a watermark in a compiled binary.

    NOT IMPLEMENTED. Recovering the watermark requires lifting machine code
    back to IR with the watermark block's alloca/load/arithmetic pattern. The
    old implementation fabricated empty 16-byte blocks with `jmp` terminators;
    detect_watermark only classifies blocks with `br` terminators and real
    instructions, so it always returned None. Fail loudly instead of reporting
    a false negative. Use `detect` on the IR for a real check.
    """
    raise NotImplementedError(
        "binary watermark detection requires a machine-code lifter; "
        "run `detect` on the IR instead"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    """CLI entry point for watermarking tool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Nixon IR Watermarking Tool"
    )
    sub = parser.add_subparsers(dest="command")

    gen_p = sub.add_parser("gen", help="Generate watermark")
    gen_p.add_argument(
        "--customer-id", required=True, help="Per-customer identifier (hex)"
    )
    gen_p.add_argument(
        "--build-id", required=True, help="Per-build identifier (hex)"
    )
    gen_p.add_argument(
        "--no-ecc", action="store_true", help="Disable error correction"
    )

    embed_p = sub.add_parser("embed", help="Embed watermark into IR")
    embed_p.add_argument("input", help="Input IR file")
    embed_p.add_argument("-o", "--output", required=True, help="Output IR file")
    embed_p.add_argument(
        "--watermark", required=True, help="Watermark bytes (hex)"
    )
    embed_p.add_argument(
        "--seed", default="00" * 16,
        help="Build seed used to authenticate marker placement (hex)",
    )

    detect_p = sub.add_parser("detect", help="Detect watermark in IR")
    detect_p.add_argument("input", help="Input IR file")
    detect_p.add_argument("--seed", required=True, help="Build seed (hex)")

    detect_bin_p = sub.add_parser(
        "detect-binary", help="Detect watermark in compiled binary"
    )
    detect_bin_p.add_argument("binary", help="Binary file")
    detect_bin_p.add_argument("--seed", required=True, help="Build seed (hex)")

    args = parser.parse_args()

    if not _PHASE2_ENABLED:
        print("[Advanced Protection disabled] Set advanced_protection.enabled=true in config/default.json")
        return

    if args.command == "gen":
        customer_id = bytes.fromhex(args.customer_id)
        build_id = bytes.fromhex(args.build_id)
        wm, meta = generate_watermark(
            customer_id, build_id, error_correct=not args.no_ecc
        )
        print(f"Watermark: {wm.hex()}")
        print(f"Bit count: {meta.get('bit_count', 0)}")
        print(f"BCH used: {meta.get('bch_used', False)}")

    elif args.command == "embed":
        from .compile import ir_module_to_text

        watermark_bytes = bytes.fromhex(args.watermark)
        meta: dict[str, Any] = {
            "encoded": [],
            "patterns": {},
            "bch_used": False,
            "build_seed": bytes.fromhex(args.seed),
        }
        for byte in watermark_bytes:
            for i in range(7, -1, -1):
                meta["encoded"].append((byte >> i) & 1)

        module: IrModule = load_ir(args.input)
        module = embed_watermark(module, watermark_bytes, meta)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(ir_module_to_text(module))
        print(f"Watermarked IR written to {args.output}")

    elif args.command == "detect":
        module = load_ir(args.input)
        seed = bytes.fromhex(args.seed)
        wm = detect_watermark(module, seed)
        if wm:
            print(f"Detected watermark: {wm.hex()}")
        else:
            print("No watermark detected")

    elif args.command == "detect-binary":
        seed = bytes.fromhex(args.seed)
        try:
            wm = detect_watermark_from_binary(args.binary, seed)
        except NotImplementedError as exc:
            raise SystemExit(f"detect-binary: {exc}") from exc
        if wm:
            print(f"Detected watermark: {wm.hex()}")
        else:
            print("No watermark detected")


def load_ir(path: str) -> IrModule:
    """
    Load an IR module from a text file.

    Simple parser that handles module, function, and basic block
    definitions. Populates blocks with NOP instructions for
    structure detection.
    """
    from .compile import IrModule, IrFunction, IrBlock, IrInstruction

    module = IrModule(os.path.basename(path))
    current_func: Optional[IrFunction] = None
    current_block: Optional[IrBlock] = None

    with open(path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("module @"):
                module.name = stripped.split("@", 1)[1].strip()
            elif stripped.startswith("func @"):
                name_part = stripped.split("@", 1)[1]
                func_name = name_part.split("(")[0].strip()
                current_func = IrFunction(func_name)
                module.functions.append(current_func)
                current_block = None
            elif stripped.endswith(":") and not stripped.startswith(" ") and current_func:
                label = stripped.rstrip(":")
                current_block = current_func.new_block(label)
            elif current_block and current_func:
                parts = stripped.split()
                if (len(parts) > 2 and parts[0].startswith("%")
                        and parts[1] == "="):
                    op = parts[2]
                else:
                    op = parts[0] if parts else ""
                if op == "ret":
                    current_block.set_terminator("ret")
                elif op == "jmp":
                    labels = [parts[i + 1].rstrip(",")
                              for i, p in enumerate(parts)
                              if p == "label" and i + 1 < len(parts)]
                    if labels:
                        current_block.set_terminator("jmp", operands=[labels[0]])
                elif op == "br":
                    labels = [parts[i + 1].rstrip(",")
                              for i, p in enumerate(parts)
                              if p == "label" and i + 1 < len(parts)]
                    cond = (parts[2].rstrip(",")
                            if len(parts) > 2 else "cond")
                    if len(labels) >= 2:
                        current_block.set_terminator(
                            "br", operands=[cond, labels[0], labels[1]])
                elif op == "nop":
                    current_block.nop()
                elif op in ("alloca", "store", "load", "add", "sub", "mul",
                            "div", "and", "or", "xor", "eq", "ne", "lt",
                            "le", "gt", "ge", "icmp", "select", "gep",
                            "call", "zext", "sext", "trunc", "bitcast"):
                    # The detector classifies watermark blocks by opcode
                    # presence; keep the instruction (the old parser
                    # replaced every line with a NOP, so every block
                    # looked empty and detection always failed).
                    current_block.instructions.append(IrInstruction(op))

    return module


if __name__ == "__main__":
    main()
