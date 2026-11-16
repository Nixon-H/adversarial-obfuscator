"""Regression tests for the ORAM pass's integer-only slot contract.

The pass stores a virtualized value as ``struct.pack('<q', value)``, which
raises "required argument is not an integer" for anything that is not an int.
It used to virtualize every name whose spelling looked sensitive, so
``key = b"..."`` and ``blob_key = None`` both emitted a struct.pack call that
killed the artefact at import.  That is what broke the native build's Python
fallback: ``_nx_sb_activate`` assigns a bytes key and ``_load_native`` assigns
``blob_key = None``, and both died before the payload ran.

These tests pin three things:
  * non-int right-hand sides are left as ordinary locals,
  * int right-hand sides are still virtualized (the feature is preserved),
  * the emitted code actually executes, including the read path.
"""

import ast
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from scripts.data_obfuscation.data_protector import (  # noqa: E402
    DataProtector,
    _int_safe_names,
    _is_int_expr,
)


def _oram(source: str) -> str:
    tree = DataProtector()._oram_protect(ast.parse(source))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _exec(source: str, func: str, *args):
    ns = {}
    exec(compile(_oram(source), "<oram-test>", "exec"), ns)
    return ns[func](*args)


# ── the crash that motivated the fix ────────────────────────────────────

def test_bytes_rhs_is_not_virtualized():
    out = _oram('def f():\n    key = b"abcdefgh"\n    return key\n')
    assert "struct.pack" not in out
    assert _exec('def f():\n    key = b"abcdefgh"\n    return key\n', "f") == b"abcdefgh"


def test_none_rhs_is_not_virtualized():
    out = _oram("def f():\n    blob_key = None\n    return blob_key\n")
    assert "struct.pack" not in out
    assert _exec("def f():\n    blob_key = None\n    return blob_key\n", "f") is None


def test_str_rhs_is_not_virtualized():
    src = 'def f():\n    blob_key = "linux"\n    return blob_key\n'
    assert "struct.pack" not in _oram(src)
    assert _exec(src, "f") == "linux"


def test_mixed_int_then_bytes_is_not_virtualized():
    """One non-int assignment disqualifies the name for the whole function."""
    src = 'def f():\n    key = 5\n    key = b"xyz"\n    return key\n'
    assert "struct.pack" not in _oram(src)
    assert _exec(src, "f") == b"xyz"


# ── the feature still works ─────────────────────────────────────────────

def test_int_rhs_is_still_virtualized():
    out = _oram("def f():\n    hash_count = 0\n    return hash_count\n")
    assert "struct.pack" in out
    assert "_nx_oram" in out


def test_int_counter_round_trips():
    src = (
        "def f():\n"
        "    hash_count = 0\n"
        "    hash_count = hash_count + 1\n"
        "    hash_count = hash_count + 1\n"
        "    return hash_count\n"
    )
    assert _exec(src, "f") == 2


def test_int_read_in_return_position():
    """`return counter` must read the slot, not the vanished binding."""
    src = "def f():\n    hash_count = 7\n    return hash_count\n"
    assert _exec(src, "f") == 7


def test_int_read_in_call_argument():
    src = "def f():\n    hash_count = 7\n    return abs(hash_count)\n"
    assert _exec(src, "f") == 7


def test_int_read_in_fstring():
    src = 'def f():\n    hash_count = 3\n    return f"v={hash_count}"\n'
    assert _exec(src, "f") == "v=3"


def test_int_and_bytes_in_same_function():
    src = (
        "def f():\n"
        "    hash_count = 0\n"
        '    key = b"zzz"\n'
        "    hash_count = hash_count + 1\n"
        "    return (hash_count, key)\n"
    )
    assert _exec(src, "f") == (1, b"zzz")


def test_read_path_slices_the_eight_byte_payload():
    """The slot is 32 bytes wide; struct.unpack('<q', ...) needs exactly 8."""
    out = _oram("def f():\n    hash_count = 1\n    return hash_count\n")
    assert "[0:8]" in out


# ── the predicate itself ────────────────────────────────────────────────

