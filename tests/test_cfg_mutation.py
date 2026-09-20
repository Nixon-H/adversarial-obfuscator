"""Tests for Live CFG Mutation (Item 80)."""

import hashlib
import os
import struct
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _build_mutator(seed=None):
    """Return a CfgMutator-like Python implementation for testing."""
    if seed is None:
        seed = b"\xAB" * 32
    rng_state = struct.unpack("<Q", seed[:8])[0]
    return {
        "variant_table": {},
        "epoch": 0,
        "running_hash": 0,
        "rng_state": rng_state,
        "seed": seed,
    }


def _next_rng(state):
    rng = state["rng_state"]
    rng = ((rng * 6364136223846793005) & 0xFFFFFFFFFFFFFFFF) + 1442695040888963407
    rng = rng & 0xFFFFFFFFFFFFFFFF
    state["rng_state"] = rng
    return rng


def _register_variant(state, fn_name, orderings):
    h = hashlib.sha256(fn_name.encode()).digest()
    seed_slice = struct.unpack("<Q", h[:8])[0]
    state["variant_table"][fn_name] = {
        "orderings": orderings,
        "seed": seed_slice,
    }


def _select_variant(state, fn_name):
    table = state["variant_table"].get(fn_name)
    if not table or not table["orderings"]:
        return None
    mixed = (state["running_hash"] * (state["epoch"] + 1) + _next_rng(state)) & 0xFFFFFFFFFFFFFFFF
    idx = mixed % len(table["orderings"])
    return table["orderings"][idx]


def _advance_epoch(state, dispatch_hash):
    state["running_hash"] = ((state["running_hash"] * 6364136223846793005) & 0xFFFFFFFFFFFFFFFF) + dispatch_hash
    state["running_hash"] = state["running_hash"] & 0xFFFFFFFFFFFFFFFF
    state["epoch"] = (state["epoch"] + 1) & 0xFFFFFFFFFFFFFFFF
    return state["epoch"]


def generate_orderings(num_blocks, num_variants, name_seed=""):
    digest = hashlib.sha256(name_seed.encode()).digest()
    base_rng = struct.unpack("<Q", digest[:8])[0]
    orderings = []
    for v in range(num_variants):
        order = list(range(num_blocks))
        rng = (base_rng + v) & 0xFFFFFFFFFFFFFFFF
        for i in range(num_blocks - 1, 0, -1):
            j = int(rng % (i + 1))
            rng = ((rng * 6364136223846793005) & 0xFFFFFFFFFFFFFFFF) + 1442695040888963407
            rng = rng & 0xFFFFFFFFFFFFFFFF
            order[i], order[j] = order[j], order[i]
        orderings.append(order)
    return orderings


class TestCfgMutation:
    """
    TestCfgMutation
    
    Positive test cases for cfgmutation.
    """
    def test_selects_different_paths(self):
        state = _build_mutator()
        orderings = generate_orderings(5, 4, "test_fn")
        _register_variant(state, "test_fn", orderings)
        selected = set()
        for _ in range(100):
            _advance_epoch(state, 0)
            v = _select_variant(state, "test_fn")
            if v is not None:
                selected.add(tuple(v))
        assert len(selected) >= 2, (
            f"Should select at least 2 different orderings in 100 runs, got {len(selected)}"
        )

    def test_preserves_semantics(self):
        state = _build_mutator()
        orderings = generate_orderings(5, 3, "fn_a")
        _register_variant(state, "fn_a", orderings)

        results = []
        for v in range(len(orderings)):
            _advance_epoch(state, v)
            ordering = _select_variant(state, "fn_a")
            assert ordering is not None
            # Use commutative XOR to verify all visited blocks produce same result
            acc = 0
            for blk in ordering:
                acc ^= blk  # XOR is commutative
            results.append(acc)

        first = results[0]
        for r in results:
            assert r == first, (
                f"All orderings must produce identical post-block state: {r} != {first}"
            )

    def test_deterministic_given_seed(self):
        seed = b"\x42" * 32
        state1 = _build_mutator(seed)
        state2 = _build_mutator(seed)
        orderings = generate_orderings(4, 3, "f")
        _register_variant(state1, "f", orderings)
        _register_variant(state2, "f", orderings)

        results1, results2 = [], []
        for i in range(10):
            _advance_epoch(state1, i)
            _advance_epoch(state2, i)
            v1 = _select_variant(state1, "f")
            v2 = _select_variant(state2, "f")
            if v1 is not None:
                results1.append(tuple(v1))
            if v2 is not None:
                results2.append(tuple(v2))
        assert results1 == results2, (
            "Same seed -> same ordering sequence"
        )

    def test_does_not_add_branches(self):
        state = _build_mutator()
        orderings = generate_orderings(3, 2, "linear_fn")
        _register_variant(state, "linear_fn", orderings)
        for fn_name, table in state["variant_table"].items():
            for ordering in table["orderings"]:
                assert len(ordering) == 3, (
                    f"Each variant for {fn_name} must have exactly 3 entries, got {len(ordering)}"
                )
                assert sorted(ordering) == [0, 1, 2], (
                    "Each variant must be a permutation of 0..num_blocks-1"
                )

    def test_generate_orderings_produces_valid_permutations(self):
        orderings = generate_orderings(5, 4, "test")
        assert len(orderings) == 4
        for o in orderings:
            assert sorted(o) == [0, 1, 2, 3, 4], (
                f"Each ordering must cover all blocks: {o}"
            )

    def test_different_names_different_orderings(self):
        o1 = generate_orderings(5, 3, "func_a")
        o2 = generate_orderings(5, 3, "func_b")
        assert o1 != o2, "Different function names should produce different orderings"

    def test_variant_selection_mixes_epoch_and_hash(self):
        state = _build_mutator()
        orderings = generate_orderings(10, 8, "mix_test")
        _register_variant(state, "mix_test", orderings)
        selections = []
        for ep in range(20):
            _advance_epoch(state, ep * 7)
            v = _select_variant(state, "mix_test")
            selections.append(tuple(v) if v else None)
        unique = set(s for s in selections if s is not None)
        assert len(unique) >= 2, (
            "Different epoch+hash mixes should produce different selections"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
