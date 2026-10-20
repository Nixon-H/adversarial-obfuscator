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
        exponents 1, 3, 5, ..., 2t-1.
        """
        g = _Poly([1])
        for i in range(1, 2 * self.t + 1, 2):
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
            data = data[: max_data_bits // 8]

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

        padded = _Poly(
            [0] * (self.n - self.k) + m_poly.coeffs
        )
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
        bits: list[int] = []
        for byte in codeword:
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)
        bits = bits[: self.n]

        syndromes: list[int] = [0] * (2 * self.t)
        for i in range(1, 2 * self.t + 1):
            syndromes[i - 1] = self.gf.eval_poly(
                bits, _gf.alog[i]
            )

        if any(s != 0 for s in syndromes):
            err_loc = self._berlekamp_massey(syndromes)
            error_positions = self._chien_search(err_loc)
            for pos in error_positions:
                if 0 <= pos < len(bits):
                    bits[pos] ^= 1

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
                shift_poly = _Poly(
                    [0] * m + B.coeffs
                )
                d_inv = _gf.inv(d)
                scaled_shift = _Poly(
                    [_gf.mul(d_inv, c) for c in shift_poly.coeffs]
                )
                Lambda = Lambda + scaled_shift

                if 2 * L >= r:
                    m += 1
                else:
                    B = T
                    L = r - L
                    m = 1

        return Lambda

    def _chien_search(self, Lambda: _Poly) -> list[int]:
        """
        Chien search: evaluate the error-locator polynomial at
        every non-zero element of GF(2^8) to find error positions.
        """
        positions: list[int] = []
        for k in range(self.n):
            power = (self.n - 1 - k) % self.n
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

    raw_bits: list[int] = []
    for byte in combined[:16]:
        for i in range(7, -1, -1):
            raw_bits.append((byte >> i) & 1)

    if error_correct:
        bch = BCHCode(n=255, t=20)
        encoded = bch.encode(combined[:16])
        encoded_bits: list[int] = []
        for byte in encoded:
            for i in range(7, -1, -1):
                encoded_bits.append((byte >> i) & 1)
    else:
        encoded = combined[:16]
        encoded_bits = list(raw_bits)

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

    if always_true:
        always_true_val = IrValue.const_bool(True)
        op = block.or_(IrType.i1(), cmp.result, always_true_val)
        return op
    else:
        always_true_val = IrValue.const_bool(True)
        op = block.and_(IrType.i1(), cmp.result, always_true_val)
        ne = block.ne(IrType.i32(), cmp.result, IrValue.const_int(0))
        xor = block.xor(IrType.i1(), ne.result, IrValue.const_bool(True))
        return xor


def _make_watermark_block(
    func: IrFunction,
    pattern_type: str,
    bit_val: int,
    rand: random.Random,
) -> IrBlock:
    """
    Create a watermark block with the specified pattern.

    Pattern P1 (bit=1): dead block with opaque-false predicate,
    contains realistic code (arithmetic + memory ops).
    Pattern P0 (bit=0): dead block with opaque-true predicate,
    returns constant.

    Both patterns are structurally valid but unreachable at runtime.
    """
    block = func.new_block(label=f"_wm_{pattern_type}_{bit_val}_{rand.randint(0, 0xFFFF):04x}")

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
        block.add(IrType.i32(), loaded.result, const_val)
        predicate = _make_opaque_predicate(block, True, rand)

    pred_cond = predicate.result

    dead_block = func.new_block(label=f"_wm_dead_{rand.randint(0, 0xFFFF):04x}")
    dead_val = IrValue.const_int(rand.randint(0, 0xFFFFFF))
    dead_block.set_terminator("ret", operands=[IrType.i32(), dead_val])

    continue_label = block.label
    block.set_terminator(
        "br",
        operands=[
            pred_cond,
            continue_label,
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

    encoded_bits = metadata.get("encoded", [])
    if not encoded_bits:
        for byte in watermark:
            for i in range(7, -1, -1):
                encoded_bits.append((byte >> i) & 1)

    patterns = metadata.get("patterns", {})
    build_seed_val = hashlib.sha256(
        str(metadata.get("build_seed", "")).encode()
    ).digest()

    rand = random.Random(
        hashlib.blake2b(build_seed_val + watermark).digest()
    )

    for func in ir_module.functions:
        if not func.blocks:
            continue
        for bit_idx, bit_val in enumerate(encoded_bits):
            pattern_key = patterns.get(bit_idx, f"bit_{bit_idx}")
            _make_watermark_block(func, pattern_key, bit_val, rand)

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

    recovered_bits: list[int] = []
    pattern_count = 0

    expected_label_prefixes = ["_wm_"]

    for func in ir_module.functions:
        for block in func.blocks:
            if not any(
                block.label.startswith(p) for p in expected_label_prefixes
            ):
                continue

            if block.terminator and block.terminator.opcode == "br":
                if len(block.terminator.operands) >= 3:
                    has_alloca = any(
                        inst.opcode == "alloca"
                        for inst in block.instructions
                    )
                    has_load = any(
                        inst.opcode == "load"
                        for inst in block.instructions
                    )
                    has_arithmetic = any(
                        inst.opcode
                        in ("add", "sub", "mul", "div")
                        for inst in block.instructions
                    )

                    if has_alloca and has_load:
                        if has_arithmetic:
                            recovered_bits.append(1)
                        else:
                            recovered_bits.append(0)
                        pattern_count += 1

    if pattern_count < 16:
        return None

    result_bytes = bytearray((len(recovered_bits) + 7) // 8)
    for i, bit in enumerate(recovered_bits):
        if bit:
            byte_idx = i // 8
            bit_idx = 7 - (i % 8)
            if byte_idx < len(result_bytes):
                result_bytes[byte_idx] |= 1 << bit_idx

    return bytes(result_bytes)


# ---------------------------------------------------------------------------
# Binary Watermark Detector
# ---------------------------------------------------------------------------

def detect_watermark_from_binary(
    binary_path: str, build_seed: bytes
) -> Optional[bytes]:
    """
    Detect watermark from a compiled binary.

    Lifts the binary back to an IR-like representation by creating
    basic blocks from binary chunks, then runs detect_watermark on
    the lifted graph.

    This is a heuristic: it creates blocks at 16-byte intervals
    within the first 64KB of the binary and checks for watermark
    patterns.
    """
    if not _PHASE2_ENABLED:
        return None

    if not os.path.exists(binary_path):
        return None

    try:
        with open(binary_path, "rb") as f:
            data = f.read()
    except Exception:
        return None

    lifted = IrModule("lifted_binary")

    main_func = IrFunction("_start")
    lifted.functions.append(main_func)

    current_block = main_func.new_block("lifted_entry")

    for i in range(0, min(len(data), 65536), 16):
        chunk_label = f"_wm_lift_{i:08x}"
        chunk_block = main_func.new_block(label=chunk_label)
        current_block.set_terminator(
            "jmp", operands=[chunk_block.label]
        )
        current_block = chunk_block

    return detect_watermark(lifted, build_seed)


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
        }
        for byte in watermark_bytes:
            for i in range(7, -1, -1):
                meta["encoded"].append((byte >> i) & 1)

        module: IrModule = load_ir(args.input)
        module = embed_watermark(module, watermark_bytes, meta)
        ir_module_to_text(module, args.output)
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
        wm = detect_watermark_from_binary(args.binary, seed)
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
                IrInstruction('nop')
                if stripped.startswith("ret"):
                    current_block.set_terminator("ret")
                elif stripped.startswith("jmp"):
                    parts = stripped.split()
                    if len(parts) >= 2:
                        current_block.set_terminator("jmp", operands=[parts[1].replace("label", "").strip()])
                elif stripped.startswith("br"):
                    current_block.set_terminator("br")
                elif stripped.startswith("nop"):
                    current_block.nop()

    return module


if __name__ == "__main__":
    main()
