"""Tests for obfuscator.reorder_pack."""


from obfuscator.reorder_pack import pack_container, unpack_container


def test_roundtrip_single():
    blobs = [b"hello world, this is a single blob"]
    pack = pack_container(blobs, b"seed-1", chunk_size=4)
    assert set(pack.keys()) >= {"order", "table", "data"}
    assert len(pack["table"]) == 256
    assert unpack_container(pack) == blobs


def test_roundtrip_multi():
    blobs = [bytes(range(256)) * 3, b"", b"short", b"x" * 9000]
    pack = pack_container(blobs, b"seed-2")
    assert unpack_container(pack) == blobs


def test_roundtrip_empty():
    pack = pack_container([], b"seed-3")
    assert pack["order"] == []
    assert pack["data"] == b""
    assert len(pack["table"]) == 256
    assert unpack_container(pack) == []


def test_tampered_order_fails_or_mismatches():
    blobs = [bytes((i * 37 + 11) % 256 for i in range(512))]
    pack = pack_container(blobs, b"seed-4", chunk_size=16)
    assert len(pack["order"]) > 1  # need >1 chunk for a meaningful swap
    bad = dict(pack)
    order = list(pack["order"])
    order[0], order[1] = order[1], order[0]
    bad["order"] = order
    try:
        result = unpack_container(bad)
    except ValueError:
        return  # raising is acceptable
    assert result != blobs


def test_tampered_table_mismatches():
    blobs = [bytes(range(256))]
    pack = pack_container(blobs, b"seed-5", chunk_size=32)
    bad = dict(pack)
    table = bytearray(pack["table"])
    table[0], table[1] = table[1], table[0]
    bad["table"] = bytes(table)
    try:
        result = unpack_container(bad)
    except ValueError:
        return
    assert result != blobs


def test_determinism_same_seed_same_output():
    blobs = [b"deterministic?" * 100, b"second blob"]
    a = pack_container(blobs, b"same-seed", chunk_size=64)
    b = pack_container(blobs, b"same-seed", chunk_size=64)
    assert a == b
    c = pack_container(blobs, b"other-seed", chunk_size=64)
    assert (c["order"] != a["order"] or c["table"] != a["table"] or c["data"] != a["data"])
