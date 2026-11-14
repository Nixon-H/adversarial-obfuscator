"""The master index must not carry the fragment encryption keys."""
from scripts.distributed.multi_binary import MasterIndex


def test_cross_keys_are_not_serialized():
    index = MasterIndex(
        binary_count=2, fragment_count=3, threshold=2,
        fragment_map=[(0, 0), (1, 1)], cross_keys=[b"secret-key-a"])
    data = index.serialize()
    assert b"secret-key-a" not in data
    restored = MasterIndex.deserialize(data)
    assert restored.cross_keys == []
    assert restored.fragment_map == [(0, 0), (1, 1)]
