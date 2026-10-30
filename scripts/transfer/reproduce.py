"""Regenerate every number the research documents report.

The manuscript cites figures from six documents. This regenerates them in one
run and prints a comparison against the values the documents state, so a reader
can check the paper without trusting either the prose or this script.

Every measurement here is the same code path the documents used. If a number
moves, either the build changed or a document is stale; the comparison column
says which values the documents claim.

    python3 scripts/transfer/reproduce.py

Deterministic: all builds take an explicit seed, all tasks are in the
repository, no network is used.
"""

import importlib.util
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

FAM_A = ["rename", "dead_code", "mba", "cfg_flatten"]
FAM_B = ["rename", "dead_code", "opaque_pred", "string_encode"]
FAM_C = ["rename", "mba", "string_encode"]


def _score(code, props):
    td = tempfile.mkdtemp(prefix="nxk_rep_")
    p = os.path.join(td, "b.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write(code)
    spec = importlib.util.spec_from_file_location("rep_%d" % abs(hash(code[:200])), p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    funcs = {n: getattr(mod, n) for n in dir(mod)
             if isinstance(getattr(mod, n), types.FunctionType)}
    passing = []
    for name, fn in funcs.items():
        try:
            if all(pr(fn) for pr in props):
                passing.append(name)
        except Exception:
            pass
    return passing


def _tasks():
    out = []
    for name, t in SYNTH.items():
        out.append(("synth", name, t["target"] + "\n" + "\n".join(t["siblings"]), t["props"]))
    for name, t in REAL.items():
        out.append(("real", name, module_source(name), t["props"]))
    return out


def table_singleton():
    """Documents claim 51 cells, zero non-singleton."""
    cells = non_singleton = 0
    for label, name, src, props in _tasks():
        for k in (0, 2, 4):
            code = generate_variant(src, k, {"master_seed": 4242})
            cells += 1
            if len(_score(code, props)) != 1:
                non_singleton += 1
    return "singleton", cells, non_singleton, "51 cells, 0 non-singleton"


def table_module_size():
    """Documents claim 2.0 probes at one candidate, 8.3 at four."""
    means = {}
    for n in range(0, 4):
        probes = []
        for name, t in SYNTH.items():
            src = t["target"] + "\n" + "\n".join(t["siblings"][:n])
            code = generate_variant(src, 4, {"master_seed": 4242})
            td = tempfile.mkdtemp(prefix="nxk_rep_")
            p = os.path.join(td, "b.py")
            with open(p, "w", encoding="utf-8") as f:
                f.write(code)
            probes.append(AccumulatingAttack().apply(p, t["props"])["probes"])
        means[n + 1] = round(statistics.mean(probes), 1)
    return "module-size", means, None, "2.0 at 1 candidate, 8.6 at 4"


def table_diversity():
    """Documents claim B-vs-C is 0.00 on both families."""
    out = {}
    for label, f1, f2 in (("A-vs-B", FAM_A, FAM_B), ("A-vs-C", FAM_A, FAM_C),
                          ("B-vs-C", FAM_B, FAM_C)):
        diffs = []
        for kind, name, src, props in _tasks():
            def probes(fam, seed):
                code = generate_variant(src, 4, {"master_seed": seed, "pass_sets": [fam]})
                td = tempfile.mkdtemp(prefix="nxk_rep_")
                p = os.path.join(td, "b.py")
                with open(p, "w", encoding="utf-8") as f:
                    f.write(code)
                return AccumulatingAttack().apply(p, props)["probes"]
            seed_only = [probes(f1, s) for s in (11, 22, 33)]
            varying = [probes(f1, 11), probes(f2, 22), probes(f1, 33)]
            diffs.append(statistics.mean(varying) - statistics.mean(seed_only))
        out[label] = round(statistics.mean(diffs), 2)
    return "diversity", out, None, "A-vs-B +0.33, A-vs-C +0.33, B-vs-C 0.00"


def table_fixed_build():
    """Documents claim probes are constant in experience on a fixed build."""
    t = SYNTH["sumselected"]
    src = t["target"] + "\n" + "\n".join(t["siblings"])
    target = None
    series = []
    for k in (0, 1, 2, 4, 6):
        a = AccumulatingAttack()
        for j in range(k):
            code = generate_variant(src, 4, {"master_seed": 7000 + j})
            td = tempfile.mkdtemp(prefix="nxk_rep_")
            p = os.path.join(td, "b.py")
            with open(p, "w", encoding="utf-8") as f:
                f.write(code)
            a.observe(p)
        if target is None:
            code = generate_variant(src, 4, {"master_seed": 4242})
            td = tempfile.mkdtemp(prefix="nxk_rep_")
            target = os.path.join(td, "b.py")
            with open(target, "w", encoding="utf-8") as f:
                f.write(code)
        series.append(a.apply(target, t["props"])["probes"])
    return "fixed-build", series, None, "9 9 9 9 9"



def table_fault_control():
    """Documents claim the counter moves from 9 to 11 probes on a fault."""
    t = SYNTH["sumselected"]
    src = t["target"] + "\n" + "\n".join(t["siblings"])

    def probes(code):
        td = tempfile.mkdtemp(prefix="nxk_rep_")
        p = os.path.join(td, "b.py")
        with open(p, "w", encoding="utf-8") as f:
            f.write(code)
        return AccumulatingAttack().apply(p, t["props"])["probes"]

    good = probes(generate_variant(src, 4, {"master_seed": 4242}))
    faulty = probes(generate_variant(src.replace("lo <= v < hi", "lo <= v <= hi"),
                                     4, {"master_seed": 4242}))
    return "fault-control", {"correct": good, "fault": faulty}, None, "9 then 11 probes"


def table_authoring():
    """Documents claim 33 properties across the synthetic tasks, 1-2 essential."""
    total = sum(len(t["props"]) for t in SYNTH.values())
    return "authoring", {"properties": total}, None, "38 properties across 9 tasks"


def main():
    rows = [table_singleton(), table_module_size(), table_diversity(),
            table_fixed_build(), table_fault_control(), table_authoring()]
    width = max(len(r[0]) for r in rows)
    print("%-*s | %-58s | documents claim" % (width, "measurement", "regenerated"))
    print("-" * (width + 62 + 40))
    for name, got, _extra, claim in rows:
        print("%-*s | %-58s | %s" % (width, name, str(got)[:58], claim))
    print()
    print("If 'regenerated' differs from 'documents claim', either the build")
    print("changed or the document is stale. Both are worth a round.")


if __name__ == "__main__":
    main()
