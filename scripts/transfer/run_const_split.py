"""T_const_split runner (Experiment v2.0, amendments 1-2).

Builds the registered 2x2 constant-hiding factorial, applies the frozen
semantic gate to every variant, then scores every ordered (develop,
apply) build pair with :mod:`scripts.transfer.const_attack`.

Nothing here is tunable at run time: the arm table, the seed block and
the scoring rule are the ones registered in
``docs/research/protocol-v2.md`` before the first number was taken.
Amendment 2 (flatten folded sequences) is an instrument-validity fix;
both the corrected and the disclosed pre-amendment aggregates are
emitted from the same builds.

Usage:
    python3 -m scripts.transfer.run_const_split [--out DIR] [--programs N]

Outputs ``results.json`` and ``RESULTS.md`` in ``--out``.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

from scripts.transfer import arms as arms_mod
from scripts.transfer import builds as builds_mod
from scripts.transfer import const_attack
from scripts.transfer import corpus as corpus_mod
from scripts.diversity.generator import DiversityGenerator

# --- registered constants (amendment 1) ---------------------------------

ARMS = {
    "C0": {"split_vars": False, "unfold_constants": False},
    "C1": {"split_vars": True, "unfold_constants": False},
    "C2": {"split_vars": False, "unfold_constants": True},
    "C3": {"split_vars": True, "unfold_constants": True},
}
ARM_ORDER = ["C0", "C1", "C2", "C3"]
PASS_SET = ["rename"]
SEED_BLOCK = 201
N_BUILDS = 3
MIN_CONSTANTS = 3
MIN_GATE_S = 0.80
STR_GATE_TOL = 1e-9


def freeze_hash(flatten=True):
    """sha256 over the arm table + seed block + instrument params.

    ``flatten=False`` reproduces the amendment-1 hash, so the disclosed
    pre-amendment table is traceable to the spec that produced it.
    """
    canonical = {
        "arms": ARMS,
        "order": ARM_ORDER,
        "pass_set": PASS_SET,
        "seed_block": SEED_BLOCK,
        "n_builds": N_BUILDS,
        "min_constants": MIN_CONSTANTS,
        "min_gate_s": MIN_GATE_S,
        "min_text_len": const_attack.MIN_TEXT_LEN,
        "isolation": arms_mod.ISOLATION_OFF,
    }
    if flatten:
        canonical["instrument_version"] = 2
        canonical["flatten_sequences"] = True
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True).encode()).hexdigest()


def _extra_options(arm):
    extra = dict(arms_mod.ISOLATION_OFF)
    extra.update(ARMS[arm])
    return extra


def _seed(master_seed, build_index):
    return master_seed * 1000 + SEED_BLOCK + build_index


def build_arm(prog_entry, out_root):
    """Build every (arm, build) variant for one program + gate them."""
    prog = corpus_mod.load_program(prog_entry["dir"])
    name = prog_entry["name"]
    out_dir = os.path.join(out_root, name)
    os.makedirs(out_dir, exist_ok=True)

    orig_path = os.path.join(out_dir, "unprotected.py")
    with open(orig_path, "w", encoding="utf-8") as fh:
        fh.write(prog["source"])

    records, excluded = [], []
    for arm in ARM_ORDER:
        for i in range(N_BUILDS):
            seed = _seed(prog["config"]["master_seed"], i)
            gen = DiversityGenerator(config={
                "master_seed": seed,
                "pass_sets": [PASS_SET],
                "extra_options": _extra_options(arm),
            })
            with tempfile.TemporaryDirectory(prefix="nxk_const_") as td:
                path = gen.generate(orig_path, 1, td)[0]
                with open(path, encoding="utf-8") as fh:
                    code = fh.read()
            dst = os.path.join(out_dir, "%s_%d.py" % (arm, i))
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write(code)

            ok, detail = builds_mod.semantic_gate(orig_path, dst, name)
            rec = {"arm": arm, "build": i, "path": dst, "seed": seed,
                   "gate_passed": ok, "gate_detail": detail,
                   "source": code}
            (records if ok else excluded).append(rec)
    return {
        "program": name,
        "split": prog_entry["split"],
        "records": records,
        "excluded": excluded,
        "config_freeze_hash": corpus_mod.config_freeze_hash(prog["config"]),
        "n_constants_source": const_attack.extract(prog["source"])["n"],
        "n_constants_source_pre": const_attack.extract(
            prog["source"], flatten=False)["n"],
    }


def score_program(built, flatten=True):
    """Score every ordered build pair. Returns cells + exclusions.

    ``flatten=True`` is the amendment-2 instrument; ``False`` reproduces
    amendment 1 for the disclosed comparison.
    """
    recs = built["records"]
    profiles = {}
    for r in recs:
        prof = const_attack.extract(r["source"], flatten=flatten)
        if prof["ok"]:
            profiles[(r["arm"], r["build"])] = prof

    # Denominator gate: S(B_j|P_j) must be 1.00 for every usable build.
    denom_fail = []
    for key, prof in profiles.items():
        s, total, hits = const_attack.score(prof, prof)
        if s is None or abs(s - 1.0) > STR_GATE_TOL:
            denom_fail.append({"build": list(key), "S_self": s,
                               "n": total, "hits": hits})

    cells, excluded = {}, []
    for a_i in ARM_ORDER:
        for a_j in ARM_ORDER:
            pairs = []
            for bi in range(N_BUILDS):
                pi = profiles.get((a_i, bi))
                if pi is None:
                    continue
                for bj in range(N_BUILDS):
                    if a_i == a_j and bi == bj:
                        continue          # self-pair is the denominator
                    pj = profiles.get((a_j, bj))
                    if pj is None:
                        continue
                    s_all, n_all, h_all = const_attack.score(pi, pj)
                    s_int, n_int, h_int = const_attack.score(pi, pj, tag="i")
                    s_str, n_str, h_str = const_attack.score(pi, pj, tag="s")
                    if s_all is None or n_all < MIN_CONSTANTS:
                        excluded.append({"from": [a_i, bi], "to": [a_j, bj],
                                         "reason": "constants<%d" % MIN_CONSTANTS})
                        continue
                    pairs.append({"S": s_all, "n": n_all, "hits": h_all,
                                  "S_int": s_int, "n_int": n_int,
                                  "S_str": s_str, "n_str": n_str})
            if not pairs:
                continue
            def _mean(key):
                vals = [p[key] for p in pairs if p.get(key) is not None]
                return sum(vals) / len(vals) if vals else None
            cells["%s>%s" % (a_i, a_j)] = {
                "from": a_i, "to": a_j,
                "S": _mean("S"), "n": _mean("n"),
                "S_int": _mean("S_int"), "n_int": _mean("n_int"),
                "S_str": _mean("S_str"), "n_str": _mean("n_str"),
                "n_pairs": len(pairs),
            }
    return {"cells": cells, "excluded": excluded, "denom_fail": denom_fail}


def compute_T(cells):
    """T and the matched same-arm control that makes T interpretable.

    ``S(B_j|P_j)`` is 1.00 by construction, so the protocol's literal
    ``T = S_cross / S_self`` would read any absolute recovery loss as
    "transfer resistance" -- e.g. a rule that hides 30% of literals in
    every build gives T = 0.70 without resisting anything, because the
    attack is equally weak against the *same* arm.

    The informative control is therefore the matched same-arm cell
    ``B->B``: cross-arm ``A->B`` only demonstrates transfer resistance if
    it falls below what the attacker already achieves against B's own
    builds. ``delta`` is that difference; ``human`` labels it.
    """
    for key, c in cells.items():
        s = c.get("S")
        c["T"] = s if s is None else s / 1.0
        si = c.get("S_int")
        c["T_int"] = si if si is None else si / 1.0
        a, b = key.split(">")
        if a == b:
            c["S_control"] = s
            c["delta"] = None if s is None else 0.0
        else:
            ctrl = (cells.get("%s>%s" % (b, b)) or {}).get("S")
            c["S_control"] = ctrl
            c["delta"] = (None if (s is None or ctrl is None) else s - ctrl)
    return cells


def _fmt(x, nd=3):
    return "n/a" if x is None else ("%.*f" % (nd, x))


def render_markdown(report):
    lines = []
    lines.append("# Experiment v2.0 — T_const_split (amendments 1-2)\n")
    lines.append("Pre-registered arm and instrument: "
                 "`docs/research/protocol-v2.md`, amendments 1 and 2 "
                 "(both written before the number they govern).\n")
    lines.append("**config_freeze_hash_const**: `%s`  " % report["freeze_hash"])
    lines.append("**pre-amendment (disclosed)**: `%s`\n"
                 % report["freeze_hash_pre"])
    lines.append("Builds per arm per program: %d. Seeds block: +%d. "
                 "Semantic gate: every variant or excluded.\n"
                 % (N_BUILDS, SEED_BLOCK))

    agg = report["aggregate"]
    lines.append("## Aggregate (mean over programs)\n")
    lines.append("`delta` = S(A->B) minus S(B->B), the matched same-arm "
                 "control. A negative delta is transfer resistance; zero is "
                 "absolute-only loss.\n")
    lines.append("| cell | S_all | S_int | S_str (control) | same-arm control | delta | n_int | pairs |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for key in sorted(agg, key=lambda k: (ARM_ORDER.index(k.split(">")[0]),
                                          ARM_ORDER.index(k.split(">")[1]))):
        c = agg[key]
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %d |"
                     % (key, _fmt(c["S"]), _fmt(c["S_int"]),
                        _fmt(c["S_str"]), _fmt(c.get("S_control")),
                        _fmt(c.get("delta")), _fmt(c["n_int"], 1),
                        c["n_pairs"]))
    lines.append("")
    lines.append("### Verdict\n")
    lines.append(report["verdict"])
    lines.append("")

    pre = report.get("aggregate_pre") or {}
    if pre:
        lines.append("### Pre-amendment instrument (disclosed)\n")
        lines.append("Same builds, amendment-1 extraction (folded sequences "
                     "dropped). Reported because the correction was made "
                     "after a number existed; the table above is primary.\n")
        lines.append("| cell | S_all | S_int | S_str | same-arm control | delta | n_int |")
        lines.append("|---|---|---|---|---|---|---|")
        for key in sorted(pre, key=lambda k: (ARM_ORDER.index(k.split(">")[0]),
                                              ARM_ORDER.index(k.split(">")[1]))):
            c = pre[key]
            lines.append("| %s | %s | %s | %s | %s | %s | %s |"
                         % (key, _fmt(c["S"]), _fmt(c["S_int"]),
                            _fmt(c["S_str"]), _fmt(c.get("S_control")),
                            _fmt(c.get("delta")), _fmt(c["n_int"], 1)))
        lines.append("")
        lines.append("Pre-amendment verdict: %s" % report.get("verdict_pre", ""))
        lines.append("")

    lines.append("## Per program\n")
    for prog in report["programs"]:
        lines.append("### %s (%s)\n" % (prog["program"], prog["split"]))
        lines.append("Source constants: %d corrected (%d pre-amendment). "
                     "Usable builds: %d. Excluded: %d."
                     % (prog["n_constants_source"],
                        prog.get("n_constants_source_pre", 0),
                        len(prog["records"]), len(prog["excluded"])))
        lines.append("")
        lines.append("| cell | S_all | S_int | S_str | same-arm control | delta | n_int |")
        lines.append("|---|---|---|---|---|---|---|")
        for key, c in sorted(prog["cells"].items()):
            lines.append("| %s | %s | %s | %s | %s | %s | %s |"
                         % (key, _fmt(c["S"]), _fmt(c["S_int"]),
                            _fmt(c["S_str"]), _fmt(c.get("S_control")),
                            _fmt(c.get("delta")), _fmt(c["n_int"], 1)))
        lines.append("")
    lines.append("## Gates\n")
    lines.append("- Denominator `S(B_j|P_j)` = 1.00 for every usable build: %s"
                 % ("PASS" if not report["denom_fail_all"] else "FAIL"))
    lines.append("- Negative control C0->C0 >= %.2f: %s"
                 % (MIN_GATE_S, _fmt(report["control_c0c0"])))
    lines.append("- String specificity control stays 1.00 in every cell: %s"
                 % ("PASS" if report["string_control_ok"] else "FAIL"))
    lines.append("")
    if report["notes"]:
        lines.append("## Notes\n")
        for n in report["notes"]:
            lines.append("- %s" % n)
        lines.append("")
    return "\n".join(lines)


def _aggregate(cells_by_key):
    out = {}
    for key, rows in cells_by_key.items():
        def _mean(field):
            vals = [r[field] for r in rows if r.get(field) is not None]
            return sum(vals) / len(vals) if vals else None
        out[key] = {
            "S": _mean("S"), "T": _mean("T"),
            "S_int": _mean("S_int"), "T_int": _mean("T_int"),
            "S_str": _mean("S_str"),
            "S_control": _mean("S_control"),
            "delta": _mean("delta"),
            "n_int": _mean("n_int"),
            "n_pairs": sum(r["n_pairs"] for r in rows),
        }
    return out


def _verdict(aggregate):
    """Verdict + worst delta/loss, from the matched same-arm controls."""
    cross = {k: c for k, c in aggregate.items()
             if k.split(">")[0] != k.split(">")[1]}
    deltas = [c["delta"] for c in cross.values() if c.get("delta") is not None]
    min_cross = min((c["S"] for c in cross.values() if c.get("S") is not None),
                    default=None)
    max_loss = None if min_cross is None else 1.0 - min_cross
    max_delta = min(deltas) if deltas else None
    if max_delta is None:
        return ("UNMEASURED: no cross-arm cell produced a score, so the "
                "endpoint has no value in this corpus."), None, None
    if max_delta < -0.05:
        return (("TRANSFER RESISTANCE OBSERVED: the worst cross-arm cell is "
                 "%.3f below its matched same-arm control. Absolute loss %.3f. "
                 "This is the only pattern that supports the hypothesis.")
                % (max_delta, max_loss or 0.0)), max_delta, max_loss
    return (("NO TRANSFER RESISTANCE. Cross-arm cells sit at their matched "
             "same-arm controls (worst delta %+.3f). Absolute recovery loss "
             "is %.3f, and that loss is identical whether the attacker "
             "applies the constants to another build of the same arm or to "
             "the protected arm: the hiding rule is build-invariant, so it "
             "lowers the ceiling without changing transfer. Any T below "
             "1.00 here is absolute loss, not transfer resistance.")
            % (max_delta, max_loss or 0.0)), max_delta, max_loss


def run(out_dir, max_programs=None):
    progs = corpus_mod.list_programs()
    if max_programs:
        progs = progs[:max_programs]
    os.makedirs(out_dir, exist_ok=True)
    built = [build_arm(p, out_dir) for p in progs]

    per_program, agg_cells, agg_pre, all_denom_fail = [], {}, {}, []
    for b in built:
        corrected = score_program(b, flatten=True)
        pre = score_program(b, flatten=False)
        cells = compute_T(corrected["cells"])
        pre_cells = compute_T(pre["cells"])
        per_program.append({
            "program": b["program"], "split": b["split"],
            "records": [{k: v for k, v in r.items() if k != "source"}
                        for r in b["records"]],
            "excluded": b["excluded"], "cells": cells, "pre_cells": pre_cells,
            "cell_exclusions": corrected["excluded"],
            "n_constants_source": b["n_constants_source"],
            "n_constants_source_pre": b["n_constants_source_pre"],
        })
        all_denom_fail.extend(corrected["denom_fail"])
        for key, c in cells.items():
            agg_cells.setdefault(key, []).append(c)
        for key, c in pre_cells.items():
            agg_pre.setdefault(key, []).append(c)

    aggregate = _aggregate(agg_cells)
    aggregate_pre = _aggregate(agg_pre)
    verdict, max_delta, max_loss = _verdict(aggregate)
    verdict_pre, max_delta_pre, max_loss_pre = _verdict(aggregate_pre)

    string_vals = [c["S_str"] for c in aggregate.values()
                   if c.get("S_str") is not None]
    string_ok = all(abs(v - 1.0) <= STR_GATE_TOL for v in string_vals)
    control = (aggregate.get("C0>C0") or {}).get("S")

    notes = []
    n_const = [p["n_constants_source"] for p in per_program]
    n_const_pre = [p["n_constants_source_pre"] for p in per_program]
    n_int_used = [c.get("n_int") for c in aggregate.values()
                  if c.get("n_int") is not None]
    notes.append("Runtime: CPython %s." % sys.version.split()[0])
    notes.append("Instrument: amendment 2 (folded sequences flattened). "
                 "The pre-amendment aggregate is disclosed below; it drops "
                 "every element of a folded tuple/list/dict-key constant. "
                 "The corpus carries only 2-3 folded elements per program "
                 "(%d-%d constants corrected vs %d-%d pre-amendment), but "
                 "the sensitivity fixture carries 20 in one display "
                 "(22 ints corrected vs 2 pre-amendment)."
                 % (min(n_const), max(n_const),
                    min(n_const_pre), max(n_const_pre)))
    notes.append("Denominator power is low by construction: the corpus "
                 "programs carry %d-%d literal constants in total, and "
                 "the integer subset used by the split arm averages %s per "
                 "cell. A 1.00 here is a low-power 1.00, not a precise one."
                 % (min(n_const), max(n_const),
                    _fmt(sum(n_int_used) / len(n_int_used), 1)
                    if n_int_used else "n/a"))
    notes.append("`split_vars` only rewrites `name = <int>` assignments and "
                 "`unfold_constants` only rewrites ints in (1, 1000); the "
                 "corpus has few of either, so the registered arms act on a "
                 "small population. This is reported rather than fixed after "
                 "the fact (anti-tuning rule).")
    notes.append("Mechanism: `unfold_constants` has three branches, but the "
                 "compiler folds `(v^m)^m` and `(b<<s)+r` back to `v`; only "
                 "`sum([parts])` survives into the bytecode pool. The other "
                 "two branches hide `v` from source-text search but not from "
                 "the compiled pool this endpoint measures.")
    notes.append("Scope: literal search only. `C` split as `C ^ m` and `m` "
                 "is algebraically recoverable; a T below 1.00 would support "
                 "'hides literals from search', never 'hides values'.")
    if (max_delta is not None and max_delta_pre is not None
            and (max_delta < -0.05) != (max_delta_pre < -0.05)):
        notes.append("VERDICT CHANGED between instruments: pre-amendment "
                     "worst delta %s (loss %s), corrected %s (loss %s). "
                     "The corrected instrument is primary by amendment 2."
                     % (_fmt(max_delta_pre), _fmt(max_loss_pre),
                        _fmt(max_delta), _fmt(max_loss)))
    else:
        notes.append("The disclosed pre-amendment instrument gives the same "
                     "verdict (worst delta %s vs %s corrected)."
                     % (_fmt(max_delta_pre), _fmt(max_delta)))

    report = {
        "freeze_hash": freeze_hash(True),
        "freeze_hash_pre": freeze_hash(False),
        "spec": "docs/research/protocol-v2.md amendments 1-2",
        "arms": ARMS, "seed_block": SEED_BLOCK, "n_builds": N_BUILDS,
        "programs": per_program, "aggregate": aggregate,
        "aggregate_pre": aggregate_pre,
        "denom_fail_all": all_denom_fail,
        "control_c0c0": control,
        "string_control_ok": string_ok,
        "verdict": verdict,
        "verdict_pre": verdict_pre,
        "notes": notes,
    }
    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
    with open(os.path.join(out_dir, "RESULTS.md"), "w", encoding="utf-8") as fh:
        fh.write(render_markdown(report))
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="docs/research/const-split-results")
    ap.add_argument("--programs", type=int, default=None,
                    help="limit to the first N corpus programs (smoke test)")
    ap.add_argument("--json", action="store_true", help="print results.json")
    args = ap.parse_args(argv)
    rep = run(args.out, args.programs)
    print(render_markdown(rep))
    if args.json:
        print(json.dumps(rep["aggregate"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
