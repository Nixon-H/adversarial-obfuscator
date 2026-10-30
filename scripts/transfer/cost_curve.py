"""Price the attack: cost to identify a function as builds accumulate.

Protocol v3's primary endpoint is a curve: attacker cost to identify a target
as a function of k previously analysed builds of the same program. Its
prediction is falsifiable in both directions -- a flat curve means per-build
diversity buys nothing, a rising one is the first credible evidence that it
does.

This measures it for the spec-directed attacker, whose work has two parts:

  * WRITING the property set, done once per task (the analyst's labour);
  * RUNNING it against a build, done per build (probes + CPU).

If the property set transfers -- and it should, since the specification does
not change when the source is transformed -- the per-build cost is flat in k.
That is a negative result for diversity, and it is the result the study
needs either way.

Cost currency, per protocol v3: CPU-seconds of attacker tooling, plus a
charged cost per target execution. Probes are counted separately because
they are the quantity an analyst actually spends.
"""

import importlib.util
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.diversity.generator import generate_variant  # noqa: E402

EXEC_CHARGE_S = 0.5  # protocol v3: 0.5 s per target execution

TARGET = (
    "def sumselected(values, lo, hi):\n"
    "    total = 0\n"
    "    for v in values:\n"
    "        if lo <= v < hi:\n"
    "            total += v\n"
    "    return total\n"
)
SIBLINGS = [
    ("sibling_a", "    total += v * 2\n"),
    ("sibling_b", None),  # bound flipped below
    ("sibling_c", None),  # start at 1
    ("sibling_d", None),  # returns a list
]


def _module_source():
    parts = [TARGET]
    parts.append(
        "def sibling_a(values, lo, hi):\n"
        "    total = 0\n"
        "    for v in values:\n"
        "        if lo <= v < hi:\n"
        "            total += v * 2\n"
        "    return total\n"
    )
    parts.append(
        "def sibling_b(values, lo, hi):\n"
        "    total = 0\n"
        "    for v in values:\n"
        "        if lo < v <= hi:\n"
        "            total += v\n"
        "    return total\n"
    )
    parts.append(
        "def sibling_c(values, lo, hi):\n"
        "    total = 1\n"
        "    for v in values:\n"
        "        if lo <= v < hi:\n"
        "            total += v\n"
        "    return total\n"
    )
    parts.append(
        "def sibling_d(values, lo, hi):\n"
        "    out = []\n"
        "    for v in values:\n"
        "        if lo <= v < hi:\n"
        "            out.append(v)\n"
        "    return out\n"
    )
    return "\n".join(parts)


PROPERTIES = [
    lambda f: f([1, 2, 3], 0, 10) == 6,
    lambda f: f([], 0, 10) == 0,
    lambda f: f([1, 2, 3], 2, 2) == 0,
    lambda f: f([5], 0, 5) == 0,     # hi exclusive
    lambda f: f([5], 5, 6) == 5,     # lo inclusive
]


def _apply(path, props):
    """Run the frozen property set at one build; return (hits, probes)."""
    spec = importlib.util.spec_from_file_location("cc_%d" % abs(hash(path)), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    names = [n for n in dir(mod) if not n.startswith("__")]
    hits, probes = [], 0
    for name in names:
        fn = getattr(mod, name, None)
        if not callable(fn):
            continue
        ok = True
        for p in props:
            probes += 1
            try:
                if not p(fn):
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            hits.append(name)
    return hits, probes


def main():
    src = _module_source()
    rows = []
    for k in range(0, 6):
        with tempfile.TemporaryDirectory(prefix="nxk_cost_") as td:
            t0 = time.monotonic()
            code = generate_variant(src, k, {"master_seed": 7717})
            build_s = time.monotonic() - t0
            p = os.path.join(td, "b%d.py" % k)
            open(p, "w", encoding="utf-8").write(code)

            t1 = time.monotonic()
            hits, probes = _apply(p, PROPERTIES)
            apply_s = time.monotonic() - t1

            cpu = build_s + apply_s
            rows.append({
                "k": k,
                "identifiable": len(hits) == 1,
                "candidates": None,
                "probes": probes,
                "apply_s": round(apply_s, 4),
                "cpu_s": round(cpu, 4),
                "charged_s": round(cpu + EXEC_CHARGE_S * probes, 3),
            })
    print(json.dumps(rows, indent=2))
    keys = [r["identifiable"] for r in rows]
    probes = [r["probes"] for r in rows]
    print("\nidentifiable at every k: %s" % all(keys))
    print("probes per build: min %d max %d spread %d"
          % (min(probes), max(probes), max(probes) - min(probes)))
    print("charged seconds per build:", [r["charged_s"] for r in rows])


if __name__ == "__main__":
    main()
