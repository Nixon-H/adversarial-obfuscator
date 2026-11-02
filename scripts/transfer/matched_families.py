"""Matched-callable-count replication of the transform-family diversity table.

`reproduce.table_diversity()` compares FAM_A / FAM_B / FAM_C by generating one
artefact per family per seed and running `AccumulatingAttack` on it.  That
comparison never controlled for module size, and `callable-count-confound.md`
showed the families do not insert equal numbers of module-level callables:
family A inserts one fewer than B and C on every task measured, and one probe
less.

This script asks the follow-up question:

    If all three families insert the SAME number of module-level callables,
    does the A-vs-B / A-vs-C probe difference go to 0.00?

Method
------
1. For each task and each of the three master seeds (11, 22, 33) used by
   `table_diversity()`, generate the artefact under each family with
   `generate_variant(src, 4, {"master_seed": s, "pass_sets": [fam]})`.
2. Count module-level callables: `ast.FunctionDef`, `ast.AsyncFunctionDef`
   and `ast.ClassDef` directly in `tree.body`.
3. Equalise each task/seed cell to the maximum of its three counts by
   appending N trivial no-op module-level functions to the artefacts that
   have fewer.  A pad is

       def _nx_pad_<i>():
           return None

   emitted as source text *after* generation, so it cannot influence the
   obfuscator.  Each padded artefact is re-parsed with `ast.parse` and its
   callable count re-checked before it is measured.
4. Re-run the identical three-way comparison with the equalised artefacts.

The comparison is copied verbatim from `table_diversity()`:

    seed_only = [probes(f1, 11), probes(f1, 22), probes(f1, 33)]
    varying   = [probes(f1, 11), probes(f2, 22), probes(f1, 33)]
    diff      = mean(varying) - mean(seed_only)

so only the seed-22 cell crosses families and a one-probe difference in that
cell shows up as +0.33.

Bias checks (reported, not assumed)
-----------------------------------
*   Pad additivity: for every task/family/seed, measure probes with 0, 1, 2
    and 3 pads.  If a pad ever costs something other than exactly one probe,
    the equalisation is not neutral and the matched table is biased.
*   Source-side padding: generate from a source that already contains the pad
    callables and compare the emitted count and probe count against the
    append-after-generation artefacts.  This tests whether the obfuscator's
    own insertion behaviour reacts to the pads, which appending after
    generation cannot (but which a reader may reasonably suspect).
*   Common-target padding: pad all three families to max+2 rather than max,
    so B and C also receive pads.  If matched diffs are still 0.00, the result
    is not an artefact of A being the only padded family.
*   Residual discrimination cost: write `probes = k + c`, where `k` is the
    number of module-level callables and `c` is the extra cost of telling the
    good candidate from the bad ones.  Matching `k` can only drive the probe
    difference to zero if `c` is already family-invariant; a behavioural
    channel (one family's transforms altering what a property accepts) would
    show up as `c` differing.  This test is not entailed by the padding.
*   Full survival trajectory: the total probe count can coincide by accident
    even when families disagree about *which* property eliminates *which*
    candidate.  Comparing the per-property surviving-candidate counts
    (pads excluded) checks the whole trajectory, not just its sum.

Usage
-----
    python3 scripts/transfer/matched_families.py

Deterministic; no network; writes only to temporary directories.
"""

import argparse
import ast
import contextlib
import io
import json
import os
import statistics
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from scripts.diversity.generator import generate_variant  # noqa: E402
from scripts.transfer.accumulating_attack import AccumulatingAttack  # noqa: E402
from scripts.transfer.real_tasks import TASKS as REAL  # noqa: E402
from scripts.transfer.real_tasks import module_source  # noqa: E402
from scripts.transfer.tasks import TASKS as SYNTH  # noqa: E402

# Copied from scripts/transfer/reproduce.py so the comparison is like-for-like.
FAM_A = ["rename", "dead_code", "mba", "cfg_flatten"]
FAM_B = ["rename", "dead_code", "opaque_pred", "string_encode"]
FAM_C = ["rename", "mba", "string_encode"]
FAMILIES = (("A", FAM_A), ("B", FAM_B), ("C", FAM_C))

