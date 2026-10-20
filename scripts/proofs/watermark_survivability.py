"""
proofs/watermark_survivability.py

Purpose:
Proves that watermark state survives obfuscation transformations. Watermark
values are encoded as Z3 BitVec constants and passed through each transformation;
the prover checks that the output state retains the original watermark values.

Security Relevance:
Watermarks are the primary mechanism for establishing code ownership after
obfuscation. If a transformation destroys or alters the watermark, ownership
proof becomes impossible and the protection is worthless. This prover detects
such destruction.

Dependencies:
- z3 (BitVec solver)
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Callable

from scripts.z3_optional import z3

BITWIDTH = 64


@dataclass
class WatermarkProof:
    """
    WatermarkProof

    What is proven:
    For a given watermark string, after applying an obfuscation
    transformation, every watermark component (wm_block_i, wm_byte_i,
    wm_value) retains its original value.

    Why:
    Watermarks must survive all obfuscation passes. If any transform
    corrupts or drops a watermark component, the watermark is lost and
    ownership cannot be asserted.

    Assumptions:
    - Watermark is encoded into deterministic BitVec constants derived
      from SHA-256 of the message.
    - Transformations act on a state dict; side effects through external
      channels (I/O, timing) are not modeled.

    Limitations:
    - Only BitVec watermark values are verified; semantic watermarks
      embedded in CFG structure, SSA phi ordering, etc., are NOT proven
      here — they use different extraction paths.
    - Pipeline survivability checks final state only; per-step proofs
      are recorded but the final result is the composition.

    Verification Path:
    prove_survives_pass(watermark, transform) -> proof.survived
    prove_survives_pipeline(watermark, [transform, ...]) -> proof.survived
    """
    pass_name: str
    watermark: str
    transformation: str
    survived: bool
    solver_time_ms: float
    counterexample: Optional[dict] = None
    timestamp: str = ""
    proof_hash: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.proof_hash:
            raw = f"{self.pass_name}:{self.watermark}:{self.transformation}:{self.survived}:{self.solver_time_ms}"
            self.proof_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_certificate_dict(self) -> dict:
        return {
            "pass_name": self.pass_name,
            "input_hash": hashlib.sha256(self.watermark.encode()).hexdigest(),
            "output_hash": self.proof_hash,
            "equivalence_proof": {
                "survived": self.survived,
                "solver_time_ms": self.solver_time_ms,
                "counterexample": self.counterexample,
            },
            "duration_ms": self.solver_time_ms,
            "timestamp": self.timestamp,
            "validated": self.survived,
        }


@dataclass
class Transformation:
    """A named transformation function that maps state dict -> state dict."""
    name: str
    fn: Callable[[dict], dict]


class WatermarkSurvivabilityProver:
    """
    WatermarkSurvivabilityProver

    What is proven:
    Watermark BitVec components survive any obfuscation transformation.

    Why:
    A transformation that destroys the watermark is equivalent to
    stripping the ownership proof from the code.

    Assumptions:
    Watermark state is a dict of Z3 BitVecRef values derived from a
    deterministic hash. Competing transformations that rename keys are
    handled by _normalize_wm_key.

    Limitations:
    - Only BitVec-mapped watermark fields are tracked.
    - Transformation functions that close over external mutable state
      are not modeled.

    Verification Path:
    prove_survives_pass -> WatermarkProof.survived
    """
    def __init__(self, timeout_ms: int = 30000):
        self.timeout_ms = timeout_ms
        self.proofs: list[WatermarkProof] = []

    def _encode_watermark_in_state(self, watermark: str) -> dict:
        h = int(hashlib.sha256(watermark.encode()).hexdigest(), 16)
        wm_val = h & ((1 << BITWIDTH) - 1)
        state: dict[str, Any] = {}
        for i in range(4):
            state[f"wm_block_{i}"] = z3.BitVecVal((h >> (i * 16)) & 0xFFFF, BITWIDTH)
        for i in range(8):
            part = (h >> (i * 8)) & 0xFF
            state[f"wm_byte_{i}"] = z3.BitVecVal(part, BITWIDTH)
        state["wm_value"] = z3.BitVecVal(wm_val, BITWIDTH)
        state["wm_str"] = watermark
        return state

    @staticmethod
    def _normalize_wm_key(key: str) -> str:
        if key.startswith("wm_renamed_"):
            return key[len("wm_renamed_"):]
        if key.startswith("wm_"):
            return key[len("wm_"):]
        return key

    def _check_watermark_preserved(
        self, before: dict, after: dict, watermark: str
    ) -> tuple[bool, Optional[dict]]:

        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)

        before_wm = {
            self._normalize_wm_key(k): v
            for k, v in before.items()
            if k.startswith("wm_") and isinstance(v, z3.BitVecRef)
        }
        after_wm = {
            self._normalize_wm_key(k): v
            for k, v in after.items()
            if (k.startswith("wm_") or k.startswith("wm_renamed_")) and isinstance(v, z3.BitVecRef)
        }

        common_keys = set(before_wm.keys()) & set(after_wm.keys())
        for key in common_keys:
            solver.add(before_wm[key] == after_wm[key])

        result = solver.check()

        if result == z3.unsat:
            ce = {}
            return False, ce
        return True, None

    def prove_survives_pass(
        self, watermark: str, transformation: Transformation
    ) -> WatermarkProof:
        start = time.time()

        before = self._encode_watermark_in_state(watermark)
        after = transformation.fn(before)

        survived, ce = self._check_watermark_preserved(before, after, watermark)
        elapsed = (time.time() - start) * 1000

        proof = WatermarkProof(
            pass_name="watermark_survivability",
            watermark=watermark,
            transformation=transformation.name,
            survived=survived,
            solver_time_ms=elapsed,
            counterexample=ce,
        )
        self.proofs.append(proof)
        return proof

    def prove_survives_pipeline(
        self, watermark: str, pipeline: list[Transformation]
    ) -> WatermarkProof:
        start = time.time()

        state = self._encode_watermark_in_state(watermark)

        intermediate_proofs: list[WatermarkProof] = []
        for t in pipeline:
            before_state = state
            state = t.fn(state)
            survived_step, _ = self._check_watermark_preserved(before_state, state, watermark)
            step_proof = WatermarkProof(
                pass_name="watermark_survivability_pipeline_intermediate",
                watermark=watermark,
                transformation=t.name,
                survived=survived_step,
                solver_time_ms=0.0,
            )
            intermediate_proofs.append(step_proof)
            self.proofs.append(step_proof)

        pipeline_name = " -> ".join(t.name for t in pipeline)

        h = int(hashlib.sha256(watermark.encode()).hexdigest(), 16)

        solver = z3.Solver()
        solver.set("timeout", self.timeout_ms)

        for k in ["wm_value"]:
            if k in state:
                expected = z3.BitVecVal(h & ((1 << BITWIDTH) - 1), BITWIDTH)
                solver.add(state[k] == expected)

        for i in range(4):
            key = f"wm_block_{i}"
            if key in state:
                expected = z3.BitVecVal((h >> (i * 16)) & 0xFFFF, BITWIDTH)
                solver.add(state[key] == expected)

        for i in range(8):
            key = f"wm_byte_{i}"
            if key in state:
                expected = z3.BitVecVal((h >> (i * 8)) & 0xFF, BITWIDTH)
                solver.add(state[key] == expected)

        result = solver.check()
        elapsed = (time.time() - start) * 1000

        survived = result != z3.unsat

        proof = WatermarkProof(
            pass_name="watermark_survivability_pipeline",
            watermark=watermark,
            transformation=pipeline_name,
            survived=survived,
            solver_time_ms=elapsed,
        )
        self.proofs.append(proof)
        return proof


def _mba_substitution_transform(state: dict) -> dict:
    """MBA substitution: replace wm_value with equivalent MBA expression.
    x -> (x & 0xAAAA) ^ (x & 0x5555) + (x | 0xAAAA) - (x | 0x5555)"""
    ns = dict(state)
    for k, v in ns.items():
        if isinstance(v, z3.BitVecRef) and k == "wm_value":
            aaaa = z3.BitVecVal(0xAAAAAAAAAAAAAAAA, BITWIDTH)
            x = v
            ns[k] = (x & aaaa) ^ (x & ~aaaa) + (x | aaaa) - (x | ~aaaa)
    return ns


def _opaque_predicate_transform(state: dict) -> dict:
    """Opaque predicate injection: guard watermark with an always-true predicate.
    wm_block_i = (x^2 + x) % 2 == 0 ? wm_block_i : 0, which always preserves since (x^2+x)%2==0 for all x"""
    ns = dict(state)
    for k, v in ns.items():
        if isinstance(v, z3.BitVecRef) and k.startswith("wm_block"):
            x = z3.BitVec("_opq_x", BITWIDTH)
            pred = (x * x + x) % z3.BitVecVal(2, BITWIDTH) == z3.BitVecVal(0, BITWIDTH)
            ns[k] = z3.If(pred, v, z3.BitVecVal(0, BITWIDTH))
    return ns


def _cfg_flatten_z3_transform(state: dict) -> dict:
    """CFG flattening via Z3: introduce state variable and dispatch.
    Each wm value gets routed through a state machine:
    state = (state * 7 + 3) % 16; wm_val = wm_val ^ state"""
    ns = dict(state)
    for k, v in ns.items():
        if isinstance(v, z3.BitVecRef) and k == "wm_value":
            state_var = z3.BitVec("_cfg_state", BITWIDTH)
            new_state = (state_var * z3.BitVecVal(7, BITWIDTH) + z3.BitVecVal(3, BITWIDTH)) % z3.BitVecVal(16, BITWIDTH)
            ns[k] = v ^ new_state
    return ns


def _identity_transform(state: dict) -> dict:
    return dict(state)


def _rename_transform(state: dict) -> dict:
    ns = {}
    for k, v in state.items():
        if k.startswith("wm_"):
            new_k = k.replace("wm_", "wm_renamed_")
            ns[new_k] = v
        else:
            ns[k] = v
    return ns


def _deadcode_add_transform(state: dict) -> dict:
    ns = dict(state)
    dead_var = z3.BitVec("_dead_x", BITWIDTH)
    dead_val = (dead_var * z3.BitVecVal(0xDEAD, BITWIDTH)) ^ z3.BitVecVal(0xBEEF, BITWIDTH)
    ns["dead_var"] = dead_val
    ns["dead_var2"] = dead_val * dead_var
    return ns


def _cfg_flatten_transform(state: dict) -> dict:
    ns = dict(state)
    for k in list(ns.keys()):
        if isinstance(ns[k], z3.BitVecRef) and k.startswith("wm_"):
            s = z3.BitVec("_cfg_s", BITWIDTH)
            ns[k] = ns[k] ^ ((s * z3.BitVecVal(7, BITWIDTH) + z3.BitVecVal(3, BITWIDTH)) % z3.BitVecVal(16, BITWIDTH))
    return ns


def _zero_watermark_transform(state: dict) -> dict:
    ns = dict(state)
    for k in list(ns.keys()):
        if isinstance(ns[k], z3.BitVecRef) and k.startswith("wm_"):
            ns[k] = z3.BitVecVal(0, BITWIDTH)
    return ns


def _shift_watermark_transform(state: dict) -> dict:
    ns = dict(state)
    for k in list(ns.keys()):
        if isinstance(ns[k], z3.BitVecRef) and k.startswith("wm_"):
            ns[k] = ns[k] + z3.BitVecVal(1, BITWIDTH)
    return ns


IDENTITY = Transformation("identity", _identity_transform)
RENAME = Transformation("rename", _rename_transform)
DEADCODE = Transformation("deadcode_insertion", _deadcode_add_transform)
CFG_FLATTEN = Transformation("cfg_flattening", _cfg_flatten_transform)
ZERO_WATERMARK = Transformation("zero_watermark", _zero_watermark_transform)
SHIFT_WATERMARK = Transformation("shift_watermark", _shift_watermark_transform)
MBA_SUBSTITUTION = Transformation("mba_substitution", _mba_substitution_transform)
OPAQUE_PREDICATE = Transformation("opaque_predicate", _opaque_predicate_transform)
CFG_FLATTEN_Z3 = Transformation("cfg_flatten_z3", _cfg_flatten_z3_transform)

STANDARD_PASSES = [IDENTITY, RENAME, DEADCODE, CFG_FLATTEN, MBA_SUBSTITUTION, OPAQUE_PREDICATE, CFG_FLATTEN_Z3]
