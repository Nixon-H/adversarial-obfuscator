"""Tests for the VM-dispatcher recovery attack (v2.0, T_VM_table).

Gate-keeping tests assert extractor soundness (self-decode == 1.0);
the cross-seed transfer NUMBERS belong to the experiment run, not to
tests (anti-tuning: tests must pass regardless of measured T).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obfuscator.vm_dispatch import virtualize_source
from scripts.transfer import vm_attack as V

TOY = (
    "def f(n):\n"
    "    a = 0\n"
    "    for i in range(n):\n"
    "        a = a + i\n"
    "    return a\n"
)


def _virt(seed, family):
    code, stats = virtualize_source(TOY, seed=seed, family=family)
    assert stats.get("virtualized", 0) >= 1
    return code


def test_self_decode_is_one_both_families():
    for fam in ("a", "b"):
        for seed in (11, 22):
            src = _virt(seed, fam)
            s, npos, ntot, reason = V.self_score(src)
            assert reason == "ok", (fam, seed, reason)
            assert s == 1.0, (fam, seed, s)
            assert npos > 0 and ntot >= 1


def test_cross_seed_below_self():
    a = _virt(11, "a")
    b = _virt(22, "a")
    ea = V.extract(a)
    assert ea["ok"]
    s, na, nt, npos = V.decode_score(b, ea)
    assert s is not None and npos > 0
    assert s < 1.0  # distinct permutations must disagree somewhere


def test_cross_family_decodes_at_chance():
    a = _virt(11, "a")
    b = _virt(11, "b")
    ea = V.extract(a)
    assert ea["ok"]
    s, na, nt, npos = V.decode_score(b, ea)
    assert s is not None
    assert s < 0.5


def test_align_matches_same_function_only():
    a = _virt(11, "a")
    b = _virt(22, "a")
    ea, eb = V.extract(a), V.extract(b)
    assert ea["ok"] and eb["ok"]
    pairs = V.align(ea, eb)
    assert len(pairs) == len(eb["functions"])  # toy: single function
    # A different function (extra MUL op) must not align.
    toy2 = TOY.replace("a = a + i", "a = a * i + 1")
    other, st = virtualize_source(toy2, seed=99, family="a")
    assert st.get("virtualized", 0) >= 1
    eo = V.extract(other)
    assert eo["ok"]
    assert V.align(ea, eo) == {}


def test_no_vm_source_excluded():
    ext = V.extract("def g(x):\n    return x + 1\n")
    assert ext["ok"] is False and ext["reason"] == "no-vm-functions"
    s, na, nt, npos = V.decode_score(
        "def g(x):\n    return x + 1\n", {"ok": True, "functions": {}})
    assert s is None and npos == 0


def test_committed_calc_builds_pass_gate():
    import glob
    base = os.path.join(os.path.dirname(__file__), "..", "docs",
                        "research", "h0h5-results", "calc")
    files = sorted(glob.glob(os.path.join(base, "h[345]_*.py")))
    assert len(files) == 18
    for f in files:
        src = open(f, encoding="utf-8").read()
        s, npos, ntot, reason = V.self_score(src)
        assert s is not None and s >= 0.80, (f, s, reason)
