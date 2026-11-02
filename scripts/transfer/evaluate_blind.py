"""Gates for the blind (docstring-derived) tasks.

Same two gates as the internal benchmark and the external tasks:

  * evaluator distinguishability -- exactly one candidate in the obfuscated
    module matches the original's return values on the evaluator inputs;
  * attacker singleton -- exactly one candidate in the obfuscated module
    passes the property set.

Reported per task and per build index rather than pooled, for the same reason
as `evaluate_external.py`: a cell that fails the evaluator gate is an invalid
task and must not be averaged in with the rest.

The candidate collector is copied from `evaluate_external.py` deliberately.
Classes are excluded (an exception class is callable and constructs, so every
exception class otherwise counts as a "matching candidate"), and
underscore-prefixed names are excluded (a private alias of the target matches
the evaluator inputs exactly and is not API a caller could pick).
"""

import importlib.util
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.diversity.generator import generate_variant  # noqa: E402
from scripts.transfer.accumulating_attack import AccumulatingAttack  # noqa: E402
from scripts.transfer.blind_tasks import TASKS, functions, module_source, source_path  # noqa: E402


def _candidates(code, seed):
    td = tempfile.mkdtemp(prefix="nxk_blind_")
    path = os.path.join(td, "b.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    spec = importlib.util.spec_from_file_location("blind_%d" % seed, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {n: getattr(mod, n) for n in dir(mod)
            if callable(getattr(mod, n)) and not n.startswith("__")
            and not isinstance(getattr(mod, n), type)
            and not n.startswith("_")}


def _matches(fn, inputs, truth):
    for args, want in zip(inputs, truth):
        try:
            if fn(*args) != want:
                return False
        except Exception:
            return False
    return True


def main():
    rows = []
    for name, task in TASKS.items():
        src = module_source(name)
        path = source_path(name)
        ref = functions(src, path)
        truth = [ref[name](*args) for args in task["eval_inputs"]]
        for k in (0, 2, 4):
            code = generate_variant(src, k, {"master_seed": 4242})
            fns = _candidates(code, k)
            matches = sum(1 for fn in fns.values()
                          if _matches(fn, task["eval_inputs"], truth))
            td = tempfile.mkdtemp(prefix="nxk_blind_")
            opath = os.path.join(td, "b.py")
            with open(opath, "w", encoding="utf-8") as f:
                f.write(code)
            result = AccumulatingAttack().apply(opath, task["props"])
            rows.append({
                "task": name,
                "module": os.path.basename(path),
                "k": k,
                "candidates": len(fns),
                "matches": matches,
                "passing": len(result["passing"]),
                "unique": matches == 1,
                "singleton": len(result["passing"]) == 1,
            })

    valid = sum(1 for r in rows if r["unique"])
    single = sum(1 for r in rows if r["singleton"])
    print("%-13s %-15s %-2s %-5s %-8s %-4s %-8s" %
          ("task", "module", "k", "cand", "matches", "pass", "unique"))
    for r in rows:
        print("%-13s %-15s %-2d %-5d %-8d %-4d %-8s" %
              (r["task"], r["module"], r["k"], r["candidates"],
               r["matches"], r["passing"], r["unique"]))
    print()
    print("cells %d  evaluator-unique %d  attacker-singleton %d" %
          (len(rows), valid, single))
    print()
    per_task = {}
    for r in rows:
        per_task.setdefault(r["task"], []).append(r)
    for task, rs in per_task.items():
        print("%-13s evaluator-unique %d/%d  attacker-singleton %d/%d" %
              (task, sum(r["unique"] for r in rs), len(rs),
               sum(r["singleton"] for r in rs), len(rs)))
    return rows


if __name__ == "__main__":
    main()