def test_is_int_expr_accepts_int_literals_and_arithmetic():
    assert _is_int_expr(ast.parse("5", mode="eval").body)
    assert _is_int_expr(ast.parse("5 + 3", mode="eval").body)
    assert _is_int_expr(ast.parse("len(x)", mode="eval").body)
    assert _is_int_expr(ast.parse("int(x)", mode="eval").body)


def test_is_int_expr_rejects_non_ints():
    for expr in ('b"x"', "None", '"s"', "1.5", "True", "x", "f(x)", "[1]"):
        assert not _is_int_expr(ast.parse(expr, mode="eval").body), expr


def test_int_safe_names_drops_the_non_int_name_only():
    func = ast.parse(
        "def f():\n"
        "    hash_count = 0\n"
        '    key = b"zzz"\n'
        "    return hash_count, key\n"
    ).body[0]
    assert _int_safe_names(func, {"hash_count", "key"}) == {"hash_count"}


def test_int_safe_names_handles_self_reference():
    func = ast.parse(
        "def f():\n"
        "    hash_count = 0\n"
        "    hash_count = hash_count + 1\n"
        "    return hash_count\n"
    ).body[0]
    assert _int_safe_names(func, {"hash_count"}) == {"hash_count"}


def test_no_oram_injected_when_nothing_is_int_safe():
    out = _oram('def f():\n    key = b"a"\n    return key\n')
    assert "_nx_oram" not in out
    assert "import struct" not in out


# ── names bound outside the function ────────────────────────────────────

def test_module_level_constant_read_is_not_virtualized():
    """The NATIVE_BLOBS shape.

    ``NATIVE_BLOBS`` is spelled with "iv" in "native", so the keyword scan
    flags it as sensitive.  It is bound at module level, so the write path
    never gives it a slot -- rewriting its reads made the loader compare
    against 0 instead of the blob table and die with
    "'NoneType' object is not subscriptable".
    """
    src = (
        'NATIVE_BLOBS = {"linux": "abc"}\n'
        "def f():\n"
        '    blob_key = "linux"\n'
        '    if not blob_key or "PLACEHOLDER" in str(NATIVE_BLOBS):\n'
        '        return "fallback"\n'
        "    return NATIVE_BLOBS[blob_key]\n"
    )
    assert _exec(src, "f") == "abc"


def test_module_level_int_constant_read_is_not_virtualized():
    src = "IV_COUNT = 7\ndef f():\n    return IV_COUNT\n"
    assert _exec(src, "f") == 7


def test_int_safe_names_requires_a_top_level_assignment():
    func = ast.parse("def f():\n    return NATIVE_BLOBS\n").body[0]
    assert _int_safe_names(func, {"NATIVE_BLOBS"}) == set()


def test_int_safe_names_ignores_names_bound_only_in_a_branch():
    func = ast.parse(
        "def f():\n"
        "    if x:\n"
        "        hash_count = 1\n"
        "    return hash_count\n"
    ).body[0]
    assert _int_safe_names(func, {"hash_count"}) == set()


# ── function arguments ──────────────────────────────────────────────────

def test_bitwise_only_argument_is_virtualized_and_correct():
    """`encrypt(key, data)` with `key ^ data`.

    The ORAM used to be injected for this shape but the arguments were
    never written to their slots, so the protection was dead code.  They
    are now bound at entry, and the function still returns the right
    answer.
    """
    src = (
        "def encrypt(key, data):\n"
        "    result = key ^ data\n"
        "    return result\n"
    )
    out = _oram(src)
    assert "_nx_oram" in out
    assert _exec(src, "encrypt", 10, 6) == 10 ^ 6


def test_argument_used_outside_bitwise_is_not_virtualized():
    """A plain `return key` could be any type, so it must stay a local."""
    src = "def encrypt(key):\n    return key\n"
    out = _oram(src)
    assert "_nx_oram" not in out
    assert _exec(src, "encrypt", b"bytes-are-fine") == b"bytes-are-fine"


def test_unwritten_slot_reads_as_zero_not_none():
    """read() returns None for an empty slot; the unpack must not raise."""
    out = _oram("def f():\n    hash_count = 1\n    return hash_count\n")
    assert "or b'\\x00' * 8" in out or 'or b"\\x00" * 8' in out
