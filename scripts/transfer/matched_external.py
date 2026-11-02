"""Matched-callable-count experiment on the independent (non-author) task pool.

`matched_families.py` equalised the number of module-level callables inserted
by the three transform families and re-ran `table_diversity()`'s comparison on
the 17 hand-written tasks.  The result was exact: +0.33/+0.33/0.00 before,
+0.00/+0.00/+0.00 after.  But that script's own residual-cost audit showed the
null is *forced* on 10 of those 17 tasks (`probes == k`), so the empirical
content sits on 7 tasks -- a thin base for a title-level claim.

This script applies the identical procedure to the only tasks in the project
that were not specified by the paper's author:

  * **blind** -- the 6 tasks in `scripts/transfer/blind_tasks.py`, written from
    the functions' docstrings and doctests by an author who had not read the
    research programme, over three vendored third-party modules
    (`recipes.py`, `statistics.py`, `strutils.py`);
  * **prior** -- the author's own external tasks in
    `scripts/transfer/external_tasks.py` (`all_equal`, `dotproduct`, `take`
    from recipes.py and `median_low` from statistics.py), which use the same
    modules but whose specifications the programme's author wrote.

This distinction is the point of the extension: the blind group is the
strongest independent evidence available in this repository, and it is small.

Method (identical to `matched_families.py` unless stated)
---------------------------------------------------------
1. For each task, each family and each master seed in (11, 22, 33), generate
   the artefact with

       generate_variant(src, 4, {"master_seed": seed, "pass_sets": [fam]})

   where `src` is the task's whole module (`module_source(name)`) and the
   families are `reproduce.py`'s FAM_A/FAM_B/FAM_C.  Generation is
   deterministic for a fixed source and seed, so no caching is used and the
   artefacts here are exactly what the same call would produce in
   `matched_families.py`.
2. Count module-level callables `k`: `ast.FunctionDef`, `ast.AsyncFunctionDef`
   and `ast.ClassDef` directly in `tree.body`.
3. Equalise to `max(k)` over the three families for each (task, seed) cell by
   appending

       def _nx_pad_<i>():
           return None

   to the generated source text, re-parsing with `ast.parse` and re-checking
   `k_after == k_before + pads` before measuring.  Pads are appended after
   generation, so the obfuscator never sees them.
4. Measure probes with a fresh `AccumulatingAttack().apply(path, props)` on
   both the unpadded and the padded artefact.
5. Compute the same statistic as `table_diversity()`:

       seed_only = [probes(f1, 11), probes(f1, 22), probes(f1, 33)]
       varying   = [probes(f1, 11), probes(f2, 22), probes(f1, 33)]
       diff      = mean(varying) - mean(seed_only)

   so only the seed-22 cell crosses families and a one-probe difference there
   shows up as +0.33.

Residual discrimination cost, and why this script reports two of them
---------------------------------------------------------------------
`matched_families.py` writes `probes = k + c` and calls `c = probes - k` the
`residual discrimination cost`.  That is exact only when the attacker's
candidate universe is the module-level callables counted by the AST.  On these
three vendored modules it is not:

  * the attacker collects `types.FunctionType` bindings from the executed
    module namespace, so it probes **imported functions** (`dataclass`,
    `lru_cache`, `namedtuple`, `decompress`), module-level aliases
    (`padnone = pad_none`) and closures created at module level, while it
    **never probes classes** (`Stats`, `StatisticsError`, `NormalDist`,
    `DeaccenterDict`, `HTMLTextExtractor`, `MultiReplace`);
  * therefore `m = probes`' actual candidate base can be larger *or smaller*
    than `k`, and `c = probes - k` can be negative (it is, on strutils.py),
    which makes the "forced iff c == 0" rule undefined there.

So the script reports both:

  * `c  = probes - k`  -- the definition `matched_families.py` used, kept so
    the two experiments are directly comparable;
  * `c' = probes - m`  -- the residual against the universe the attacker
    actually probes, where `m` is the number of `types.FunctionType` bindings
    in the executed module.  `c' >= 0` always, and `c' == 0` is the honest
    statement that the equality is forced.

The verdict is stated against both, and the discrepancy is itself a result.

Usage
-----
    python3 scripts/transfer/matched_external.py [--json PATH]

Deterministic; no network; writes only to a temporary directory.
"""

