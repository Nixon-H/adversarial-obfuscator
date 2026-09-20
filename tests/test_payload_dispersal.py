import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.payload.dispersal import PayloadDisperser, Slice
from scripts.dispersal.payload_dispersal import PayloadDispersal, PayloadShare, ShamirSharing


def test_disperse_creates_slices():
    disperser = PayloadDisperser()
    source = """
def compute():
    a = 1
    b = 2
    c = a + b
    d = c * 2
    return d
"""
    slices = disperser.disperse(source, num_slices=3)
    assert len(slices) == 3
    assert all(isinstance(s, Slice) for s in slices)
    for s in slices:
        assert len(s.source) > 0


def test_create_merge_points():
    disperser = PayloadDisperser()
    source = """
def process():
    x = 10
    y = 20
    z = x + y
    w = z * 2
    return w
"""
    disperser.disperse(source, num_slices=4)
    mps = disperser.create_merge_points()
    assert len(mps) >= 1


def test_reconstruct_combines_results():
    disperser = PayloadDisperser()
    results = {
        0: {"x": 10, "y": 20},
        1: {"z": 30},
        2: {"w": 60},
    }
    merged = disperser.reconstruct(results)
    assert merged["x"] == 10
    assert merged["y"] == 20
    assert merged["z"] == 30
    assert merged["w"] == 60


def test_dispersal_summary():
    disperser = PayloadDisperser()
    source = """
def fn():
    a = 1
    b = 2
    c = 3
    d = a + b + c
    return d
"""
    disperser.disperse(source, num_slices=2)
    summary = disperser.get_dispersal_summary()
    assert summary["num_slices"] == 2
    assert "slices" in summary


# PayloadDispersal / ShamirSharing tests

def test_shamir_split_and_recover():
    secret = b"hello world"
    shares = ShamirSharing.split_secret(secret, num_shares=5, threshold=3)
    assert len(shares) == 5
    recovered = ShamirSharing.recover_secret(shares, 3)
    assert recovered == secret


def test_shamir_threshold_required():
    secret = b"test secret data"
    shares = ShamirSharing.split_secret(secret, num_shares=5, threshold=3)
    recovered = ShamirSharing.recover_secret(shares[:3], 3)
    assert recovered == secret


def test_shamir_not_enough_shares():
    secret = b"test secret"
    shares = ShamirSharing.split_secret(secret, num_shares=5, threshold=3)
    try:
        ShamirSharing.recover_secret(shares[:2], 3)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_shamir_different_threshold():
    secret = b"another secret"
    shares = ShamirSharing.split_secret(secret, num_shares=10, threshold=5)
    recovered = ShamirSharing.recover_secret(shares[:5], 5)
    assert recovered == secret


def test_payload_dispersal_disperse():
    disperser = PayloadDispersal(seed=42)
    payload = b"this is the secret payload data"
    shares = disperser.disperse(payload, num_shares=5, threshold=3)
    assert len(shares) == 5
    assert all(isinstance(s, PayloadShare) for s in shares)
    assert all(s.mmap_addr is not None for s in shares)


def test_payload_dispersal_reconstruct():
    disperser = PayloadDispersal(seed=42)
    payload = b"secret payload data here"
    shares = disperser.disperse(payload, num_shares=5, threshold=3)
    recovered = disperser.reconstruct(shares[:3], 3)
    assert recovered == payload


def test_payload_dispersal_not_enough_shares():
    disperser = PayloadDispersal(seed=42)
    payload = b"test"
    shares = disperser.disperse(payload, num_shares=5, threshold=3)
    try:
        disperser.reconstruct(shares[:2], 3)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_payload_dispersal_summary():
    disperser = PayloadDispersal(seed=42)
    disperser.disperse(b"test payload", num_shares=5, threshold=3)
    summary = disperser.get_dispersal_summary()
    assert summary["num_shares"] == 5
    assert summary["threshold"] == 3
    assert len(summary["share_indices"]) == 5
    assert len(summary["mmap_addresses"]) == 5
