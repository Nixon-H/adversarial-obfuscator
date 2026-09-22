"""Smoke test for the lowering-shim perf benchmark (V10 perf evidence).

Runs scripts/benchmark/lowering_perf.py with a small N and asserts
every family ratio is a finite positive float and shim results equal
plain results (correctness under timing). Deliberately does NOT
assert specific perf numbers — those vary by machine and live in
obfuscator/lowering_DESIGN.md as measured-on-this-host evidence.

Python 3.10 compatible: stdlib only, no match statements, no X|Y
annotations in evaluated positions.
"""

import ast
import math
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_benchmark_module_parses_on_310():
    path = os.path.join(REPO_ROOT, "scripts", "benchmark",
                        "lowering_perf.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    ast.parse(src, feature_version=(3, 10))


def test_small_benchmark_ratios_finite_and_parity_ok():
    from scripts.benchmark import lowering_perf as lp
    bundle = lp.run_benchmark(n=200, repeats=2)
    assert bundle["results"], "no ops benchmarked"
    assert bundle["summary"], "no family summary"
    for r in bundle["results"]:
        assert math.isfinite(r["ratio"]) and r["ratio"] > 0, r
        assert math.isfinite(r["plain_us"]) and r["plain_us"] > 0, r
        assert math.isfinite(r["shim_us"]) and r["shim_us"] > 0, r
        assert r["ok"], "parity mismatch under timing: %s" % r["op"]
    for fam, s in bundle["summary"].items():
        assert math.isfinite(s["geomean"]) and s["geomean"] > 0, fam
        assert s["all_ok"], fam


def test_family_subset_and_json_roundtrip(tmp_path):
    from scripts.benchmark import lowering_perf as lp
    bundle = lp.run_benchmark(n=100, repeats=1,
                              families=["scalar", "container"])
    assert set(bundle["summary"]) == {"scalar", "container"}
    assert bundle["results"]
    out = str(tmp_path / "lp.json")
    rc = lp.main(["--iterations", "100", "--repeats", "1",
                  "--families", "scalar,container", "--json", out,
                  ])
    assert rc == 0
    import json
    with open(out, encoding="utf-8") as f:
        back = json.load(f)
    assert set(back["summary"]) == {"scalar", "container"}


def test_all_default_families_with_callable_ops_covered():
    from scripts.benchmark import lowering_perf as lp
    from obfuscator import lowering
    node_kinds = {"BinOp", "Compare", "BoolOp", "Not", "Subscript",
                  "JoinedStr", "FormattedValue", "AugAssign"}
    uncovered = []
    # Bare-name ops shared by two families (legacy "str" overlap in
    # scalar + protocol) map to one shim token, so coverage is by op
    # NAME, not (family, op): one timed case covers both listings.
    cased = {c["op"] for c in lp.CASES}
    for fam, info in lowering.FAMILIES.items():
        for op in info["ops"]:
            if op in node_kinds:
                continue  # Phase-2 node kinds: no runtime fn yet
            if op in ("input", "open", "aiter", "anext", "breakpoint",
                      "help", "copyright", "credits", "license"):
                continue  # interactive/async/site helpers: not timed
            if op not in cased:
                uncovered.append((fam, op))
    assert not uncovered, uncovered
