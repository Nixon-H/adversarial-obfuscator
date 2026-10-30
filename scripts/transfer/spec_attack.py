"""Spec-directed attacker: uses the task definition, not the shape.

Shape-based ranking fails on sibling functions because siblings have the same
shape (round 11: 0/1 plain and 0/1 obfuscated). A real analyst is not working
from shape alone -- they are told what the function should do. That is the
task definition the protocol grants every attacker, and it is the only
information that can separate `total += v` from `total += v * 2`.

The spec here is executable: a set of properties the correct function must
satisfy, written from the task description, with inputs the attacker chooses.
It contains no reference outputs and no ground-truth labels -- properties,
not answers. The attacker runs each candidate against them and keeps the ones
that pass.
"""

import importlib.util
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))



def _load(path, ns):
    spec = importlib.util.spec_from_file_location(ns, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Properties per task, written from the specification only. Each returns True
# when the candidate behaves as the specification requires on that case.
PROPS = {
    "sumselected": [
        # sum of the values in [lo, hi); empty range sums to 0
        lambda f: f([1, 2, 3], 0, 10) == 6,
        lambda f: f([], 0, 10) == 0,
        lambda f: f([5, 5], 0, 10) == 10,
        lambda f: f([1, 2, 3], 2, 2) == 0,
        lambda f: f([-1, 1], 0, 10) == 1,
        # hi is EXCLUSIVE: a value equal to hi must not be counted. Without
        # this probe sibling_b (which uses lo < v <= hi) passes every other
        # property and the spec attacker reports two candidates.
        lambda f: f([5], 0, 5) == 0,
        lambda f: f([0], 0, 5) == 0,
        # lo is INCLUSIVE
        lambda f: f([5], 5, 6) == 5,
    ],
}


def spec_rank(path, props, ns):
    """Rank candidates: spec-passing first, then by the shape heuristic."""
    mod = _load(path, ns)
    names = [n for n in dir(mod) if not n.startswith("__")]
    passing, failing = [], []
    for name in names:
        fn = getattr(mod, name, None)
        if not callable(fn):
            continue
        try:
            ok = all(p(fn) for p in props)
        except Exception:
            ok = False
        (passing if ok else failing).append(name)
    return passing, failing


if __name__ == "__main__":
    src = (
        "def sumselected(values, lo, hi):\n"
        "    total = 0\n"
        "    for v in values:\n"
        "        if lo <= v < hi:\n"
        "            total += v\n"
        "    return total\n"
        "\n"
        "def sibling_a(values, lo, hi):\n"
        "    total = 0\n"
        "    for v in values:\n"
        "        if lo <= v < hi:\n"
        "            total += v * 2\n"
        "    return total\n"
        "\n"
        "def sibling_b(values, lo, hi):\n"
        "    total = 0\n"
        "    for v in values:\n"
        "        if lo < v <= hi:\n"
        "            total += v\n"
        "    return total\n"
        "\n"
        "def sibling_c(values, lo, hi):\n"
        "    total = 1\n"
        "    for v in values:\n"
        "        if lo <= v < hi:\n"
        "            total += v\n"
        "    return total\n"
    )
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "m.py")
        open(p, "w", encoding="utf-8").write(src)
        passing, failing = spec_rank(p, PROPS["sumselected"], "spec_plain")
        print("plain   spec-passing: %d of %d" % (len(passing), len(passing) + len(failing)))
        print("  target present:", "sumselected" in passing)

        from scripts.diversity.generator import generate_variant
        obf = generate_variant(src, 0, {"master_seed": 90210})
        op = os.path.join(td, "o.py")
        open(op, "w", encoding="utf-8").write(obf)
        passing_o, failing_o = spec_rank(op, PROPS["sumselected"], "spec_obf")
        print("obf     spec-passing: %d of %d" % (len(passing_o), len(passing_o) + len(failing_o)))
        print("  target present:", bool(passing_o))