SEEDS = (11, 22, 33)
BUILD_INDEX = 4
PAIRINGS = (("A-vs-B", "A", "B"), ("A-vs-C", "A", "C"), ("B-vs-C", "B", "C"))
CALLABLE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


# --------------------------------------------------------------------------
# tasks and artefacts
# --------------------------------------------------------------------------
def tasks():
    """Same task pool and source construction as reproduce._tasks()."""
    out = []
    for name, t in SYNTH.items():
        out.append(("synth", name, t["target"] + "\n" + "\n".join(t["siblings"]),
                    t["props"]))
    for name, t in REAL.items():
        out.append(("real", name, module_source(name), t["props"]))
    return out


def callables(code):
    """Module-level callable nodes: ast.FunctionDef/AsyncFunctionDef/ClassDef."""
    return [n for n in ast.parse(code).body if isinstance(n, CALLABLE_NODES)]


def callable_count(code):
    return len(callables(code))


def pad_source(n):
    """Source text for n trivial no-op module-level callables."""
    return "".join("\ndef _nx_pad_%d():\n    return None\n" % i for i in range(n))


def add_pads(code, n):
    """Append n no-op callables to generated source; verify it still parses.

    The pads are appended after generation by design: the obfuscator never
    sees them, so this cannot change its own insertion behaviour.  The
    source-side variant is tested separately in check_prepad().
    """
    if n <= 0:
        return code
    base = callable_count(code)
    names = {node.name for node in callables(code)}
    for i in range(n):
        if "_nx_pad_%d" % i in names:
            raise AssertionError("pad name collides with generated name")
    out = code.rstrip("\n") + "\n" + pad_source(n)
    ast.parse(out)  # must still parse
    got = callable_count(out)
    if got != base + n:
        raise AssertionError("padding changed count by %d, not %d" % (got - base, n))
    return out


def generate(src, family, seed):
    """Generate one artefact, silencing the obfuscator's advisory warnings."""
    with contextlib.redirect_stdout(io.StringIO()):
        return generate_variant(src, BUILD_INDEX,
                                {"master_seed": seed, "pass_sets": [family]})