import argparse
import ast
import atexit
import contextlib
import io
import json
import os
import shutil
import statistics
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from scripts.diversity.generator import generate_variant  # noqa: E402
from scripts.transfer import blind_tasks, external_tasks  # noqa: E402
from scripts.transfer.accumulating_attack import AccumulatingAttack  # noqa: E402

# Copied from scripts/transfer/reproduce.py (via matched_families.py) so the
# comparison is like-for-like.
FAM_A = ["rename", "dead_code", "mba", "cfg_flatten"]
FAM_B = ["rename", "dead_code", "opaque_pred", "string_encode"]
FAM_C = ["rename", "mba", "string_encode"]
FAMILIES = (("A", FAM_A), ("B", FAM_B), ("C", FAM_C))

SEEDS = (11, 22, 33)
BUILD_INDEX = 4
PAIRINGS = (("A-vs-B", "A", "B"), ("A-vs-C", "A", "C"), ("B-vs-C", "B", "C"))
CALLABLE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

# external_tasks.py has held exactly these since it was written; median_low was
# added second and lives in statistics.py rather than recipes.py.
PRIOR_EXPECTED = ("all_equal", "dotproduct", "take", "median_low")

_TMP = tempfile.mkdtemp(prefix="nxk_matched_ext_")
atexit.register(shutil.rmtree, _TMP, True)


# --------------------------------------------------------------------------
# counting, padding, generation, measurement
# --------------------------------------------------------------------------
def callables(code):
    """Module-level callable nodes: ast.FunctionDef/AsyncFunctionDef/ClassDef."""
    return [n for n in ast.parse(code).body if isinstance(n, CALLABLE_NODES)]


def callable_count(code):
    return len(callables(code))


def probed_candidates(code):
    """The attacker's actual candidate base: types.FunctionType bindings.

    `AccumulatingAttack.apply()` does

        exec(compile(src, path, "exec"), tree_mod)
        funcs = {n: v for n, v in tree_mod.items()
                 if isinstance(v, types.FunctionType)}

    so imported functions, module-level aliases and module-level closures count,
    and classes do not.  This mirrors that line exactly.
    """
    ns = {}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(code, "<artefact>", "exec"), ns)
    return sum(1 for v in ns.values() if isinstance(v, types.FunctionType))


def pad_source(n):
    """Source text for n trivial no-op module-level callables."""
    return "".join("\ndef _nx_pad_%d():\n    return None\n" % i for i in range(n))


def add_pads(code, n):
    """Append n no-op callables to generated source; verify it still parses."""
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


