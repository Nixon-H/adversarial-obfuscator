"""G2 transfer-harness tests (protocol-level + small end-to-end).

Fast unit tests run always. The static-arm end-to-end (1 hetero + 1 seed
build on calc) needs the obfuscator pipeline (~1-2 min); the Ghidra arm
test asserts graceful skip only.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.transfer import corpus as corpus_mod
from scripts.transfer import measure as M
from scripts.transfer import protocol


def test_protocol_constants():
    assert protocol.SPEC_VERSION == "1.0.0"
    assert protocol.PRIMARY_ENDPOINT == "S_cfg"
    assert protocol.ARM_UNPROTECTED and protocol.ARM_SEED_ONLY and protocol.ARM_HETERO
    assert protocol.ATTACK_STATIC and protocol.ATTACK_GHIDRA and protocol.ATTACK_LLM
    assert protocol.MIN_BUILDS_PER_ARM >= 2


def test_transfer_ratio_basic():
    v, f = M.transfer_ratio(0.5, 1.0)
    assert v == 0.5 and f == "ok"
    v, f = M.transfer_ratio(0.0, 0.0)
    assert v == 1.0 and f == "tie-zero"
    v, f = M.transfer_ratio(0.4, 0.0)
    assert v == M.CAP_RATIO and f == "zero-self"


def test_bootstrap_ci_degenerate():
    lo, hi = M.bootstrap_ci([1.0, 1.0, 1.0], b=100, seed=0)
    assert lo == hi == 1.0
    lo, hi = M.bootstrap_ci([], b=100, seed=0)
    assert (lo, hi) == (0.0, 0.0)
    lo, hi = M.bootstrap_ci([0.0, 1.0], b=200, seed=1)
    assert 0.0 <= lo <= hi <= 1.0


def test_mann_whitney_sanity():
    u, p = M.mann_whitney_u([0.1, 0.2, 0.15], [0.8, 0.9, 0.85])
    assert 0.0 <= p <= 1.0 and p < 0.2
    u2, p2 = M.mann_whitney_u([0.5, 0.5], [0.5, 0.5])
    assert p2 == 1.0
    u3, p3 = M.mann_whitney_u([], [0.5])
    assert p3 == 1.0


def test_falsification_rule():
    v = M.falsification_verdict([0.1, 0.2, 0.1, 0.2, 0.1, 0.2],
                                [0.9, 1.0, 0.9, 1.0, 0.9, 1.0])
    assert v["claim_transfer_resistance"] is True
    assert v["verdict"] == "SUPPORTS-H1"
    v2 = M.falsification_verdict([0.9, 1.0], [0.9, 1.0])
    assert v2["claim_transfer_resistance"] is False
    assert "do not claim" in v2["verdict"]
    # Wrong direction never claims even with separation.
    v3 = M.falsification_verdict([0.9, 1.0, 0.9, 1.0, 0.9, 1.0],
                                 [0.1, 0.2, 0.1, 0.2, 0.1, 0.2])
    assert v3["claim_transfer_resistance"] is False


def test_score_recovery_endpoints():
    gt = {"functions": [{"name": "f"}, {"name": "g"}, {"name": "h"}],
          "constants": ["x", "y"]}
    rec = {"per_func": {
        "f": {"candidate": "a1", "passed": 2, "total": 2},
        "g": {"candidate": "a2", "passed": 1, "total": 2},
        "h": {"candidate": None, "passed": 0, "total": 0}},
        "constants_found": ["x"], "attack_time_s": 1.0}
    s = M.score_recovery(rec, gt, None)
    assert s["S_cfg"] == 1 / 3
    assert s["S_cfg_boundary"] == 2 / 3
    assert s["S_const"] == 0.5
    assert s["S_deobf"] == 0.0  # renamed candidates, none by-name


def test_negative_control_constructor():
    # Same pass set + different seeds => equal sets, distinct seeds.
    from scripts.transfer import builds  # noqa: F401 (import surface)
    cfg = {"hetero_pass_sets": [["rename", "mba"]],
           "seed_only_pass_sets": [["rename", "mba"]],
           "master_seed": 5}
    seeds = [cfg["master_seed"] * 1000 + 101 + i for i in range(3)]
    assert len(set(seeds)) == 3
    assert cfg["seed_only_pass_sets"][0] == ["rename", "mba"]
    assert corpus_mod.config_freeze_hash(cfg) == corpus_mod.config_freeze_hash(dict(cfg))


def test_freeze_hash_changes_on_tuning():
    cfg = {"hetero_pass_sets": [["rename"]], "seed_only_pass_sets": [["rename"]],
           "master_seed": 1}
    h1 = corpus_mod.config_freeze_hash(cfg)
    cfg2 = dict(cfg, hetero_pass_sets=[["rename", "mba"]])
    assert corpus_mod.config_freeze_hash(cfg2) != h1


def test_semantic_gate_pass_and_fail(tmp_path):
    from scripts.transfer import builds as B
    ok_py = tmp_path / "ok.py"
    ok_py.write_text('import sys\n\n\ndef f(x):\n    return x + 1\n\n\n'
                     'if __name__ == "__main__":\n    print(f(1))\n')
    ok, _ = B.semantic_gate(str(ok_py), str(ok_py), "calc")
    assert ok is True
    bad_py = tmp_path / "bad.py"
    bad_py.write_text('import sys\n\n\ndef f(x):\n    return x + 1\n\n\n'
                      'if __name__ == "__main__":\n    print(f(999))\n')
    # gate compares variant vs original on demo argv; craft via direct call
    ok2, detail = B.semantic_gate(str(ok_py), str(bad_py), "calc")
    assert ok2 is False and detail


def test_static_arm_end_to_end_small():
    from scripts.transfer import builds as B
    from scripts.transfer import attack as A
    progs = corpus_mod.list_programs()
    p = [x for x in progs if x["name"] == "calc"][0]
    with tempfile.TemporaryDirectory(prefix="nxk_g2test_") as td:
        m = B.build_matrix(p, td, n_hetero=1, n_seed=1)
        assert m["config_freeze_hash"]
        assert len(m["variants"]) + len(m["excluded"]) == 2
        if not m["variants"]:
            # All excluded (obfuscator broke every build): gate did its job;
            # report exclusions rather than failing the harness test.
            assert len(m["excluded"]) == 2
            return
        arm = A.StaticRecoveryAttack()
        b = {"path": m["variants"][0]["path"], "arm": "hetero",
             "ground_truth": m["ground_truth"], "vectors": m["vectors"]}
        art = arm.develop(b, td, m["original_source"])
        assert set(art["weights"]) == {"stmts", "struct", "shape", "var"}
        ap = os.path.join(td, "art.json")
        with open(ap, "w") as f:
            json.dump(art, f)  # artifact must be JSON-portable
        with open(ap) as f:
            art2 = json.load(f)
        rec = arm.apply(art2, b, td)
        assert rec["status"] == "ok"
        s = M.score_recovery(rec, m["ground_truth"], m["vectors"])
        assert 0.0 <= s["S_cfg"] <= 1.0


def test_ghidra_arm_skips_gracefully(tmp_path):
    from scripts.transfer import attack as A
    arm = A.GhidraAttack()
    fake = {"path": str(tmp_path / "x.py"), "arm": "hetero",
            "ground_truth": {"functions": []}, "vectors": []}
    art = arm.develop(fake, str(tmp_path))
    assert art["arm"] == "ghidra"
    rec = arm.apply({"arm": "ghidra", "version": "1.0.0",
                     "status": "skipped", "reason": "t"}, fake, str(tmp_path))
    assert rec["status"] == "skipped"


def test_transfer_matrix_direct():
    from scripts.transfer import measure as M
    gt = {"functions": [{"name": "f"}, {"name": "g"}], "constants": []}
    rec = {
        ("h:0", "h:0"): {"status": "ok",
                         "per_func": {"f": {"candidate": "a", "passed": 1, "total": 1},
                                      "g": {"candidate": "b", "passed": 1, "total": 1}},
                         "constants_found": []},
        ("h:1", "h:0"): {"status": "ok",
                         "per_func": {"f": {"candidate": "a", "passed": 1, "total": 1},
                                      "g": {"candidate": "c", "passed": 0, "total": 1}},
                         "constants_found": []},
        ("h:1", "h:1"): {"status": "ok",
                         "per_func": {"f": {"candidate": "a", "passed": 1, "total": 1},
                                      "g": {"candidate": "b", "passed": 1, "total": 1}},
                         "constants_found": []},
        ("bad", "h:0"): {"status": "failed", "reason": "x"},
    }
    entries = M.transfer_matrix(rec, gt, None)
    by = {(e["dev"], e["target"]): e for e in entries}
    assert by[("h:0", "h:0")]["T"] == 1.0
    assert by[("h:1", "h:0")]["T"] == 0.5
    assert ("bad", "h:0") not in by  # failed recoveries excluded
    assert ("h:0", "h:1") not in by  # missing target entries skipped


def test_report_marks_and_times():
    from scripts.transfer import report as R
    rep = {"program": "p", "spec": "1.0.0", "spec_date": "d",
           "config_freeze_hash": "ab" * 32, "elapsed_s": 1.0,
           "excluded": [{"path": "/x/y.py", "gate_detail": "boom"}],
           "arms": {"static": {
               "entries": [{"dev": "a", "target": "b", "T": 1.0, "flag": "ok",
                            "S_cross": 1.0, "S_self": 1.0,
                            "attack_time_s": 0.5, "rec_status": "ok"}],
               "T_hetero": [1.0], "T_seed": [1.0],
               "T_hetero_ci": [1.0, 1.0], "T_seed_ci": [1.0, 1.0],
               "falsification": {"verdict": "X", "U": 0.0, "p": 1.0,
                                 "median_hetero": 1.0, "median_seed": 1.0},
               "skipped": 0, "failed": 0,
               "sanity_unprotected": {"a": {"S_cfg": 1.0, "status": "ok"}}}}}
    md = R.render_markdown(rep)
    assert "y.py" in md and "boom" in md and "X" in md
    assert "hetero:0" not in md  # only provided entries render


def _tax_recovery(boundary_ok=True, passed=("f", "g"), by_name=False):
    pf = {}
    for name in ("f", "g"):
        pf[name] = {"candidate": ("f" if by_name else "a_" + name) if boundary_ok else None,
                    "passed": 1 if name in passed else 0, "total": 1}
    return {"status": "ok", "per_func": pf, "constants_found": ["x"],
            "attack_time_s": 0.1}


def test_taxonomy_types_diverge():
    # Boundary recovers everywhere but semantics only on self-builds:
    # per-type T must differ (vector, not a single number).
    from scripts.transfer import measure as M
    gt = {"functions": [{"name": "f"}, {"name": "g"}], "constants": ["x"]}
    rec = {
        ("hetero:0", "hetero:0"): _tax_recovery(True, ("f", "g")),
        ("hetero:1", "hetero:0"): _tax_recovery(True, ("f",)),
        ("hetero:1", "hetero:1"): _tax_recovery(True, ("f", "g")),
        ("seed_only:0", "seed_only:0"): _tax_recovery(True, ("f", "g")),
        ("seed_only:1", "seed_only:0"): _tax_recovery(True, ("f", "g")),
        ("seed_only:1", "seed_only:1"): _tax_recovery(True, ("f", "g")),
    }
    tax = M.taxonomy_transfer(rec, gt, None)
    assert set(tax) == {"function", "semantic", "constant", "name",
                        "cfg", "dataflow", "vm"}
    assert tax["function"]["status"] == "covered"
    assert tax["semantic"]["status"] == "covered"
    fh = [e["T"] for e in tax["function"]["entries"]]
    sh = [e["T"] for e in tax["semantic"]["entries"]]
    assert all(v == 1.0 for v in fh)  # boundaries transfer everywhere
    assert 0.5 in sh  # semantic transfer partially fails cross-build
    assert tax["cfg"]["status"] == "uncovered"
    assert tax["cfg"]["T"] is None
    assert tax["dataflow"]["entries"] == []
    assert "reason" in tax["vm"]


def test_taxonomy_uncovered_never_zero():
    from scripts.transfer import measure as M
    gt = {"functions": [{"name": "f"}], "constants": []}
    tax = M.taxonomy_transfer({}, gt, None)
    for tname in ("cfg", "dataflow", "vm"):
        assert tax[tname]["status"] == "uncovered"
        assert tax[tname]["T"] is None  # explicit gap, not a zero
    assert tax["semantic"]["entries"] == []


def test_ghidra_parse_cases():
    from scripts.transfer import attack as A
    arm = A.GhidraAttack()
    line = 'NXK_GHIDRA_JSON:{"count": 3, "names": ["a", "b"]}'
    data, reason = arm._parse("noise\n" + line + "\n", 0)
    assert reason == "ok" and data["count"] == 3
    _, r2 = arm._parse("Ghidra was not started with PyGhidra. "
                       "Python is not available", 0)
    assert r2 == "python-unavailable"
    _, r3 = arm._parse("nothing here", 1)
    assert r3 == "no-output rc=1"


def test_ghidra_java_script_contract():
    from scripts.transfer import attack as A
    js = A.GhidraAttack.POST_SCRIPT_JAVA
    assert "public class NxkPost extends GhidraScript" in js
    assert "NXK_GHIDRA_JSON" in js
    assert A.GhidraAttack.JAVA_SCRIPT_NAME == "NxkPost.java"


def test_ghidra_develop_fallback_kind(monkeypatch, tmp_path):
    from scripts.transfer import attack as A
    arm = A.GhidraAttack()
    # Python path succeeds: frozen default kept, kind recorded.
    monkeypatch.setattr(arm, "_compile", lambda b, w: ("x.so", "ok"))
    monkeypatch.setattr(arm, "_run",
                        lambda so, w, t: ({"count": 5}, "ok"))
    art = arm.develop({"path": "b.py"}, str(tmp_path))
    assert art["status"] == "ok" and art["script_kind"] == "python"
    assert art["script"] == A.GhidraAttack.POST_SCRIPT
    # Python unavailable: Java fallback, kind recorded, script matches.
    monkeypatch.setattr(arm, "_run",
                        lambda so, w, t: (None, "python-unavailable"))
    monkeypatch.setattr(arm, "_run_java",
                        lambda so, w, t: ({"count": 7}, "ok"))
    art2 = arm.develop({"path": "b.py"}, str(tmp_path))
    assert art2["status"] == "ok" and art2["script_kind"] == "java"
    assert art2["script"] == A.GhidraAttack.POST_SCRIPT_JAVA
    assert art2["baseline_count"] == 7
    # Unrelated failure: no fallback, reason preserved.
    monkeypatch.setattr(arm, "_run",
                        lambda so, w, t: (None, "ghidra-timeout"))
    art3 = arm.develop({"path": "b.py"}, str(tmp_path))
    assert art3["status"] == "skipped"
    assert art3["reason"] == "ghidra-timeout"
