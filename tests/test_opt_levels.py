"""Tests for obfuscator.opt_levels."""

import argparse

import pytest

from obfuscator.opt_levels import ALL_FLAGS, LEVELS, apply_to_args, describe, resolve


def test_l0_all_false():
    cfg = resolve(0)
    assert set(cfg.keys()) == set(ALL_FLAGS)
    assert all(v is False for v in cfg.values())


def test_l4_is_superset_of_l1():
    l1 = resolve(1)
    l4 = resolve(4)
    for flag in ALL_FLAGS:
        if l1[flag]:
            assert l4[flag] is True, f"L4 dropped L1 flag {flag}"


def test_monotonic_each_level_superset_of_previous():
    for lvl in range(0, 5):
        cur = resolve(lvl)
        nxt = resolve(lvl + 1)
        for flag in ALL_FLAGS:
            if cur[flag]:
                assert nxt[flag] is True, f"L{lvl+1} dropped L{lvl} flag {flag}"
        # each step must add at least one flag (except L0->..., check total growth)
    totals = [sum(1 for v in resolve(l).values() if v) for l in range(6)]
    assert totals == sorted(totals)
    assert totals[-1] == len(ALL_FLAGS)  # L5 enables everything


def test_resolve_rejects_bad_levels():
    with pytest.raises(ValueError):
        resolve(6)
    with pytest.raises(ValueError):
        resolve(-1)


def test_apply_to_args_sets_attrs():
    args = argparse.Namespace()
    out = apply_to_args(args, 4)
    assert out is args
    expected = resolve(4)
    for flag, value in expected.items():
        assert getattr(args, flag) == value
    assert args.opt_level == 4
    assert isinstance(describe(4), str) and "4" in describe(4)
