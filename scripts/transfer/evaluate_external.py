"""Gates for the external tasks (more_itertools.recipes, MIT).

Same two gates as the internal benchmark:

  * evaluator distinguishability — exactly one candidate matches the original
    on evaluator inputs;
  * attacker singleton — exactly one candidate passes the property set.

Reports per cell rather than a single number, because a cell that fails the
evaluator gate is an invalid task and must not be pooled with the rest.
"""

import importlib.util
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.diversity.generator import generate_variant  # noqa: E402
from scripts.transfer.accumulating_attack import AccumulatingAttack  # noqa: E402
from scripts.transfer.external_tasks import TASKS, functions, module_source, source_path  # noqa: E402


def _candidates(code, seed):
    td = tempfile.mkdtemp(prefix="nxk_ext_")
    path = os.path.join(td, "b.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    spec = importlib.util.spec_from_file_location("ext_%d" % seed, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {n: getattr(mod, n) for n in dir(mod)
            if callable(getattr(mod, n)) and not n.startswith("__")}


def main():
    ref = None
    rows = []
    for name, task in TASKS.items():
        src = module_source(name)
        path = source_path(name)
        ref = functions(src, path)
        truth = [ref[name](*args) for args in task["eval_inputs"]]
        for k in (0, 2, 4):
            code = generate_variant(src, k, {"master_seed": 4242})
            fns = _candidates(code, k)
            matches = 0
            for fn in fns.values():
                ok = True
                for args, want in zip(task["eval_inputs"], truth):
                    try:
                        if fn(*args) != want:
                            ok = False
                            break
                    except Exception:
                        ok = False
                        break
                if ok:
                    matches += 1
            td = tempfile.mkdtemp(prefix="nxk_ext_")
            path = os.path.join(td, "b.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
            passing = len(AccumulatingAttack().apply(path, task["props"])["passing"])
            rows.append({"task": name, "k": k, "unique": matches == 1,
                         "singleton": passing == 1})

    valid = sum(1 for r in rows if r["unique"])
    single = sum(1 for r in rows if r["singleton"])
    print("%-12s %-3s %-9s %-10s" % ("task", "k", "unique", "singleton"))
    for r in rows:
        print("%-12s %-3d %-9s %-10s" % (r["task"], r["k"], r["unique"], r["singleton"]))
    print()
    print("cells %d  evaluator-unique %d  attacker-singleton %d" % (len(rows), valid, single))


if __name__ == "__main__":
    main()
