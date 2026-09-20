import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.binding.temporal_key import TemporalKey


def test_derive_key():
    tk = TemporalKey()
    k0 = tk.derive_key(0)
    assert k0 is not None
    assert len(k0) == 32
    assert tk.get_current_epoch() >= 0


def test_keys_from_different_epochs_differ():
    tk = TemporalKey()
    k0 = tk.derive_key(0)
    k1 = tk.derive_key(1)
    assert k0 != k1


def test_deterministic_keys_same_seed():
    seed = b"fixed-32-byte-seed-for-testing!!!!"
    tk1 = TemporalKey(seed=seed)
    tk2 = TemporalKey(seed=seed)
    k1 = tk1.derive_key(5)
    k2 = tk2.derive_key(5)
    assert k1 == k2


def test_no_rewind():
    tk = TemporalKey()
    tk.derive_key(5)
    result = tk.derive_key(3)
    assert result is None, "Should not rewind to earlier epoch"


def test_chain_length_increases():
    tk = TemporalKey()
    e0 = tk.get_current_epoch()
    tk.derive_key(0)
    e1 = tk.get_current_epoch()
    assert e1 >= e0


def test_reseed_resets_epoch():
    tk = TemporalKey()
    tk.derive_key(10)
    tk.reseed(b"new-32-byte-seed-for-reseed-test!!!!")
    assert tk.get_current_epoch() == 0
    k = tk.derive_key(0)
    assert k is not None
    assert len(k) == 32