def measure(code, props):
    """Probes and candidate base for one artefact.

    Probe count comes from the production path; the candidate base comes from a
    second exec because `apply()` does not return it.
    """
    path = os.path.join(_TMP, "artefact.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    with contextlib.redirect_stdout(io.StringIO()):
        probes = AccumulatingAttack().apply(path, props)["probes"]
    return {"probes": probes, "m": probed_candidates(code)}


def diff_from(cells, f1, f2):
    """table_diversity()'s statistic from a {(family, seed): probes} map."""
    seed_only = [cells[(f1, s)] for s in SEEDS]
    varying = [cells[(f1, 11)], cells[(f2, 22)], cells[(f1, 33)]]
    return statistics.mean(varying) - statistics.mean(seed_only)


# --------------------------------------------------------------------------
# task loading
# --------------------------------------------------------------------------
def load_groups():
    """(group, name, src, path, props) for every task, plus unevaluable list.

    A task is unevaluable, and is reported rather than dropped, if its target
    is no longer a module-level function or its own property set does not hold
    on the un-obfuscated target (which would make the cell meaningless).
    """
    pools = (("blind", blind_tasks, tuple(blind_tasks.TASKS)),
             ("prior", external_tasks, PRIOR_EXPECTED))
    groups, bad = [], []
    for group, mod, names in pools:
        present = set(mod.TASKS)
        for name in names:
            if name not in present:
                bad.append({"group": group, "task": name,
                            "reason": "not in %s.TASKS" % mod.__name__})
                continue
            try:
                src = mod.module_source(name)
                path = mod.source_path(name)
            except (KeyError, OSError) as exc:
                bad.append({"group": group, "task": name,
                            "reason": "module unavailable: %r" % (exc,)})
                continue
            fns = mod.functions(src, path)
            if name not in fns:
                bad.append({"group": group, "task": name,
                            "reason": "target not a module-level function"})
                continue
            props = mod.TASKS[name]["props"]
            try:
                ok = all(bool(p(fns[name])) for p in props)
            except Exception as exc:  # noqa: BLE001 - reported, not hidden
                bad.append({"group": group, "task": name,
                            "reason": "property raised on original: %r" % (exc,)})
                continue
            if not ok:
                bad.append({"group": group, "task": name,
                            "reason": "a property is false on the original"})
                continue
            groups.append((group, name, src, path, props))
    extra = [n for n in external_tasks.TASKS if n not in PRIOR_EXPECTED]
    return groups, bad, extra


# --------------------------------------------------------------------------
# measurement
# --------------------------------------------------------------------------
def measure_all(groups):
    """Generate and measure every (task, family, seed) cell, unpadded."""
    data = {}
    for group, name, src, path, props in groups:
        for fam, family in FAMILIES:
            for seed in SEEDS:
                code = generate(src, family, seed)
                got = measure(code, props)
                data[(group, name, fam, seed)] = {
                    "group": group, "name": name, "path": path,
                    "props": props, "code": code,
                    "k": callable_count(code),
                    "m": got["m"], "probes": got["probes"],
                }
    return data


def equalise(data, group, name):
    """Pads per (seed, family) to the max callable count of the task/seed cell."""
    pads = {}
    for seed in SEEDS:
        peers = [data[(group, name, f, seed)]["k"] for f, _ in FAMILIES]
        target = max(peers)
        for f, _ in FAMILIES:
            pads[(f, seed)] = target - data[(group, name, f, seed)]["k"]
    return pads


def matched(data, group, name, pads, props):
    """Measure padded artefacts; verify pad additivity in passing."""
    out, deviations = {}, []
    for f, _ in FAMILIES:
        for seed in SEEDS:
            rec = data[(group, name, f, seed)]
            padded = add_pads(rec["code"], pads[(f, seed)])
            got = measure(padded, props)
            out[(f, seed)] = got
            expected = rec["probes"] + pads[(f, seed)]
            if got["probes"] != expected:
                deviations.append({"task": name, "family": f, "seed": seed,
                                   "pads": pads[(f, seed)],
                                   "base": rec["probes"],
                                   "got": got["probes"],
                                   "expected": expected})
    return out, deviations


def task_row(data, group, name, pads, after):
    """One per-task record: counts, pads, residual costs, diffs."""
    counts = {f: data[(group, name, f, 11)]["k"] for f, _ in FAMILIES}
    bases = {f: data[(group, name, f, 11)]["m"] for f, _ in FAMILIES}
    seed_counts = {f: [data[(group, name, f, s)]["k"] for s in SEEDS]
                   for f, _ in FAMILIES}
    seed_m = {f: [data[(group, name, f, s)]["m"] for s in SEEDS]
              for f, _ in FAMILIES}
    seed_probes = {f: [data[(group, name, f, s)]["probes"] for s in SEEDS]
                   for f, _ in FAMILIES}
    seed_c = {f: [data[(group, name, f, s)]["probes"]
                  - data[(group, name, f, s)]["k"] for s in SEEDS]
              for f, _ in FAMILIES}
    seed_cm = {f: [data[(group, name, f, s)]["probes"]
                   - data[(group, name, f, s)]["m"] for s in SEEDS]
               for f, _ in FAMILIES}
    matched_probes = {f: after[(f, 11)]["probes"] for f, _ in FAMILIES}
    matched_probes_all = {f: [after[(f, s)]["probes"] for s in SEEDS]
                          for f, _ in FAMILIES}

    before_d, after_d = {}, {}
    for label, f1, f2 in PAIRINGS:
        b = {(f, s): data[(group, name, f, s)]["probes"]
             for f, _ in FAMILIES for s in SEEDS}
        a = {(f, s): after[(f, s)]["probes"]
             for f, _ in FAMILIES for s in SEEDS}
        before_d[label] = diff_from(b, f1, f2)
        after_d[label] = diff_from(a, f1, f2)

    return {
        "group": group, "task": name,
        "counts": counts, "candidate_base": bases,
        "seed_counts": seed_counts, "seed_candidate_base": seed_m,
        "seed_probes": seed_probes,
        "pads": {f: pads[(f, 11)] for f, _ in FAMILIES},
        "matched_probes": matched_probes,
        "matched_probes_all_seeds": matched_probes_all,
        "c": {f: seed_c[f][0] for f, _ in FAMILIES},
        "c_seed": seed_c,
        "cp": {f: seed_cm[f][0] for f, _ in FAMILIES},
        "cp_seed": seed_cm,
        "before": before_d, "after": after_d,
    }


def classify_c(c):
    """matched_families.py's rule, with the third case made explicit."""
    if c > 0:
        return "load-bearing"
    if c == 0:
        return "forced"
    return "undefined (c<0)"


def classify_cp(cp):
    if cp > 0:
        return "load-bearing"
    return "forced"


def check_profiles(data, group, name, pads, props):
    """Per-property surviving-candidate counts, counts matched.

    Mirrors `matched_families.survival_profile()`: identical total probe counts
    could in principle coincide while families disagree about which property
    eliminates which candidate.  Pads appear once in the first entry and are
    eliminated there.
    """
    mismatches = []
    for seed in SEEDS:
        profiles = {}
        for f, _ in FAMILIES:
            rec = data[(group, name, f, seed)]
            code = add_pads(rec["code"], pads[(f, seed)])
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
                for cand in remaining:
                    try:
                        ok = bool(pr(ns[cand]))
                    except Exception:
                        ok = False
                    if ok:
                        kept.append(cand)
                remaining = kept
            profiles[f] = tuple(profile)
        if len(set(profiles.values())) != 1:
            mismatches.append({"task": name, "seed": seed,
                               "profiles": {k: list(v)
                                            for k, v in profiles.items()}})
    return mismatches


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------
def aggregate(rows):
    """Mean diffs and forced/load-bearing counts, per group."""
    out = {}
    for group in ("blind", "prior"):
        rs = [r for r in rows if r["group"] == group]
        if not rs:
            continue
        out[group] = {
            "tasks": len(rs),
            "before": {label: round(statistics.mean(r["before"][label]
                                                    for r in rs), 2)
                       for label, _, _ in PAIRINGS},
            "after": {label: round(statistics.mean(r["after"][label]
                                                   for r in rs), 2)
                      for label, _, _ in PAIRINGS},
            "load_bearing_c": sum(1 for r in rs
                                  if r["c"]["A"] > 0),
            "forced_c": sum(1 for r in rs if r["c"]["A"] == 0),
            "undefined_c": sum(1 for r in rs if r["c"]["A"] < 0),
            "load_bearing_cp": sum(1 for r in rs if r["cp"]["A"] > 0),
            "forced_cp": sum(1 for r in rs if r["cp"]["A"] == 0),
        }
    return out


def render(rows, agg, deviations, bad, extra, seed_invariance, exact,
           profile_mismatches):
    L = []
    add = L.append

    add("## Tasks")
    add("")
    add("blind (docstring-derived, other author): %s"
        % ", ".join("`%s`" % r["task"] for r in rows if r["group"] == "blind"))
    add("")
    add("prior (author's external tasks): %s"
        % ", ".join("`%s`" % r["task"] for r in rows if r["group"] == "prior"))
    add("")
    if extra:
        add("excluded from `external_tasks.TASKS` because they are not in the "
            "prior list: %s" % ", ".join("`%s`" % n for n in extra))
        add("")
    if bad:
        add("unevaluable (reported, not dropped):")
        for b in bad:
            add("- `%s` (%s): %s" % (b["task"], b["group"], b["reason"]))
        add("")

    add("## Table 1 -- callables, pads, matched probes")
    add("")
    add("`k` is module-level callables (FunctionDef/AsyncFunctionDef/ClassDef); "
        "`m` is the attacker's candidate base (types.FunctionType bindings).")
    add("")
    add("| group | task | k A/B/C | pads A/B/C | k after | matched probes A/B/C |")
    add("|---|---|---|---|---|---|")
    for r in rows:
        k = r["counts"]
        p = r["pads"]
        mp = r["matched_probes"]
        add("| %s | `%s` | %d/%d/%d | +%d/+%d/+%d | %d | %d/%d/%d |"
            % (r["group"], r["task"], k["A"], k["B"], k["C"],
               p["A"], p["B"], p["C"],
               k["A"] + p["A"], mp["A"], mp["B"], mp["C"]))

    add("")
    add("## Table 2 -- residual discrimination cost")
    add("")
    add("`c = probes - k` is `matched_families.py`'s definition; `c' = probes - m` "
        "uses the universe the attacker actually probes. Reported at seed 11; "
        "seed-invariance is checked below.")
    add("")
    add("| group | task | m A/B/C | c A/B/C | class (c) | c' A/B/C | class (c') |")
    add("|---|---|---|---|---|---|---|")
    for r in rows:
        m, c, cp = r["candidate_base"], r["c"], r["cp"]
        cls_c = "/".join(classify_c(c[f]).split()[0] for f in ("A", "B", "C"))
        cls_cp = "/".join(classify_cp(cp[f]) for f in ("A", "B", "C"))
        add("| %s | `%s` | %d/%d/%d | %+d/%+d/%+d | %s | %+d/%+d/%+d | %s |"
            % (r["group"], r["task"], m["A"], m["B"], m["C"],
               c["A"], c["B"], c["C"], cls_c,
               cp["A"], cp["B"], cp["C"], cls_cp))

    add("")
    add("## Table 3 -- probe difference per task and pairing")
    add("")
    add("| group | task | A-vs-B before | matched | A-vs-C before | matched | B-vs-C before | matched |")
    add("|---|---|---|---|---|---|---|---|")
    for r in rows:
        b, a = r["before"], r["after"]
        add("| %s | `%s` | %+.2f | %+.2f | %+.2f | %+.2f | %+.2f | %+.2f |"
            % (r["group"], r["task"], b["A-vs-B"], a["A-vs-B"],
               b["A-vs-C"], a["A-vs-C"], b["B-vs-C"], a["B-vs-C"]))

    add("")
    add("## Aggregate by group")
    add("")
    add("| group | tasks | pairing | before | matched |")
    add("|---|---|---|---|---|")
    for group in ("blind", "prior"):
        if group not in agg:
            continue
        g = agg[group]
        for label, _, _ in PAIRINGS:
            add("| %s | %d | %s | %+.2f | %+.2f |"
                % (group, g["tasks"], label, g["before"][label],
                   g["after"][label]))
    add("")
    add("| group | tasks | load-bearing (c>0) | forced (c==0) | undefined (c<0) "
        "| load-bearing (c'>0) | forced (c'==0) |")
    add("|---|---|---|---|---|---|---|")
    for group in ("blind", "prior"):
        if group not in agg:
            continue
        g = agg[group]
        add("| %s | %d | %d | %d | %d | %d | %d |"
            % (group, g["tasks"], g["load_bearing_c"], g["forced_c"],
               g["undefined_c"], g["load_bearing_cp"], g["forced_cp"]))

    add("")
    add("## Checks")
    add("")
    add("- pad additivity: cells where `matched_probes != base_probes + pads`: "
        "**%d** / %d" % (len(deviations), len(rows) * len(FAMILIES) * len(SEEDS)))
    for d in deviations[:10]:
        add("  - `%s` %s seed %s: %d pads, base %d, got %d, expected %d"
            % (d["task"], d["family"], d["seed"], d["pads"], d["base"],
               d["got"], d["expected"]))
    add("- seed-invariance of k: %s" % seed_invariance["k"])
    add("- seed-invariance of m: %s" % seed_invariance["m"])
    add("- seed-invariance of probes: %s" % seed_invariance["probes"])
    add("- cells where matched probes are equal across A/B/C: **%d** / %d"
        % (exact["cells_equal"], exact["cells"]))
    mismatches = exact["cells"] - exact["cells_equal"]
    if mismatches:
        add("  - see per-task matched probes in Table 1")
    add("- cells where the per-property survival trajectory differs across "
        "A/B/C: **%d** / %d"
        % (len(profile_mismatches), len(rows) * len(SEEDS)))
    for m in profile_mismatches[:10]:
        add("  - `%s` seed %s: %s" % (m["task"], m["seed"], m["profiles"]))
    return "\n".join(L)


def invariance(rows, key):
    """'invariant' or a list of tasks/seeds where values move."""
    bad = []
    for r in rows:
        for f in ("A", "B", "C"):
            base = r[key][f][0]
            if any(v != base for v in r[key][f]):
                bad.append("%s/%s: %s"
                           % (r["task"], f, r[key][f]))
    return "invariant" if not bad else "VARIES: " + "; ".join(bad)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", metavar="PATH",
                    help="also write the raw tables to PATH as JSON")
    args = ap.parse_args(argv)

    groups, bad, extra = load_groups()
    data = measure_all(groups)

    rows, deviations, exact_cells, exact_equal = [], [], 0, 0
    profile_mismatches = []
    for group, name, _src, _path, props in groups:
        pads = equalise(data, group, name)
        after, devs = matched(data, group, name, pads, props)
        deviations.extend(devs)
        row = task_row(data, group, name, pads, after)
        rows.append(row)
        profile_mismatches.extend(
            check_profiles(data, group, name, pads, props))
        for seed in SEEDS:
            exact_cells += 1
            vals = {after[(f, seed)]["probes"] for f, _ in FAMILIES}
            if len(vals) == 1:
                exact_equal += 1

    agg = aggregate(rows)
    seed_invariance = {
        "k": invariance(rows, "seed_counts"),
        "m": invariance(rows, "seed_candidate_base"),
        "probes": invariance(rows, "seed_probes"),
    }
    exact = {"cells": exact_cells, "cells_equal": exact_equal}

    report = render(rows, agg, deviations, bad, extra, seed_invariance, exact,
                    profile_mismatches)
    print(report)
    print()
    print("VERDICT INPUTS: %s" % json.dumps(agg, indent=2))

    if args.json:
        cells = []
        for (group, name, fam, seed), rec in sorted(data.items()):
            cells.append({"group": group, "task": name, "family": fam,
                          "seed": seed, "k": rec["k"], "m": rec["m"],
                          "probes": rec["probes"]})
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"aggregate": agg, "rows": rows, "cells": cells,
                       "pad_deviations": deviations, "unevaluable": bad,
                       "excluded_extras": extra,
                       "seed_invariance": seed_invariance,
                       "exact": exact,
                       "profile_mismatches": profile_mismatches}, f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
