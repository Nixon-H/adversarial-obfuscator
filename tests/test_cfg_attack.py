"""Tests for the structural-signature attack (v2.0, T_CFG_hash).

Gate-keeping tests assert instrument properties (determinism,
rename-invariance, flatten-sensitivity); cross-arm NUMBERS belong to
the experiment run, not to tests.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.transfer import cfg_attack as C

TOY = (
    "def f(x):\n"
    "    a = x + 1\n"
    "    if a > 2:\n"
    "        b = a * 10\n"
    "    else:\n"
    "        b = a - 10\n"
    "    return b\n"
)

TOY_RENAMED = (
    "def qqq(zzz):\n"
    "    www = zzz + 1\n"
    "    if www > 2:\n"
    "        eee = www * 10\n"
    "    else:\n"
    "        eee = www - 10\n"
    "    return eee\n"
)

TOY_FLAT = (
    "def f(x):\n"
    "    _st = 0\n"
    "    _lp = True\n"
    "    while _lp:\n"
    "        if _st == 0:\n"
    "            a = x + 1\n"
    "            _st = 1\n"
    "        elif _st == 1:\n"
    "            if a > 2:\n"
    "                b = a * 10\n"
    "            else:\n"
    "                b = a - 10\n"
    "            _st = 2\n"
    "        elif _st == 2:\n"
    "            _lp = False\n"
    "    return b\n"
)


def test_self_is_one():
    ext = C.profile(TOY)
    assert ext["ok"]
    s = C.decode_score(TOY, ext)
    assert s[0] == 1.0 and s[1] == 1.0 and s[2] == 1.0
    assert (s[3], s[4]) == (1, 1)


def test_rename_invisible():
    ei = C.profile(TOY)
    assert ei["ok"]
    st, se, sb, n, nt = C.decode_score(TOY_RENAMED, ei)
    assert (n, nt) == (1, 1)
    assert st == 1.0 and se == 1.0 and sb == 1.0


def test_flatten_moves_edges():
    ei = C.profile(TOY)
    assert ei["ok"]
    st, se, sb, n, nt = C.decode_score(TOY_FLAT, ei)
    assert (n, nt) == (1, 1)
    assert st < 1.0  # dispatcher adds blocks/branches (topology moves)
    assert se < 1.0


def test_uncompilable_excluded():
    ext = C.profile("def broken(:\n")
    assert ext["ok"] is False
    s = C.decode_score("def broken(:\n", {"ok": True, "functions": {}})
    assert s[0] is None


def test_alignment_coverage_reported():
    two = TOY + "def g(y):\n    return y\n"
    ei = C.profile(TOY)
    assert ei["ok"]
    st, se, sb, n, nt = C.decode_score(two, ei)
    assert nt == 2 and n == 1  # g unaligned, reported not hidden
