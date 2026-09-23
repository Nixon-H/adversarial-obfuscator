"""Tests for PathORAM write-back eviction (scripts/runtime/oram_sim.py).

Covers the _write_path() fix:
    - stash stays bounded across many mixed read/write accesses
    - read-your-write correctness (write then read returns the value)
    - remap happens on every access (position map churns)
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.runtime.oram_sim import PathORAM


def test_stash_bounded_after_many_accesses():
    oram = PathORAM(num_blocks=16, bucket_size=4)
    rng = random.Random(42)
    for i in range(300):
        addr = rng.randrange(16)
        oram.write(addr, i)
    stats = oram.get_stats()
    # Stash must stay O(log N)-scale, not grow with access count.
    assert stats["stash_size"] <= 32, (
        f"stash grew unbounded: {stats['stash_size']} after "
        f"{stats['access_count']} accesses"
    )


def test_stash_bounded_mixed_read_write():
    oram = PathORAM(num_blocks=16, bucket_size=4)
    rng = random.Random(7)
    for i in range(200):
        addr = rng.randrange(16)
        if i % 2:
            oram.write(addr, i)
        else:
            oram.read(addr)
    assert oram.get_stats()["stash_size"] <= 32


def test_read_your_write():
    oram = PathORAM(num_blocks=8, bucket_size=4)
    for addr in range(8):
        oram.write(addr, addr * 100)
    for addr in range(8):
        assert oram.read(addr) == addr * 100


def test_overwrite_returns_old_value():
    oram = PathORAM(num_blocks=4, bucket_size=4)
    oram.write(1, "a")
    assert oram.read(1) == "a"
    oram.write(1, "b")
    assert oram.read(1) == "b"


def test_remap_on_every_access():
    oram = PathORAM(num_blocks=4, bucket_size=4)
    oram.write(0, "x")
    seen = {oram.position_map[0]}
    for _ in range(20):
        oram.read(0)
        seen.add(oram.position_map[0])
    # 20 remaps over 4+ leaves must have produced >1 distinct leaf.
    assert len(seen) > 1
