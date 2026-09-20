"""Batch-4: per-wrapper JIT class-id emit convention tests."""

import hashlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.wrapper_jit import (
    assign_class_ids,
    class_id_for_name,
    emit_wrapper_call,
)

SRC_TWO = "def f():\n    return 1\n\ndef g():\n    return 2\n"
SRC_NESTED = (
    "class C:\n"
    "    def m(self):\n"
    "        return 1\n"
    "def outer():\n"
    "    def inner():\n"
    "        return 2\n"
    "    return inner()\n"
)


def test_deterministic_ids():
    assert assign_class_ids(SRC_TWO) == assign_class_ids(SRC_TWO)


def test_distinct_per_function():
    ids = assign_class_ids(SRC_TWO)
    assert set(ids) == {"f", "g"}
    assert ids["f"] != ids["g"]
    for v in ids.values():
        assert 0 <= v <= 0xFFFFFFFF


def test_nested_qualified_names():
    ids = assign_class_ids(SRC_NESTED)
    assert set(ids) == {"C.m", "outer", "outer.inner"}
    assert len(set(ids.values())) == 3


def test_stable_across_runs_matches_sha256():
    expected = int.from_bytes(hashlib.sha256(b"f").digest()[:4], "little")
    assert class_id_for_name("f") == expected
    assert assign_class_ids("def f():\n    pass\n")["f"] == expected


def test_empty_source_gives_empty_map():
    assert assign_class_ids("x = 1\n") == {}


def test_emit_string_contains_class_id_and_convention():
    snippet = emit_wrapper_call("f", 12345)
    assert "12345" in snippet
    assert "f" in snippet
    assert "specialize_template_with_class" in snippet
    assert "runtime_values" in snippet
