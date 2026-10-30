"""Evaluate the spec attacker with identity and scoring kept apart.

Rounds 14-15 could not attribute nine zero-hit cells because one number mixed
two different questions:

  * WHICH candidate is the target?  Only the evaluator can answer, because
    only the evaluator has the original function.
  * WHAT did the attacker conclude?  That is the property set's verdict.

Scoring the attacker by "how many candidates passed" conflates them: a
candidate can pass for the wrong reason (a sibling that agrees on the tested
inputs) or fail for the wrong reason (a property that raises).

This module answers the two separately and only then compares:

  1. evaluator: run every candidate of the obfuscated build on evaluator
     inputs and keep those whose outputs match the original. That set is the
     truth about identity, and it may contain more than one function -- if a
     sibling happens to agree on those inputs, the evaluator says so instead
     of pretending the task has a unique answer.
  2. attacker: apply the frozen property set, which uses different inputs.
  3. score: does the attacker's passing set overlap the evaluator's truth,
     and does the attacker's ranking of the truth set make sense.

Reporting the two separately is what makes a zero-hit cell attributable.
"""

import importlib.util
import json
import os
import sys
import tempfile
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.diversity.generator import generate_variant  # noqa: E402
from scripts.transfer.tasks import TASKS  # noqa: E402

# Evaluator inputs: DIFFERENT from the attacker's property inputs, so a
# candidate that merely memorised the properties does not pass here.
EVAL_INPUTS = {
    "sumselected": [([1, 2, 3, 4], 1, 4), ([2], 2, 3), ([9, 9], 9, 10)],
    "countchars": [("abcabc", "b"), ("zzz", "z"), ("q", "x")],
    "clamp01": [(-0.5,), (1.5,), (0.25,)],
    "is_even": [(10,), (7,), (0,)],
    "maxlen": [(["aa", "b"],), ([],), ([""],)],
    "running_total": [([2, 3],), ([],), ([5],)],
    # (0, -1) is required: sibling s3 uses (a >= 0) where the target uses
    # (a > 0), so the two differ only when a is zero. Without a zero in the
    # evaluator inputs the task is ambiguous by construction.
    "signdiff": [(2, -3), (-2, -3), (2, 3), (0, -1)],
    "first_negative": [([1, 2, -3],), ([4, 5],), ([0, -1],)],
    # (5, 5) is required: sibling ca1 uses >= where the target uses >, so the
    # two differ only when a value equals the limit.
    "count_above": [([1, 2, 3], 1), ([], 5), ([5], 5)],
}


def _load(path, ns):
    spec = importlib.util.spec_from_file_location(ns, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _functions(mod):
    return {n: getattr(mod, n) for n in dir(mod)
            if isinstance(getattr(mod, n), types.FunctionType)}


def _behaviour(fn, inputs):
    try:
        return [fn(*a) for a in inputs]
    except Exception:
        return None


def evaluate(task_name, k, seed):
    task = TASKS[task_name]
    src = task["target"] + "\n" + "\n".join(task["siblings"])
    code = generate_variant(src, k, {"master_seed": seed})

    ref_ns = {}
    exec(task["target"], ref_ns)
    ref = ref_ns[task_name]
    truth_vals = _behaviour(ref, EVAL_INPUTS[task_name])

    with tempfile.TemporaryDirectory(prefix="nxk_eval_") as td:
        p = os.path.join(td, "b.py")
        open(p, "w", encoding="utf-8").write(code)
        mod = _load(p, "eval_%s_%d_%d" % (task_name, k, seed))
        funcs = _functions(mod)

        # 1. identity, decided by the evaluator alone
        truth = []
        for name, fn in funcs.items():
            vals = _behaviour(fn, EVAL_INPUTS[task_name])
            if vals is not None and vals == truth_vals:
                truth.append(name)

        # 2. the attacker's verdict, on its own inputs
        passing = []
        for name, fn in funcs.items():
            ok = True
            for prop in task["props"]:
                try:
                    if not prop(fn):
                        ok = False
                        break
                except Exception:
                    ok = False
                    break
            if ok:
                passing.append(name)

        # 3. comparison
        hit = bool(set(passing) & set(truth))
        return {
            "task": task_name, "k": k, "seed": seed,
            "n_functions": len(funcs),
            "truth": len(truth),
            "passing": len(passing),
            "attacker_hit": hit,
            "unique": len(truth) == 1,
        }


def main():
    rows = []
    for name in TASKS:
        for k, seed in ((0, 5501), (2, 5503), (4, 5505)):
            rows.append(evaluate(name, k, seed))
    print(json.dumps(rows, indent=1))
    n = len(rows)
    uniq = sum(1 for r in rows if r["unique"])
    hits = sum(1 for r in rows if r["attacker_hit"])
    print("\ncells: %d   evaluator-unique identity: %d   attacker hit: %d"
          % (n, uniq, hits))
    amb = [r for r in rows if not r["unique"]]
    print("cells where the evaluator itself cannot name a unique target: %d"
          % len(amb))


if __name__ == "__main__":
    main()