def probes(code, props):
    """Run the accumulating attacker on one artefact and return its probes."""
    td = tempfile.mkdtemp(prefix="nxk_matched_")
    path = os.path.join(td, "b.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    # Some real-task sources carry a `_demo` helper that is itself a candidate
    # callable; properties call it and it prints.  Silencing property
    # side-effects cannot change the probe count, but it keeps the report
    # clean.  The same silencing applies to every family and both conditions.
    with contextlib.redirect_stdout(io.StringIO()):
        return AccumulatingAttack().apply(path, props)["probes"]


def diff_from(cells, f1, f2):
    """table_diversity()'s statistic from a {(family, seed): probes} map."""
    seed_only = [cells[(f1, s)] for s in SEEDS]
    varying = [cells[(f1, 11)], cells[(f2, 22)], cells[(f1, 33)]]
    return statistics.mean(varying) - statistics.mean(seed_only)


# --------------------------------------------------------------------------
# measurement
# --------------------------------------------------------------------------
def measure():
    """Generate every artefact once; record counts and probe counts."""
    data = {}
    for kind, name, src, props in tasks():
        for fam, family in FAMILIES:
            for seed in SEEDS:
                code = generate(src, family, seed)
                data[(name, fam, seed)] = {
                    "kind": kind,
                    "props": props,
                    "src": src,
                    "code": code,
                    "count": callable_count(code),
                }
    return data


def equalise(data, slack=0):
    """Pad each task/seed cell to max(family counts)+slack.

    Pads are computed per (task, seed) because that is the cell the
    comparison actually contrasts: at seed 22 the varying term replaces
    family f1's artefact with family f2's.  Counts turn out to be
    seed-invariant, but the script does not rely on that.
    """
    pads = {}
    for (name, fam, seed), rec in data.items():
        peers = [data[(name, f, seed)]["count"] for f, _ in FAMILIES]
        target = max(peers) + slack
        pads[(name, fam, seed)] = target - rec["count"]
    return pads


def probe_table(data, pads):
    """Probe counts for the padded artefacts, keyed by (name, fam, seed)."""
    out = {}
    for (name, fam, seed), rec in data.items():
        padded = add_pads(rec["code"], pads[(name, fam, seed)])
        out[(name, fam, seed)] = probes(padded, rec["props"])
    return out


def matched_table(data, pads, probe_after):
    """Per-task, per-pairing diffs before and after equalisation."""
    rows = []
    for name in dict.fromkeys(k[0] for k in data):
        before, after = {}, {}
        for label, f1, f2 in PAIRINGS:
            b = {(f, s): data[(name, f, s)]["probes"] for f, _ in FAMILIES
                 for s in SEEDS}
            a = {(f, s): probe_after[(name, f, s)] for f, _ in FAMILIES
                 for s in SEEDS}
            before[label] = diff_from(b, f1, f2)
            after[label] = diff_from(a, f1, f2)
        counts = {f: data[(name, f, 11)]["count"] for f, _ in FAMILIES}
        seed_counts = {f: [data[(name, f, s)]["count"] for s in SEEDS]
                       for f, _ in FAMILIES}
        added = {f: pads[(name, f, 11)] for f, _ in FAMILIES}
        rows.append({"task": name, "kind": data[(name, "A", 11)]["kind"],
                     "counts": counts, "seed_counts": seed_counts,
                     "pads": added, "before": before, "after": after})
    return rows


# --------------------------------------------------------------------------
# bias checks
# --------------------------------------------------------------------------
def check_additivity(data, max_pads=3):
    """Does each appended pad cost exactly one probe, for every cell?"""
    deviations = []
    for (name, fam, seed), rec in data.items():
        base = probes(rec["code"], rec["props"])
        for k in range(1, max_pads + 1):
            got = probes(add_pads(rec["code"], k), rec["props"])
            if got != base + k:
                deviations.append({"task": name, "family": fam, "seed": seed,
                                   "pads": k, "base": base, "got": got,
                                   "expected": base + k})
    return deviations


def survival_profile(code, props):
    """Per-property count of surviving candidates, mirroring apply().

    `AccumulatingAttack.apply()` starts each fresh attack with no learned
    ordering, so properties run in list order.  The returned tuple is the
    number of candidates probed at each property; a pad appears once, in the
    first entry, and is then eliminated.
    """
    ns = {}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(code, "<artefact>", "exec"), ns)
        remaining = [n for n, v in ns.items()
                     if isinstance(v, types.FunctionType)]
        profile = []
        for pr in props:
            if len(remaining) <= 1:
                break
            profile.append(len(remaining))
            kept = []
            for name in remaining:
                try:
                    ok = bool(pr(ns[name]))
                except Exception:
                    ok = False
                if ok:
                    kept.append(name)
            remaining = kept
    return tuple(profile)


def check_profiles(data, pads):
    """Compare the full survival trajectory across families, counts matched."""
    mismatches = []
    for name in dict.fromkeys(k[0] for k in data):
        for seed in SEEDS:
            profiles = {}
            for fam, _ in FAMILIES:
                code = add_pads(data[(name, fam, seed)]["code"],
                                pads[(name, fam, seed)])
                profiles[fam] = survival_profile(code,
                                                 data[(name, fam, seed)]["props"])
            if len(set(profiles.values())) != 1:
                mismatches.append({"task": name, "seed": seed,
                                   "profiles": {k: list(v) for k, v in
                                                profiles.items()}})
    return mismatches


def check_prepad(data, n=2):
    """Generate from a source that ALREADY contains n pads.

    If the obfuscator's own insertion behaviour reacts to the pads, the
    emitted callable count or probe count will differ from base+n.  That is
    the bias question; appending after generation cannot have it, but this
    measures whether it would matter if it did.
    """
    rows = []
    for (name, fam, seed), rec in data.items():
        src_padded = rec["src"].rstrip("\n") + "\n" + pad_source(n)
        code = generate(src_padded, dict(FAMILIES)[fam], seed)
        rows.append({"task": name, "family": fam, "seed": seed,
                     "base_count": rec["count"],
                     "pre_count": callable_count(code),
                     "base_probes": rec["probes"],
                     "pre_probes": probes(code, rec["props"]),
                     "post_count": rec["count"] + n,
                     "post_probes": rec["probes"] + n})
    return rows


