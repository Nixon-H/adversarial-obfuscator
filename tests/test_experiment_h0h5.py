"""Tests for the frozen H0-H5 experiment machinery (no full runs here).

Covers: arm resolution determinism + H5 alternation, freeze-hash
stability, D_VM cases, VM coverage, perf probe, locked config loads.
Heavy experiment runs are manual (pilot-validated), not CI-gated.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.transfer import arms as arms_mod
from scripts.transfer import extended as ext_mod


def test_arm_order_and_purposes():
    assert arms_mod.ARM_ORDER == ["H0", "H1", "H2", "H3", "H4", "H5"]
    for aid in arms_mod.ARM_ORDER:
        assert arms_mod.ARMS[aid]["purpose"]
        assert arms_mod.ARMS[aid]["pass_sets"]


def test_h0_matches_legacy_seed_control():
    psets, extra = arms_mod.resolve_options("H0", 0)
    assert psets == [["rename", "dead_code", "mba", "cfg_flatten", "vm"]]
    assert extra == {}


def test_h5_alternates_vm_family():
    _, e0 = arms_mod.resolve_options("H5", 0)
    _, e1 = arms_mod.resolve_options("H5", 1)
    assert e0["vm_dispatch"] == "a"
    assert e1["vm_dispatch"] == "b"
    assert e0["rep_diversify"] is True


def test_isolation_flags_present():
    _, extra = arms_mod.resolve_options("H2", 0)
    for k in ("cfg_flatten", "mba_subs", "obf_calls", "strip_meta",
              "break_decompiler", "code_checksums"):
        assert extra[k] is False, k
    assert extra["rep_diversify"] is True
    _, e3 = arms_mod.resolve_options("H3", 0)
    assert e3["vm_dispatch"] == "a"
    _, e4 = arms_mod.resolve_options("H4", 0)
    assert e4["vm_dispatch"] == "b"


def test_resolve_deterministic():
    assert arms_mod.resolve_options("H5", 3) == arms_mod.resolve_options("H5", 3)


def test_freeze_hash_stable_and_sensitive():
    h1 = arms_mod.config_freeze_hash()
    assert len(h1) == 64
    assert arms_mod.config_freeze_hash() == h1


def test_locked_config_loads():
    with open(os.path.join(os.path.dirname(__file__), "..", "scripts",
                           "transfer", "experiment_H0H5.json"),
              encoding="utf-8") as f:
        cfg = json.load(f)
    assert cfg["version"] == "1.0.0"
    assert cfg["n_per_arm"] == 6
    assert set(cfg["programs"]) == {"calc", "parser", "auth", "store",
                                    "codec", "sched"}


def test_detect_vm_family():
    assert ext_mod.detect_vm_family("x = 1") is None
    assert ext_mod.detect_vm_family("while _pc:\n    pass\n") is None
    assert ext_mod.detect_vm_family("if x:\n    elif _op:\n    pass\n") is None
    full_a = "while _pc:\n    elif _op == 1:\n        pass\n"
    assert ext_mod.detect_vm_family(full_a) == "a"
    full_b = "_handlers = {}\n_h_cmp = 1\n"
    assert ext_mod.detect_vm_family(full_b) == "b"
    assert ext_mod.detect_vm_family(full_a + full_b) == "both"


def test_vm_distance_cases(tmp_path):
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("x = 1\n")
    b.write_text("y = 2\n")
    assert ext_mod.vm_distance(str(a), str(b)) == 0.0
    a.write_text("while _pc:\n    elif _op:\n        pass\n")
    assert ext_mod.vm_distance(str(a), str(b)) == 1.0
    assert ext_mod.vm_distance(str(a), "/nonexistent.py") is None


def test_vm_distance_same_family(tmp_path):
    body = ("    _code = ((1, 0), (2, 1))\n"
            "    while _pc:\n        _pc = _pc\n"
            "    if True:\n        x = 1\n    elif _op:\n        x = 2\n")
    src = "def f():\n" + body
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text(src)
    b.write_text(src.replace("(1, 0), (2, 1)", "(2, 0), (1, 1)"))
    d = ext_mod.vm_distance(str(a), str(b))
    assert d == 1.0
    assert ext_mod.vm_distance(str(a), str(a)) == 0.0


def test_vm_coverage_counts(tmp_path):
    from scripts.transfer import corpus as C
    progs = C.list_programs()
    p = [x for x in progs if x["name"] == "calc"][0]
    d = C.load_program(p["dir"])
    v = tmp_path / "v.py"
    v.write_text(d["source"])
    virt, elig = ext_mod.vm_coverage(d["source"], str(v))
    assert elig == 4 and virt == 0


def test_perf_probe_trivial(tmp_path):
    m = tmp_path / "m.py"
    m.write_text("def f(x):\n    return x + 1\n")
    # perf_probe runs demo argv as SCRIPT; a bare def module runs clean.
    out = ext_mod.perf_probe(str(m), [[]])
    assert out["startup_s"] is not None and out["startup_s"] >= 0
    assert out["runs"][0]["ok"] is True
    assert out["runs"][0]["rc"] == 0