def common_target_table(data, slack):
    """Diff table when every family is padded to max+slack (all get pads)."""
    pads = equalise(data, slack=slack)
    after = probe_table(data, pads)
    out = {}
    for label, f1, f2 in PAIRINGS:
        vals = []
        for name in dict.fromkeys(k[0] for k in data):
            cells = {(f, s): after[(name, f, s)] for f, _ in FAMILIES
                     for s in SEEDS}
            vals.append(diff_from(cells, f1, f2))
        out[label] = round(statistics.mean(vals), 2)
    return out, pads


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------
def render(data, pads, rows, deviations, prepad_rows, slack_result,
           profile_mismatches):
    lines = []
    add = lines.append

    add("## Callable counts before equalisation")
    add("")
    add("| task | kind | A | B | C | per-seed A/B/C |")
    add("|---|---|---|---|---|---|")
    for r in rows:
        c = r["counts"]
        sc = r["seed_counts"]
        same = all(len(set(sc[f])) == 1 for f in ("A", "B", "C"))
        add("| `%s` | %s | %d | %d | %d | %s%s |"
            % (r["task"], r["kind"], c["A"], c["B"], c["C"],
               "/".join("%d" % c[f] for f in ("A", "B", "C")),
               " (seed-invariant)" if same else " (**varies by seed**)"))

    add("")
    add("## Equalisation")
    add("")
    add("| task | A pads | B pads | C pads | count after |")
    add("|---|---|---|---|---|")
    for r in rows:
        p = r["pads"]
        add("| `%s` | +%d | +%d | +%d | %d |"
            % (r["task"], p["A"], p["B"], p["C"],
               r["counts"]["A"] + p["A"]))

    add("")
    add("## Probe difference per task and pairing")
    add("")
    add("| task | A-vs-B before | A-vs-B matched | A-vs-C before | A-vs-C matched | B-vs-C before | B-vs-C matched |")
    add("|---|---|---|---|---|---|---|")
    for r in rows:
        b, a = r["before"], r["after"]
        add("| `%s` | %+.2f | %+.2f | %+.2f | %+.2f | %+.2f | %+.2f |"
            % (r["task"], b["A-vs-B"], a["A-vs-B"], b["A-vs-C"], a["A-vs-C"],
               b["B-vs-C"], a["B-vs-C"]))

    agg_b = {label: round(statistics.mean(r["before"][label] for r in rows), 2)
             for label, _, _ in PAIRINGS}
    agg_a = {label: round(statistics.mean(r["after"][label] for r in rows), 2)
             for label, _, _ in PAIRINGS}
    add("| **mean over %d tasks** | **%+.2f** | **%+.2f** | **%+.2f** | **%+.2f** | **%+.2f** | **%+.2f** |"
        % (len(rows), agg_b["A-vs-B"], agg_a["A-vs-B"], agg_b["A-vs-C"],
           agg_a["A-vs-C"], agg_b["B-vs-C"], agg_a["B-vs-C"]))

    add("")
    add("## Bias checks")
    add("")
    add("### Pad additivity (0,1,2,3 pads; expected probes = base + pads)")
    add("")
    add("- cells measured: %d" % len(data))
    add("- cells where a pad did not cost exactly one probe: **%d**"
        % len(deviations))
    for d in deviations[:10]:
        add("  - `%s` %s seed %s: %d pads -> %d probes (expected %d)"
            % (d["task"], d["family"], d["seed"], d["pads"], d["got"],
               d["expected"]))

    bad_count = [r for r in prepad_rows
                 if r["pre_count"] != r["post_count"]]
    bad_probe = [r for r in prepad_rows
                 if r["pre_probes"] != r["post_probes"]]
    add("")
    add("### Source-side padding vs append-after-generation (2 pads)")
    add("")
    add("- cells where emitted callable count differs: **%d** / %d"
        % (len(bad_count), len(prepad_rows)))
    for r in bad_count[:10]:
        add("  - `%s` %s seed %s: pre %d, post %d"
            % (r["task"], r["family"], r["seed"], r["pre_count"],
               r["post_count"]))
    add("- cells where probe count differs: **%d** / %d"
        % (len(bad_probe), len(prepad_rows)))
    for r in bad_probe[:10]:
        add("  - `%s` %s seed %s: pre %d, post %d"
            % (r["task"], r["family"], r["seed"], r["pre_probes"],
               r["post_probes"]))

    add("")
    add("### Symmetric padding to max+2 (B and C padded too)")
    add("")
    add("| pairing | matched diff (max) | matched diff (max+2) |")
    add("|---|---|---|")
    for label, _, _ in PAIRINGS:
        add("| %s | %+.2f | %+.2f |"
            % (label, agg_a[label], slack_result[label]))

    add("")
    add("### Residual discrimination cost, `c = probes - callable count`")
    add("")
    add("`k` is the family's own (unpadded) count.  Matching `k` removes the")
    add("difference only if `c` is already family-invariant; this is measured,")
    add("not implied by the padding.")
    add("")
    add("| task | k (A/B/C) | c (A/B/C) | spread |")
    add("|---|---|---|---|")
    spreads = []
    for name in dict.fromkeys(k[0] for k in data):
        k = [data[(name, f, 11)]["count"] for f, _ in FAMILIES]
        c_by_fam = [[data[(name, f, s)]["probes"] - data[(name, f, s)]["count"]
                     for s in SEEDS] for f, _ in FAMILIES]
        spread = max(max(v) for v in c_by_fam) - min(min(v) for v in c_by_fam)
        spreads.append(spread)
        add("| `%s` | %d/%d/%d | %s | %d |"
            % (name, k[0], k[1], k[2],
               "/".join(str(v[0]) for v in c_by_fam), spread))
    add("")
    add("max spread in residual discrimination cost: **%d probe(s)**"
        % max(spreads))

    add("")
    add("### Full survival trajectory (counts matched, pads included)")
    add("")
    add("- task/seed cells compared: **%d**" % (len(data) // len(FAMILIES) * 1))
    add("- cells where the per-property surviving-candidate counts differ "
        "across families: **%d**" % len(profile_mismatches))
    for m in profile_mismatches[:10]:
        add("  - `%s` seed %s: %s" % (m["task"], m["seed"], m["profiles"]))
    return "\n".join(lines), agg_b, agg_a


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", metavar="PATH",
                    help="also write the raw tables to PATH as JSON")
    args = ap.parse_args(argv)

    data = measure()
    for key, rec in data.items():
        rec["probes"] = probes(rec["code"], rec["props"])

    pads = equalise(data)
    probe_after = probe_table(data, pads)
    rows = matched_table(data, pads, probe_after)

    deviations = check_additivity(data)
    prepad_rows = check_prepad(data)
    profile_mismatches = check_profiles(data, pads)
    slack_result, _ = common_target_table(data, slack=2)

    report, agg_b, agg_a = render(data, pads, rows, deviations, prepad_rows,
                                  slack_result, profile_mismatches)
    print(report)
    print()
    print("VERDICT INPUTS: before %s -> after %s"
          % (json.dumps(agg_b), json.dumps(agg_a)))

    if args.json:
        cells = [{"task": name, "family": fam, "seed": seed,
                  "kind": rec["kind"], "count": rec["count"],
                  "pads": pads[(name, fam, seed)],
                  "probes": rec["probes"],
                  "probes_matched": probe_after[(name, fam, seed)]}
                 for (name, fam, seed), rec in sorted(data.items())]
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"aggregate_before": agg_b, "aggregate_after": agg_a,
                       "rows": rows, "cells": cells,
                       "pad_deviations": deviations, "prepad": prepad_rows,
                       "profile_mismatches": profile_mismatches,
                       "common_target_max_plus_2": slack_result}, f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
